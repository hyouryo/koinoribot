import os
import random
import copy
import hoshino
from . import config
from .serif import no_fish_serif, get_fish_serif
from .. import money
from .._R import userPath
from .async_util import getUserInfo, load_to_save_data


dbPath = os.path.join(userPath, 'fishing/db')
user_info_path = os.path.join(dbPath, 'user_info.json')
fish_list = config.FISH_LIST + ['🔮', '✉', '🍙', '水之心']
fish_price = config.FISH_PRICE  # 价格换算
default_info = {
    'fish': {'🐟': 0, '🦐': 0, '🦀': 0, '🐡': 0, '🐠': 0, '🔮': 0, '✉': 0, '🍙': 0},
    'statis': {'free': 0, 'sell': 0, 'total_fish': 0, 'frags': 0},
    'rod': {'current': 0, 'total_rod': [0]}
}

init_prob = (5, 10, 65, 5, 15)
init_prob_2 = tuple([(int(100 / len(config.FISH_LIST)) for i in range(len(config.FISH_LIST)))])



async def fishing(uid, skip_random_events=False, user_info=None):
    """
        mode=0: 普通鱼竿，
        mode=1: 永不空军，不会钓不到东西
        mode=2: 海之眷顾，更大可能性钓到水之心或漂流瓶
        mode=3：时运，钓上的鱼可能双倍
    """
    uid = str(uid)
    if not user_info:
        user_info = await getUserInfo(uid)
    mode = user_info['rod']['current']
    probability = config.PROBABILITY[0 if mode == 3 else mode]  # 第一概率元组
    if not sum(probability) == 100:
        probability = init_prob
        hoshino.logger.info('钓鱼概率配置错误（各个概率之和不为100%），将使用默认概率')
    probability_2 = config.PROBABILITY_2[0 if mode == 3 else mode]  # 第二概率元组
    if not sum(probability_2) == 100:
        probability_2 = init_prob_2
        hoshino.logger.info('鱼上钩概率配置错误（各个概率之和不为100%），将使用默认概率')

    # 第一次掷骰子——选择一种情况
    first_choose = config.FREEZE_FC if config.FREEZE_FC and config.DEBUG_MODE else random.randint(1, 1000)

    if config.DEBUG_MODE:
        hoshino.logger.info(f'{uid}使用钓竿：{mode}，随机数为{first_choose}')

    # 如果需要跳过随机事件和漂流瓶，则直接返回普通鱼
    if skip_random_events:
        if first_choose <= probability[0] * 10:
            result = {'code': 1, 'msg': random.choice(no_fish_serif)}
            return result
        elif first_choose <= (probability[1] + probability[0]) * 10:
            result = {'code': 1, 'msg': random.choice(no_fish_serif)}  # 即使是随机事件，也返回普通鱼
            return result
        elif first_choose <= (probability[2] + probability[1] + probability[0]) * 10:
            second_choose = random.randint(1, 1000)
            prob_sum = 0
            fish = fish_list[0]
            for i in range(len(probability_2)):
                prob_sum += (int(probability_2[i]) * 10)
                if second_choose <= prob_sum:
                    fish = fish_list[i]
                    break
            multi = random.randint(1, 2) if mode == 3 else 1
            add_msg = f'另外，鱼竿发动了时运效果，{fish}变成了{multi}条！' if multi > 1 else ''
            await increase_value(uid, 'fish', fish, 1 * multi, user_info)
            await increase_value(uid, 'statis', 'total_fish', 1 * multi, user_info)
            msg = f'钓到了一条{fish}~' if random.randint(1, 10) <= 5 else random.choice(get_fish_serif).format(fish)
            msg = msg + add_msg + '\n你将鱼放进了背包。'
            result = {'code': 1, 'msg': msg}
            return result
        else:
            result = {'code': 1, 'msg': random.choice(no_fish_serif)}  # 直接返回普通鱼
            return result

    # 正常情况下钓鱼，随机事件和漂流瓶可以触发
    if first_choose <= probability[0] * 10:
        result = {'code': 1, 'msg': random.choice(no_fish_serif)}
        return result
    elif first_choose <= (probability[1] + probability[0]) * 10:
        result = {'code': 3, 'msg': '<随机事件case>'}
        return result
    elif first_choose <= (probability[2] + probability[1] + probability[0]) * 10:
        second_choose = config.FREEZE_SC if config.FREEZE_SC and config.DEBUG_MODE else random.randint(1, 1000)
        prob_sum = 0
        fish = fish_list[0]
        for i in range(len(probability_2)):
            prob_sum += (int(probability_2[i]) * 10)
            if second_choose <= prob_sum:
                fish = fish_list[i]
                break
        multi = random.randint(1, 2) if mode == 3 else 1
        add_msg = f'另外，鱼竿发动了时运效果，{fish}变成了{multi}条！' if multi > 1 else ''
        await increase_value(uid, 'fish', fish, 1 * multi, user_info)
        await increase_value(uid, 'statis', 'total_fish', 1 * multi, user_info)
        msg = f'钓到了一条{fish}~' if random.randint(1, 10) <= 5 else random.choice(get_fish_serif).format(fish)
        msg = msg + add_msg + '\n你将鱼放进了背包。'
        result = {'code': 1, 'msg': msg}
        return result
    elif first_choose <= (probability[3] + probability[2] + probability[1] + probability[0]) * 10:
        second_choose = random.randint(1, 1000)
        if second_choose <= 800:
            coin_amount = random.randint(1, 30)
            money.increase_user_money(uid, 'gold', coin_amount)
            result = {'code': 1, 'msg': f'你钓到了一个布包，里面有{coin_amount}枚金币，但是没有钓到鱼...'}
            return result
        else:
            coin_amount = random.randint(1, 3)
            money.increase_user_money(uid, 'luckygold', coin_amount)
            result = {'code': 1, 'msg': f'你钓到了一个锦囊，里面有{coin_amount}枚幸运币，但是没有钓到鱼...'}
            return result
    else:
        result = {'code': 2, 'msg': '<漂流瓶case>'}
        return result


