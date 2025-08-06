import os
import json

import hoshino
from ._R import userPath

# 用于用户金钱控制
# get_user_money(user_id, key) return int    获取某种资源用户有多少
# set_user_money(user_id, key, value)        直接设置用户某种资源为多少
# increase_user_money(user_id, key, value)   增加用户某种资源多少
# reduce_user_money(user_id, key, value)     减少用户某种资源多少（含数值校验）
# increase_all_user_money(key, value         增加全部用户某种资源多少
# translatename(name)                        将货币昵称转换成关键字
# tran_kira(uid, key, num)                   将羽毛石转换成某个其他物资（请先用translatename(name) 转换为关键字）


path = os.path.join(userPath, 'icelogin/user_money.json')
bg_path = os.path.join(os.path.dirname(__file__),
                       'icelogin/user_background.json')
config = {  # 初始物资
    "default": {
        "gold": 2000,  # 金币
        "luckygold": 0,  # 幸运币
        "starstone": 12500,  # 星星
        "kirastone": 0,  # 羽毛石
        "last_login": 0,  # 最后签到日期   防止单日多次签到
        "rp": 0,  # 记录运势rp值   只是防止单日多次抽签rp改变，不做其他用途
        "logindays": 0,  # 记录连续签到次数
        "exgacha": 0,
        "goodluck": 0,  # 宜做事项索引
        "badluck": 0,  # 忌做事项索引
    }
}

keyword_list = [  # 避免错误设置
    "gold",
    "luckygold",
    "starstone",
    "kirastone",
    "last_login",
    "rp",
    "logindays",
    "exgacha",
    "goodluck",
    "badluck"
]

user_money = {}

key_list = ["gold", "luckygold", "starstone", "kirastone"]  # 钱包里的货币：金币，幸运币，星星

name_list = {
    "starstone": ["starstone", "星星", "星石", "星",
                  "stars", "爱星", "艾星"],
    "luckygold": ["luckygold", "lucky", "幸运",
                  "幸运币"],
    "gold": ["gold", "金币", "金子", "黄金"
             ],
    "exgacha": ["井券", "兑换券", "exgacha"],
    "kirastone": ["羽毛石", "宝石"]
}



def translatename(name):
    for key in name_list.keys():
        if name in name_list[key]:
            return key
    else:
        return ''


def load_user_money():
    try:
        if not os.path.exists(path):
            return 0
        with open(path, encoding='utf8') as f:
            d = json.load(f)
            for k, v in d.items():
                user_money[k] = v
        return 1
    except:
        return 0


load_user_money()


def delete_user_account(user_id):
    """删除用户钱包数据"""
    try:
        user_id = str(user_id)
        if user_id in user_money:
            del user_money[user_id]
            with open(path, 'w', encoding='utf8') as f:
                json.dump(user_money, f, ensure_ascii=False, indent=2)
            return 1
        return 0
    except:
        return 0


def batch_delete_inactive_users():
    """
    批量删除不活跃的用户数据。
    不活跃条件：gold < 2000 且 starstone < 13000 且 kirastone == 0。

    Returns:
        list: 被成功删除的用户ID列表。
    """
    # 确保内存中的数据是来自文件的最新版本
    load_user_money()
    
    uids_to_delete = []
    for user_id in list(user_money.keys()):
        user_data = user_money.get(user_id, {})
        gold = user_data.get('gold', 0)
        starstone = user_data.get('starstone', 0)
        kirastone = user_data.get('kirastone', 0)
        last_login = user_data.get('last_login', 0)
        # 检查是否同时满足所有条件
        if gold < 2000 and starstone < 50000 and kirastone == 0:
            uids_to_delete.append(user_id)
            
    # 如果没有找到符合条件的用户，则直接返回空列表
    if not uids_to_delete:
        return []
        
    # 从 user_money 字典中批量删除这些用户
    for user_id in uids_to_delete:
        if user_id in user_money:
            del user_money[user_id]
            
    # 将修改后的 user_money 字典一次性写回文件
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(user_money, f, ensure_ascii=False, indent=2)
        # 成功写入文件后，返回被删除的ID列表
        return uids_to_delete
    except Exception as e:
        hoshino.logger.error(f'批量删除用户数据并写入文件时失败: {e}')
        return []

def get_user_money(user_id, key):  # 自带初始化的读取钱包功能
    load_user_money()
    try:
        if key not in keyword_list:
            return None
        user_id = str(user_id)
        if user_id not in user_money:
            user_money[user_id] = {}
            for k, v in config['default'].items():
                user_money[user_id][k] = v
            with open(path, 'w', encoding='utf8') as f:
                json.dump(user_money, f, ensure_ascii=False, indent=2)
        if key in user_money[user_id]:
            return user_money[user_id][key]
        else:
            return None
    except:
        return None
        

        

