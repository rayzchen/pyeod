import traceback
from pyeod import config
import os
import sysconfig


def format_traceback(err):
    _traceback = "".join(traceback.format_exception(
        type(err),
        err,
        err.__traceback__
    ))
    error = f"```py\n{_traceback}\n```"
    workdir = os.path.abspath("/<workdir>")
    packagedir = os.path.abspath("/<packages>")
    error = error.replace(config.package_location, workdir)
    error = error.replace(sysconfig.get_paths()["stdlib"], packagedir)
    return error
