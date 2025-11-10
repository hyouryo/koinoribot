import json
import asyncio
from aiocqhttp.message import MessageSegment
from hoshino.service import Service
from hoshino.typing import HoshinoBot, CQEvent as Event
from hoshino.util import silence
from random import randint, shuffle
from itertools import cycle
from hoshino import R
from ..utils import chain_reply, saveData, loadData
from .._R import get, userPath
import sys
import os
from .. import money, config
from hoshino.config import SUPERUSERS
import time

sv = Service('金币炸弹', visible=True, enable_on_default=True)
no = get('emotion/no.png').cqcode
ok = get('emotion/ok.png').cqcode
# 游戏会话管理
game_sessions = {}  # {group_id: {session_id: 金币炸弹session}}
session_id_counter = 0 # 用于生成唯一的会话ID
MAX_POT_LIMIT = 1000 #最大奖池
PENALTY = 1000 #失败惩罚
TIMEOUT = 300 # 超时时间

# 金币炸弹会话类
class GoldBombSession:
    def __init__(self, group_id, starter_id, bot):
        global session_id_counter
        session_id_counter += 1
        self.session_id = session_id_counter #生成唯一的会话ID
        self.group_id = group_id
        self.starter_id = starter_id
        self.bot = bot  # HoshinoBot 实例
        self.players = {}  # {user_id: pot_amount}  所有参与者的金币奖池（用于最后结算）
        self.player_order = [] # 活跃玩家顺序列表（只包含未失败且未停止的玩家）
        self.is_running = False # 游戏是否正在运行
        self.prepared = {}  # {user_id: True/False}  玩家是否准备
        self.failed = {} # {user_id: True/False} 玩家是否失败（用于最后结算）
        self.all_stopped = False # 玩家是否都停止下注
        self.turn = None  # 当前回合玩家的迭代器
        self.current_player = None # 当前轮到的玩家
        self.task = None  # 定时任务
        self.start_time = None # 记录游戏开始的时间

    async def start(self):
        self.is_running = True # 标记游戏开始
        self.start_time = time.time()  # 记录游戏开始的时间
        # player_order 只包含活跃玩家
        self.player_order = list(self.players.keys())
        shuffle(self.player_order)  # 打乱玩家顺序
        self.turn = cycle(self.player_order) # 轮流下注的玩家
        await self.next_turn()  # 开始第一回合
        self.set_timer() # 启动定时任务

    async def next_turn(self):
        # [REPAIR] 优化 next_turn 逻辑
        # self.player_order 只包含活跃玩家（未失败且未停止）
        # 如果列表为空，说明游戏结束
        if not self.player_order:
            await self.end_game()
            return

        try:
            self.current_player = next(self.turn)
            await self.bot.send_group_msg(group_id=self.group_id, message=f'轮到 {MessageSegment.at(self.current_player)} 下注 (下注/停止下注)。')

        except StopIteration:
            # 理论上 cycle() 不会触发 StopIteration，但作为保险
            await self.end_game()
        except Exception as e:
            print(f"next_turn error: {e}")
            await self.end_game()

    async def bet(self, user_id):
        if user_id != self.current_player:
            await self.bot.send_group_msg(group_id=self.group_id, message=f'还没轮到你下注。');
            return

        amount = randint(100, 500)
        current_pot = self.players[user_id]
        new_pot = current_pot + amount

        if new_pot > MAX_POT_LIMIT:
            self.failed[user_id] = True # 标记玩家失败
            self.players[user_id] = MAX_POT_LIMIT # 奖池固定为上限
            await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} 下注 {amount} 金币，超出上限！判定失败，已达到{MAX_POT_LIMIT}金币，禁止继续下注。')

            #从玩家顺序中移除
            if user_id in self.player_order:
                self.player_order.remove(user_id)

            # [FIX] 核心修复：必须重置迭代器
            if self.player_order:
                self.turn = cycle(self.player_order)
            else:
                self.turn = None # 列表为空，无人可迭代

            await self.next_turn() # 轮到下一位玩家

        else:
            self.players[user_id] = new_pot
            await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} 下注 {amount} 金币，目前奖池 {new_pot}。')
            await self.next_turn()

    async def stop_bet(self, user_id):
        if user_id not in self.players:
            return
        
        # 玩家必须在活跃列表（player_order）中才能停止下注
        if user_id not in self.player_order:
            # 可能已经失败或已经停止过了
            return

        self.player_order.remove(user_id) # 从活跃玩家顺序中移除
        if not self.player_order: # 如果所有玩家都停止下注
            await self.end_game()
            return

        # 重置轮换器 (这部分原代码是正确的)
        self.turn = cycle(self.player_order)
        await self.next_turn()

    async def end_game(self):
        if not self.is_running:
            return

        self.is_running = False
        await self.bot.send_group_msg(group_id=self.group_id, message='所有玩家已停止下注或失败，正在结算...')

        winner = None
        min_diff = float('inf')
        all_failed = True  # 默认所有人都失败

        # 寻找离上限最近的玩家
        # 结算时，遍历 self.players (所有参与者)
        for user_id, pot in self.players.items():
            if not self.failed.get(user_id, False):  # 排除失败的玩家
                all_failed = False  # 至少有一个人没失败
                diff = MAX_POT_LIMIT - pot
                if diff < min_diff:
                    min_diff = diff
                    winner = user_id

        # 判断胜负
        if all_failed:
            message = '所有玩家都失败了，游戏流局！每人扣除1000金币。\n'
            for user_id in self.players:
                money.reduce_user_money(user_id, 'gold', PENALTY)
                message += f'{MessageSegment.at(user_id)} 扣除 {PENALTY} 金币。\n'
            await self.bot.send_group_msg(group_id=self.group_id, message=message)

        else:
            message = f'恭喜 {MessageSegment.at(winner)} 获胜，获得奖池中的所有金币！\n'
            wining_money = self.players[winner]
            money.increase_user_money(winner, 'gold', wining_money)
            message += f'获得 {wining_money} 金币。\n'
            # 惩罚其他所有参与者 (包括失败者和未失败但未获胜者)
            for user_id in self.players:
                if user_id != winner:
                        money.reduce_user_money(user_id, 'gold', PENALTY)
                        message += f'{MessageSegment.at(user_id)} 扣除 {PENALTY} 金币。\n'
            await self.bot.send_group_msg(group_id=self.group_id, message=message)

        # 清理会话
        self.cancel_timer()
        if self.group_id in game_sessions and self.session_id in game_sessions[self.group_id]:
            del game_sessions[self.group_id][self.session_id]
            if not game_sessions[self.group_id]:
                del game_sessions[self.group_id]

    async def close(self):
        if not self.is_running:
             # 如果游戏没在运行（例如在准备阶段被关闭），也需要清理
            if self.group_id in game_sessions and self.session_id in game_sessions[self.group_id]:
                del game_sessions[self.group_id][self.session_id]
                if not game_sessions[self.group_id]:
                    del game_sessions[self.group_id]
            return

        self.is_running = False
        await self.bot.send_group_msg(group_id=self.group_id, message='游戏已关闭。')

        self.cancel_timer() #取消定时任务
        if self.group_id in game_sessions and self.session_id in game_sessions[self.group_id]:
            del game_sessions[self.group_id][self.session_id]
            if not game_sessions[self.group_id]:
                del game_sessions[self.group_id]

    # 定时任务
    async def auto_close(self):
        # 检查超时
        current_time = time.time()
        start_time = self.start_time if self.start_time else self.session_id_counter # (session_id_counter 粗略当作创建时间)
        effective_start_time = self.start_time if self.start_time else self.creation_time # 假设已在 __init__ 添加 creation_time
        
        # [Compromise] 维持原逻辑：只在 running 时检查超时
        if self.is_running:
            if time.time() - self.start_time >= TIMEOUT: # 检查是否超时
                await self.bot.send_group_msg(group_id=self.group_id, message='游戏会话超时，自动关闭。')
                await self.close()
        else:
            # 增加对准备阶段超时的检查
            if not hasattr(self, 'creation_time'):
                self.creation_time = time.time() # 兼容旧会话
            
            if time.time() - self.creation_time >= TIMEOUT:
                await self.bot.send_group_msg(group_id=self.group_id, message='游戏准备超时，自动关闭。')
                await self.close() # 调用 close 来清理会话

    def set_timer(self):
        if not hasattr(self, 'creation_time'):
             self.creation_time = time.time()
        self.task = asyncio.ensure_future(self.auto_close_loop())
        self.task.set_name(f"金币炸弹-{self.group_id}-{self.session_id}") #设置任务名称

    async def auto_close_loop(self):
        while self.group_id in game_sessions and self.session_id in game_sessions[self.group_id]:
            await asyncio.sleep(60)  # 每隔60秒检查一次是否超时
            
            # 再次检查会话是否在 sleep 期间被关闭
            if self.group_id in game_sessions and self.session_id in game_sessions[self.group_id]:
                await self.auto_close()
            else:
                break # 会话已关闭，退出循环

    def cancel_timer(self):
        if self.task and not self.task.done():
            self.task.cancel()

    async def player_ready(self, user_id):
        if user_id not in self.players:
            await self.bot.send_group_msg(group_id=self.group_id, message='你还没有加入游戏。')
            return

        self.prepared[user_id] = True # 标记玩家已准备
        await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} 已准备。')

        # 检查是否所有 *已加入* 的玩家都准备了
        all_ready = True
        if len(self.players) < 2: # 至少需要2人
             all_ready = False
             
        for uid in self.players:
            if not self.prepared.get(uid, False):
                all_ready = False
                break

        if all_ready: # 检查是否所有玩家都已准备
            await self.bot.send_group_msg(group_id=self.group_id, message='所有玩家已准备，游戏即将开始...')
            await self.start()

    async def player_quit(self, user_id):
        if user_id not in self.players:
            await self.bot.send_group_msg(group_id=self.group_id, message='你还没有加入游戏。')
            return

        if self.is_running: # 游戏已经开始
            await self.bot.send_group_msg(group_id=self.group_id, message='游戏已经开始，无法退出。')
            return

        del self.players[user_id] # 移除玩家
        if user_id in self.prepared:
            del self.prepared[user_id]

        await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} 退出了游戏。')

        if not self.players: # 没有玩家了
            await self.bot.send_group_msg(group_id=self.group_id, message='所有玩家已退出，游戏关闭。')
            await self.close()