async def sell_fish(uid, fish, num: int = 1):
    """
        卖鱼

    :param uid: 用户id
    :param fish: 鱼的emoji
    :param num: 出售的鱼数量
    :return: 获得的金币数量
    """
    user_info = await getUserInfo(uid)  # 直接使用 getUserInfo 获取用户数据
    uid = str(uid)
    if not user_info['fish'].get(fish):
        return '数量不够喔'
    if num > user_info['fish'].get(fish):
        num = user_info['fish'].get(fish)
    await decrease_value(uid, 'fish', fish, num)
    get_golds = fish_price[fish] * num
    money.increase_user_money(uid, 'gold', get_golds)
    if fish == '🍙':
        return f'成功退还了{num}个🍙，兑换了{get_golds}枚金币~'
    await increase_value(uid, 'statis', 'sell', get_golds)
    return f'成功出售了{num}条{fish}, 得到了{get_golds}枚金币~'


async def free_fish(uid, fish, num: int = 1):
    """
        放生鱼

    :param uid: 用户id
    :param fish: 鱼的emoji
    :param num: 放生的鱼数量
    :return: 水之心碎片数量
    """
    user_info = await getUserInfo(uid)  # 直接使用 getUserInfo 获取用户数据
    uid = str(uid)
    if not user_info['fish'].get(fish):
        return '数量不足喔'
    if num > user_info['fish'].get(fish):
        num = user_info['fish'].get(fish)
    await decrease_value(uid, 'fish', fish, num)
    get_frags = fish_price[fish] * num
    user_frags = (await getUserInfo(uid))['statis']['frags']
    total_frags = user_frags + get_frags  # 计算总碎片数
    
    crystals = 0
    if total_frags >= config.FRAG_TO_CRYSTAL:
        crystals = int(total_frags / config.FRAG_TO_CRYSTAL)
        remaining_frags = total_frags % config.FRAG_TO_CRYSTAL
        await set_value(uid, 'statis', 'frags', remaining_frags)
        await increase_value(uid, 'fish', '🔮', crystals)
    else:
        await increase_value(uid, 'statis', 'frags', get_frags)
    
    await increase_value(uid, 'statis', 'free', num)
    
    addition = f'\n一条美人鱼浮出水面！为了表示感谢，TA将{crystals}颗水之心放入了你的手中~' if crystals > 0 else ''

    classifier = '条' if fish in ['🐟', '🐠', '🦈'] else '只'
    return f'{num}{classifier}{fish}成功回到了水里，获得{get_frags}个水心碎片~{addition}'


