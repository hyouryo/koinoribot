from .utils import get_wallet_handle
from hoshino import Service

sv = Service('说晚安', enable_on_default=True)

@sv.on_fullmatch('/晚安')
async def say_goodnight(bot, ev) -> None:
    async with get_wallet_handle(ev.user_id) as wallet:
        if wallet.gold >= 50:
            wallet.gold -= 50
            await bot.send(ev, '晚安喵~')