from rcon.source import Client
from config import *
import json
from nonebot import on_command, CommandSession, log, get_bot
from aiocqhttp import Event, Message, MessageSegment
import requests
from PIL import Image, ImageOps
import minecraftmap
from nbt import nbt
import os
import io

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
    with open(RUNTIME, 'r') as file:
        runtime = json.load(file)
        playernameMap: dict[str, str] = runtime['names']
        mapNum: int = runtime['map_num']
        log.logger.debug(str(runtime))
except FileNotFoundError | json.JSONDecodeError:
    playernameMap: dict[str, str] = {}
    mapNum = 100
    runtime = {}
    runtime['names'] = playernameMap
    runtime['map_num'] = mapNum

def save() -> None:
    runtime['map_num'] = mapNum
    with open(RUNTIME, 'w') as file:
        json.dump(runtime, file)

bot = get_bot()
    
def getName(qq: str) -> str | None:
    if qq in playernameMap:
        return playernameMap[qq]
    else:
        return None

def convertImage(url: str) -> int:
    global mapNum
    req = requests.get(url)
    img = Image.open(io.BytesIO(req.content))
    w, h = img.size
    w /= 2
    h /= 2
    r = max(w, h)
    img = img.crop((w-r, h-r, w+r, h+r))
    img = ImageOps.fit(img, (128, 128))
    map = minecraftmap.Map()
    map.file['data']['trackingPosition'].value = 0
    map.file['data'].tags.append(nbt.TAG_Byte(value=1, name='locked'))
    map.im = img
    map.imagetonbt()
    num = mapNum
    mapPath = os.path.join(SERVER_ROOT, WORLD, 'data', 'map_' + str(mapNum) + '.dat')
    map.savenbt(mapPath)
    mapNum += 1
    save()
    removePath = os.path.join(SERVER_ROOT, WORLD, 'data', 'map_' + str(mapNum - MAX_MAP_NUM) + '.dat')
    if os.path.exists(removePath):
        os.remove(removePath)
    return num

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
    save()
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
            raw += '\"' + str(segment) + '\",'
            continue
        if type == 'image':
            try:
                num = convertImage(segment.data['url'])
                log.logger.info('Converted image to map %d' % num)
                raw += '{\"text\":\"[图片]\",\"color\":\"blue\",\"clickEvent\":{\"action\":\"run_command\",\"value\":\"/give @p minecraft:filled_map{map:%d}\"}},' % num
            except Exception as e:
                raise e
                raw += '\"[图片]\",'
            continue
        if type == 'reply':
            raw += '\"回复 \",'
            continue
        if type == 'at':
            targ_qq = segment.data['qq']
            targ_name = getName(targ_qq)
            if not targ_name:
                member = await bot.get_group_member_info(group_id=event.group_id, user_id=targ_qq)
                targ_name = member['card']
            raw += '\"@' + targ_name + ' \",'
    raw = raw[:-1]
    raw += ']'
    if len(raw) <= 3:
        return
    text = '[\"<' + name + '> \",' + raw
    if rcon:
        command = '/tellraw @a {}'.format(text)
        rcon.run(command)
