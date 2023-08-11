from typing import Optional, Dict, Tuple, List, Union
import copy
import time


class ModelBaseError(Exception):
    def __init__(
        self, type: str, message: str = "No Message Provided", meta: dict = {}
    ) -> None:
        self.type = type
        self.message = message
        self.meta = meta  # Used to transfer useful error info


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

    def convert_to_dict(self, data: dict) -> None:
        data["name"] = self.name
        data["author"] = self.author.id if self.author is not None else None
        data["created"] = self.created
        data["id"] = self.id

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "Element":
        if data["author"] is None:
            author = None
        else:
            author = loader.users[data["author"]]
        element = Element(data["name"], author, data["created"], data["id"])
        loader.elem_id_lookup[element.id] = element
        return element


class User:
    def __init__(
        self,
        inv: List[int],
        active_polls: int,
        id: int,
        last_combo: Tuple[Element, ...] = (),
    ) -> None:
        self.inv = inv
        self.active_polls = active_polls
        self.id = id
        self.last_combo = last_combo

    def add_element(
        self, element: Element
    ):  # Maybe raise an error if a duplicate element is added?
        if element.id not in self.inv:
            self.inv.append(element.id)

    def convert_to_dict(self, data: dict) -> None:
        data["inv"] = self.inv
        data["active_polls"] = self.active_polls
        data["id"] = self.id

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "User":
        user = User(
            data["inv"],
            data["active_polls"],
            data["id"],
        )
        loader.users[user.id] = user
        return user


class Poll:
    def __init__(self, author: User) -> None:
        self.author = author
        self.votes = 0
        self.accepted = False  # is this needed?

    def resolve(self, database):
        pass

    def convert_to_dict(self, data: dict) -> None:
        raise TypeError

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "Poll":
        raise TypeError


def capitalize(name: str) -> str:
    if name.lower() != name:
        return name
    words = [word.capitalize() for word in name.split(" ")]
    return " ".join(words)


class ElementPoll(Poll):
    def __init__(
        self, author: User, combo: Tuple[Element, ...], result: str, exists: bool
    ) -> None:
        super(ElementPoll, self).__init__(author)
        self.combo = combo
        self.result = capitalize(result)
        self.exists = exists

    def resolve(self, database: "Database") -> Element:  # Return Element back
        if not self.exists:
            element = Element(
                self.result, self.author, round(time.time()), len(database.elements) + 1
            )
            database.add_element(element)
        else:
            element = database.elements[self.result.lower()]
        database.set_combo_result(self.combo, element)
        if self.author.last_combo == self.combo:
            self.author.last_combo = ()
        return element

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["combo"] = [elem.id for elem in self.combo]
        data["result"] = self.result
        data["exists"] = self.exists

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "ElementPoll":
        poll = ElementPoll(
            loader.users[data["author"]],
            [loader.elem_id_lookup[elem] for elem in data["combo"]],
            data["result"],
            data["exists"],
        )
        poll.votes = data["votes"]
        return poll


class Database:
    def __init__(
        self,
        elements: Dict[str, Element],
        starters: Tuple[Element, ...],
        combos: Dict[Tuple[int, ...], Element],
        users: Dict[int, User],
        polls: List[Poll],
    ) -> None:
        self.elements = elements
        self.elem_id_lookup = {elem.id: elem for elem in self.elements.values()}
        self.starters = starters
        self.combos = combos
        self.users = users
        self.polls = polls

    @staticmethod
    def new_db(starter_elements: Tuple[Element, ...]) -> "Database":
        return Database(
            elements={i.name.lower(): i for i in starter_elements},
            starters=starter_elements,
            combos={},
            users={},
            polls=[],
        )

    def add_element(self, element: Element):
        self.elements[element.name.lower()] = element
        self.elem_id_lookup[element.id] = element

    def has_element(self, element: str) -> bool:
        return element.lower() in self.elements

    def get_combo_result(self, combo: Tuple[Element, ...]) -> Union[Element, None]:
        sorted_combo = tuple(sorted(elem.id for elem in combo))
        if sorted_combo in self.combos:
            return self.combos[sorted_combo]
        return None

    def set_combo_result(self, combo: Tuple[Element, ...], result: Element) -> None:
        sorted_combo = tuple(sorted(elem.id for elem in combo))
        if sorted_combo in self.combos:
            raise InternalError("Combo exists", "That combo already exists")
        self.combos[sorted_combo] = result

    def convert_to_dict(self, data: dict) -> None:
        # Users MUST be first
        data["users"] = self.users
        data["elements"] = list(self.elements.values())
        data["starters"] = [elem.id for elem in self.starters]
        data["combos"] = {}
        for combo in self.combos:
            combo_ids = ",".join(str(elem) for elem in combo)
            data["combos"][combo_ids] = self.combos[combo].id
        data["polls"] = self.polls

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "Database":
        starters = [loader.elem_id_lookup[elem] for elem in data["starters"]]
        combos = {}
        for combo_ids in data["combos"]:
            key = tuple(int(id) for id in combo_ids.split(","))
            combos[key] = loader.elem_id_lookup[data["combos"][combo_ids]]
        users = {int(id): user for id, user in data["users"].items()}

        return Database(
            {elem.name.lower(): elem for elem in data["elements"]},
            starters,
            combos,
            users,
            data["polls"],
        )


