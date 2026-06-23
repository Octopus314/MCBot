from config import *
import asyncio
from prompt import *
from collections import deque
from dataclasses import dataclass
import json
import os
from typing import Any
from urllib.parse import urlparse

import nonebot
import aiocqhttp
from aiocqhttp import MessageSegment
from aiocqhttp.exceptions import ApiNotAvailable
from nonebot import on_command, CommandSession

bot = nonebot.get_bot()
LATTE = 1872230241
RECENT_MESSAGE_LIMIT = 25
LATTE_CHECK_INTERVAL = 5
LATTE_MUTE_DURATION = 60
LATTE_IMAGE_NAME_MAP: dict[str, str] = {
    "A25718E642427CAAF34CFBD329007EF8": "这小学生",
    "2B4082A96C5B33330ED9D0802043BDDD": "这日本人",
    "862BDF4221969D5DDB01D39E684DACC6": "册那",
    "B99D515802EBDC2397C5D227FEC01ACE": "做狗这方面我真的不如你"
}
recent_messages: deque['StoredMessage'] = deque(maxlen=RECENT_MESSAGE_LIMIT)
last_asked_latte_message: 'StoredMessage | None' = None
latte_inflight_message: 'StoredMessage | None' = None
latte_check_task: asyncio.Task | None = None


@dataclass
class StoredMessage:
    message_id: int
    user_id: int
    text: str


@dataclass
class LLMConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str = 'gpt-4o-mini'
    timeout: float = 60.0
    max_retries: int = 2


class LLMNotConfiguredError(RuntimeError):
    pass


_llm_client = None
_llm_client_key: tuple[str | None, str | None, float, int] | None = None


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        api_key=globals().get('LLM_API_KEY') or os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY'),
        base_url=globals().get('LLM_BASE_URL') or os.getenv('LLM_BASE_URL') or os.getenv('OPENAI_BASE_URL'),
        model=globals().get('LLM_MODEL') or os.getenv('LLM_MODEL') or 'gpt-4o-mini',
        timeout=float(globals().get('LLM_TIMEOUT') or os.getenv('LLM_TIMEOUT') or 60.0),
        max_retries=int(globals().get('LLM_MAX_RETRIES') or os.getenv('LLM_MAX_RETRIES') or 2),
    )


def llm_available() -> bool:
    return bool(get_llm_config().api_key)


def _get_llm_client(config: LLMConfig | None = None):
    global _llm_client, _llm_client_key

    config = config or get_llm_config()
    if not config.api_key:
        raise LLMNotConfiguredError('Set LLM_API_KEY or OPENAI_API_KEY before calling the LLM API.')

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise LLMNotConfiguredError('Install the openai package before calling the LLM API.') from exc

    key = (config.api_key, config.base_url, config.timeout, config.max_retries)
    if _llm_client is None or _llm_client_key != key:
        _llm_client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        _llm_client_key = key
    return _llm_client


async def llm_chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    config = get_llm_config()
    client = await asyncio.to_thread(_get_llm_client, config)
    params: dict[str, Any] = {
        'model': model or config.model,
        'messages': messages,
    }
    if temperature is not None:
        params['temperature'] = temperature
    if max_tokens is not None:
        params['max_tokens'] = max_tokens
    params.update(kwargs)

    response = await client.chat.completions.create(**params)
    return response.choices[0].message.content or ''


