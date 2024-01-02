__all__ = ["GameInstance"]


from pyeod.errors import GameError, InternalError
from pyeod.model.mixins import SavableMixin
from pyeod.model.polls import ElementPoll
from pyeod.model.types import Database, Element, Poll, User
from pyeod.utils import int_to_roman
from typing import List, Tuple, Optional
import copy

AIR = Element("Air", id=1, color=0x99E5DC)
EARTH = Element("Earth", id=2, color=0x806043)
FIRE = Element("Fire", id=3, color=0xFF7000)
WATER = Element("Water", id=4, color=0x239AFF)
DEFAULT_STARTER_ELEMENTS = (AIR, EARTH, FIRE, WATER)


class GameInstance(SavableMixin):
    def __init__(
        self,
        db: Optional[Database] = None,
        vote_req: int = 4,
        poll_limit: int = 21,
        starter_elements: Optional[Tuple[Element, ...]] = None,
    ) -> None:
        if db is None:
            if starter_elements is None:
                starter_elements = copy.deepcopy(DEFAULT_STARTER_ELEMENTS)
            self.db = Database.new_db(starter_elements)
        else:
            self.db = db
        self.vote_req = vote_req
        self.poll_limit = poll_limit

    # Deprecate this function?
    async def normalize_starter(self, element: Element) -> Element:
        async with self.db.element_lock.reader:
            starter = self.db.elements[element.name.lower()]
            assert starter in self.db.starters
            return starter

    async def login_user(self, user_id: int) -> User:
        async with self.db.user_lock.writer:
            if user_id not in self.db.users:
                inv = [elem.id for elem in self.db.starters]
                self.db.users[user_id] = User(user_id, inv)
            return self.db.users[user_id]

    async def check_element(
        self, element_name: str, user: Optional[User] = None
    ) -> Element:
        async with self.db.element_lock.reader:
            if not await self.db.has_element(element_name):
                raise GameError(
                    "Not an element",
                    "The element requested does not exist",
                    {"name": element_name},
                )
            element = self.db.elements[element_name.lower()]
            if user is not None and element.id not in user.inv:
                raise GameError(
                    "Not in inv",
                    "The user does not have the element requested",
                    {"element": element, "user": user},
                )
            return element

    async def check_elements(
        self, element_name_list: Tuple[str, ...], user: Optional[User] = None
    ) -> Tuple[Element, ...]:
        elements = []
        unobtained = set()
        nonexistent = set()
        for i in element_name_list:
            try:
                elements.append(await self.check_element(i, user))
            except GameError as g:
                if g.type == "Not in inv":
                    unobtained.add(g.meta["element"])
                elif g.type == "Not an element":
                    nonexistent.add(g.meta["name"])
                else:
                    raise g
        if unobtained:
            element_list = sorted(unobtained, key=lambda elem: elem.id)
            raise GameError(
                "Not in inv",
                "The user does not have the element requested",
                {"elements": element_list, "user": user},
            )
        if nonexistent:
            raise GameError(
                "Do not exist",
                "The elements requested do not exist",
                {"elements": sorted(nonexistent), "user": user},
            )
        return tuple(elements)

    async def combine(self, user: User, combo: Tuple[str, ...]) -> Element:
        element_combo = await self.check_elements(combo, user)
        user.last_combo = tuple(sorted(element_combo))
        result = await self.db.get_combo_result(element_combo)
        if result is None:
            raise GameError("Not a combo", "That combo does not exist")
        user.last_element = result
        await self.db.give_element(user, result)
        return result

    async def suggest_poll(self, poll: Poll) -> Poll:
        async with self.db.poll_lock.writer:
            if poll.author.active_polls > self.poll_limit:
                raise GameError("Too many active polls")
            self.db.polls.append(poll)
            poll.author.active_polls += 1
            return poll

    async def suggest_element(
        self, user: User, combo: Tuple[Element, ...], result: str
    ) -> ElementPoll:
        poll = ElementPoll(user, combo, result, await self.db.has_element(result))
        await self.suggest_poll(poll)
        return poll

    async def check_polls(self) -> List[Poll]:
        """
        Check all polls stored in this instance.

        The caller must not acquire ``element_lock`` to
        prevent deadlock.

        """
        async with self.db.poll_lock.writer:
            new_polls = []
            deleted_polls = []
            for poll in self.db.polls:
                if poll.votes >= self.vote_req:
                    # Poll was accepted
                    poll.accepted = True
                    try:
                        await poll.resolve(self.db)
                    except InternalError:
                        # Sometimes occurs when poll is accepted twice
                        pass
                    deleted_polls.append(poll)
                    poll.author.active_polls -= 1
                elif poll.votes <= -self.vote_req:
                    # Poll was denied
                    deleted_polls.append(poll)
                    poll.author.active_polls -= 1
                else:
                    new_polls.append(poll)
            self.db.polls = new_polls
            return deleted_polls

    async def check_single_poll(self, poll: Poll) -> bool:
        if abs(poll.votes) >= self.vote_req:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll.accepted = True
                await poll.resolve(self.db)
            async with self.db.poll_lock.writer:
                poll.author.active_polls -= 1
                self.db.polls.remove(poll)
            return True
        return False

    async def get_achievements(self, user: User) -> List[str]:
        achievements: List[str] = []
        async with self.db.user_lock.reader:  # Lock needed?
            persistent_achievements = user.persistent_achievements

            # Elements found achievements

            element_amount = len(user.inv)
            if element_amount >= 25_000:
                achievements.append(
                    f"Ultimate Elementalist {int_to_roman(element_amount//25_000)}"
                )
            elif element_amount >= 10_000:  # Could be condensed
                achievements.append(f"True Elementalist III")
            elif element_amount >= 5_000:
                achievements.append(f"True Elementalist II")
            elif element_amount >= 2_500:
                achievements.append(f"True Elementalist I")
            elif element_amount >= 1_000:
                achievements.append(f"Elementalist III")
            elif element_amount >= 500:
                achievements.append(f"Elementalist II")
            elif element_amount >= 250:
                achievements.append(f"Elementalist I")
            elif element_amount >= 100:
                achievements.append(f"Beginner Elementalist II")
            elif element_amount >= 50:
                achievements.append(f"Beginner Elementalist II")
            elif element_amount >= 25:
                achievements.append(f"Beginner Elementalist I")

            # Created combos achievements

            combos_created = user.created_combo_count
            if combos_created >= 15_000:
                achievements.append(
                    f"Mighty Creator {int_to_roman(combos_created//15_000)}"
                )
            elif combos_created >= 12_500:  # Could be condensed
                achievements.append(f"Powerful Creator IV")
            elif combos_created >= 10_000:
                achievements.append(f"Powerful Creator III")
            elif combos_created >= 7_500:
                achievements.append(f"Powerful Creator II")
            elif combos_created >= 5_000:
                achievements.append(f"Powerful Creator I")
            elif combos_created >= 4_000:
                achievements.append(f"Strong Creator IV")
            elif combos_created >= 3_000:
                achievements.append(f"Strong Creator III")
            elif combos_created >= 2_000:
                achievements.append(f"Strong Creator II")
            elif combos_created >= 1_000:
                achievements.append(f"Strong Creator I")
            elif combos_created >= 900:
                achievements.append(f"Creator X")
            elif combos_created >= 800:
                achievements.append(f"Creator IX")
            elif combos_created >= 700:
                achievements.append(f"Creator VIII")
            elif combos_created >= 600:
                achievements.append(f"Creator VII")
            elif combos_created >= 500:
                achievements.append(f"Creator VI")
            elif combos_created >= 400:
                achievements.append(f"Creator V")
            elif combos_created >= 300:
                achievements.append(f"Creator IV")
            elif combos_created >= 200:
                achievements.append(f"Creator III")
            elif combos_created >= 100:
                achievements.append(f"Creator II")
            elif combos_created >= 50:
                achievements.append(f"Creator I")

            # Votes cast achievements

            cast_votes = user.votes_cast_count
            if cast_votes >= 1_000:
                achievements.append(f"Judge {int_to_roman(cast_votes//1_000)}")
            elif cast_votes >= 500:
                achievements.append(f"Avid Voter")
            elif cast_votes >= 250:
                achievements.append(f"Dedicated Voter")
            elif cast_votes >= 125:
                achievements.append(f"Keen Voter")
            elif cast_votes >= 50:
                achievements.append(f"Voter")
            elif cast_votes >= 25:
                achievements.append(f"New Voter")
            elif cast_votes >= 1:
                achievements.append(f"I Voted!")

            #! Persistent Achievements
            #! Do not alter (unless willing to manually replace for ALL players)
            #! Only add to

            # Complicated element achievements

            if user.last_element:
                async with self.db.element_lock.reader:  # Scuffed af
                    complexity = self.db.complexities[user.last_element.id]
                    if complexity >= 100:
                        path = await self.db.get_path(user.last_element)
                        tree_size = len(path)
                        achievement = None
                        if tree_size >= 5_000:
                            achievement = f"Ultimate Element Tier {int_to_roman(complexity//5_000)}"
                        elif tree_size >= 3_000:
                            achievement = "Insane Element"
                        elif tree_size >= 1_000:
                            achievement = "Extreme Element"
                        elif tree_size >= 500:
                            achievement = "Complex Element"
                        elif tree_size >= 250:
                            achievement = "Difficult Element"

                        if achievement and achievement not in persistent_achievements:
                            persistent_achievements.append(achievement)

            # Leaderboard ahievements

            leaderboard_position = (
                sorted(
                    self.db.users.keys(),
                    key=lambda key: len(self.db.users[key].inv),
                    reverse=True,
                ).index(user.id)
                + 1
            )
            if (  # These achievements are persistent meaning that even when losing the leaderboard position you keep them. These names are SET IN STONE
                leaderboard_position == 1
                and "🥇 Top of the pack" not in persistent_achievements
            ):
                persistent_achievements.append(f"🥇 Top of the pack")
            elif (
                leaderboard_position == 2
                and "🥈 2nd is the best" not in persistent_achievements
            ):
                persistent_achievements.append("🥈 2nd is the best")
            elif (
                leaderboard_position == 3
                and "🥉 Bronze age" not in persistent_achievements
            ):
                persistent_achievements.append("🥉 Bronze age")
            elif (
                leaderboard_position <= 10
                and "🏆 Top ten" not in persistent_achievements
            ):
                persistent_achievements.append("🏆 Top ten")

        return achievements + persistent_achievements

    def convert_to_dict(self, data: dict) -> None:
        data["db"] = self.db
        data["vote_req"] = self.vote_req
        data["poll_limit"] = self.poll_limit

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "GameInstance":
        return GameInstance(
            data.get("db"), data.get("vote_req", 4), data.get("poll_limit", 20)
        )


def generate_test_game():
    game = GameInstance()
    user = game.login_user(0)
    combo = ("fire", "fire")
    try:
        game.combine(user, combo)
    except GameError as g:
        if g.type == "Not a combo":
            game.suggest_element(
                user, tuple(game.check_element(name) for name in combo), "Inferno"
            )
    game.db.polls[0].votes += 4
    game.check_polls()
    return game


if __name__ == "__main__":
    print(generate_test_game().login_user(0).inv)
