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
    # Mapping of Roman numerals (in Unicode) to their corresponding integer values
    val_syms = [
        (1000, "\u216F"),  # M
        (900, "\u216D\u216F"),  # CM
        (500, "\u216E"),  # D
        (400, "\u216D\u216E"),  # CD
        (100, "\u216D"),  # C
        (90, "\u2169\u216D"),  # XC
        (50, "\u216C"),  # L
        (40, "\u2169\u216C"),  # XL
        (10, "\u2169"),  # X
        (9, "\u2160\u2169"),  # IX
        (5, "\u2164"),  # V
        (4, "\u2160\u2164"),  # IV
        (1, "\u2160"),  # I
    ]

    roman_num = ""

    for val, sym in val_syms:
        while num >= val:
            roman_num += sym
            num -= val

    return roman_num
