"""Fork-local DI registrations for Rain.

Kept in a DEDICATED module (not services.py) on purpose: upstream merges may
overwrite upstream-owned files like services.py and silently drop our custom
additions. Files that upstream does not have — like this one — survive merges.

History: on 2026-06-19 an upstream merge (v0.8.x) overwrote services.py and
removed the NalogReceiptsService registration. That un-subscribed the purchase
-> Moy Nalog receipt handler, so receipts stopped reaching the tax service.
Registering here prevents that recurrence. Add fork-specific services here.
"""

from dishka import Provider, Scope, provide

from src.application.services.nalog_receipts import NalogReceiptsService


class CustomProvider(Provider):
    scope = Scope.APP

    # Auto-discovered by the event bus; NalogReceiptsService.on_purchase
    # listens to UserPurchaseEvent (RUB, non-trial) and queues the receipt task.
    nalog_receipts = provide(NalogReceiptsService, scope=Scope.APP)
