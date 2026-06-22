from config import *
from dataclasses import dataclass
import os
from typing import Any

import nonebot
import aiocqhttp
from nonebot import on_command, CommandSession

bot = nonebot.get_bot()


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
    client = _get_llm_client(config)
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
    await bot.get_group_member_info(group_id=GROUP_ID, user_id=SELF_ID, no_cache=True)

@nonebot.on_notice
async def _(event: nonebot.NoticeSession):
    event = event.event
    if event['notice_type'] != 'group_card' or event['group_id'] != GROUP_ID or event['user_id'] != SELF_ID or event['card_new'] == '':
        return
    await bot.send_group_msg(message = f"谁给我改的{event['card_new']}", group_id = GROUP_ID)
    await bot.set_group_card(group_id = GROUP_ID, user_id = SELF_ID, card = '')
