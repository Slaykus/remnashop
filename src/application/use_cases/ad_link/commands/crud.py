from dataclasses import dataclass
from typing import Optional

from loguru import logger

from src.application.common import Interactor
from src.application.common.dao.ad_link import AdLinkDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.dto.ad_link import AdLinkDto


@dataclass(frozen=True)
class CreateAdLinkDto:
    name: str
    code: str
    bonus_points: int = 0
    bonus_days: int = 0
    bonus_discount_pct: int = 0


class CreateAdLink(Interactor[CreateAdLinkDto, AdLinkDto]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, uow: UnitOfWork, ad_link_dao: AdLinkDao) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao

    async def _execute(self, actor: UserDto, data: CreateAdLinkDto) -> AdLinkDto:
        link = await self.ad_link_dao.create(
            name=data.name,
            code=data.code,
            bonus_points=data.bonus_points,
            bonus_days=data.bonus_days,
            bonus_discount_pct=data.bonus_discount_pct,
        )
        await self.uow.commit()
        logger.info(f"[AdLink] Admin {actor.telegram_id} created link '{data.code}'")
        return link


@dataclass(frozen=True)
class UpdateAdLinkDto:
    link: AdLinkDto


class UpdateAdLink(Interactor[UpdateAdLinkDto, AdLinkDto]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, uow: UnitOfWork, ad_link_dao: AdLinkDao) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao

    async def _execute(self, actor: UserDto, data: UpdateAdLinkDto) -> AdLinkDto:
        updated = await self.ad_link_dao.update(data.link)
        await self.uow.commit()
        logger.info(f"[AdLink] Admin {actor.telegram_id} updated link id={data.link.id}")
        return updated


@dataclass(frozen=True)
class DeleteAdLinkDto:
    link_id: int


class DeleteAdLink(Interactor[DeleteAdLinkDto, None]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, uow: UnitOfWork, ad_link_dao: AdLinkDao) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao

    async def _execute(self, actor: UserDto, data: DeleteAdLinkDto) -> None:
        await self.ad_link_dao.delete(data.link_id)
        await self.uow.commit()
        logger.info(f"[AdLink] Admin {actor.telegram_id} deleted link id={data.link_id}")
