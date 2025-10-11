from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from hoshino import Service, priv
from hoshino.typing import CQEvent

from .ornaments import Character

#--------------------------------------
sv = Service('pet_raising', manage_priv=priv.ADMIN, enable_on_default=True)


#创建角色
def create_character(user_id: int,name:str) -> Character:
    return Character(user_id=user_id, name=name)

#--------------------------------------
#都是半成品
#--------------------------------------


#商店
@sv.on_prefix(('商店','饰品商店'))
async def show_shop(bot, ev: CQEvent):
    shop_text = (
        "欢迎来到饰品商店！\n"
        "1. 魔法帽子 - 100金币\n"
        "\n使用 '购买饰品 <物品名称>' 来购买饰品。"
    )
    await bot.send(ev, shop_text, at_sender=True)

#购买饰品
@sv.on_prefix(('购买饰品','买饰品'))
async def buy_ornament(bot, ev: CQEvent):
    user_id = ev.user_id
    args = ev.message.extract_plain_text().strip().split()
    pass

#查看饰品
@sv.on_prefix(('我的饰品','查看饰品'))
async def view_ornaments(bot, ev: CQEvent):
    user_id = ev.user_id
    pass

#售出饰品
@sv.on_prefix(('卖饰品','出售饰品'))
async def sell_ornament(bot, ev: CQEvent):
    user_id = ev.user_id
    args = ev.message.extract_plain_text().strip().split()
    pass

#--------------------------------------
#本来想写一下物品合成，但是懒得写了
#--------------------------------------