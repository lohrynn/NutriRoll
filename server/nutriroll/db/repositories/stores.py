"""Stores repository — async CRUD for stores and supermarket prices."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.store import StoreRow, SupermarketPriceRow
from nutriroll.domain.store import Store, SupermarketPrice


def _store_to_domain(row: StoreRow) -> Store:
    return Store(id=row.id, name=row.name, location=row.location, is_primary=row.is_primary)


def _price_to_domain(row: SupermarketPriceRow) -> SupermarketPrice:
    return SupermarketPrice(
        id=row.id,
        store_id=row.store_id,
        component_id=row.component_id,
        pack_size=row.pack_size,
        pack_price=row.pack_price,
        updated_at=row.updated_at,
    )


class StoresRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_stores(self) -> list[Store]:
        stmt = select(StoreRow).order_by(StoreRow.is_primary.desc(), StoreRow.name)
        result = await self._session.execute(stmt)
        return [_store_to_domain(r) for r in result.scalars().all()]

    async def get_store(self, store_id: UUID) -> Store | None:
        row = await self._session.get(StoreRow, store_id)
        return _store_to_domain(row) if row is not None else None

    async def create_store(self, store: Store) -> Store:
        if store.is_primary:
            await self._session.execute(
                update(StoreRow).values(is_primary=False).where(StoreRow.is_primary)
            )
        row = StoreRow(
            id=store.id,
            name=store.name,
            location=store.location,
            is_primary=store.is_primary,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _store_to_domain(row)

    async def update_store(self, store: Store) -> Store | None:
        row = await self._session.get(StoreRow, store.id)
        if row is None:
            return None
        if store.is_primary and not row.is_primary:
            await self._session.execute(
                update(StoreRow).values(is_primary=False).where(StoreRow.is_primary)
            )
        row.name = store.name
        row.location = store.location
        row.is_primary = store.is_primary
        await self._session.commit()
        await self._session.refresh(row)
        return _store_to_domain(row)

    async def delete_store(self, store_id: UUID) -> bool:
        row = await self._session.get(StoreRow, store_id)
        if row is None:
            return False
        await self._session.execute(
            delete(SupermarketPriceRow).where(SupermarketPriceRow.store_id == store_id)
        )
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def list_prices(self, store_id: UUID) -> list[SupermarketPrice]:
        stmt = (
            select(SupermarketPriceRow)
            .where(SupermarketPriceRow.store_id == store_id)
            .order_by(SupermarketPriceRow.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_price_to_domain(r) for r in result.scalars().all()]

    async def get_price(self, store_id: UUID, component_id: UUID) -> SupermarketPrice | None:
        stmt = select(SupermarketPriceRow).where(
            SupermarketPriceRow.store_id == store_id,
            SupermarketPriceRow.component_id == component_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _price_to_domain(row) if row is not None else None

    async def upsert_price(self, price: SupermarketPrice) -> SupermarketPrice:
        existing = await self.get_price(price.store_id, price.component_id)
        if existing is None:
            row = SupermarketPriceRow(
                id=price.id,
                store_id=price.store_id,
                component_id=price.component_id,
                pack_size=price.pack_size,
                pack_price=price.pack_price,
            )
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
            return _price_to_domain(row)
        # update existing row
        await self._session.execute(
            update(SupermarketPriceRow)
            .where(SupermarketPriceRow.id == existing.id)
            .values(pack_size=price.pack_size, pack_price=price.pack_price)
        )
        await self._session.commit()
        refreshed = await self._session.get(SupermarketPriceRow, existing.id)
        assert refreshed is not None
        return _price_to_domain(refreshed)

    async def delete_price(self, price_id: UUID) -> bool:
        row = await self._session.get(SupermarketPriceRow, price_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