async def ask_llm(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> str:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    return await llm_chat(messages, model=model, **kwargs)


def _image_name(data: dict[str, Any]) -> str:
    nonebot.log.logger.debug(f'Image data: {data}')
    name = data.get('file_unique') # only unique useful
    return str(name).upper() if name else 'unknown'


def segment_to_text(segment: Any) -> str | None:
    type_ = getattr(segment, 'type', None)
    data = getattr(segment, 'data', {}) or {}

    if type_ == 'text':
        return str(segment)
    if type_ == 'image':
        name = _image_name(data)
        return LATTE_IMAGE_NAME_MAP.get(name, f'[图片:{name}]')
    return None


def event_to_text(event: aiocqhttp.Event) -> str:
    parts: list[str] = []
    for segment in event.message:
        text = segment_to_text(segment)
        if text:
            parts.append(text)
    return ''.join(parts)


def _msg_format(message: StoredMessage) -> str:
    return f'message_id={message.message_id} sender={message.user_id}: {message.text}'


def _same_message(left: StoredMessage | None, right: StoredMessage | None) -> bool:
    return bool(left and right and left.message_id == right.message_id)


def build_latte_prompt(previous: StoredMessage | None, messages: list[StoredMessage]) -> str | None:
    previous_text = _msg_format(previous) if previous else 'None'
    context = '\n'.join(_msg_format(message) for message in messages)
    nonebot.log.logger.debug(f'Building prompt with previous_message={previous_text} and context:\n{context}')
    return PROMPT.format(previous_message=previous_text, context_messages=context)


def parse_llm_json(response: str) -> dict[str, Any] | None:
    text = response.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        nonebot.log.logger.warning(f'Unable to parse LLM response as JSON: {response}')
        return None
    if not isinstance(parsed, dict):
        nonebot.log.logger.warning(f'LLM JSON response is not an object: {response}')
        return None
    return parsed


def should_mute_latte(result: dict[str, Any]) -> bool:
    mute_messages = result.get('mute_messages')
    return result.get('should_mute') is True and isinstance(mute_messages, list) and len(mute_messages) > 0


def mute_target_info(result: dict[str, Any], fallback: StoredMessage) -> tuple[int, str]:
    mute_messages = result.get('mute_messages')
    if isinstance(mute_messages, list) and mute_messages:
        first = mute_messages[0]
        if isinstance(first, dict):
            message_id = first.get('message_id')
            reason = first.get('reason')
            try:
                message_id = int(message_id)
            except (TypeError, ValueError):
                message_id = fallback.message_id
            reason = str(reason).strip() if reason else '该禁言了'
            return message_id, reason
    reason = result.get('reason')
    return fallback.message_id, str(reason).strip() if reason else '该禁言了'


async def mute_latte(duration: int = LATTE_MUTE_DURATION) -> None:
    await bot.set_group_ban(group_id=GROUP_ID, user_id=LATTE, duration=duration)
    await asyncio.sleep(5)
    await bot.set_group_ban(group_id=GROUP_ID, user_id=LATTE, duration=0)


@bot.on_message
async def keep_recent_messages(event: aiocqhttp.Event):
    if getattr(event, 'group_id', None) != GROUP_ID:
        return

    text = event_to_text(event)
    if not text:
        return

    recent_messages.append(StoredMessage(
        message_id=event.message_id,
        user_id=event.user_id,
        text=text,
    ))


@nonebot.scheduler.scheduled_job('interval', seconds=LATTE_CHECK_INTERVAL)
async def check_latte_messages():
    global latte_check_task

    messages = list(recent_messages)
    latest_latte_message = next((message for message in reversed(messages) if message.user_id == LATTE), None)
    if not latest_latte_message:
        return
    if _same_message(latest_latte_message, last_asked_latte_message):
        return
    if _same_message(latest_latte_message, latte_inflight_message):
        return
    if latte_check_task and not latte_check_task.done():
        return
    latte_check_task = asyncio.create_task(process_latte_messages(last_asked_latte_message, messages, latest_latte_message))


async def process_latte_messages(
    previous: StoredMessage | None,
    messages: list[StoredMessage],
    latest_latte_message: StoredMessage,
):
    global last_asked_latte_message, latte_inflight_message

    if _same_message(latest_latte_message, last_asked_latte_message):
        return
    if _same_message(latest_latte_message, latte_inflight_message):
        return

    prompt = build_latte_prompt(previous, messages)
    if not prompt:
        return

    latte_inflight_message = latest_latte_message
    try:
        nonebot.log.logger.debug(f'Sending LLM request through message {latest_latte_message.message_id}')
        response = await ask_llm(prompt)
        nonebot.log.logger.debug(f'LLM response through message {latest_latte_message.message_id}: {response}')
        result = parse_llm_json(response)
    except LLMNotConfiguredError as exc:
        nonebot.log.logger.error(str(exc))
        return
    except Exception as exc:
        nonebot.log.logger.exception(exc)
        return
    finally:
        if _same_message(latte_inflight_message, latest_latte_message):
            latte_inflight_message = None

    if not result:
        nonebot.log.logger.warning(f'No usable LLM JSON result through message {latest_latte_message.message_id}')
        return
    last_asked_latte_message = latest_latte_message
    nonebot.log.logger.debug(f'LLM JSON result through message {latest_latte_message.message_id}: {result}')

    if should_mute_latte(result):
        target_message_id, reason = mute_target_info(result, latest_latte_message)
        nonebot.log.logger.info(f'Muting Latte because {reason}')
        await bot.send_group_msg(
            group_id=GROUP_ID,
            message=MessageSegment.reply(target_message_id) + MessageSegment.text(reason),
        )
        await mute_latte()


@on_command('/llm', permission=lambda sender: sender.is_groupchat, only_to_me=False)
async def call_llm(session: CommandSession):
    if session.event.group_id != GROUP_ID:
        return

    message = session.current_arg_text.strip()
    if not message:
        return

    try:
        response = await ask_llm(message + '\n\n请简短回答，控制在50字以内。')
    except LLMNotConfiguredError as exc:
        nonebot.log.logger.error(str(exc))
        await session.send('LLM 还没配好')
        return
    except Exception as exc:
        nonebot.log.logger.exception(exc)
        await session.send('LLM 调用失败')
        return

    await session.send(response or 'LLM 没有返回内容')


@nonebot.scheduler.scheduled_job('cron', minute='*')
async def _():
    try:
        await bot.get_group_member_info(group_id=GROUP_ID, user_id=SELF_ID, no_cache=True)
    except ApiNotAvailable:
        nonebot.log.logger.warning('CQHTTP API is not available while refreshing group member info.')

@nonebot.on_notice
async def _(event: nonebot.NoticeSession):
    event = event.event
    if event['notice_type'] != 'group_card' or event['group_id'] != GROUP_ID or event['user_id'] != SELF_ID or event['card_new'] == '':
        return
    await bot.send_group_msg(message = f"谁给我改的{event['card_new']}", group_id = GROUP_ID)
    await bot.set_group_card(group_id = GROUP_ID, user_id = SELF_ID, card = '')
