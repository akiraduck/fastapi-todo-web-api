from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import List, Optional

from app.models.models_db import Currency
from app.models.schemas import CurrencyCreate, CurrencyUpdate

logger = logging.getLogger(__name__)


class CurrencyService:    
    @staticmethod
    async def get_all(session: AsyncSession) -> List[Currency]:
        try:
            result = await session.execute(
                select(Currency).where(Currency.is_active == True)
            )
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения валют: {e}")
            return []
    
    @staticmethod
    async def get_by_id(session: AsyncSession, currency_id: int) -> Optional[Currency]:
        try:
            result = await session.execute(
                select(Currency).where(Currency.id == currency_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения валюты по id: {e}")
            return None
    
    @staticmethod
    async def create(session: AsyncSession, currency: CurrencyCreate) -> Optional[Currency]:
        try:
            db_currency = Currency(
                base=currency.base.upper(),
                target=currency.target.upper(),
                current_rate=currency.current_rate
            )
            session.add(db_currency)
            await session.commit()
            await session.refresh(db_currency)
            logger.info(f"Создана валюта: {db_currency}")
            return db_currency
        except SQLAlchemyError as e:
            logger.error(f"Ошибка создания валюты: {e}")
            await session.rollback()
            return None
    
    @staticmethod
    async def update(
        session: AsyncSession,
        currency_id: int,
        currency: CurrencyUpdate
    ) -> Optional[Currency]:
        try:
            result = await session.execute(
                select(Currency).where(Currency.id == currency_id)
            )
            db_currency = result.scalar_one_or_none()
            
            if not db_currency:
                return None
            
            if currency.base:
                db_currency.base = currency.base.upper()
            if currency.target:
                db_currency.target = currency.target.upper()
            if currency.current_rate:
                db_currency.current_rate = currency.current_rate
            
            await session.commit()
            await session.refresh(db_currency)
            logger.info(f"Обновленная валюта: {db_currency}")
            return db_currency
        except SQLAlchemyError as e:
            logger.error(f"Ошибка обновления валюты: {e}")
            await session.rollback()
            return None
    
    @staticmethod
    async def delete(session: AsyncSession, currency_id: int) -> bool:
        try:
            result = await session.execute(
                select(Currency).where(Currency.id == currency_id)
            )
            db_currency = result.scalar_one_or_none()
            
            if not db_currency:
                return False
            
            db_currency.is_active = False
            await session.commit()
            logger.info(f"Удалена валюта с id: {currency_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Ошибка удаления валюты: {e}")
            await session.rollback()
            return False
    
    @staticmethod
    async def get_by_pair(
        session: AsyncSession,
        base: str,
        target: str
    ) -> Optional[Currency]:
        try:
            result = await session.execute(
                select(Currency).where(
                    (Currency.base == base.upper()) &
                    (Currency.target == target.upper()) &
                    (Currency.is_active == True)
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка получения валютной пары: {e}")
            return None
