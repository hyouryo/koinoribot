import ujson
import os

from hoshino import Service
from .aslogin_v3 import as_login_v3, get_purse, dl_save_image, del_custom_bg
from .. import money
from hoshino.util import FreqLimiter
from hoshino import priv

from ..call_me_please.util import *
from .._R import get, userPath
from hoshino.config import SUPERUSERS

path = os.path.join(userPath, 'call_me_please/nickname.json')
flmt = FreqLimiter(60)
flmt_purse = FreqLimiter(30)
cost_num = 0  # 自定义图片需要的金币数

no = f"{get('emotion/no.png').cqcode}"

sv = Service('冰祈小签到')
'''简单的签到插件 生成签到卡片
'''

key_list = ["金币", "幸运币", "星星"]


@sv.on_fullmatch('签到', '冰祈签到', '#签到', '/签到')
async def as_login_bonus(bot, ev):
    uid = ev['user_id']
    if not priv.check_priv(ev, priv.SUPERUSER):
        if not flmt.check(uid):
            await bot.send(ev, f'已经领过签到卡片啦，稍微等一下再来领喔~({round(flmt.left_time(uid))}s)')
            return
    nameList = load_data(path)
    if str(uid) in nameList.keys():
        if nameList[str(uid)]['self']:
            username = nameList[str(uid)]['self']
            nick_flag = 1
        elif nameList[str(uid)]['other']:
            username = nameList[str(uid)]['other']
            nick_flag = 1
        else:
            username = ev.sender['nickname']
            nick_flag = 0
    else:
        username = ev.sender['nickname']
        nick_flag = 0
    qqname = ev.sender['nickname']
    if uid == 80000000:
        qqname = '请不要匿名使用bot'
    imageToSend = await as_login_v3(uid=uid, username=username, qqname=qqname, nick_flag=nick_flag)
    await bot.send(ev, imageToSend)
#    else:
#        msg = as_login(uid, username)
#        await bot.send(ev,
    #        f'[CQ:image,file=base64://{image.image_to_base64(image.text_to_image(msg.strip())).decode()}]')
    flmt.start_cd(uid)


@sv.on_fullmatch('我的钱包', '#我的钱包', '/我的钱包')
async def money_get(bot, ev):
    uid = ev['user_id']
#    if not priv.check_priv(ev, priv.SUPERUSER):
#        if not flmt_purse.check(uid):
#            await bot.send(ev, f'已经领过钱包卡片啦，稍微等一下再来领喔~({round(flmt_purse.left_time(uid))}s)')
#            return
    qqname = ev.sender['nickname']
    if uid == 80000000:
        qqname = '匿名者'
    purse_card = await get_purse(uid=uid, user_name=qqname)
    await bot.send(ev, purse_card)
    flmt_purse.start_cd(uid)


@sv.on_prefix('上传签到图片', '#上传签到图片')
async def upload_bg(bot, ev):
    uid = ev['user_id']
    message = ev.message
    fetch_flag = 0
    for raw_dict in message:
        if raw_dict['type'] == 'image':
            imageUrl = raw_dict['data']['url']
            fetch_flag = 1
    if fetch_flag == 0:
        await bot.send(ev, '请附带图片~')
        return
    await dl_save_image(imageUrl, uid)
    user_gold = money.get_user_money(uid, 'gold')
    if cost_num == 0:
        msg = ""
    else:
        msg = f'(将扣除{cost_num}金币)'
    if user_gold > cost_num:
        await bot.send(ev, f'已上传图片~' + msg)
        money.reduce_user_money(uid, 'gold', cost_num)
    else:
        await bot.send(ev, '金币不足...' + no)
@sv.on_fullmatch('金币排行榜','富豪榜','富翁榜')
async def gold_ranking(bot, ev):
    all_gold_data = money.get_all_user_money('gold')
    
    if not all_gold_data:
        await bot.send(ev, "排行榜暂无数据。")
        return

    # 过滤掉 SUPERUSERS 并转换为 (uid, gold) 元组列表
    ranked_list = [
        (int(uid), gold)
        for uid, gold in all_gold_data.items()
        if int(uid) not in SUPERUSERS
    ]

    if not ranked_list:
        await bot.send(ev, "排行榜暂无数据。")
        return

    # 按金币数量降序排序
    ranked_list.sort(key=lambda item: item[1], reverse=True)

    # 构建排行榜消息
    msg_parts = ["\n🏆 金币排行榜-TOP10 🏆"]
    for rank, (user_id, gold) in enumerate(ranked_list[:10], 1):
        gold_in_wan = gold / 10000
        msg_parts.append(f"第{rank}名: {user_id}: {gold_in_wan:.2f}万")

    # 查找并添加当前用户的排名信息
    current_user_id = ev.user_id
    user_rank = -1
    for i, (uid, gold) in enumerate(ranked_list):
        if uid == current_user_id:
            user_rank = i + 1
            break
            
    if user_rank != -1:
        if user_rank <= 50:
            user_rank_msg = f"您的排名: 第{user_rank}名"
        else:
            total_ranked_users = len(ranked_list)
            percentage = (user_rank / total_ranked_users) * 100
            user_rank_msg = f"您的排名: 位于前{percentage:.0f}%"
    else:
        user_rank_msg = "您未参与排名"
    
    msg_parts.append(f"\n{user_rank_msg}")
    
    final_message = "\n".join(msg_parts)
    await bot.send(ev, final_message, at_sender=True)
    





@sv.on_fullmatch('清除过期用户','清理过期用户')
async def gold_clear(bot, ev):
    """
    由SUPERUSERS触发的命令，用于清理不活跃用户数据。
    """
    # 权限检查：确保只有 SUPERUSERS 可以执行此操作
    if ev.user_id not in SUPERUSERS:
        return

    await bot.send(ev, '正在开始扫描并清理过期用户数据，请稍候...')

    try:
        # 调用核心处理函数
        deleted_uids = money.batch_delete_inactive_users()

        # 根据返回结果向管理员报告
        if not deleted_uids:
            message = '任务完成：没有找到符合条件的过期用户数据。'
        else:
            count = len(deleted_uids)
            # 为了防止消息过长刷屏，只显示部分ID
            if count > 20:
                uid_list_str = '\n'.join(deleted_uids[:20]) + f'\n...等共 {count} 个用户'
            else:
                uid_list_str = '\n'.join(deleted_uids)
            
            message = f'任务完成！成功清除了 {count} 个过期用户的数据。\n\n被删除的用户ID列表：\n{uid_list_str}'
            
        await bot.send(ev, message)

    except Exception as e:
        hoshino.logger.error(f'执行"清除过期数据"任务时发生意外错误: {e}')
        await bot.send(ev, f'执行清理任务时发生内部错误，请检查后台日志。\n错误信息: {e}')


@sv.on_prefix('清除签到图片', '删除签到图片', '#清除签到图片', '#删除签到图片')
async def remove_cstm_bg(bot, ev):
    uid = ev['user_id']
    del_custom_bg(uid)
    await bot.send(ev, '已恢复默认背景~')
