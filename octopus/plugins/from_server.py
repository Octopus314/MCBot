import os
from config import *
import nonebot

try:
    logFile = open(os.path.join(SERVER_ROOT, 'logs/latest.log'))
    logFile.seek(0, 2)
except FileNotFoundError:
    nonebot.log.logger.error('Unable to open log file, maybe server not started? ')
    if not DEBUG:
        exit(0)

@nonebot.scheduler.scheduled_job('interval', seconds = CHECK_INTERVAL)
async def _():
    bot = nonebot.get_bot()
    while True:
        line = logFile.readline()
        if not line:
            break
        line = line.split(LOG_IDENTIFIER, 1)
        if len(line) == 1:
            continue
        await nonebot.get_bot().send_group_msg(group_id = GROUP_ID, message = line[1])

@nonebot.scheduler.scheduled_job('cron', day = '*', hour = 0, minute = 0, second = 1)
async def _():
    logFile.seek(0, 2)
    nonebot.log.logger.info('New day, reseek logger file. ')