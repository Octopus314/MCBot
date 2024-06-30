import nonebot
import config
import os

if __name__ == "__main__":
    nonebot.init(config)
    nonebot.load_plugins(os.path.join(os.path.dirname(__file__), 'octopus', 'plugins'), 'octopus.plugins')
    nonebot.run()