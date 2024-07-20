from rcon.source import Client
from config import *
import json
from nonebot import on_command, CommandSession, log, get_bot
import aiocqhttp

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

@get_bot().on_message
async def forward(event: aiocqhttp.Event):
    if event.group_id != GROUP_ID:
        return
    qq = str(event.user_id)
    if qq in playernameMap:
        name = playernameMap[qq]
    else:
        name = event.sender['card']
    text = '<' + name + '> ' + event.raw_message
    if rcon:
        command = '/tellraw @a \"{}\"'.format(text)
        rcon.run(command)
