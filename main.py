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
    while True:
        reset_modules()
        try:
            bot = importlib.import_module("pyeod.bot")
            should_continue = bot.run()
            if not should_continue:
                break
        except Exception:
            print_exc()
            print("Restarting bot in 5 seconds")
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
