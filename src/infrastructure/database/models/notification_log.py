from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB as PgJSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseSql


class UserNotificationLog(BaseSql):
    """
    Что и кому уже отправляли из кампаний возврата.

    Пара «человек + повод» уникальна: это и есть защита от второго письма.
    Задача может отработать дважды — из-за перезапуска воркера или
    пересечения расписаний, — и вторая вставка просто не пройдёт.
    """

    __tablename__ = "user_notification_log"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="uq_user_notification_log"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime]
    # Размер скидки и до какого числа — чтобы потом посчитать эффект, не
    # восстанавливая его по логам бота.
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(PgJSONB, nullable=True)