async def buy_bait(uid, num = 1):
    """
        买鱼饵
    """
    money.reduce_user_money(uid, 'gold', num * config.BAIT_PRICE)
    await increase_value(uid, 'fish', '🍙', num)

async def buy_bottle(uid, num = 1):
    """
        买漂流瓶
    """
    money.reduce_user_money(uid, 'gold', num * config.BOTTLE_PRICE)
    await increase_value(uid, 'fish', '✉', num)


async def change_fishrod(uid, mode: int):
    """
        更换鱼竿
    """
    return
'''
    user_info = await getUserInfo(uid)
    uid = str(uid)
    if mode <= 0 or mode > 3:
        return {'code': -1, 'msg': '没有这种鱼竿...'}
    if (mode - 1) not in user_info['rod']['total_rod']:
        return {'code': -1, 'msg': '还没有拿到这个鱼竿喔'}
    user_info['rod']['current'] = mode - 1
    await save_user_data(user_info_path, total_info)
    return {'code': 1, 'msg': f'已更换为{mode}号鱼竿~'}
'''

async def compound_bottle(uid, num: int = 1):
    user_info = await getUserInfo(uid)
    uid = str(uid)
    if user_info['fish']['🔮'] < config.CRYSTAL_TO_BOTTLE:
        return {'code': -1, 'msg': f'要{config.CRYSTAL_TO_BOTTLE}个🔮才可以合成一个漂流瓶体喔'}
    if (num * config.CRYSTAL_TO_BOTTLE) > user_info['fish']['🔮']:
        num = int(user_info['fish']['🔮'] / config.CRYSTAL_TO_BOTTLE)
    await decrease_value(uid, 'fish', '🔮', num * config.CRYSTAL_TO_BOTTLE)
    await increase_value(uid, 'fish', '✉', num)
    return {'code': 1, 'msg': f'{num * config.CRYSTAL_TO_BOTTLE}个🔮发出柔和的光芒，融合成了{num}个漂流瓶体！\n可以使用"#扔漂流瓶+内容"来投放漂流瓶了！'}


async def decrease_value(uid, mainclass, subclass, num, user_info=None):
    """
        减少某物品的数量
    """
    uid = str(uid)
    
    if user_info:
        # 如果提供了user_info，直接修改
        if not user_info[mainclass].get(subclass): 
            user_info[mainclass][subclass] = 0
        user_info[mainclass][subclass] -= num
        if user_info[mainclass][subclass] < 0:
            user_info[mainclass][subclass] = 0
        return
    else:
        # 如果没有提供user_info，从数据库获取并更新
        user_info = await getUserInfo(uid)
        
        if not user_info[mainclass].get(subclass): 
            user_info[mainclass][subclass] = 0
        user_info[mainclass][subclass] -= num
        if user_info[mainclass][subclass] < 0:
            user_info[mainclass][subclass] = 0
        
        # 保存到数据库
        await load_to_save_data(user_info, uid)


async def increase_value(uid, mainclass, subclass, num, user_info=None):
    """
        增加某物品的数量
    """
    uid = str(uid)
    
    if user_info:
        # 如果提供了user_info，直接修改
        if not user_info[mainclass].get(subclass): 
            user_info[mainclass][subclass] = 0
        user_info[mainclass][subclass] += num
        return
    else:
        # 如果没有提供user_info，从数据库获取并更新
        user_info = await getUserInfo(uid)
        
        if not user_info[mainclass].get(subclass): 
            user_info[mainclass][subclass] = 0
        user_info[mainclass][subclass] += num
        
        # 保存到数据库
        await load_to_save_data(user_info, uid)

'''
async def set_value(uid, mainclass, subclass, num):
    """
        直接设置物品数量
    """
    uid = str(uid)
    await getUserInfo(uid)
    total_info = await load_user_data(user_info_path)
    if not user_info[mainclass].get(subclass): user_info[mainclass][subclass] = 0
    user_info[mainclass][subclass] = num
    await save_user_data(user_info_path, total_info)
'''

if __name__ == '__main__':
    pass
