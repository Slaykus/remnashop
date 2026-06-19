from .health import router as health_router
from .internal import router as internal_router
from .payments import router as payments_router
from .public import router as public_router
from .remnawave import router as remnawave_router
from .telegram import TelegramWebhookEndpoint

__all__ = [
    "health_router",
    "internal_router",
    "payments_router",
    "public_router",
    "remnawave_router",
    "TelegramWebhookEndpoint",
]
