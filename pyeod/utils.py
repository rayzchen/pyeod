from pyeod import config
import os
import sys
import site
import math
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
        (9, "\u2168"),  # IX
        (8, "\u2167"),  # VIII
        (7, "\u2166"),  # VII
        (6, "\u2165"),  # VI
        (5, "\u2164"),  # V
        (4, "\u2163"),  # IV
        (3, "\u2162"),  # III
        (2, "\u2161"),  # II
        (1, "\u2160"),  # I
    ]

    roman_num = ""

    for val, sym in val_syms:
        while num >= val:
            roman_num += sym
            num -= val

    return roman_num

def calculate_difficulty(tree_size, complexity):
    # Parameters that can be tweaked
    scaling = 1.5
    ideal_tier_size = 8
    disparity_power = 1.1
    large_elem_correction = 5
    minimum_difference = 5

    difficulty = scaling * tree_size * complexity
    tier_size_factor = math.log10(tree_size) / large_elem_correction
    adjusted_tier_size = ideal_tier_size * (1 + tier_size_factor)
    difference = minimum_difference + abs(tree_size - adjusted_tier_size * complexity)
    adjusted_difference = difference ** disparity_power + 1
    difficulty /= adjusted_difference
    return difficulty
