import json
import os
import time
import sqlite3
import asyncio
import random

from .._R import userPath
from hoshino import Service, priv, R
from .. import money, config

# 数据库路径（使用与钓鱼系统相同的数据库）
db_path = os.path.join(userPath, 'Koinoribot.db')
STOCKS_FILE = os.path.join(userPath, 'chaogu/stock_data.json')
PORTFOLIOS_FILE = os.path.join(userPath, 'chaogu/user_portfolios.json')
# 初始化状态标志
_db_initialized_stock = False
HISTORY_DURATION_HOURS = 24 # 只保留过去24小时数据
# 股票定义 (名称: 初始价格)新增或修改股票后，需要对bot发送“修复股票数据”进行初始化
STOCKS = {
    "萝莉股": 50.0,
    "猫娘股": 60.0,
    "魔法少女股": 70.0,
    "梦月股": 250.0,
    "梦馨股": 100.0,
    "高达股": 40.0,
    "雾月股": 120.0,
    "傲娇股": 60.0,
    "病娇股": 30.0,
    "梦灵股": 120.0,
    "铃音股": 110.0,
    "音祈股": 500.0,
    "梦铃股": 250.0,
    "姐妹股": 250.0,
    "橘馨股": 250.0,
    "白芷股": 250.0,
    "雾织股": 250.0,
    "筑梦股": 250.0,
    "摇篮股": 250.0,
    "筑梦摇篮股": 500.0,
}
# 市场事件定义 (类型: {描述, 影响范围, 影响函数})
MARKET_EVENTS = {
    "利好": {
        "templates": [
            "{stock}获得新的市场投资！",
            "{stock}获得异次元政府补贴！",
            "{stock}季度财报超预期！"
        ],
        "scope": "single",  # 影响单只股票
        "effect": lambda price: price * random.uniform(1.10, 1.20)  # 小幅上涨
    },
    "利空": {
        "templates": [
            "{stock}产品力下降！",
            "{stock}产品发现严重缺陷！",
            "{stock}高管突然离职！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(0.82, 0.90)  # 小幅下跌
    },
    "大盘上涨": {
        "templates": [
            "鹰酱宣布降息，市场普涨！",
            "异次元经济复苏，投资者信心增强！",
            "魔法少女在战争中大捷，领涨大盘！"
        ],
        "scope": "all",  # 影响所有股票
        "effect": lambda price: price * random.uniform(1.10, 1.15)  # 全体上涨
    },
    "大盘下跌": {
        "templates": [
            "异次元国际局势紧张，市场恐慌！",
            "经济数据不及预期，市场普跌！",
            "机构投资者大规模抛售！"
        ],
        "scope": "all",
        "effect": lambda price: price * random.uniform(0.87, 0.90)  # 全体下跌
    },
    "暴涨": {
        "templates": [
            "{stock}成为市场新宠，资金疯狂涌入！",
            "{stock}发现新资源，价值重估！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(1.25, 1.40)  # 大幅上涨
    },
    "暴跌": {
        "templates": [
            "{stock}被曝财务造假！",
            "{stock}主要产品被禁售！"
        ],
        "scope": "single",
        "effect": lambda price: price * random.uniform(0.63, 0.75)  # 大幅下跌
    }
}

# 在 MARKET_EVENTS 定义后添加
MANUAL_EVENT_TYPES = {
    "利好": "单股上涨",
    "利空": "单股下跌", 
    "暴涨": "单股暴涨",
    "暴跌": "单股暴跌",
    "大盘上涨": "全局上涨",
    "大盘下跌": "全局下跌"
}

# --- SQLite数据库操作 ---
async def init_stock_database():
    """初始化股票数据库表结构"""
    def _init_db():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建stock_data表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                stock_name TEXT PRIMARY KEY,
                initial_price REAL NOT NULL,
                history_data TEXT NOT NULL,
                events_data TEXT NOT NULL,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建user_portfolios表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_portfolios (
                uid TEXT PRIMARY KEY,
                portfolio_data TEXT NOT NULL,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
             )
        ''')
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _init_db)

# 数据库初始化状态标志
_stock_db_initialized = False

async def ensure_stock_database_initialized():
    """确保股票数据库已初始化"""
    global _stock_db_initialized
    if not _stock_db_initialized:
        await init_stock_database()
        #await migrate_stock_json_to_sqlite()
        _stock_db_initialized = True

# --- 修改后的辅助函数：SQLite操作 ---
async def get_stock_data():
    """获取所有股票数据"""
    await ensure_stock_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT stock_name, initial_price, history_data, events_data FROM stock_data')
        results = cursor.fetchall()
        
        stock_data = {}
        for stock_name, initial_price, history_data, events_data in results:
            stock_data[stock_name] = {
                "initial_price": initial_price,
                "history": json.loads(history_data),
                "events": json.loads(events_data)
            }
        
        conn.close()
        return stock_data
    
    # 确保所有股票都存在
    stock_data = await asyncio.get_event_loop().run_in_executor(None, _query)
    
    # 检查是否有缺失的股票
    missing_stocks = set(STOCKS.keys()) - set(stock_data.keys())
    if missing_stocks:
        for stock_name in missing_stocks:
            stock_data[stock_name] = {
                "initial_price": STOCKS[stock_name],
                "history": [],
                "events": []
            }
        # 保存缺失的股票数据
        await save_stock_data(stock_data)
    
    return stock_data

async def save_stock_data(data):
    """保存所有股票数据"""
    await ensure_stock_database_initialized()
    
    def _save():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for stock_name, stock_info in data.items():
            initial_price = stock_info.get('initial_price', STOCKS.get(stock_name, 50.0))
            history_data = json.dumps(stock_info.get('history', []))
            events_data = json.dumps(stock_info.get('events', []))
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_data (stock_name, initial_price, history_data, events_data)
                VALUES (?, ?, ?, ?)
            ''', (stock_name, initial_price, history_data, events_data))
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _save)

