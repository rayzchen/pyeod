from traceback import print_exc
import importlib
import sys
import time

def reset_modules():
    pending = []
    for module in sys.modules:
        if module.startswith("pyeod"):
            pending.append(module)
    for mod in pending:
        sys.modules.pop(mod)

def main():
    # Auto restart
    while True:
        reset_modules()
        try:
            bot = importlib.import_module("pyeod.bot")
            cont = bot.run()
            if not cont:
                break
        except Exception:
            print_exc()
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
