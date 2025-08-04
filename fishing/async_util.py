import math
import json
import os
import random
import time
import base64
from datetime import datetime, timedelta
import math
import asyncio
import io
from functools import wraps

from hoshino.log import default_handler
from ..utils import chain_reply
from .._R import get, userPath
from hoshino import Service, priv, R
from hoshino.typing import CQEvent, MessageSegment
from .. import money
from hoshino.config import SUPERUSERS

#常用路径
dbPath = os.path.join(userPath, 'fishing/db')
user_info_path = os.path.join(dbPath, 'user_info.json')

# 锁防止并发问题
USER_DATA_LOCK = asyncio.Lock()


default_info = {
    'fish': {'🐟': 0, '🦐': 0, '🦀': 0, '🐡': 0, '🐠': 0, '🔮': 0, '✉': 0, '🍙': 0},
    'statis': {'free': 0, 'sell': 0, 'total_fish': 0, 'frags': 0},
    'rod': {'current': 0, 'total_rod': [0]}
}
# --- 辅助函数 ---
async def load_json_data(filename, default_data):
    """异步安全地加载JSON数据"""
    if not os.path.exists(filename):
        return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default_data

async def save_json_data(filename, data):
    """异步安全地保存JSON数据"""
    try:
        temp_filename = filename + ".tmp"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(temp_filename, filename)
    except IOError as e:
        print(f"Error saving JSON data to {filename}: {e}")

def with_lock(lock):
    """自动加锁的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            async with lock:  # 进入函数前加锁
                return await func(*args, **kwargs)  # 执行函数
        return wrapped
    return decorator
    

@with_lock(USER_DATA_LOCK)
async def getUserInfo(uid):
    """
        获取用户背包，自带初始化
    """
    uid = str(uid)
    total_info = await load_user_data(user_info_path)
    if uid not in total_info:
        user_info = default_info
        total_info[uid] = user_info
        await save_user_data(user_info_path,total_info)
    else:
        user_info = total_info[uid]
    return user_info

async def load_user_data(user_path):
    return await load_json_data(user_path,{})

async def save_user_data(user_path,data):
    await save_json_data(user_path,data)

@with_lock(USER_DATA_LOCK)
async def load_to_save_data(user_path,user_info,uid):
    try:
        total_info = await load_user_data(user_path) or {}
        total_info[uid] = user_info
        await save_user_data(user_path,total_info)
    except:
        print(f"在试图读取和保存钓鱼数据时出现错误")
        raise