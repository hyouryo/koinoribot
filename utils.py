import base64
import io
import json
import os
import re

import aiohttp
import asyncio
import sys
if sys.platform == "win32" and hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .build_image import BuildImage


def saveData(obj, fp):
    """
    保存数据

    :param obj: 将要保存的数据
    :param fp: 文件路径
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    
    with open(fp, 'w', encoding="utf-8") as file:
        json.dump(obj, file, ensure_ascii=False, indent=2)  # 添加indent使输出更可读

def loadData(fp, is_list=False):
    """
    加载json，不存在则创建

    :param fp: 文件路径
    :param is_list: 如果文件不存在，创建的默认数据类型
    """
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        # 确保目录存在
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        
        default_data = [] if is_list else {}
        with open(fp, 'w', encoding='utf-8') as file:
            json.dump(default_data, file, ensure_ascii=False, indent=2)
        return default_data


def is_http_url(url):
    """
        检查字符串是否为链接
    """
    regex_ = re.compile(
        r'(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if regex_.findall(url):
        return True
    else:
        return False


async def chain_reply(bot, ev, chain, msg, user_id = 0):
    """
        合并转发
    """
    if not user_id:
        user_id = ev.self_id
    user_info = await bot.get_stranger_info(user_id=user_id)
    user_name = user_info['nickname']
    if not user_name.strip('　'):
        user_name = '奇怪的名字'
    data = {
            "type": "node",
            "data": {
                "name": user_name,
                "user_id": str(user_id),
                "content": msg
            }
        }
    chain.append(data)
    return chain


async def get_user_icon(uid) -> BuildImage:
    """
        获取用户头像，返回BuildImage类方便后续处理
    """
    imageUrl = f'https://q1.qlogo.cn/g?b=qq&nk={uid}&src_uin=www.jlwz.cn&s=0'
    async with aiohttp.ClientSession() as session:
        async with session.get(imageUrl) as r:
            content = await r.read()
    iconFile = io.BytesIO(content)
    icon = BuildImage(0, 0, background = iconFile)
    return icon


async def get_net_img(url) -> BuildImage:
    """
        下载网络图片
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            content = await r.read()
    file = io.BytesIO(content)
    icon = BuildImage(0, 0, background = file)
    return icon


async def get_net_img_proxy(url) -> BuildImage:
    """
        下载网络图片（走代理）
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url, proxy = 'http://127.0.0.1:7890') as r:
            content = await r.read()
    file = io.BytesIO(content)
    icon = BuildImage(0, 0, background = file)
    return icon


def pic2b64(pic_path) -> str:
    """
        将图片转换为base64字符串
    """
    b64string = base64.b64encode(open(pic_path, 'rb').read()).decode()
    return b64string
