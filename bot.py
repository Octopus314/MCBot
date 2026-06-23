import logging
from logging.handlers import RotatingFileHandler
import nonebot
import config
import os

os.makedirs("logs", exist_ok=True)

if __name__ == "__main__":
    nonebot.init(config)
    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=5 * 1024 * 1024, # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s %(name)s] %(levelname)s: %(message)s"
    ))
    file_handler.setLevel(logging.DEBUG)

    nonebot.log.logger.addHandler(file_handler)
    nonebot.log.logger.setLevel(logging.DEBUG)
    nonebot.load_plugins(os.path.join(os.path.dirname(__file__), 'octopus', 'plugins'), 'octopus.plugins')
    # nonebot.load_plugin('octopus.plugins.from_server')
    nonebot.run()