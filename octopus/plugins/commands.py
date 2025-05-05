from nonebot import on_command, CommandSession, get_bot
from config import *
from mctools import QUERYClient

bot = get_bot()
query = QUERYClient(QUERY_HOST, port=QUERY_PORT)

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
    '/connect       重连服务器（服务器挂了以后）'
    await bot.send_group_msg(message=message , group_id=GROUP_ID)

@on_command('/ls', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def queryPlayers(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    stats = query.get_full_stats()
    players: list[str] = stats['players']
    players = list(map(lambda player: player[:-4], players)) # remove last \x1b[0m
    message = '\n'.join(players) if len(players) == 0 else '全部睡觉' 
    await bot.send_group_msg(message=message , group_id=GROUP_ID)