import math
import json
import os
import random
import time
import base64
import sqlite3
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

# 数据库路径
db_path = os.path.join(userPath, 'Koinoribot.db')
#user_info_path = os.path.join(userPath, 'fishing/db/user_info.json')  # 保留用于迁移

default_info = {
    'fish': {'🐟': 0, '🦐': 0, '🦀': 0, '🐡': 0, '🐠': 0, '🔮': 0, '✉': 0, '🍙': 0},
    'statis': {'free': 0, 'sell': 0, 'total_fish': 0, 'frags': 0},
    'rod': {'current': 0, 'total_rod': [0]}
}

# 初始化状态标志
_db_initialized = False

# --- SQLite数据库操作 ---
def init_database_sync():
    """同步初始化数据库和表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建fishing表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fishing (
            uid TEXT PRIMARY KEY,
            fish_data TEXT NOT NULL,
            statis_data TEXT NOT NULL,
            rod_data TEXT NOT NULL,
            updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

async def ensure_database_initialized():
    """确保数据库已初始化（延迟初始化）"""
    global _db_initialized
    if not _db_initialized:
        await asyncio.get_event_loop().run_in_executor(None, init_database_sync)
        #await asyncio.get_event_loop().run_in_executor(None, migrate_json_to_sqlite_sync)
        _db_initialized = True

async def get_user_info_from_db(uid):
    """从数据库获取用户信息"""
    await ensure_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT fish_data, statis_data, rod_data FROM fishing WHERE uid = ?', (uid,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            fish_data, statis_data, rod_data = result
            return {
                'fish': json.loads(fish_data),
                'statis': json.loads(statis_data),
                'rod': json.loads(rod_data)
            }
        return None
    
    return await asyncio.get_event_loop().run_in_executor(None, _query)

async def save_user_info_to_db(uid, user_info):
    """保存用户信息到数据库"""
    await ensure_database_initialized()
    
    def _save():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        fish_data = json.dumps(user_info.get('fish', {}))
        statis_data = json.dumps(user_info.get('statis', {}))
        rod_data = json.dumps(user_info.get('rod', {}))
        
        cursor.execute('''
            INSERT OR REPLACE INTO fishing (uid, fish_data, statis_data, rod_data)
            VALUES (?, ?, ?, ?)
        ''', (uid, fish_data, statis_data, rod_data))
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _save)

# --- 修改后的函数（保持接口不变）---
async def getUserInfo(uid):
    """获取用户背包，自带初始化"""
    uid = str(uid)
    
    user_info = await get_user_info_from_db(uid)
    
    if not user_info:
        user_info = default_info.copy()
        await save_user_info_to_db(uid, user_info)
    
    return user_info


async def load_to_save_data(user_info, uid):
    """保持原有接口，优化内部实现"""
    try:
        uid = str(uid)
        await save_user_info_to_db(uid, user_info)
    except Exception as e:
        print(f"在试图读取和保存钓鱼数据时出现错误: {e}")
        raise