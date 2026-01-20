from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import CreditBalance, CreditLedger


class CreditError(Exception):
    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message


@dataclass(frozen=True)
class CreditReservation:
    ledger_id: int
    charge_seconds: int
    basic_delta_seconds: int
    topup_delta_seconds: int


def _now_utc() -> datetime:
    return datetime.utcnow()


def _next_refill_at(now_utc: datetime) -> datetime:
    tz = ZoneInfo(settings.timezone)
    now_local = now_utc.replace(tzinfo=timezone.utc).astimezone(tz)
    year = now_local.year + (1 if now_local.month == 12 else 0)
    month = 1 if now_local.month == 12 else now_local.month + 1
    next_local = datetime(year, month, 1, 0, 0, 0, tzinfo=tz)
    return next_local.astimezone(timezone.utc).replace(tzinfo=None)


async def _get_or_create_balance_for_update(
    session: AsyncSession, user_id: int, now_utc: datetime
) -> CreditBalance:
    result = await session.execute(
        select(CreditBalance)
        .where(CreditBalance.user_id == user_id)
        .with_for_update()
    )
    balance = result.scalar_one_or_none()
    if balance:
        return balance
    balance = CreditBalance(
        user_id=user_id,
        basic_remaining_seconds=settings.basic_monthly_seconds,
        topup_remaining_seconds=0,
        next_basic_refill_at=_next_refill_at(now_utc),
    )
    session.add(balance)
    session.add(
        CreditLedger(
            user_id=user_id,
            event_type="basic_refill",
            basic_delta_seconds=settings.basic_monthly_seconds,
            topup_delta_seconds=0,
            reason="initial",
        )
    )
    await session.flush()
    return balance


async def _apply_refill_if_due(
    session: AsyncSession, balance: CreditBalance, now_utc: datetime
) -> None:
    if now_utc < balance.next_basic_refill_at:
        return
    previous = balance.basic_remaining_seconds
    balance.basic_remaining_seconds = settings.basic_monthly_seconds
    balance.next_basic_refill_at = _next_refill_at(now_utc)
    delta = balance.basic_remaining_seconds - previous
    session.add(
        CreditLedger(
            user_id=balance.user_id,
            event_type="basic_refill",
            basic_delta_seconds=delta,
            topup_delta_seconds=0,
            reason="monthly",
        )
    )


def _calculate_charge_seconds(audio_duration_seconds: int) -> int:
    if audio_duration_seconds <= 0:
        return 0
    return max(1, int(ceil(audio_duration_seconds)))


def _out_of_credit_message(balance: CreditBalance) -> str:
    return (
        "Kredit tugadi. Iltimos, keyinroq yana urinib ko‘ring yoki admin’dan kredit so‘rang."
        f"\nBASIC: {balance.basic_remaining_seconds}s"
        f"\nTOPUP: {balance.topup_remaining_seconds}s"
    )


async def reserve_credits(
    session: AsyncSession,
    user_id: int,
    audio_duration_seconds: int,
    provider: str | None = None,
) -> CreditReservation:
    now_utc = _now_utc()
    balance = await _get_or_create_balance_for_update(session, user_id, now_utc)
    await _apply_refill_if_due(session, balance, now_utc)
    charge_seconds = _calculate_charge_seconds(audio_duration_seconds)
    if charge_seconds <= 0:
        raise CreditError("Invalid audio duration", user_message="⚠️ Audio davomiyligi noto‘g‘ri.")
    total_available = balance.basic_remaining_seconds + balance.topup_remaining_seconds
    if total_available < charge_seconds:
        raise CreditError("Insufficient credits", user_message=_out_of_credit_message(balance))
    basic_deduct = min(balance.basic_remaining_seconds, charge_seconds)
    remaining = charge_seconds - basic_deduct
    topup_deduct = min(balance.topup_remaining_seconds, remaining)
    balance.basic_remaining_seconds -= basic_deduct
    balance.topup_remaining_seconds -= topup_deduct
    balance.updated_at = now_utc
    ledger = CreditLedger(
        user_id=user_id,
        event_type="charge",
        basic_delta_seconds=-basic_deduct,
        topup_delta_seconds=-topup_deduct,
        charge_seconds=charge_seconds,
        audio_duration_seconds=audio_duration_seconds,
        provider=provider,
    )
    session.add(ledger)
    await session.flush()
    await session.commit()
    return CreditReservation(
        ledger_id=ledger.id,
        charge_seconds=charge_seconds,
        basic_delta_seconds=-basic_deduct,
        topup_delta_seconds=-topup_deduct,
    )


