#!/usr/bin/env pypy3

from traceback import print_exc
import sys
import time
import importlib


def reset_modules():
    pending = []
    for module in sys.modules:
        if module.startswith("pyeod"):
            pending.append(module)
    for mod in pending:
        sys.modules.pop(mod)

# Do not run web server in production
if len(sys.argv) > 1:
    run_web_server = False
else:
    run_web_server = True

def main():
    while True:
        reset_modules()
        proc = None
        if run_web_server:
            control = importlib.import_module("pyeod.control")
            proc = control.run_webserver()
        try:
            bot = importlib.import_module("pyeod.bot")
            should_continue = bot.run()
        except Exception:
            if proc is not None:
                proc.terminate()
            print_exc()
            print("Restarting bot in 5 seconds")
            time.sleep(5)
        else:
            if proc is not None:
                proc.terminate()
            if not should_continue:
                break


if __name__ == "__main__":
    main()