async def get_user_portfolios():
    """获取所有用户持仓"""
    await ensure_stock_database_initialized()
    
    def _query():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT uid, portfolio_data FROM user_portfolios')
        results = cursor.fetchall()
        
        portfolios = {}
        for uid, portfolio_data in results:
            portfolios[uid] = json.loads(portfolio_data)
        
        conn.close()
        return portfolios
    
    return await asyncio.get_event_loop().run_in_executor(None, _query)

async def save_user_portfolios(data):
    """保存所有用户持仓"""
    await ensure_stock_database_initialized()
    
    def _save():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for uid, portfolio in data.items():
            portfolio_data = json.dumps(portfolio)
            cursor.execute('''
                INSERT OR REPLACE INTO user_portfolios (uid, portfolio_data)
                VALUES (?, ?)
            ''', (uid, portfolio_data))
        
        conn.commit()
        conn.close()
    
    await asyncio.get_event_loop().run_in_executor(None, _save)

async def get_user_portfolio(user_id):
    """获取单个用户的持仓"""
    portfolios = await get_user_portfolios()
    return portfolios.get(str(user_id), {})  # user_id 转为字符串以匹配数据库键

async def update_user_portfolio(user_id, stock_name, change_amount):
    """更新用户持仓 (正数为买入，负数为卖出)"""
    await ensure_stock_database_initialized()
    
    def _update():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        uid = str(user_id)
        
        # 获取当前用户的整个持仓
        cursor.execute('SELECT portfolio_data FROM user_portfolios WHERE uid = ?', (uid,))
        result = cursor.fetchone()
        
        if result:
            portfolio = json.loads(result[0])
        else:
            portfolio = {}
        
        # 更新特定股票的持仓
        current_amount = portfolio.get(stock_name, 0)
        new_amount = current_amount + change_amount
        
        if new_amount < 0:
            conn.close()
            return False  # 持仓不能为负
        
        if new_amount == 0:
            # 从持仓中移除该股票
            if stock_name in portfolio:
                del portfolio[stock_name]
        else:
            # 更新持仓数量
            portfolio[stock_name] = new_amount
        
        # 保存更新后的整个持仓
        portfolio_data = json.dumps(portfolio)
        cursor.execute('''
            INSERT OR REPLACE INTO user_portfolios (uid, portfolio_data)
            VALUES (?, ?)
        ''', (uid, portfolio_data))
        
        conn.commit()
        conn.close()
        return True
    
    return await asyncio.get_event_loop().run_in_executor(None, _update)

async def get_current_stock_price(stock_name, stock_data=None):
    """获取指定股票的当前价格"""
    if stock_data is None:
        stock_data = await get_stock_data()
    
    if stock_name not in stock_data or not stock_data[stock_name]["history"]:
        return stock_data.get(stock_name, {}).get("initial_price")
    
    return stock_data[stock_name]["history"][-1][1]

async def get_current_stock_price(stock_name, stock_data=None):
    """获取指定股票的当前价格"""
    if stock_data is None:
        stock_data = await get_stock_data()
    
    if stock_name not in stock_data or not stock_data[stock_name]["history"]:
        # 如果没有历史记录，返回初始价格
        return stock_data.get(stock_name, {}).get("initial_price")
    
    # 返回最新价格
    return stock_data[stock_name]["history"][-1][1]  # history is [(timestamp, price), ...]

async def get_stock_price_history(stock_name, stock_data=None):
    """获取指定股票过去24小时的价格历史"""
    if stock_data is None:
        stock_data = await get_stock_data()
    
    if stock_name not in stock_data:
        return []
        
    cutoff_time = time.time() - HISTORY_DURATION_HOURS * 3600
    history = stock_data[stock_name].get("history", [])
    
    # 筛选出24小时内的数据
    recent_history = [(ts, price) for ts, price in history if ts >= cutoff_time]
    return recent_history

async def delete_user_all_accounts(user_id):
    """删除用户所有账户数据(钱包+股票)"""
    wallet_result = money.delete_user_account(user_id)  # 同步函数
    stock_result = await delete_user_stock_account(user_id)  # 异步函数
    return wallet_result and stock_result
    
async def delete_user_stock_account(user_id):
    """删除用户股票账户数据"""
    try:
        uid = str(user_id)
        
        # 使用新的数据库操作
        def _delete():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_portfolios WHERE uid = ?', (uid,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        
        result = await asyncio.get_event_loop().run_in_executor(None, _delete)
        return result
        
    except Exception as e:
        print(f'删除股票账户失败[{uid}]: {str(e)}')
        return False


# 市场事件定义 MARKET_EVENTS
# 手动事件类型 MANUAL_EVENT_TYPES  
# 事件概率配置 EVENT_PROBABILITY, EVENT_COOLDOWN
# 定时任务 hourly_price_update_job
# 初始化函数 initialize_stock_market
# 图表生成函数 generate_stock_chart
# 销户交互函数 request_delete_wallet, confirm_delete_account, cancel_delete_wallet