async def finalize_charge(
    session: AsyncSession, ledger_id: int, provider_request_id: str | None = None
) -> None:
    await session.execute(
        update(CreditLedger)
        .where(CreditLedger.id == ledger_id)
        .values(provider_request_id=provider_request_id)
    )
    await session.commit()


async def refund_charge(
    session: AsyncSession,
    ledger_id: int,
    reason: str | None = None,
    provider_request_id: str | None = None,
) -> None:
    result = await session.execute(
        select(CreditLedger).where(CreditLedger.id == ledger_id).with_for_update()
    )
    charge = result.scalar_one_or_none()
    if not charge or charge.event_type != "charge":
        return
    refund_marker = f"charge:{ledger_id}"
    existing = await session.execute(
        select(CreditLedger.id).where(
            CreditLedger.user_id == charge.user_id,
            CreditLedger.event_type == "refund",
            CreditLedger.reason == refund_marker,
        )
    )
    if existing.scalar_one_or_none():
        return
    balance_result = await session.execute(
        select(CreditBalance)
        .where(CreditBalance.user_id == charge.user_id)
        .with_for_update()
    )
    balance = balance_result.scalar_one_or_none()
    if not balance:
        balance = await _get_or_create_balance_for_update(session, charge.user_id, _now_utc())
    balance.basic_remaining_seconds += -charge.basic_delta_seconds
    balance.topup_remaining_seconds += -charge.topup_delta_seconds
    balance.updated_at = _now_utc()
    session.add(
        CreditLedger(
            user_id=charge.user_id,
            event_type="refund",
            basic_delta_seconds=-charge.basic_delta_seconds,
            topup_delta_seconds=-charge.topup_delta_seconds,
            charge_seconds=charge.charge_seconds,
            audio_duration_seconds=charge.audio_duration_seconds,
            provider=charge.provider,
            provider_request_id=provider_request_id or charge.provider_request_id,
            reason=refund_marker if not reason else f"{refund_marker} {reason}",
        )
    )
    await session.commit()


async def add_topup(
    session: AsyncSession,
    user_id: int,
    seconds: int,
    admin_id: int,
    reason: str | None = None,
    *,
    provider: str = "admin",
    package_id: str | None = None,
    provider_payment_id: str | None = None,
    amount_stars: int | None = None,
    meta: dict | None = None,
) -> None:
    if seconds <= 0:
        raise CreditError("Topup seconds must be positive")
    now_utc = _now_utc()
    balance = await _get_or_create_balance_for_update(session, user_id, now_utc)
    await _apply_refill_if_due(session, balance, now_utc)
    balance.topup_remaining_seconds += seconds
    balance.updated_at = now_utc
    session.add(
        CreditLedger(
            user_id=user_id,
            event_type="topup_add",
            basic_delta_seconds=0,
            topup_delta_seconds=seconds,
            admin_id=admin_id,
            reason=reason,
            provider=provider,
            package_id=package_id,
            provider_payment_id=provider_payment_id,
            amount_stars=amount_stars,
            meta=meta,
        )
    )
    await session.commit()


async def get_profile_summary(session: AsyncSession, user_id: int) -> dict[str, object]:
    now_utc = _now_utc()
    balance = await _get_or_create_balance_for_update(session, user_id, now_utc)
    await _apply_refill_if_due(session, balance, now_utc)
    await session.commit()
    month_start = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage = (
        await session.execute(
            select(func.coalesce(func.sum(CreditLedger.charge_seconds), 0)).where(
                CreditLedger.user_id == user_id,
                CreditLedger.event_type == "charge",
                CreditLedger.created_at >= month_start,
            )
        )
    ).scalar_one()
    return {
        "basic_remaining_seconds": balance.basic_remaining_seconds,
        "topup_remaining_seconds": balance.topup_remaining_seconds,
        "next_basic_refill_at": balance.next_basic_refill_at,
        "monthly_used_seconds": int(usage or 0),
    }


async def get_credit_snapshot(session: AsyncSession, user_id: int) -> dict[str, object]:
    now_utc = _now_utc()
    balance = await _get_or_create_balance_for_update(session, user_id, now_utc)
    await _apply_refill_if_due(session, balance, now_utc)
    await session.commit()
    return {
        "basic_remaining_seconds": balance.basic_remaining_seconds,
        "topup_remaining_seconds": balance.topup_remaining_seconds,
        "next_basic_refill_at": balance.next_basic_refill_at,
    }
