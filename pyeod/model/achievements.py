__all__ = ["achievements"]


# A separate file to store the achievements dict
# Purely to not clutter the rest of the model
# The only thing that should be exported is the "achievements" var
async def elements_collected_func(instance, user):
    async with instance.db.user_lock.reader:
        element_amount = len(user.inv)
        if element_amount >= 25_000:
            return 8 + element_amount // 25_000
        elif element_amount >= 10_000:
            return 8
        elif element_amount >= 5_000:
            return 7
        elif element_amount >= 2_500:
            return 6
        elif element_amount >= 1_000:
            return 5
        elif element_amount >= 500:
            return 4
        elif element_amount >= 250:
            return 3
        elif element_amount >= 100:
            return 2
        elif element_amount >= 50:
            return 1
        elif element_amount >= 25:
            return 0


async def elements_created_func(instance, user):
    async with instance.db.user_lock.reader:
        combos_created = user.created_combo_count
        if combos_created >= 15_000:
            return 17 + combos_created // 15_000
        elif combos_created >= 12_500:
            return 17
        elif combos_created >= 10_000:
            return 16
        elif combos_created >= 7_500:
            return 15
        elif combos_created >= 5_000:
            return 14
        elif combos_created >= 4_000:
            return 13
        elif combos_created >= 3_000:
            return 12
        elif combos_created >= 2_000:
            return 11
        elif combos_created >= 1_000:
            return 10
        elif combos_created >= 900:
            return 9
        elif combos_created >= 800:
            return 8
        elif combos_created >= 700:
            return 7
        elif combos_created >= 600:
            return 6
        elif combos_created >= 500:
            return 5
        elif combos_created >= 400:
            return 4
        elif combos_created >= 300:
            return 3
        elif combos_created >= 200:
            return 2
        elif combos_created >= 100:
            return 1
        elif combos_created >= 50:
            return 0


async def votes_cast_func(instance, user):
    async with instance.db.user_lock.reader:
        cast_votes = user.votes_cast_count
        if cast_votes >= 1_000:
            return 5 + votes_cast_func // 1_000
        elif cast_votes >= 500:
            return 5
        elif cast_votes >= 250:
            return 4
        elif cast_votes >= 125:
            return 3
        elif cast_votes >= 50:
            return 2
        elif cast_votes >= 25:
            return 1
        elif cast_votes >= 1:
            return 0


async def leaderboard_pos_func(instance, user):
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
        elif leaderboard_position == 2:
            return 2
        elif leaderboard_position == 3:
            return 1
        elif leaderboard_position <= 10:
            return 0

async def achievement_achievement_func(instance, user):
    async with instance.db.user_lock.reader:
        achievement_amount = len(user.achievements)
        if achievement_amount < 10:
            return 0
        else:
            return achievement_amount//10

# Format:
# names:list[str] = the tier names
# default:str = what is defaulted to if the check_func returns an index outside of the names list (roman numerals added based on how far off the returned index is)
# check func:func = the function that takes in user data and returns the appropriate tier of achievement

achievements = {
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
        "check func": elements_collected_func,
    },
    1: {
        "names": [
            "Creator Ⅰ",
            "Creator ⅠⅠ",
            "Creator ⅠⅠⅠ",
            "Creator ⅠV",
            "Creator V",
            "Creator VⅠ",
            "Creator VⅠⅠ",
            "Creator VⅠⅠⅠ",
            "Creator ⅠⅩ",
            "Creator Ⅹ",
            "Strong Creator Ⅰ",
            "Strong Creator ⅠⅠ",
            "Strong Creator ⅠⅠⅠ",
            "Strong Creator ⅠV",
            "Powerful Creator Ⅰ",
            "Powerful Creator ⅠⅠ",
            "Powerful Creator ⅠⅠⅠ",
            "Powerful Creator ⅠV,",
        ],
        "default": "Mighty Creator",
        "check func": elements_created_func,
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
        "check func": votes_cast_func,
    },
    3: {  # No default as it is impossible for an outside index to be returned
        "names": [
            "🏆 Top ten",
            "🥉 Bronze age",
            "🥈 2nd is the best",
            "🥇 Top of the pack",
        ],
        "check func": leaderboard_pos_func,
    },
    4: {
        "names": ["Achievement get!"],
        "default": "Achiever",
        "check func": achievement_achievement_func,
    },
}
