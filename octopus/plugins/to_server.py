from rcon.source import Client
from config import *
import json
from nonebot import on_command, CommandSession, log, get_bot
from aiocqhttp import Event, Message, MessageSegment

try:
    rcon = Client(host=RCON_HOST, port=RCON_PORT, passwd=RCON_PASSWD)
    rcon.connect(True)
    log.logger.info('Rcon connected.')
except ConnectionError:
    rcon = None
    log.logger.error('Unable to connect rcon.')
    if not DEBUG:
        exit(0)

try:
    with open(PLAYERNAME_MAP_PATH, 'r') as file:
        playernameMap: dict[str, str] = json.load(file)
        log.logger.debug(str(playernameMap))
except FileNotFoundError | json.JSONDecodeError:
    playernameMap: dict[str, str] = {}

bot = get_bot()
    
def getName(qq: str) -> str | None:
    if qq in playernameMap:
        return playernameMap[qq]
    else:
        return None

@on_command('/setplayername', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def setPlayerName(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    name = session.current_arg_text.strip()
    if not name:
        await session.send('你设置你妈呢')
        return
    name = name.split(' ')[0]
    qq = str(session.event.user_id)
    playernameMap[qq] = name
    with open(PLAYERNAME_MAP_PATH, 'w') as file:
        json.dump(playernameMap, file)
    await session.send('设置完成')

@on_command('/whoami', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def getPlayerName(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return
    qq = str(session.event.user_id)
    if qq in playernameMap:
        await session.send(playernameMap[qq])
        return
    else:
        await session.send("你是？")
        return

@bot.on_message
async def forward(event: Event):
    if event.group_id != GROUP_ID:
        return
    qq = str(event.user_id)
    name = getName(qq)
    if not name:
        name = event.sender['card']
    message: Message = event.message
    if not message:
        return
    raw = ''
    for segment in message:
        segment: MessageSegment
        type = segment.type
        if type == 'text':
            raw += str(segment)
            continue
        if type == 'image':
            raw += '[图片]'
            continue
        if type == 'reply':
            raw += '回复'
            continue
        if type == 'at':
            targ_qq = segment.data['qq']
            targ_name = getName(targ_qq)
            if not targ_name:
                member = await bot.get_group_member_info(group_id=event.group_id, user_id=targ_qq)
                targ_name = member['card']
            raw += '@' + targ_name + ' '
    if len(raw) == 0:
        return
    text = '<' + name + '> ' + raw
    if rcon:
        command = '/tellraw @a \"{}\"'.format(text)
        rcon.run(command)
