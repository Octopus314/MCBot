import os
from config import *
import nonebot
import re

LOG_PATH = os.path.join(SERVER_ROOT, 'logs/latest.log')

try:
    logFile = open(LOG_PATH, 'r')
    logFile.seek(0, 2)
except FileNotFoundError:
    nonebot.log.logger.error('Unable to open log file, maybe server not started? ')
    if not DEBUG:
        exit(0)

def needForward(str: str) -> bool:
    return re.match('<.*>', str) or str.endswith(' the game') or re.match('Done \(.*\)!', str)

@nonebot.scheduler.scheduled_job('interval', seconds = CHECK_INTERVAL)
async def _():
    global logFile
    bot = nonebot.get_bot()
    if os.path.getsize(LOG_PATH) < logFile.tell():
        nonebot.log.logger.info("Reseeking log file.")
        logFile.close()
        logFile = open(LOG_PATH, 'r')
        logFile.seek(0, 2)
    while True:
        line = logFile.readline()
        if not line:
            break
        line = line.split(LOG_IDENTIFIER, 1)
        if len(line) == 1:
            continue
        line = line[1]
        line = line[:-1] # remove \n
        if not needForward(line):
            continue
        await bot.send_group_msg(group_id = GROUP_ID, message = line)