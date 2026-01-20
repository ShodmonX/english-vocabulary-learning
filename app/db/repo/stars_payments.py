from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreditLedger, StarsPayment
from app.db.repo.credits import _apply_refill_if_due, _get_or_create_balance_for_update, _now_utc
from app.db.repo.packages import get_package


async def create_pending_payment(
    session: AsyncSession, user_id: int, package_id: str
) -> StarsPayment:
    package = await get_package(session, package_id)
    if not package or not package.is_active:
        raise ValueError("Package inactive")
    payload = f"stars:{user_id}:{package_id}:{uuid4().hex}"
    payment = StarsPayment(
        user_id=user_id,
        package_id=package_id,
        payload=payload,
        amount_stars=package.stars_price,
        status="pending",
    )
    session.add(payment)
    session.add(
        CreditLedger(
            user_id=user_id,
            event_type="stars_payment_pending",
            basic_delta_seconds=0,
            topup_delta_seconds=0,
            package_id=package_id,
            provider="telegram_stars",
            amount_stars=package.stars_price,
            provider_payment_id=payload,
        )
    )
    await session.commit()
    await session.refresh(payment)
    return payment


async def mark_failed(
    session: AsyncSession, payload: str, status: str = "failed", raw_update: dict | None = None
) -> None:
    result = await session.execute(select(StarsPayment).where(StarsPayment.payload == payload))
    payment = result.scalar_one_or_none()
    if not payment or payment.status == "credited":
        return
    payment.status = status
    payment.raw_update = raw_update
    await session.commit()


async def credit_paid_payment(
    session: AsyncSession,
    payload: str,
    telegram_charge_id: str | None = None,
    raw_update: dict | None = None,
) -> int | None:
    now_utc = _now_utc()
    async with session.begin():
        result = await session.execute(
            select(StarsPayment).where(StarsPayment.payload == payload).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return None
        if payment.status == "credited":
            return 0
        if payment.status == "pending":
            payment.status = "paid"
            payment.paid_at = now_utc
        payment.telegram_charge_id = telegram_charge_id or payment.telegram_charge_id
        payment.raw_update = raw_update or payment.raw_update
        package = await get_package(session, payment.package_id)
        if not package:
            return None
        balance = await _get_or_create_balance_for_update(session, payment.user_id, now_utc)
        await _apply_refill_if_due(session, balance, now_utc)
        balance.topup_remaining_seconds += package.seconds
        balance.updated_at = now_utc
        session.add(
            CreditLedger(
                user_id=payment.user_id,
                event_type="stars_payment_success",
                basic_delta_seconds=0,
                topup_delta_seconds=package.seconds,
                package_id=payment.package_id,
                provider="telegram_stars",
                provider_payment_id=telegram_charge_id or payment.payload,
                amount_stars=payment.amount_stars,
                meta={"payload": payment.payload},
            )
        )
        payment.status = "credited"
        payment.credited_at = now_utc
    await session.commit()
    return package.seconds


async def reprocess_paid(session: AsyncSession) -> int:
    result = await session.execute(select(StarsPayment).where(StarsPayment.status == "paid"))
    payments = list(result.scalars().all())
    processed = 0
    for payment in payments:
        seconds = await credit_paid_payment(
            session,
            payment.payload,
            telegram_charge_id=payment.telegram_charge_id,
            raw_update=payment.raw_update,
        )
        if seconds:
            processed += 1
    return processed
