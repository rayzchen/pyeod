"""
A separate file to store the achievements dict
purely to not clutter the rest of pyeod.model.
The only thing that should be exported is the
`achievements` var and the `user_icons` var.

"""

from pyeod.utils import calculate_difficulty


__all__ = ["achievements", "user_icons"]

# TODO Cache more shit so achievement check doesn't bog element making
element_stats_cache = {}
element_info_cache = {}


def boundary_list_check(boundaries, value):
    if value >= boundaries[-1]:
        return int(len(boundaries) - 1 + value // boundaries[-1])
    for i in range(len(boundaries) - 2, -1, -1):  # Iterate backwards from 2nd last
        if value >= boundaries[i]:
            return i
    return None


def get_nearest_boundary(boundaries, value):
    for boundary in boundaries:
        if value < boundary:
            return (boundary, value)
    return (int((value // boundaries[-1] + 1) * boundaries[-1]), value)


async def cache_element_stats(instance, user):
    if user.id not in element_stats_cache:
        element_stats_cache[user.id] = {
            "last_checked_inv_pos": 0,
            "highest_complexity": 0,
            "highest_tree_size": 0,
            "highest_difficulty": 0,
        }
    for element_id in user.inv[element_stats_cache[user.id]["last_checked_inv_pos"] :]:
        complexity = instance.db.complexities[element_id]
        if complexity > element_stats_cache[user.id]["highest_complexity"]:
            element_stats_cache[user.id]["highest_complexity"] = complexity
        tree_size = len(instance.db.path_lookup[element_id])
        if tree_size > element_stats_cache[user.id]["highest_tree_size"]:
            element_stats_cache[user.id]["highest_tree_size"] = tree_size
        difficulty = calculate_difficulty(tree_size, complexity)
        if difficulty > element_stats_cache[user.id]["highest_difficulty"]:
            element_stats_cache[user.id]["highest_difficulty"] = difficulty
    element_stats_cache[user.id]["last_checked_inv_pos"] = len(user.inv) - 1


async def cache_element_info(instance, user):
    element_info_cache[user.id] = {
        "elements_imaged": 0,
        "elements_colored": 0,
        "elements_iconed": 0,
        "elements_marked": 0,
    }
    for element in instance.db.elements.values():
        if element.imager == user:
            element_info_cache[user.id]["elements_imaged"] += 1
        if element.colorer == user:
            element_info_cache[user.id]["elements_colored"] += 1
        if element.iconer == user:
            element_info_cache[user.id]["elements_iconed"] += 1
        if element.marker == user:
            element_info_cache[user.id]["elements_marked"] += 1


elements_collected_boundaries = [
    25,
    50,
    100,
    250,
    500,
    1_000,
    2_500,
    5_000,
    10_000,
    25_000,
]


async def elements_collected_check(instance, user):
    async with instance.db.user_lock.reader:
        element_amount = len(user.inv)
        return boundary_list_check(elements_collected_boundaries, element_amount)


async def elements_collected_progress(instance, user):
    async with instance.db.user_lock.reader:
        element_amount = len(user.inv)
        return get_nearest_boundary(elements_collected_boundaries, element_amount)


elements_created_boundaries = [
    50,
    100,
    200,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
    1_000,
    2_000,
    3_000,
    4_000,
    5_000,
    7_500,
    10_000,
    12_500,
    15_000,
]


async def elements_created_check(instance, user):
    async with instance.db.user_lock.reader:
        combos_created = user.created_combo_count
        return boundary_list_check(elements_created_boundaries, combos_created)


async def elements_created_progress(instance, user):
    async with instance.db.user_lock.reader:
        combos_created = user.created_combo_count
        return get_nearest_boundary(elements_created_boundaries, combos_created)


votes_cast_boundaries = [1, 25, 50, 125, 250, 500, 1_000]


async def votes_cast_check(instance, user):
    async with instance.db.user_lock.reader:
        cast_votes = user.votes_cast_count
        return boundary_list_check(votes_cast_boundaries, cast_votes)


async def votes_cast_progress(instance, user):
    async with instance.db.user_lock.reader:
        cast_votes = user.votes_cast_count
        return get_nearest_boundary(votes_cast_boundaries, cast_votes)


async def leaderboard_pos_check(instance, user):
    async with instance.db.user_lock.reader:
        leaderboard_position = (
            sorted(
                instance.db.users.keys(),
                key=lambda key: len(instance.db.users[key].inv),
                reverse=True,
            ).index(user.id)
            + 1
        )
        if leaderboard_position == 1:
            return 3
        if leaderboard_position == 2:
            return 2
        if leaderboard_position == 3:
            return 1
        if leaderboard_position <= 10:
            return 0
        return None


async def leaderboard_pos_progress(instance, user):
    async with instance.db.user_lock.reader:
        leaderboard_position = (
            sorted(
                instance.db.users.keys(),
                key=lambda key: len(instance.db.users[key].inv),
                reverse=True,
            ).index(user.id)
            + 1
        )
        if leaderboard_position == 1:
            return (0, 1)
        if leaderboard_position == 2:
            return (1, 2)
        if leaderboard_position == 3:
            return (2, 3)
        if leaderboard_position <= 10:
            return (3, leaderboard_position)
        return (10, leaderboard_position)


async def achievement_achievement_check(
    instance, user
):  # Hijack achievements to cache shit
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        await cache_element_info(instance, user)
        await cache_element_stats(instance, user)
        achievement_amount = len(user.achievements)
        if achievement_amount > 0:
            return achievement_amount // 10


async def achievement_achievement_progress(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        await cache_element_info(instance, user)
        await cache_element_stats(instance, user)
        achievement_amount = len(user.achievements)
        return ((achievement_amount // 10 + 1) * 10, achievement_amount)


element_ids_in_a_row_boundaries = [
    11,
    55,
    111,
    555,
    1_111,
    5_555,
]


async def element_ids_in_a_row_check(instance, user):
    async with instance.db.user_lock.reader:
        highest_in_a_row = 0
        id_to_check = 0
        while highest_in_a_row < len(user.inv):
            id_to_check += 1
            # Missing Element Ids
            if instance.db.elem_id_lookup.get(id_to_check) is None:
                continue
            if sorted(user.inv)[highest_in_a_row] != id_to_check:
                break
            highest_in_a_row += 1
        return boundary_list_check(element_ids_in_a_row_boundaries, highest_in_a_row)


async def element_ids_in_a_row_progress(instance, user):
    async with instance.db.user_lock.reader:
        highest_in_a_row = 0
        id_to_check = 0
        while highest_in_a_row < len(user.inv):
            id_to_check += 1
            # Missing Element Ids
            if instance.db.elem_id_lookup.get(id_to_check) is None:
                continue
            if sorted(user.inv)[highest_in_a_row] != id_to_check:
                break
            highest_in_a_row += 1
        return get_nearest_boundary(element_ids_in_a_row_boundaries, highest_in_a_row)


editable_element_info_boundaries = [
    1,
    5,
    10,
    25,
    50,
    100,
    200,
    400,
    800,
    1600,
    3200,
]


async def mark_check(instance, user):
    async with instance.db.user_lock.reader:
        return boundary_list_check(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_marked"],
        )


async def mark_progress(instance, user):
    async with instance.db.user_lock.reader:
        return get_nearest_boundary(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_marked"],
        )


async def image_check(instance, user):
    async with instance.db.user_lock.reader:
        return boundary_list_check(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_imaged"],
        )


async def image_progress(instance, user):
    async with instance.db.user_lock.reader:
        return get_nearest_boundary(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_imaged"],
        )


async def color_check(instance, user):
    async with instance.db.user_lock.reader:
        return boundary_list_check(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_colored"],
        )


async def color_progress(instance, user):
    async with instance.db.user_lock.reader:
        return get_nearest_boundary(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_colored"],
        )


async def icon_check(instance, user):
    async with instance.db.user_lock.reader:
        return boundary_list_check(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_iconed"],
        )


async def icon_progress(instance, user):
    async with instance.db.user_lock.reader:
        return get_nearest_boundary(
            editable_element_info_boundaries,
            element_info_cache[user.id]["elements_iconed"],
        )


element_complexity_boundaries = [
    5,
    10,
    15,
    20,
    25,
    35,
    45,
    55,
    65,
    75,
    90,
    105,
    120,
    135,
    150,
    170,
    190,
    210,
    230,
    250,
]


async def complexity_check(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return boundary_list_check(
            element_complexity_boundaries,
            element_stats_cache[user.id]["highest_complexity"],
        )


async def complexity_progress(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return get_nearest_boundary(
            element_complexity_boundaries,
            element_stats_cache[user.id]["highest_complexity"],
        )


element_tree_size_boundaries = [
    250,
    300,
    400,
    500,
    750,
    1_000,
    1_250,
    1_500,
    2_000,
    2_500,
    3_000,
    4_000,
    5_000,
    10_000,
    25_000,
    50_000,
]


async def tree_size_check(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return boundary_list_check(
            element_tree_size_boundaries,
            element_stats_cache[user.id]["highest_tree_size"],
        )


async def tree_size_progress(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return get_nearest_boundary(
            element_tree_size_boundaries,
            element_stats_cache[user.id]["highest_tree_size"],
        )


element_difficulty_boundaries = [
    5,
    10,
    25,
    50,
    80,
    120,
    200,
    300,
    400,
    500,
    600,
    750,
    1000,
    1300,
    1600,
    2000,
    2500,
    3000,
]


async def difficulty_check(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return boundary_list_check(
            element_difficulty_boundaries,
            element_stats_cache[user.id]["highest_difficulty"],
        )


async def difficulty_progress(instance, user):
    async with instance.db.user_lock.reader, instance.db.element_lock.reader:
        return get_nearest_boundary(
            element_difficulty_boundaries,
            element_stats_cache[user.id]["highest_difficulty"],
        )


# Format:
# names: list[str] = the tier names
# default: str = what is defaulted to if the req_func returns an index outside of the names list (roman numerals added based on how far off the returned index is)
# req_func: Callable[[GameInstance, User], int] = the function that takes in user data and returns the appropriate tier of achievement
# progress_func: Callable[[GameInstance, User], Tuple[int, int]] = function that takes in user data and returns the next goal and the current value

achievements = {
    -1: {
        "names": ["Achievement get!"],
        "default": "Achiever",
        "req_func": achievement_achievement_check,
        "progress_func": achievement_achievement_progress,
        "items": "Achievement",
    },
    0: {
        "names": [
            "Beginner Elementalist Ⅰ",
            "Beginner Elementalist Ⅱ",
            "Beginner Elementalist Ⅲ",
            "Elementalist Ⅰ",
            "Elementalist Ⅱ",
            "Elementalist Ⅲ",
            "True Elementalist Ⅰ",
            "True Elementalist Ⅱ",
            "True Elementalist Ⅲ",
        ],
        "default": "Ultimate Elementalist",
        "req_func": elements_collected_check,
        "progress_func": elements_collected_progress,
        "items": "Element",
    },
    1: {
        "names": [
            "Creator Ⅰ",
            "Creator Ⅱ",
            "Creator Ⅲ",
            "Creator Ⅳ",
            "Creator Ⅴ",
            "Creator Ⅵ",
            "Creator Ⅶ",
            "Creator Ⅷ",
            "Creator Ⅸ",
            "Creator Ⅹ",
            "Strong Creator Ⅰ",
            "Strong Creator Ⅱ",
            "Strong Creator Ⅲ",
            "Strong Creator Ⅳ",
            "Powerful Creator Ⅰ",
            "Powerful Creator Ⅱ",
            "Powerful Creator Ⅲ",
            "Powerful Creator Ⅳ,",
        ],
        "default": "Mighty Creator",
        "req_func": elements_created_check,
        "progress_func": elements_created_progress,
        "items": "Created Combo",
    },
    2: {
        "names": [
            "I Voted!",
            "New Voter",
            "Voter",
            "Keen Voter",
            "Dedicated Voter",
            "Avid Voter",
        ],
        "default": "Judge",
        "req_func": votes_cast_check,
        "progress_func": votes_cast_progress,
        "items": "Vote",
    },
    3: {
        "names": [
            "🏆 Top ten",
            "🥉 Bronze age",
            "🥈 2nd is the best",
            "🥇 Top of the pack",
        ],
        "req_func": leaderboard_pos_check,
        "progress_func": leaderboard_pos_progress,
        "items": "Leaderboard Position",
        # No default as it is impossible for an outside index to be returned
        "default": None,
    },
    4: {
        "names": [
            "Order Wanter Ⅰ",
            "Order Wanter ⅠⅠ",
            "Order Protector Ⅰ",
            "Order Protector ⅠⅠ",
            "Order Keeper Ⅰ",
            "Order Keeper ⅠⅠ",
        ],
        "req_func": element_ids_in_a_row_check,
        "progress_func": element_ids_in_a_row_progress,
        "items": "Elements in a row",
        "default": "Order Guardian",
    },
    5: {
        "names": [
            "First marked element",
            "Writer Ⅰ",
            "Writer Ⅱ",
            "Writer Ⅲ",
            "Writer Ⅳ",
            "Writer Ⅴ",
            "Writer Ⅵ",
            "Writer Ⅶ",
            "Writer Ⅷ",
            "Writer Ⅸ",
            "Writer Ⅹ",
        ],
        "req_func": mark_check,
        "progress_func": mark_progress,
        "items": "Marked Element",
        "default": "Novelist",
    },
    6: {
        "names": [
            "First imaged element",
            "Imager Ⅰ",
            "Imager Ⅱ",
            "Imager Ⅲ",
            "Imager Ⅳ",
            "Imager Ⅴ",
            "Imager Ⅵ",
            "Imager Ⅶ",
            "Imager Ⅷ",
            "Imager Ⅸ",
            "Imager Ⅹ",
        ],
        "req_func": image_check,
        "progress_func": image_progress,
        "items": "Imaged Element",
        "default": "Photographer",
    },
    7: {
        "names": [
            "First colored element",
            "Colorer Ⅰ",
            "Colorer Ⅱ",
            "Colorer Ⅲ",
            "Colorer Ⅳ",
            "Colorer Ⅴ",
            "Colorer Ⅵ",
            "Colorer Ⅶ",
            "Colorer Ⅷ",
            "Colorer Ⅸ",
            "Colorer Ⅹ",
        ],
        "req_func": color_check,
        "progress_func": color_progress,
        "items": "Colored Element",
        "default": "Artist",
    },
    8: {
        "names": [
            "First iconed element",
            "Iconic Ⅰ",
            "Iconic Ⅱ",
            "Iconic Ⅲ",
            "Iconic Ⅳ",
            "Iconic Ⅴ",
            "Iconic Ⅵ",
            "Iconic Ⅶ",
            "Iconic Ⅷ",
            "Iconic Ⅸ",
            "Iconic Ⅹ",
        ],
        "req_func": icon_check,
        "progress_func": icon_progress,
        "items": "Iconed Element",
        "default": "Symbolist",
    },
    9: {
        "names": [
            "Copper Tier Element Ⅰ",
            "Copper Tier Element Ⅱ",
            "Copper Tier Element Ⅲ",
            "Copper Tier Element Ⅳ",
            "Copper Tier Element Ⅴ",
            "Silver Tier Element Ⅰ",
            "Silver Tier Element Ⅱ",
            "Silver Tier Element Ⅲ",
            "Silver Tier Element Ⅳ",
            "Silver Tier Element Ⅴ",
            "Gold Tier Element Ⅰ",
            "Gold Tier Element Ⅱ",
            "Gold Tier Element Ⅲ",
            "Gold Tier Element Ⅳ",
            "Gold Tier Element Ⅴ",
            "Diamond Tier Element Ⅰ",
            "Diamond Tier Element Ⅱ",
            "Diamond Tier Element Ⅲ",
            "Diamond Tier Element Ⅳ",
            "Diamond Tier Element Ⅴ",
        ],
        "req_func": complexity_check,
        "progress_func": complexity_progress,
        "items": "Tier",
        "default": "Platinum Tier Element",
    },
    10: {
        "names": [
            "Sub-Ultimate Element Ⅰ",
            "Sub-Ultimate Element Ⅱ",
            "Sub-Ultimate Element Ⅲ",
            "Ultimate Element Ⅰ",
            "Ultimate Element Ⅱ",
            "Ultimate Element Ⅲ",
            "Ultimate Element Ⅳ",
            "Ultimate Element Ⅴ",
            "Ultimate Element ⅤⅠ",
            "Ultimate Element ⅤⅡ",
            "Ultimate Element ⅤⅢ",
            "Ultimate Element Ⅸ",
            "Ultimate Element Ⅹ",
            "Ultra Ultimate Element Ⅰ",
            "Ultra Ultimate Element Ⅱ",
            "Ultra Ultimate Element Ⅲ",
        ],
        "req_func": tree_size_check,
        "progress_func": tree_size_progress,
        "items": "Tree Size",
        "default": "Transcended Element",
    },
    11: {
        "names": [
            "Easy Element Ⅰ",
            "Easy Element Ⅱ",
            "Easy Element Ⅲ",
            "Medium Element Ⅰ",
            "Medium Element Ⅱ",
            "Medium Element Ⅲ",
            "Hard Element Ⅰ",
            "Hard Element Ⅱ",
            "Hard Element Ⅲ",
            "Hard Element Ⅳ",
            "Hard Element Ⅴ",
            "Hard Element ⅤⅠ",
            "Extreme Element Ⅰ",
            "Extreme Element Ⅱ",
            "Extreme Element Ⅲ",
            "Insane Element Ⅰ",
            "Insane Element Ⅱ",
            "Insane Element Ⅲ",
        ],
        "req_func": difficulty_check,
        "progress_func": difficulty_progress,
        "items": "Difficulty",
        "default": "Demon Element",
    },
}

# Format
# emoji: str = the emoji to display by the user
# req: List[int] = the achievement and tier required for that icon to be used

user_icons = {
    0: {"emoji": "👤", "req": None},  # The default icon available to everyone
    1: {"emoji": "🔝", "req": [3, 3]},
    2: {"emoji": "🏵️", "req": [3, 0]},
    3: {"emoji": "🧑‍⚖️", "req": [2, 6]},
    4: {"emoji": "💧", "req": [0, 3]},
    5: {"emoji": "🌫️", "req": [0, 3]},
    6: {"emoji": "🔥", "req": [0, 3]},
    7: {"emoji": "🪨", "req": [0, 3]},
    8: {"emoji": "🌊", "req": [0, 6]},
    9: {"emoji": "🌪️", "req": [0, 6]},
    10: {"emoji": "💥", "req": [0, 6]},
    11: {"emoji": "🌎", "req": [0, 6]},
    12: {"emoji": "🪄", "req": [1, 9]},
    13: {"emoji": "🔮", "req": [1, 13]},
    14: {"emoji": "✨", "req": [1, 17]},
    15: {"emoji": "🏆", "req": [3, 3]},
    16: {"emoji": "🥈", "req": [3, 2]},
    17: {"emoji": "🥉", "req": [3, 1]},
    18: {"emoji": "⭐", "req": [-1, 0]},
    19: {"emoji": "🌞", "req": [-1, 1]},
    20: {"emoji": "🌟", "req": [-1, 2]},
    21: {"emoji": "🌠", "req": [-1, 3]},
    22: {"emoji": "☄️", "req": [-1, 4]},
    23: {"emoji": "🪐", "req": [-1, 5]},
    24: {"emoji": "🌌", "req": [-1, 6]},
    25: {"emoji": "💠", "req": [0, 9]},
    26: {"emoji": "🎨", "req": [1, 18]},
    # wizard emoji causes black to freak out
    27: {"emoji": "\U0001F9D9", "req": [0, 0]},
    28: {"emoji": "🤍", "req": [7, 0]},
    29: {"emoji": "🩶", "req": [7, 1]},
    30: {"emoji": "🖤", "req": [7, 2]},
    31: {"emoji": "🤎", "req": [7, 3]},
    32: {"emoji": "❤️", "req": [7, 4]},
    33: {"emoji": "🧡", "req": [7, 5]},
    34: {"emoji": "💛", "req": [7, 6]},
    35: {"emoji": "💚", "req": [7, 7]},
    36: {"emoji": "🩵", "req": [7, 8]},
    37: {"emoji": "💙", "req": [7, 9]},
    38: {"emoji": "💜", "req": [7, 10]},
    39: {"emoji": "🩷", "req": [7, 11]},
    40: {"emoji": "💗", "req": [7, 12]},
    41: {"emoji": "💖", "req": [7, 13]},
    42: {"emoji": "🖌️", "req": [6, 0]},
    43: {"emoji": "🖼️", "req": [6, 2]},
    44: {"emoji": "📸", "req": [6, 5]},
    45: {"emoji": "🧑‍🎨", "req": [6, 8]},
    46: {"emoji": "📝", "req": [5, 0]},
    47: {"emoji": "✏️", "req": [5, 1]},
    48: {"emoji": "🖋️", "req": [5, 2]},
    49: {"emoji": "🖊️", "req": [5, 3]},
    50: {"emoji": "📑", "req": [5, 4]},
    51: {"emoji": "🔖", "req": [5, 5]},
    52: {"emoji": "📙", "req": [5, 6]},
    53: {"emoji": "📗", "req": [5, 7]},
    54: {"emoji": "📕", "req": [5, 8]},
    55: {"emoji": "📘", "req": [5, 9]},
    56: {"emoji": "📖", "req": [5, 10]},
    57: {"emoji": "📍", "req": [8, 0]},
    58: {"emoji": "❗", "req": [8, 1]},
    59: {"emoji": "❓", "req": [8, 2]},
    60: {"emoji": "🔅", "req": [8, 3]},
    61: {"emoji": "🔆", "req": [8, 4]},
    62: {"emoji": "〽️", "req": [8, 5]},
    63: {"emoji": "⚠️", "req": [8, 6]},
    64: {"emoji": "🚸", "req": [8, 7]},
    65: {"emoji": "⚜️", "req": [8, 8]},
    66: {"emoji": "🔱", "req": [8, 9]},
    67: {"emoji": "🔰", "req": [8, 10]},
    68: {"emoji": "♻️", "req": [8, 11]},
    69: {"emoji": "🔑", "req": [9, 0]},
    70: {"emoji": "🗝️", "req": [9, 3]},
    71: {"emoji": "🔐", "req": [9, 5]},
    72: {"emoji": "💿", "req": [9, 6]},
    73: {"emoji": "⛓️", "req": [9, 8]},
    74: {"emoji": "🔩", "req": [9, 10]},
    75: {"emoji": "📀", "req": [9, 11]},
    76: {"emoji": "🪙", "req": [9, 12]},
    77: {"emoji": "💴", "req": [9, 13]},
    78: {"emoji": "💳", "req": [9, 14]},
    79: {"emoji": "💰", "req": [9, 15]},
    80: {"emoji": "💎", "req": [9, 16]},
    81: {"emoji": "🪩", "req": [9, 17]},
    82: {"emoji": "🌀", "req": [9, 18]},
    83: {"emoji": "🧿", "req": [9, 19]},
    84: {"emoji": "🪬", "req": [9, 20]},
    85: {"emoji": "😇", "req": [9, 21]},
    86: {"emoji": "☁️", "req": [9, 21]},
    87: {"emoji": "🌫️", "req": [9, 21]},
    88: {"emoji": "😶‍🌫️", "req": [9, 21]},
    89: {"emoji": "0️⃣", "req": [4, 0]},
    90: {"emoji": "1️⃣", "req": [4, 1]},
    91: {"emoji": "2️⃣", "req": [4, 2]},
    92: {"emoji": "3️⃣", "req": [4, 3]},
    93: {"emoji": "4️⃣", "req": [4, 4]},
    94: {"emoji": "5️⃣", "req": [4, 5]},
    95: {"emoji": "6️⃣", "req": [4, 6]},
    96: {"emoji": "7️⃣", "req": [4, 7]},
    97: {"emoji": "8️⃣", "req": [4, 8]},
    98: {"emoji": "9️⃣", "req": [4, 9]},
    99: {"emoji": "🔟", "req": [4, 10]},
    100: {"emoji": "🔢", "req": [4, 11]},
    101: {"emoji": "#️⃣", "req": [4, 12]},
    102: {"emoji": "🆔", "req": [10, 0]},
    103: {"emoji": "✝️", "req": [10, 1]},
    104: {"emoji": "☦️", "req": [10, 2]},
    105: {"emoji": "☮️", "req": [10, 3]},
    106: {"emoji": "⛎", "req": [10, 4]},
    107: {"emoji": "♈", "req": [10, 5]},
    108: {"emoji": "♉", "req": [10, 6]},
    109: {"emoji": "♊", "req": [10, 7]},
    110: {"emoji": "♋", "req": [10, 8]},
    111: {"emoji": "♌", "req": [10, 9]},
    112: {"emoji": "♍", "req": [10, 10]},
    113: {"emoji": "♎", "req": [10, 11]},
    114: {"emoji": "♏", "req": [10, 12]},
    115: {"emoji": "♐", "req": [10, 13]},
    116: {"emoji": "♑", "req": [10, 14]},
    117: {"emoji": "♒", "req": [10, 15]},
    118: {"emoji": "♓", "req": [10, 16]},
    119: {"emoji": "☪️", "req": [10, 17]},
    120: {"emoji": "🕉️", "req": [10, 18]},
    121: {"emoji": "☸️", "req": [10, 19]},
    122: {"emoji": "🪯", "req": [10, 20]},
    123: {"emoji": "🕎", "req": [10, 21]},
    124: {"emoji": "✡️", "req": [10, 22]},
    125: {"emoji": "🔯", "req": [10, 23]},
    126: {"emoji": "☯️", "req": [10, 24]},
    127: {
        "emoji": "⚛️",
        "req": [10, 25],
    },  # If anyone gets this icon, I will eat my right nut
    128: {"emoji": "🟢", "req": [11, 0]},
    129: {"emoji": "🟩", "req": [11, 1]},
    130: {"emoji": "✅", "req": [11, 2]},
    131: {"emoji": "❎", "req": [11, 3]},
    132: {"emoji": "✳️", "req": [11, 4]},
    133: {"emoji": "❇️", "req": [11, 5]},
    134: {"emoji": "⭕", "req": [11, 6]},
    135: {"emoji": "🚫", "req": [11, 7]},
    136: {"emoji": "🛑", "req": [11, 8]},
    137: {"emoji": "📛", "req": [11, 9]},
    138: {"emoji": "⛔", "req": [11, 10]},
    139: {"emoji": "💢", "req": [11, 11]},
    140: {"emoji": "♨️", "req": [11, 12]},
    141: {"emoji": "🆘", "req": [11, 13]},
    142: {"emoji": "💯", "req": [11, 14]},
    143: {"emoji": "🎴", "req": [11, 15]},
    144: {"emoji": "❤️‍🔥", "req": [11, 16]},
    145: {"emoji": "🤬", "req": [11, 17]},
    146: {"emoji": "😈", "req": [11, 18]},
    147: {"emoji": "👿", "req": [11, 18]},
    148: {"emoji": "👹", "req": [11, 18]},
    149: {"emoji": "👺", "req": [11, 18]},
    150: {"emoji": "🧌", "req": [11, 18]},
    151: {"emoji": "🧛", "req": [11, 18]},
    152: {"emoji": "🧟", "req": [11, 18]},
}
