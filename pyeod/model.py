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
    def __init__(self, author: User) -> None:
        self.author = author
        self.votes = 0
        self.accepted = False

    def resolve(self, database):
        pass

class ElementPoll(Poll):
    def __init__(
        self, author: User, combo: Tuple[Element], result: str, exists: bool
    ) -> None:
        super(ElementPoll, self).__init__(author)
        self.combo = combo
        self.result = result
        self.exists = exists

    def resolve(self, database):
        element = Element(
            self.result, self.author, time.time(), len(database.elements) + 1
        )
        database.elements[self.result.lower()] = element
        database.set_combo_result(self.combo, element)


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

    @staticmethod
    def new_db(starter_elements: List[Element]) -> "Database":
        return Database(
            elements={i.name.lower(): i for i in starter_elements},
            starters=starter_elements,
            combos={},
            users={},
            polls=[],
        )

    def has_element(self, element: str) -> bool:
        return element.lower() in self.elements

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

    # Deprecate this function?
    def normalize_starter(self, element: Element) -> Element:
        starter = self.db.elements[element.name.lower()]
        assert starter in self.starter_elements
        return starter

    def login_user(self, user_id: int) -> User:
        if user_id not in self.db.users:
            self.db.users[user_id] = User(list(self.db.starters), 0, user_id)
        return self.db.users[user_id]

    def check_element(self, element_name: str, user: Optional[User] = None) -> Element:
        if not self.db.has_element(element_name):
            raise GameError(
                "Not an element", "The element requested does not exist"
            )
        element = self.db.elements[element_name.lower()]
        if user is not None and element not in user.inv:
            raise GameError(
                "Not in inv", "The user does not have the element requested"
            )
        return element

    def combine(self, user: User, combo: Tuple[str]) -> Element:
        element_combo = (self.check_element(name, user) for name in combo)
        result = self.db.get_combo_result(element_combo)
        if result is None:
            raise GameError("Not a combo", "The combo requested does not exist")
        if result in user.inv:
            raise GameError(
                "Already have element", f"You made {result.name}, but already have it"
            )
        user.inv.append(result)
        return result

    def suggest_element(self, user: User, combo: Tuple[str], result: str) -> Poll:
        if user.active_polls > self.poll_limit:
            raise GameError("Too many active polls")
        # Technically not needed since combine already checks
        element_combo = (self.check_element(name, user) for name in combo)
        poll = ElementPoll(user, element_combo, result, self.db.has_element(result))
        self.db.polls.append(poll)
        user.active_polls += 1
        return poll

    def check_polls(self) -> List[Poll]:
        new_polls = []
        deleted_polls = []
        for poll in self.db.polls:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll.resolve(self.db)
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


if __name__ == "__main__":
    game = GameInstance()
    user = game.login_user(0)
    combo = ("fire", "fire")
    try:
        game.combine(user, combo)
    except GameError as g:
        if g.type == "Not a combo":
            game.suggest_element(user, combo, "Inferno")
    game.db.polls[0].votes += 4
    game.check_polls()
    game.combine(user, combo)
    print(user.inv)
