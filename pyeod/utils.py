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


def format_list(items: list, final_sep: str = "or") -> str:
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return str(items[0])
    if len(items) == 2:
        return f"{items[0]} {final_sep} {items[1]}"
    return f"{', '.join(map(str, items[:-1]))}, {final_sep} {items[-1]}"


def int_to_roman(num: int) -> str:
    # Mapping of Roman numerals to their corresponding integer values
    val_syms = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]

    roman_num = ""

    for val, sym in val_syms:
        while num >= val:
            roman_num += sym
            num -= val

    return roman_num
