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
        control = importlib.import_module("pyeod.control")
        proc = control.run_webserver()
        try:
            bot = importlib.import_module("pyeod.bot")
            should_continue = bot.run()
        except Exception:
            proc.terminate()
            print_exc()
            print("Restarting bot in 5 seconds")
            time.sleep(5)
        else:
            proc.terminate()
            if not should_continue:
                break


if __name__ == "__main__":
    main()