def get_all_user_money(key):
    """
    获取所有用户指定类型(key)的资产数量。

    Args:
        key (str): 资产的关键字 (例如 "gold", "starstone")。

    Returns:
        dict: 一个字典，键为用户ID(str)，值为对应的资产数量(int)。
              如果提供的 key 无效，则返回空字典。
    """
    # 1. 检查 key 是否为有效的资产关键字
    if key not in keyword_list:
        hoshino.logger.warning(f'无效的资产key: {key}')
        return {}

    # 2. 确保内存中的用户数据为最新
    load_user_money()

    # 3. 遍历所有用户，收集指定资产的数据
    all_users_asset = {}
    for user_id, data in user_money.items():
        # 使用 .get() 方法安全地获取资产数量
        asset_value = data.get(key, config['default'].get(key, 0))
        all_users_asset[user_id] = asset_value

    return all_users_asset


def set_user_money(user_id, key, value):  # 自带初始化的设置货币功能
    try:
        if key not in keyword_list:
            return 0
        user_id = str(user_id)
        if user_id not in user_money:
            user_money[user_id] = {}
            for k, v in config['default'].items():
                user_money[user_id][k] = v
        user_money[user_id][key] = value
        with open(path, 'w', encoding='utf8') as f:
            json.dump(user_money, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def increase_user_money(user_id, key, value):  # 自带初始化的增加货币功能
    if int(user_id) == 80000000:
        return

    try:
        if key not in keyword_list:
            return 0
        user_id = str(user_id)
        if user_id not in user_money:
            user_money[user_id] = {}
            for k, v in config['default'].items():
                user_money[user_id][k] = v
        if key not in user_money[user_id].keys():
            user_money[user_id][key] = config['default'][key] + value
        else:
            now_money = int(get_user_money(user_id, key)) + value
            user_money[user_id][key] = now_money
        with open(path, 'w', encoding='utf8') as f:
            json.dump(user_money, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def reduce_user_money(user_id, key, value):  # 自带初始化的减少货币功能
    if int(user_id) == 80000000:
        return

    try:
        if key not in keyword_list:
            return 0
        user_id = str(user_id)
        if user_id not in user_money:
            user_money[user_id] = {}
            for k, v in config['default'].items():
                user_money[user_id][k] = v
        if key not in user_money[user_id].keys():
            user_money[user_id][key] = config['default'][key]
            return 0
        else:
            now_money = int(get_user_money(user_id, key)) - value
        if now_money < 0:
            return 0
        user_money[user_id][key] = now_money
        with open(path, 'w', encoding='utf8') as f:
            json.dump(user_money, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def increase_all_user_money(key, value):
    try:
        if key not in keyword_list:
            return 0
        for user_id in user_money.keys():
            if key not in user_money[user_id].keys():
                user_money[user_id][key] = config['default'][key]
            user_money[user_id][key] += value
        with open(path, 'w', encoding='utf8') as f:
            json.dump(user_money, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def tran_kira(uid, key, num):
    if key == 'gold':
        value = num * 10
    elif key == 'starstone':
        value = num * 10
    elif key == 'luckygold':
        value = num // 50
        num = value * 50
    else:
        value = 0
        num = 0
    increase_user_money(uid, key, value)
    reduce_user_money(uid, 'kirastone', num)
    return num, value


def load_user_background():
    if not os.path.exists(bg_path):
        empty_dict = {}
        with open(bg_path, 'w', encoding='utf-8') as f:
            json.dump(empty_dict, f, ensure_ascii=False, indent=2)
        return {}
    else:
        try:
            user_dict = json.load(open(bg_path, encoding='utf-8'))
        except:
            hoshino.logger.error('用户背景图片配置加载失败。')
            user_dict = {}
        return user_dict


user_bg = load_user_background()


def get_user_background(uid):
    if int(uid) == 80000000:
        return {'default': '', 'custom': '', 'mode': 0}
    user_bg = load_user_background()
    return user_bg[str(uid)] if str(uid) in user_bg else {'default': '', 'custom': '', 'mode': 0}


def set_user_background(uid: int, bg: str, kind: str = 'default'):
    if uid == 80000000:
        return
    try:
        user_id = str(uid)
        if user_id not in user_bg:
            user_bg[user_id] = {'default': '', 'custom': '', 'mode': 0}
        user_bg[user_id][kind] = bg
        with open(bg_path, 'w', encoding='utf8') as f:
            json.dump(user_bg, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def set_user_bg_mode(uid: int, mode: int):
    """
    :param: mode:0-默认，1-hoshi，2-自定义
    """
    if uid == 80000000:
        return
    try:
        user_id = str(uid)
        if user_id not in user_bg:
            user_bg[user_id] = {'default': '', 'custom': '', 'mode': 0}
        user_bg[user_id]['mode'] = mode
        with open(bg_path, 'w', encoding='utf8') as f:
            json.dump(user_bg, f, ensure_ascii=False, indent=2)
        return 1
    except:
        return 0


def check_mode(uid):
    if str(uid) not in user_bg:
        set_user_bg_mode(uid, 0)
        return
    if user_bg[str(uid)]['custom']:
        set_user_bg_mode(uid, 2)
    elif 'hoshi' in user_bg[str(uid)]['default']:
        set_user_bg_mode(uid, 1)
    elif user_bg[str(uid)]['default']:
        set_user_bg_mode(uid, 0)
    else:
        set_user_background(uid, 'Background3.jpg')
        set_user_bg_mode(uid, 0)
