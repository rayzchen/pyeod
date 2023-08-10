from typing import Optional, Dict, Tuple, List, Union
import copy
import time


class ModelBaseError(Exception):
    def __init__(self, type: str, message: str = "No Message Provided") -> None:
        self.type = type
        self.message = message


class InternalError(ModelBaseError):
    pass


class GameError(ModelBaseError):
    pass


class Element:
    def __init__(
        self, name: str, author: Optional["User"] = None, created: int = 0, id: int = 1
    ) -> None:  # author:User
        self.name = name
        self.author = author
        self.created = created
        self.id = id

    def __repr__(self) -> str:
        return f"<Name: {self.name}, Id: {self.id}>"

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Element):
            return self.name < other.name
        return NotImplemented


class User:
    def __init__(self, inv: List[Element], active_polls: int, id: int) -> None:
        self.inv = inv
        self.active_polls = active_polls
        self.id = id


class Poll:
    def __init__(
        self, combo: Tuple[Element], result: str, author: User, votes: int
    ) -> None:
        self.combo = combo
        self.result = result
        self.author = author
        self.votes = votes


class Database:
    def __init__(
        self,
        elements: Dict[str, Element],
        starters: List[Element],
        combos: Dict[Tuple[Element], Element],
        users: Dict[int, User],
        polls: List[Poll],
    ) -> None:
        self.elements = elements
        self.starters = starters
        self.combos = combos
        self.users = users
        self.polls = polls

    def new_db(starter_elements: List[Element]) -> "Database":
        return Database(
            elements={i.name.lower(): i for i in starter_elements},
            starters=starter_elements,
            combos={},
            users={},
            polls=[],
        )

    def get_combo_result(self, combo: Tuple[Element]) -> Union[Element, None]:
        sorted_combo = tuple(sorted(combo))
        if sorted_combo in self.combos:
            return self.combos[sorted_combo]
        return None

    def set_combo_result(self, combo: Tuple[Element], result: Element) -> None:
        sorted_combo = tuple(sorted(combo))
        if sorted_combo in self.combos:
            raise InternalError("Combo exists", "The combo already exists")
        self.combos[sorted_combo] = result


AIR = Element("Air", id=1)
EARTH = Element("Earth", id=2)
FIRE = Element("Fire", id=3)
WATER = Element("Water", id=4)
DEFAULT_STARTER_ELEMENTS = (AIR, EARTH, FIRE, WATER)


class GameInstance:
    def __init__(
        self,
        starter_elements: Optional[List[Element]] = None,
        db: Optional[Database] = None,
        vote_req: int = 4,
        poll_limit: int = 21,
    ) -> None:
        self.starter_elements = starter_elements
        if self.starter_elements is None:
            self.starter_elements = copy.deepcopy(DEFAULT_STARTER_ELEMENTS)
        if db == None:
            self.db = Database.new_db(self.starter_elements)
        else:
            self.db = db
        self.vote_req = vote_req
        self.poll_limit = poll_limit

    def normalize_starter(self, element: Element) -> Element:
        starter = self.db.elements[element.name.lower()]
        assert starter in self.starter_elements
        return starter

    def login_user(self, user_id) -> User:
        if user_id not in self.db.users:
            self.db.users[user_id] = User(self.db.starters, 0, user_id)
        return self.db.users[user_id]

    def combine(self, user: User, combo: Tuple[Element]) -> Element:
        for i in combo:
            if i not in user.inv:
                raise GameError(
                    "Not in inv", "The user does not have the element requested"
                )
            if i.name.lower() not in self.db.elements:
                raise GameError(
                    "Not an element", "The element requested does not exist"
                )
        result = self.db.get_combo_result(combo)
        if result is None:
            raise GameError("Not a combo", "The combo requested does not exist")
        user.inv.append(result)
        return result

    def suggest_element(self, user: User, combo: Tuple[Element], result: str):
        if user.active_polls > self.poll_limit:
            raise GameError("Too many active polls")
        for i in combo:
            if i not in user.inv:
                raise GameError(
                    "Not in inv", "The user does not have the element requested"
                )
            if i.name.lower() not in self.db.elements:
                raise GameError(
                    "Not an element", "The element requested does not exist"
                )
        self.db.polls.append(Poll(combo, result, user, 0))

    def check_polls(self) -> List[Poll]:
        new_polls = []
        deleted_polls = []
        for poll in self.db.polls:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                element = Element(
                    poll.result, poll.author, time.time(), len(self.db.elements) + 1
                )
                self.db.elements[poll.result.lower()] = element
                self.db.set_combo_result(poll.combo, element)
                deleted_polls.append(poll)
            elif poll.votes <= -self.vote_req:
                # Poll was denied
                deleted_polls.append(poll)
            else:
                new_polls.append(poll)
        self.db.polls = new_polls
        return deleted_polls


if __name__ == "__main__":
    game = GameInstance()
    user = game.login_user(0)
    fire = game.normalize_starter(FIRE)
    combo = (fire, fire)
    try:
        game.combine(user, combo)
    except GameError as g:
        if g.type == "Not a combo":
            game.suggest_element(user, combo, "Inferno")
    game.db.polls[0].votes += 4
    game.check_polls()
    game.combine(user, combo)
    print(user.inv)
