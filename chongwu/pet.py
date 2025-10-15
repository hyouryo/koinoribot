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
from .._R import get, userPath
from .petconfig import GACHA_COST, GACHA_REWARDS, GACHA_CONSOLE_PRIZE, BASE_PETS, EVOLUTIONS, growth1, growth2, growth3, PET_SHOP_ITEMS, STATUS_DESCRIPTIONS

# 数据库路径（使用与钓鱼系统相同的数据库）
db_path = os.path.join(userPath, 'Koinoribot.db')

# 初始化状态标志
_db_initialized = False

# --- SQLite数据库操作 ---
def init_pet_database_sync():
    """同步初始化宠物数据库和表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建user_pets表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_pets (
            uid TEXT PRIMARY KEY,
            pet_data TEXT NOT NULL,
            updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建user_items表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_items (
            uid TEXT PRIMARY KEY,
            items_data TEXT NOT NULL,
            updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()



async def ensure_pet_database_initialized():
    """确保宠物数据库已初始化（延迟初始化）"""
    global _db_initialized
    if not _db_initialized:
        await asyncio.get_event_loop().run_in_executor(None, init_pet_database_sync)
        _db_initialized = True

# --- 宠物数据操作 ---
async def get_user_pets():
    """获取所有用户的宠物数据"""
    await ensure_pet_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT uid, pet_data FROM user_pets')
        results = cursor.fetchall()
        
        user_pets = {}
        for uid, pet_data_json in results:
            if pet_data_json:
                user_pets[uid] = json.loads(pet_data_json)
        
        conn.close()
        return user_pets
    
    return await asyncio.get_event_loop().run_in_executor(None, _query)


async def get_user_pet(user_id):
    """获取单个用户的宠物"""
    await ensure_pet_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT pet_data FROM user_pets WHERE uid = ?', (str(user_id),))
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0]:
            return json.loads(result[0])
        return None
    
    return await asyncio.get_event_loop().run_in_executor(None, _query)

async def update_user_pet(user_id, pet_data):
    """更新用户的宠物数据"""
    await ensure_pet_database_initialized()
    
    def _update():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_pets (uid, pet_data)
            VALUES (?, ?)
        ''', (str(user_id), json.dumps(pet_data, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _update)

async def remove_user_pet(user_id):
    """移除用户的宠物"""
    await ensure_pet_database_initialized()
    
    def _remove():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM user_pets WHERE uid = ?', (str(user_id),))
        affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        return affected > 0
    
    return await asyncio.get_event_loop().run_in_executor(None, _remove)

# --- 物品数据操作 ---
async def get_user_items():
    """获取用户的所有物品数据"""
    await ensure_pet_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT uid, items_data FROM user_items')
        results = cursor.fetchall()
        
        user_items = {}
        for uid, items_data_json in results:
            if items_data_json:
                user_items[uid] = json.loads(items_data_json)
        
        conn.close()
        return user_items
    
    return await asyncio.get_event_loop().run_in_executor(None, _query)


async def add_user_item(user_id, item_name, quantity=1):
    """给用户添加物品"""
    await ensure_pet_database_initialized()
    
    def _add():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取当前物品数据
        cursor.execute('SELECT items_data FROM user_items WHERE uid = ?', (str(user_id),))
        result = cursor.fetchone()
        
        if result and result[0]:
            items_data = json.loads(result[0])
        else:
            items_data = {}
        
        # 更新物品数量
        current_quantity = items_data.get(item_name, 0)
        items_data[item_name] = current_quantity + quantity
        
        # 保存回数据库
        cursor.execute('''
            INSERT OR REPLACE INTO user_items (uid, items_data)
            VALUES (?, ?)
        ''', (str(user_id), json.dumps(items_data, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _add)

async def use_user_item(user_id, item_name, quantity=1):
    """使用用户物品"""
    await ensure_pet_database_initialized()
    
    def _use():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取当前物品数据
        cursor.execute('SELECT items_data FROM user_items WHERE uid = ?', (str(user_id),))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return False
        
        items_data = json.loads(result[0])
        current_quantity = items_data.get(item_name, 0)
        
        if current_quantity < quantity:
            conn.close()
            return False
        
        # 更新物品数量
        new_quantity = current_quantity - quantity
        if new_quantity <= 0:
            # 数量为0时删除该物品
            del items_data[item_name]
        else:
            items_data[item_name] = new_quantity
        
        # 保存回数据库
        cursor.execute('''
            INSERT OR REPLACE INTO user_items (uid, items_data)
            VALUES (?, ?)
        ''', (str(user_id), json.dumps(items_data, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
        return True
    
    return await asyncio.get_event_loop().run_in_executor(None, _use)


async def get_pet_data():
    """获取宠物基础数据"""
    return BASE_PETS



async def get_status_description(stat_name, value):
    """获取状态描述"""
    thresholds = sorted(STATUS_DESCRIPTIONS[stat_name].keys(), reverse=True)
    for threshold in thresholds:
        if value >= threshold:
            return STATUS_DESCRIPTIONS[stat_name][threshold]
    return "状态异常"

async def update_pet_status(pet):
    """更新宠物状态"""
    current_time = time.time()
    last_update = pet.get("last_update", current_time)
    time_passed = current_time - last_update
    # 先更新时间戳，避免时间差问题
    pet["last_update"] = current_time
    
    # 如果处于离家出走状态，不更新任何状态
    if pet["runaway"]:
        return pet
    #初始化成长值上限
    if pet["stage"] == 0:
        pet["growth_required"] = growth1
    elif pet["stage"] == 1:
        pet["growth_required"] = growth2
    elif pet["stage"] == 2:
        pet["growth_required"] = growth3
    
    
    # 随时间减少状态值
    pet["hunger"] = max(0, pet["hunger"] - time_passed / 3600 * 2)  # 每小时减少2点
    pet["energy"] = max(0, pet["energy"] - time_passed / 3600 * 2)  # 每小时减少2点
    
    # 检查是否触发离家出走条件
    if (pet["hunger"] < 10 or pet["energy"] < 10) :
        pet["happiness"] = max(0, pet["happiness"] - time_passed / 3600 * 30)  # 每小时减少大量好感度

    else:
        pet["happiness"] = max(0, pet["happiness"] - time_passed / 3600 * 1)  # 正常情况每小时减少1点
        
    if pet["happiness"] < 1:
        pet["runaway"] = True  # 标记为离家出走状态

    # 更新成长值

    growth_rate = pet.get("growth_rate", 1.0)
        # 成年体依然可以获得成长值，但没有上限
    pet["growth"] = min(pet["growth_required"], pet.get("growth", 0) + time_passed / 3600 * growth_rate)
    return pet

async def check_pet_evolution(pet):
    """检查宠物是否可以进化"""
    # 幼年体 -> 成长体
    if pet["stage"] == 0 and pet["growth"] >= pet.get("growth_required", 100):
        return "stage1"
    # 成长体 -> 成年体
    elif pet["stage"] == 1 and pet["growth"] >= pet.get("growth_required", 200):
        return "stage2"
    return None
    
    