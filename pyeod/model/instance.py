__all__ = ["GameInstance"]


from pyeod.errors import GameError, InternalError
from pyeod.model.achievements import achievements, user_icons
from pyeod.model.mixins import SavableMixin
from pyeod.model.polls import ElementPoll
from pyeod.model.types import Database, Element, Poll, User
from pyeod.utils import format_list, int_to_roman
from typing import List, Tuple, Union, Optional
import copy
import random
import asyncio

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
        poll_limit: int = 32,
        combo_limit: int = 21,
        polls_rejected: Optional[int] = 0,
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
        self.combo_limit = combo_limit
        self.polls_rejected = polls_rejected

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
                self.db.created_by_lookup[user_id] = []
            return self.db.users[user_id]

    async def check_elements(
        self, element_name_list: Tuple[str, ...], user: Optional[User] = None
    ) -> Tuple[Element, ...]:
        elements = []
        unobtained = set()
        nonexistent = set()
        async with self.db.element_lock.reader:
            for i in element_name_list:
                try:
                    element = await self.get_element_by_str(user, i)
                    if user is not None and element.id not in user.inv:
                        unobtained.add(element)
                    else:
                        elements.append(element)
                except GameError as e:
                    if e.type == "Element does not exist":
                        nonexistent.add(e.meta["element_name"])
                    else:
                        raise e

        if unobtained:
            unobtained = sorted(list(unobtained), key=lambda elem: elem.id)
            raise GameError(
                "Not in inv",
                f"You don't have {format_list([i.name for i in unobtained])}",
                {"elements": unobtained, "user": user},
            )
        if nonexistent:
            nonexistent = sorted(list(nonexistent))
            raise GameError(
                "Elements do not exist",
                f"Elements {format_list(nonexistent, 'and')} don't exist",
                {"elements": nonexistent, "user": user},
            )
        return tuple(elements)

    async def combine(self, user: User, combo: Tuple[str, ...]) -> Element:
        element_combo = await self.check_elements(combo, user)
        user.last_combo = tuple(sorted(element_combo))
        result = await self.db.get_combo_result(element_combo)
        if result is None:
            user.last_element = None
            raise GameError(
                "Not a combo",
                "Not a combo! Use **!s <element_name>** to suggest an element",
                meta={"emoji": "🟥", "element": result},
            )
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
                    self.polls_rejected += 1
                else:
                    new_polls.append(poll)
            self.db.polls = new_polls
            return deleted_polls

    async def check_single_poll(self, poll: Poll) -> bool:
        if abs(poll.votes) >= self.vote_req:
            async with self.db.poll_lock.writer:
                poll.author.active_polls -= 1
                self.db.polls.remove(poll)
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll.accepted = True
                await poll.resolve(self.db)
            else:
                self.polls_rejected += 1
            return True
        return False

    async def get_achievements(self, user: User) -> List[List[int]]:
        user_achievements: List[List[int]] = user.achievements
        new_achievements: List[List[int]] = []
        achievement_ids = list(achievements)
        await achievements[-1]["req_func"](self, user)  # Run check func to cache things
        achievement_ids.append(achievement_ids.pop(0))  # move first achievement to end
        for achievement_id in achievement_ids:
            achievement_data = achievements[achievement_id]
            returned_tier = await achievement_data["req_func"](self, user)
            if returned_tier is None:
                continue
            returned_tier = int(returned_tier)
            if [achievement_id, returned_tier] not in user_achievements:
                user_achievements.append([achievement_id, returned_tier])
                new_achievements.append([achievement_id, returned_tier])
            # Check previous achievements if skipped over
            if [achievement_id, returned_tier - 1] not in user_achievements:
                for i in range(returned_tier):
                    if [achievement_id, i] not in user_achievements:
                        user_achievements.append([achievement_id, i])
                        new_achievements.append([achievement_id, i])

        return new_achievements

    async def get_achievement_name(self, achievement: Union[List[int], None]) -> str:
        if achievement is None:
            return "Default"
        name = ""
        achievement_data = achievements[achievement[0]]
        try:
            name = achievement_data["names"][achievement[1]]
        except IndexError:
            if achievement_data["default"] != None:
                name = f"{achievement_data['default']} {int_to_roman(achievement[1] - len(achievement_data['names']) + 1)}"
            else:
                return None
        return name

    async def get_unlocked_icons(self, achievement: List[int]) -> List[int]:
        unlocked_icons = []
        for icon_id, icon_data in user_icons.items():
            if icon_data["req"] is not None and achievement == icon_data["req"]:
                unlocked_icons.append(icon_id)
        return unlocked_icons

    async def get_available_icons(self, user: User):
        available_icons = []
        for achievement in user.achievements:
            available_icons += await self.get_unlocked_icons(achievement)
        return available_icons + [0]

    async def get_achievement_progress(self, achievement: List[int], user: User) -> int:
        return await achievements[achievement[0]]["progress_func"](self, user)

    async def get_achievement_item_name(
        self, achievement: List[int], amount: int = 1
    ) -> str:
        items = achievements[achievement[0]]["items"]
        return items if amount == 1 else f"{items}s"

    def get_icon(self, icon: int) -> str:
        return user_icons[icon]["emoji"]

    def get_icon_requirement(self, icon: int) -> str:
        return user_icons[icon]["req"]

    def get_icon_by_emoji(self, icon_emoji: str) -> int:
        for icon_id, icon_data in user_icons.items():
            if icon_emoji in icon_data["emoji"]:
                return icon_id
        raise KeyError

    async def set_icon(self, user: User, icon: int) -> None:
        if (
            user_icons[icon]["req"] == None
            or user_icons[icon]["req"] in user.achievements
        ):
            user.icon = icon
        else:
            raise GameError(
                "Cannot use icon",
                "You do not have the achievement required to use that icon",
            )

    async def get_element_by_str(self, user: User, string: str) -> Element:
        async with self.db.element_lock.reader:
            if not string:
                if user.last_element is not None:
                    return user.last_element
                else:
                    raise GameError(
                        "No previous element",
                        "Combine something first",
                        {"element_name": string, "user": user},
                    )
            if string.startswith("#"):
                elem_id = string[1:].strip()
                if elem_id.isdecimal() and int(elem_id) in self.db.elem_id_lookup:
                    return self.db.elem_id_lookup[int(elem_id)]
                elif elem_id in ["l", "last"] and user is not None:
                    if user.last_element is not None:
                        return user.last_element
                    else:
                        raise GameError(
                            "No previous element",
                            "Combine something first",
                            {"element_name": string, "user": user},
                        )
                elif elem_id in ["r", "random"]:
                    return random.choice(list(self.db.elements.values()))
                elif elem_id in ["ri", "randomininv"]:
                    return self.db.elem_id_lookup[random.choice(user.inv)]
                else:
                    raise GameError(
                        "Element id does not exist",
                        f"Element with ID **#{elem_id}** doesn't exist",
                        {"element_name": string, "user": user},
                    )
            if string.lower() in self.db.elements:
                return self.db.elements[string.lower()]
            else:
                raise GameError(
                    "Element does not exist",
                    f"Element **{string}** doesn't exist",
                    {"element_name": string, "user": user},
                )

    def convert_to_dict(self, data: dict) -> None:
        data["db"] = self.db
        data["vote_req"] = self.vote_req
        data["poll_limit"] = self.poll_limit
        data["combo_limit"] = self.combo_limit
        data["polls_rejected"] = self.polls_rejected

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "GameInstance":
        return GameInstance(
            data.get("db"),
            data.get("vote_req", 4),
            data.get("poll_limit", 32),
            data.get("combo_limit", 21),
            data.get("polls_rejected", 0),
        )


async def generate_test_game():
    game = GameInstance()
    user = await game.login_user(0)
    combo = ("fire", "fire")
    try:
        await game.combine(user, combo)
    except GameError as g:
        if g.type == "Not a combo":
            await game.suggest_element(
                user,
                tuple([await game.check_element(name) for name in combo]),
                "Inferno",
            )
    game.db.polls[0].votes += 4
    await game.check_polls()
    return game


async def test_function():
    game = await generate_test_game()
    user = await game.login_user(0)
    print(user.inv)


if __name__ == "__main__":
    asyncio.run(test_function())
