import traceback
from pyeod import config
import os
import sys


def format_traceback(err):
    _traceback = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    error = f"```py\n{_traceback}\n```"
    workdir = os.path.abspath("/<workdir>")
    packagedir = os.path.abspath("/<python>")
    error = error.replace(config.package_location, workdir)
    error = error.replace(sys.prefix, packagedir)
    return error


def format_list(items, final_sep="or"):
    if len(items) == 0:
        return ""
    elif len(items) == 1:
        return str(items[0])
    elif len(items) == 2:
        return f"{items[0]} {final_sep} {items[1]}"
    else:
        return f"{', '.join(map(str, items[:-1]))}, {final_sep} {items[-1]}"
