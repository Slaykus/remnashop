from typing import Final

from src.application.common import Interactor

from .commands.management import (
    AdminDeleteDevices,
    DeleteUserAllDevices,
    DeleteUserDevice,
    ReissueSubscription,
    ReissueUserSubscription,
    ResetUserTraffic,
)
from .commands.synchronization import SyncAllUsersFromBot, SyncAllUsersFromPanel, SyncRemnaUser
from .queries.squads import GetExternalSquads, GetInternalSquads

REMNAWAVE_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    SyncAllUsersFromBot,
    SyncAllUsersFromPanel,
    SyncRemnaUser,
    DeleteUserDevice,
    DeleteUserAllDevices,
    AdminDeleteDevices,
    ResetUserTraffic,
    ReissueSubscription,
    ReissueUserSubscription,
    GetInternalSquads,
    GetExternalSquads,
)
