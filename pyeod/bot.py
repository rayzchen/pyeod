from . import packagedir, stopfile
import os
import sys
import glob
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from discord import AutoShardedBot # upm packge(py-cord)

if os.path.isfile(".token"):
    print("Loading token")
    with open(".token") as f:
        os.environ["TOKEN"] = f.read().rstrip()

opts = {
    "auto_sync_commands": True
}

if "NO_MAIN_SERVER" not in os.environ:
    from . import main_server
    opts["debug_guilds"] = main_server

def run():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    opts["loop"] = loop

    bot = AutoShardedBot(**opts)
    for file in os.listdir(os.path.join(packagedir, "cogs")):
        bot.load_extension(__name__ + ".cogs." + file.replace(".py", ""))

    try:
        loop.run_until_complete(bot.start(os.getenv("TOKEN")))
    except KeyboardInterrupt:
        print("Stopped")
        return False
    if os.path.isfile(stopfile):
        os.remove(stopfile)
        return False
    return True
