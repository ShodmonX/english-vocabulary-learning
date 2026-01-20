from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Package, PackageChangeLog
from app.services.i18n import t


class PackageError(Exception):
    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message


@dataclass(frozen=True)
class PackageDTO:
    package_key: str
    seconds: int
    approx_attempts_5s: int
    manual_price_uzs: int
    stars_price: int
    is_active: bool


async def list_packages(session: AsyncSession) -> list[PackageDTO]:
    result = await session.execute(select(Package).order_by(Package.id))
    return [
        PackageDTO(
            package_key=item.package_key,
            seconds=item.seconds,
            approx_attempts_5s=item.approx_attempts_5s,
            manual_price_uzs=item.manual_price_uzs,
            stars_price=item.stars_price,
            is_active=item.is_active,
        )
        for item in result.scalars().all()
    ]


async def get_package(session: AsyncSession, package_key: str) -> Package | None:
    result = await session.execute(
        select(Package).where(Package.package_key == package_key.upper())
    )
    return result.scalar_one_or_none()


async def get_active_package(session: AsyncSession, package_key: str) -> Package | None:
    result = await session.execute(
        select(Package).where(
            Package.package_key == package_key.upper(),
            Package.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def validate_manual_price(value: int) -> None:
    if value <= 0 or value > 10_000_000:
        raise PackageError(
            "Manual price out of range", user_message=t("packages.price_invalid")
        )


def validate_seconds(value: int) -> None:
    if value <= 0 or value > 1_000_000:
        raise PackageError(
            "Seconds out of range", user_message=t("packages.seconds_invalid")
        )


def validate_stars_price(value: int) -> None:
    if value <= 0 or value > 100_000:
        raise PackageError(
            "Stars price out of range", user_message=t("packages.stars_invalid")
        )


async def update_package_prices(
    session: AsyncSession,
    package_key: str,
    *,
    seconds: int | None = None,
    manual_price_uzs: int | None = None,
    stars_price: int | None = None,
    is_active: bool | None = None,
    admin_id: int,
    reason: str | None = None,
) -> Package:
    result = await session.execute(
        select(Package).where(Package.package_key == package_key.upper()).with_for_update()
    )
    package = result.scalar_one_or_none()
    if not package:
        raise PackageError("Package not found", user_message=t("packages.not_found"))
    if seconds is not None:
        validate_seconds(seconds)
    if manual_price_uzs is not None:
        validate_manual_price(manual_price_uzs)
    if stars_price is not None:
        validate_stars_price(stars_price)
    old_seconds = package.seconds
    old_attempts = package.approx_attempts_5s
    old_manual = package.manual_price_uzs
    old_stars = package.stars_price
    old_active = package.is_active
    if seconds is not None:
        package.seconds = seconds
        package.approx_attempts_5s = max(1, int(ceil(seconds / 5)))
    if manual_price_uzs is not None:
        package.manual_price_uzs = manual_price_uzs
    if stars_price is not None:
        package.stars_price = stars_price
    if is_active is not None:
        package.is_active = is_active
    package.updated_by_admin_id = admin_id
    session.add(
        PackageChangeLog(
            admin_id=admin_id,
            package_key=package.package_key,
            old_seconds=old_seconds,
            new_seconds=package.seconds,
            old_approx_attempts_5s=old_attempts,
            new_approx_attempts_5s=package.approx_attempts_5s,
            old_manual_price_uzs=old_manual,
            new_manual_price_uzs=package.manual_price_uzs,
            old_stars_price=old_stars,
            new_stars_price=package.stars_price,
            old_is_active=old_active,
            new_is_active=package.is_active,
            reason=reason,
        )
    )
    await session.commit()
    await session.refresh(package)
    return package


async def set_package_active(
    session: AsyncSession, package_key: str, is_active: bool, admin_id: int, reason: str | None = None
) -> Package:
    return await update_package_prices(
        session,
        package_key,
        is_active=is_active,
        admin_id=admin_id,
        reason=reason,
    )
