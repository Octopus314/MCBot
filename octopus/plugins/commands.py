from nonebot import on_command, CommandSession, get_bot
from config import *
from mctools import QUERYClient
from aiocqhttp import MessageSegment
import re

bot = get_bot()
query = QUERYClient(QUERY_HOST, port=QUERY_PORT)


def is_admin(user_id: int) -> bool:
    return user_id in SUPERUSERS


def extract_at_user(session: CommandSession) -> int | None:
    for segment in session.event.message:
        if segment.type == 'at':
            return int(segment.data['qq'])
    return None


@on_command('/help', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def help(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    message = '基础功能：\n' \
    '/help  展示本信息\n' \
    '/ls    查询服务器内玩家\n' \
    '转发到服务器：\n' \
    '/iam <name>    设置关联的Minecraft ID（也可以乱写）\n' \
    '/whoami        查询关联的Minecraft ID\n' \
    '/connect       重连服务器（服务器挂了以后）\n' \
    '管理员功能：\n' \
    '/ban @用户 [分钟]  禁言用户（默认60分钟）\n' \
    '/unban @用户       解除禁言\n' \
    '/mute              全体禁言\n' \
    '/unmute            解除全体禁言\n' \
    '/kick @用户        踢出用户'
    await bot.send_group_msg(message=message , group_id=GROUP_ID)

@on_command('/ls', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def queryPlayers(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    stats = query.get_full_stats()
    players: list[str] = stats['players']
    players = list(map(lambda player: player[:-4], players)) # remove last \x1b[0m
    message = '\n'.join(players) if len(players) != 0 and len(players[0]) != 0 else '全部睡觉' # return ['\x1b[0m'] when no players online
    await bot.send_group_msg(message=message , group_id=GROUP_ID)


@on_command('/ban', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def ban(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    if not is_admin(session.event.user_id):
        await session.send('你不是管理员')
        return
    target_id = extract_at_user(session)
    if not target_id:
        await session.send('请使用 /ban @用户 [分钟] 格式')
        return
    # 解析禁言时长，默认60分钟
    args = session.current_arg_text.strip()
    duration = 60
    if args:
        time_match = re.search(r'(\d+)\s*分钟?', args)
        if time_match:
            duration = int(time_match.group(1))
    await bot.set_group_ban(group_id=GROUP_ID, user_id=target_id, duration=duration * 60)
    await session.send(f'已禁言用户 {target_id} {duration} 分钟')


@on_command('/unban', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def unban(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    if not is_admin(session.event.user_id):
        await session.send('你不是管理员')
        return
    target_id = extract_at_user(session)
    if not target_id:
        await session.send('请使用 /unban @用户 格式')
        return
    await bot.set_group_ban(group_id=GROUP_ID, user_id=target_id, duration=0)
    await session.send(f'已解除用户 {target_id} 的禁言')


@on_command('/mute', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def mute(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    if not is_admin(session.event.user_id):
        await session.send('你不是管理员')
        return
    await bot.set_group_whole_ban(group_id=GROUP_ID, enable=True)
    await session.send('全体禁言已开启')


@on_command('/unmute', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def unmute(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    if not is_admin(session.event.user_id):
        await session.send('你不是管理员')
        return
    await bot.set_group_whole_ban(group_id=GROUP_ID, enable=False)
    await session.send('全体禁言已关闭')


@on_command('/kick', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def kick(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    if not is_admin(session.event.user_id):
        await session.send('你不是管理员')
        return
    target_id = extract_at_user(session)
    if not target_id:
        await session.send('请使用 /kick @用户 格式')
        return
    await bot.set_group_kick(group_id=GROUP_ID, user_id=target_id)
    await session.send(f'已踢出用户 {target_id}')