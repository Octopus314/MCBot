from config import *
import nonebot
import aiocqhttp

bot = nonebot.get_bot()

@nonebot.scheduler.scheduled_job('cron', minute='*')
async def _():
    await bot.get_group_member_info(group_id=GROUP_ID, user_id=SELF_ID, no_cache=True)

@nonebot.on_notice
async def _(event: nonebot.NoticeSession):
    event = event.event
    if event['notice_type'] != 'group_card' or event['group_id'] != GROUP_ID or event['user_id'] != SELF_ID or event['card_new'] == '':
        return
    await bot.send_group_msg(message = f"谁给我改的{event['card_new']}", group_id = GROUP_ID)
    await bot.set_group_card(group_id = GROUP_ID, user_id = SELF_ID, card = '')
