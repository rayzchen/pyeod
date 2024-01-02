from pyeod import config
import os
import sys
import site
import traceback


def format_traceback(err) -> str:
    _traceback = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    error = f"```py\n{_traceback}\n```"
    workdir = os.path.abspath("/<workdir>")
    packagedir = os.path.abspath("/<python>")
    sitepackagedir = os.path.abspath("/<site-packages>")
    error = error.replace(config.package_location, workdir)
    error = error.replace(sys.prefix, packagedir)
    error = error.replace(site.getusersitepackages(), sitepackagedir)
    return error


def format_list(items:list, final_sep:str="or") -> str:
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return str(items[0])
    if len(items) == 2:
        return f"{items[0]} {final_sep} {items[1]}"
    return f"{', '.join(map(str, items[:-1]))}, {final_sep} {items[-1]}"
