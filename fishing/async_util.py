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
from ..config import fish_limit_count
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
    
    # 创建fish_limit表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fish_limit (
            uid TEXT PRIMARY KEY,
            date_str TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            limit_count INTEGER NOT NULL DEFAULT 0,
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
    
    

# --- 钓鱼次数限制功能 ---
async def check_and_update_fish_limit(uid, count):
    """
    检查并更新用户钓鱼次数限制
    参数: uid, count(要增加的次数)
    返回: 如果未达到上限则增加计数并返回True，达到上限返回False
    """
    await ensure_database_initialized()
    
    uid = str(uid)
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    def _update_fish_limit():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 查询用户今天的记录
            cursor.execute(
                'SELECT date_str, count, limit_count FROM fish_limit WHERE uid = ?', 
                (uid,)
            )
            result = cursor.fetchone()
            
            if result:
                date_str, current_count, current_limit_count = result
                
                # 如果是同一天
                if date_str == today_str:
                    # 负数直接增加增加 limit_count
                    if count < 0:
                        new_limit_count = current_limit_count - count  # 因为count是负数，所以用减号
                        cursor.execute(
                            'UPDATE fish_limit SET limit_count = ?, updated_time = CURRENT_TIMESTAMP WHERE uid = ?',
                            (new_limit_count, uid)
                        )
                    else:
                        # 正常情况：检查是否超过上限
                        new_count = current_count + count
                        if new_count > current_limit_count:
                            conn.close()
                            return False
                        # 更新计数
                        cursor.execute(
                            'UPDATE fish_limit SET count = ?, updated_time = CURRENT_TIMESTAMP WHERE uid = ?',
                            (new_count, uid)
                        )
                else:
                    # 不是同一天，重置计数和限制次数
                    if count < 0:
                        # 对于负数，重置后增加 limit_count
                        new_limit_count = fish_limit_count - count  # 重置为基础值 + 恢复值
                        cursor.execute(
                            'UPDATE fish_limit SET date_str = ?, count = 0, limit_count = ?, updated_time = CURRENT_TIMESTAMP WHERE uid = ?',
                            (today_str, new_limit_count, uid)
                        )
                    else:
                        # 对于正数，正常重置
                        cursor.execute(
                            'UPDATE fish_limit SET date_str = ?, count = ?, limit_count = ? WHERE uid = ?',
                            (today_str, count, fish_limit_count, uid)
                        )
            else:
                # 没有记录，插入新记录
                if count < 0:
                    # 对于负数，设置基础 limit_count 并增加
                    new_limit_count = fish_limit_count - count
                    cursor.execute(
                        'INSERT INTO fish_limit (uid, date_str, count, limit_count) VALUES (?, ?, 0, ?)',
                        (uid, today_str, new_limit_count)
                    )
                else:
                    # 对于正数，正常插入
                    cursor.execute(
                        'INSERT INTO fish_limit (uid, date_str, count, limit_count) VALUES (?, ?, ?, ?)',
                        (uid, today_str, count, fish_limit_count)
                    )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"更新钓鱼次数限制时出错: {e}")
            return False
    
    return await asyncio.get_event_loop().run_in_executor(None, _update_fish_limit)

async def get_user_fish_count_today(uid):
    """
    获取用户今日已钓鱼次数
    参数: uid
    返回: 今日钓鱼次数
    """
    await ensure_database_initialized()
    
    uid = str(uid)
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    def _query_count():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT count, limit_count FROM fish_limit WHERE uid = ? AND date_str = ?', 
            (uid, today_str)
        )
        result = cursor.fetchone()
        
        conn.close()
        if result:
            return result[0], result[1]  # 返回 (count, limit_count)
        else:
            return 0, fish_limit_count  # 没有记录时返回默认值
    
    return await asyncio.get_event_loop().run_in_executor(None, _query_count)



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