AIR = Element("Air", id=1)
EARTH = Element("Earth", id=2)
FIRE = Element("Fire", id=3)
WATER = Element("Water", id=4)
DEFAULT_STARTER_ELEMENTS = (AIR, EARTH, FIRE, WATER)


class GameInstance:
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
    def normalize_starter(self, element: Element) -> Element:
        starter = self.db.elements[element.name.lower()]
        assert starter in self.db.starter_elements
        return starter

    def login_user(self, user_id: int) -> User:
        if user_id not in self.db.users:
            inv = [elem.id for elem in self.db.starters]
            self.db.users[user_id] = User(inv, 0, user_id)
        return self.db.users[user_id]

    def check_element(self, element_name: str, user: Optional[User] = None) -> Element:
        if not self.db.has_element(element_name):
            raise GameError(
                "Not an element", "The element requested does not exist"
            )  # Is message needed?
        element = self.db.elements[element_name.lower()]
        if user is not None and element.id not in user.inv:
            raise GameError(
                "Not in inv", "The user does not have the element requested"
            )
        return element

    def combine(self, user: User, combo: Tuple[str, ...]) -> Element:
        element_combo = tuple(self.check_element(name, user) for name in combo)
        user.last_combo = tuple(sorted(element_combo))
        result = self.db.get_combo_result(element_combo)
        if result is None:
            raise GameError("Not a combo", "That combo does not exist")
        if result.id in user.inv:
            raise GameError(
                "Already have element",
                f"You made {result.name}, but you already have it",
            )
        user.add_element(result)
        return result

    def suggest_element(
        self, user: User, combo: Tuple[Element, ...], result: str
    ) -> ElementPoll:
        if user.active_polls > self.poll_limit:
            raise GameError("Too many active polls")
        poll = ElementPoll(user, combo, result, self.db.has_element(result))
        self.db.polls.append(poll)
        user.active_polls += 1
        return poll

    def check_polls(self) -> List[Poll]:
        new_polls = []
        deleted_polls = []
        for poll in self.db.polls:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll_return = poll.resolve(self.db)
                deleted_polls.append(poll)
                if isinstance(
                    poll, ElementPoll
                ):  # If it's an element poll, give the author the elemtent
                    poll.author.add_element(poll_return)
                poll.author.active_polls -= 1
            elif poll.votes <= -self.vote_req:
                # Poll was denied
                deleted_polls.append(poll)
                poll.author.active_polls -= 1
            else:
                new_polls.append(poll)
        self.db.polls = new_polls
        return deleted_polls

    def convert_to_dict(self, data: dict) -> None:
        data["db"] = self.db
        data["vote_req"] = self.vote_req
        data["poll_limit"] = self.poll_limit

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "GameInstance":
        return GameInstance(data["db"], data["vote_req"], data["poll_limit"])


if __name__ == "__main__":
    game = GameInstance()
    user = game.login_user(0)
    combo = ("fire", "fire")
    try:
        game.combine(user, combo)
    except GameError as g:
        if g.type == "Not a combo":
            game.suggest_element(user, combo, "inferno")
    game.db.polls[0].votes += 4
    game.check_polls()
    print(user.inv)