# 指令处理
@sv.on_fullmatch('金币炸弹')
async def start_game(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id in game_sessions and game_sessions[group_id]:
        await bot.send(ev, '当前群已有进行中的金币炸弹游戏。')
        return

    # 创建新的游戏会话
    session = GoldBombSession(group_id, user_id, bot)
    session.creation_time = time.time() # 记录创建时间用于超时

    # 初始化会话
    if group_id not in game_sessions:
        game_sessions[group_id] = {}
    game_sessions[group_id][session.session_id] = session
    
    # 启动定时器（用于处理准备阶段超时）
    session.set_timer()

    await bot.send(ev, f'金币炸弹游戏已发起，等待玩家加入，发送“加入游戏”加入游戏（房主也需要加入游戏哦~）。')

@sv.on_fullmatch('加入游戏')
async def join_game(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id
    user_gold = money.get_user_money(user_id, 'gold')
    if user_gold<1000:
        await bot.send(ev, '你没有足够的赌资喔...' + no)
        return
    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '当前群没有进行中的金币炸弹游戏，发送“金币炸弹”发起游戏。')
        return

    # 获取当前会话 (假设一个群只有一个会话)
    session = list(game_sessions[group_id].values())[0] #只取第一个
    
    if session.is_running:
        await bot.send(ev, '游戏已经开始了，无法加入。')
        return

    if user_id in session.players:
        await bot.send(ev, '你已经加入了游戏。')
        return

    if len(session.players) >= 3:
        await bot.send(ev, '游戏人数已满。')
        return

    # 加入玩家
    session.players[user_id] = 0  # 初始金币奖池为0
    session.prepared[user_id] = False  # 初始为未准备
    session.failed[user_id] = False # 初始为未失败

    await bot.send(ev, f'{MessageSegment.at(user_id)} 加入游戏。当前人数 {len(session.players)}/3。请发送"准备"开始游戏')

@sv.on_fullmatch('准备')
async def player_ready(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '当前群没有进行中的金币炸弹游戏。')
        return

    session = list(game_sessions[group_id].values())[0]
    if session.is_running:
        await bot.send(ev, '游戏已经开始了。')
        return

    await session.player_ready(user_id)

@sv.on_fullmatch('退出游戏')
async def player_quit(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '当前群没有进行中的金币炸弹游戏。')
        return

    session = list(game_sessions[group_id].values())[0]
    await session.player_quit(user_id)

@sv.on_fullmatch('下注')
async def bet(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        # await bot.send(ev, '当前群没有进行中的金币炸弹游戏。') # 避免刷屏
        return

    session = list(game_sessions[group_id].values())[0]
    if not session.is_running:
        await bot.send(ev, '游戏尚未开始，请等待所有玩家准备。')
        return

    await session.bet(user_id)

@sv.on_fullmatch('停止下注')
async def stop_bet(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        # await bot.send(ev, '当前群没有进行中的金币炸弹游戏。') # 避免刷屏
        return

    session = list(game_sessions[group_id].values())[0]
    if not session.is_running:
         await bot.send(ev, '游戏尚未开始，请等待所有玩家准备。')
         return
    await bot.send(ev, f'{MessageSegment.at(user_id)} 停止下注。')
    await session.stop_bet(user_id)
    
    
@sv.on_prefix('关闭游戏')
async def close_game_by_admin(bot: HoshinoBot, ev: Event):
    """
    管理员直接关闭当前群聊中的金币炸弹会话。
    """
    group_id = ev.group_id
    user_id = ev.user_id

    if user_id not in SUPERUSERS:
        await bot.send(ev, "只有管理员才能使用此指令。", at_sender=True)
        return

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '当前群没有进行中的金币炸弹游戏。')
        return

    # 关闭当前群组的所有金币炸弹会话
    sessions_to_close = list(game_sessions[group_id].items())  # 复制一份会话列表，避免迭代中修改字典
    for session_id, session in sessions_to_close:
        # session.close() 会自动取消定时器并从 game_sessions 字典中删除自己
        await session.close() 

    # 确保 group_id 键被删除
    if group_id in game_sessions and not game_sessions[group_id]:
        del game_sessions[group_id]

    await bot.send(ev, '管理员已关闭当前群的金币炸弹游戏。')
    
help_goldboom = '''
金币炸弹游戏帮助：

这是一个最多三人参与的金币奖池游戏。

**游戏流程：**
1.  发送“金币炸弹”发起游戏。
2.  玩家发送“加入游戏”加入游戏。
3.  加入游戏的玩家发送“准备”指令，当所有玩家（至少2人）都准备后，游戏开始。
4.  玩家轮流发送“下注”指令，随机增加自己奖池的金币。
5.  每个玩家的奖池上限为1000金币，超过上限则立即判定失败。
6.  玩家可以发送“停止下注”指令提前结束自己的下注。
7.  当所有玩家都停止下注或失败后，游戏结束，未失败的玩家中，奖池金额最接近上限的玩家获胜，获得自己奖池中的所有金币。
8.  失败的玩家或未获胜的玩家扣除1000金币。
9.  游戏开始前，玩家可以发送“退出游戏”指令退出游戏
10. 如果游戏准备阶段或进行中超过3分钟无人操作（或未结束），则自动关闭会话。

**指令列表：**
* 金币炸弹：发起游戏
* 加入游戏：加入游戏
* 准备：准备游戏
* 退出游戏：退出游戏
* 下注：增加奖池金额
* 停止下注：停止下注
* 金币炸弹帮助：查看游戏帮助
'''
@sv.on_fullmatch('金币炸弹帮助')
async def goldboom_help(bot, ev):
    """
        拉取游戏帮助
    """
    chain = []
    await chain_reply(bot, ev, chain, help_goldboom)
    await bot.send_group_forward_msg(group_id=ev.group_id, messages=chain)