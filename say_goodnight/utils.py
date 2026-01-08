from ..money import get_user_money, set_user_money
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from dataclasses import dataclass
from pydantic import Field


@dataclass
class Wallet:
    gold: int = Field(0, ge=0)
    luckygold: int = Field(0, ge=0)
    starstone: int = Field(0, ge=0)
    kirastone: int = Field(0, ge=0)


async def get_wallet(uid: int) -> Wallet:
    gold = get_user_money(uid, "gold")
    luckygold = get_user_money(uid, "luckygold")
    starstone = get_user_money(uid, "starstone")
    kirastone = get_user_money(uid, "kirastone")
    return Wallet(gold, luckygold, starstone, kirastone)


async def set_wallet(uid: int, wallet: Wallet):
    set_user_money(uid, "gold", wallet.gold)
    set_user_money(uid, "luckygold", wallet.luckygold)
    set_user_money(uid, "starstone", wallet.starstone)
    set_user_money(uid, "kirastone", wallet.kirastone)





@asynccontextmanager
async def get_wallet_handle(user_id: int) -> AsyncGenerator[Wallet, None]:
    try:
        wallet = await get_wallet(user_id)
        yield wallet
    finally:
        await set_wallet(user_id, wallet)
