from typing import Protocol


class Redirect(Protocol):
    async def to_main_menu(self, telegram_id: int) -> None: ...

    async def to_user_editor(self, telegram_id: int, target_telegram_id: int) -> None: ...
