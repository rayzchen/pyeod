"""
A separate file to store the achievements dict
purely to not clutter the rest of pyeod.model.
The only thing that should be exported is the
`achievements` var and the `user_icons` var.

"""

__all__ = ["achievements", "user_icons"]


def boundary_list_check(boundaries, value):
    if value >= boundaries[-1]:
        return len(boundaries) - 1 + value // boundaries[-1]
    for i in range(len(boundaries) - 2, -1, -1):  # Iterate backwards from 2nd last
        if value >= boundaries[i]:
            return i
    return None


def get_distance_to_nearest_boundary(boundaries, value):
    for boundary in boundaries:
        if value < boundary:
            return boundary - value
    return boundaries[-1] - (value % boundaries[-1])


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
        return get_distance_to_nearest_boundary(
            elements_collected_boundaries, element_amount
        )


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
        return get_distance_to_nearest_boundary(
            elements_created_boundaries, combos_created
        )


votes_cast_boundaries = [1, 25, 50, 125, 250, 500, 1_000]


async def votes_cast_check(instance, user):
    async with instance.db.user_lock.reader:
        cast_votes = user.votes_cast_count
        return boundary_list_check(votes_cast_boundaries, cast_votes)


async def votes_cast_progress(instance, user):
    async with instance.db.user_lock.reader:
        cast_votes = user.votes_cast_count
        return get_distance_to_nearest_boundary(votes_cast_boundaries, cast_votes)


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
            return 0
        if leaderboard_position == 2:
            return 1
        if leaderboard_position == 3:
            return 1
        if leaderboard_position <= 10:
            return leaderboard_position - 3
        return leaderboard_position - 10


async def achievement_achievement_check(instance, user):
    async with instance.db.user_lock.reader:
        achievement_amount = len(user.achievements)
        if achievement_amount < 10:
            return 0
        return achievement_amount // 10


async def achievement_achievement_progress(instance, user):
    async with instance.db.user_lock.reader:
        achievement_amount = len(user.achievements)
        return 10 - (achievement_amount % 10)


# Format:
# names: list[str] = the tier names
# default: str = what is defaulted to if the check_check returns an index outside of the names list (roman numerals added based on how far off the returned index is)
# req_check: Callable[GameInstance, User] = the checktion that takes in user data and returns the appropriate tier of achievement

achievements = {
    -1: {
        "names": ["Achievement get!"],
        "default": "Achiever",
        "req_func": achievement_achievement_check,
        "progress_func": achievement_achievement_progress,
        "items" : "Achievement"
    },
    0: {
        "names": [
            "Beginner Elementalist Ⅰ",
            "Beginner Elementalist ⅠⅠ",
            "Beginner Elementalist ⅠⅠⅠ",
            "Elementalist Ⅰ",
            "Elementalist ⅠⅠ",
            "Elementalist ⅠⅠⅠ",
            "True Elementalist Ⅰ",
            "True Elementalist ⅠⅠ",
            "True Elementalist ⅠⅠⅠ",
        ],
        "default": "Ultimate Elementalist",
        "req_func": elements_collected_check,
        "progress_func": elements_collected_progress,
        "items" : "Element"
    },
    1: {
        "names": [
            "Creator Ⅰ",
            "Creator ⅠⅠ",
            "Creator ⅠⅠⅠ",
            "Creator ⅠⅤ",
            "Creator Ⅴ",
            "Creator ⅤⅠ",
            "Creator ⅤⅠⅠ",
            "Creator ⅤⅠⅠⅠ",
            "Creator ⅠⅩ",
            "Creator Ⅹ",
            "Strong Creator Ⅰ",
            "Strong Creator ⅠⅠ",
            "Strong Creator ⅠⅠⅠ",
            "Strong Creator ⅠⅤ",
            "Powerful Creator Ⅰ",
            "Powerful Creator ⅠⅠ",
            "Powerful Creator ⅠⅠⅠ",
            "Powerful Creator ⅠⅤ,",
        ],
        "default": "Mighty Creator",
        "req_func": elements_created_check,
        "progress_func": elements_created_progress,
        "items" : "Created Combos"
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
        "items" : "Vote"
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
        "items" : "Leaderboard Position",
        # No default as it is impossible for an outside index to be returned
        "default": None,
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
}
