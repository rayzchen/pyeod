__all__ = ["GameInstance"]


from pyeod.errors import GameError, InternalError
from pyeod.model.mixins import SavableMixin
from pyeod.model.polls import ElementPoll
from pyeod.model.types import Database, Element, Poll, User
from typing import List, Tuple, Optional
import asyncio
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
        async with self.db.poll_lock.writer:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll.accepted = True
                await poll.resolve(self.db)
                poll.author.active_polls -= 1
                self.db.polls.remove(poll)
                return True
            if poll.votes <= -self.vote_req:
                # Poll was denied
                poll.author.active_polls -= 1
                self.db.polls.remove(poll)
                return True
            return False

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
