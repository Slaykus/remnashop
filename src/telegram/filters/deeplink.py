from aiogram.filters import BaseFilter, CommandObject
from aiogram.types import Message

from src.core.enums import Deeplink


class DeeplinkFilter(BaseFilter):
    """Совпадение по аргументу /start, а не по подстроке всего сообщения.

    `F.text.contains(Deeplink.ADVERTISING)` искал «ad» во всём тексте, поэтому
    реферальный код с такими буквами уезжал в рекламный обработчик и там,
    разумеется, не находился.

    Ставится только после `CommandStart`: `command` приходит из его результата.
    """

    def __init__(self, deeplink: Deeplink) -> None:
        self.deeplink = deeplink

    async def __call__(self, event: Message, command: CommandObject) -> bool:
        args = command.args or ""
        return args == self.deeplink.value or args.startswith(self.deeplink.with_underscore)
