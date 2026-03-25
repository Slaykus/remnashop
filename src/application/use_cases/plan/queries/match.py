from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from loguru import logger

from src.application.common import Interactor
from src.application.dto import PlanDto, PlanSnapshotDto, UserDto

if TYPE_CHECKING:
    from src.application.dto import SubscriptionDto


@dataclass(frozen=True)
class MatchPlanDto:
    plan_snapshot: PlanSnapshotDto
    plans: list[PlanDto]
    subscription: Optional["SubscriptionDto"] = None


class MatchPlan(Interactor[MatchPlanDto, Optional[PlanDto]]):
    required_permission = None

    async def _execute(self, actor: UserDto, data: MatchPlanDto) -> Optional[PlanDto]:
        snapshot = data.plan_snapshot

        for plan in data.plans:
            if self._is_plan_equal(snapshot, plan, data.subscription):
                return plan

        logger.warning(f"{actor.log} No matching plan found for snapshot '{snapshot.id}'")
        return None

    def _is_plan_equal(
        self,
        snapshot: PlanSnapshotDto,
        plan: PlanDto,
        subscription: Optional["SubscriptionDto"],
    ) -> bool:
        is_imported = snapshot.id == -1
        if not is_imported and snapshot.id != plan.id:
            return False

        # For imported users use the subscription's up-to-date values,
        # because plan_snapshot is never updated after the initial sync.
        if is_imported and subscription is not None:
            device_limit = subscription.device_limit
            internal_squads = subscription.internal_squads
            traffic_limit = subscription.traffic_limit
            traffic_limit_strategy = subscription.traffic_limit_strategy
            external_squad = subscription.external_squad
        else:
            device_limit = snapshot.device_limit
            internal_squads = snapshot.internal_squads
            traffic_limit = snapshot.traffic_limit
            traffic_limit_strategy = snapshot.traffic_limit_strategy
            external_squad = snapshot.external_squad

        return (
            snapshot.type == plan.type
            and traffic_limit == plan.traffic_limit
            and device_limit == plan.device_limit
            and traffic_limit_strategy == plan.traffic_limit_strategy
            and sorted(internal_squads) == sorted(plan.internal_squads)
            and external_squad == plan.external_squad
        )
