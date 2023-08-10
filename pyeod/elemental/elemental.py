from typing import Optional, Dict, Tuple, List


class GameError(Exception):
    def __init__(self, type: str, message: str = "No Message Provided") -> None:
        self.type = type
        self.message = message


class Element:
    def __init__(
        self, name: str, author: Optional["User"] = None, created: int = 0, id: int = 1
    ) -> None:  # author:User
        self.name = name
        self.author = author
        self.created = created
        self.id = id

    def __repr__(self):
        return f"<Name: {self.name}, Id: {self.id}>"


class User:
    def __init__(self, inv: List[Element], active_polls: int, id: int) -> None:
        self.inv = inv
        self.active_polls = active_polls
        self.id = id


class Poll:
    def __init__(
        self, combo: tuple[Element], result: str, author: User, votes: int
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


AIR = Element("Air", id=1)
EARTH = Element("Earth", id=2)
FIRE = Element("Fire", id=3)
WATER = Element("Water", id=4)
STARTER_ELEMENTS = [AIR, EARTH, FIRE, WATER]


class GameInstance:
    def __init__(
        self,
        starting_elements: Optional[List[Element]] = None,
        db: Optional[Database] = None,
        vote_req: int = 4,
        poll_limit: int = 21,
    ) -> None:
        self.starting_elements = starting_elements
        if self.starting_elements is None:
            self.starting_elements = copy.deepcopy(STARTER_ELEMENTS)
        if db == None:
            self.db = self.new_db()
        else:
            self.db = db
        self.vote_req = vote_req
        self.poll_limit = poll_limit

    def new_db(self) -> Database:
        return Database(
            elements={i.name: i for i in self.starting_elements},
            starters=self.starting_elements,
            combos={},
            users={},
            polls=[],
        )

    def login_user(self, user_id) -> User:
        if user_id not in self.db.users:
            self.db.users[user_id] = User(self.db.starters, 0, user_id)
            return self.db.users[user_id]
        else:
            return self.db.users[user_id]

    def combine(self, user: User, combo: Tuple[Element]) -> Element:
        for i in combo:
            if i not in user.inv:
                raise GameError(
                    "Not in inv", "The user does not have the element requested"
                )
            if i.name not in self.db.elements:
                raise GameError(
                    "Not an element", "The element requested does not exist"
                )
        if combo not in self.db.combos:
            raise GameError("Not a combo", "The combo requested does not exist")
        result = self.db.combos[sorted(combo)]
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
            if i.name not in self.db.elements:
                raise GameError(
                    "Not an element", "The element requested does not exist"
                )
        self.db.polls.append(Poll(sorted(combo), result, user, 0))

    def check_polls(self) -> None:
        new_polls = []
        deleted_polls = []
        for i in self.db.polls:
            if i.votes >= self.vote_req:
                self.db.elements[i.result.name] = i.result
                self.db.combos[i.combo] = i.result
                deleted_polls.append(i)
            elif i.votes <= -self.vote_req:
                deleted_polls.append(i)
            else:
                new_polls.append(i)
        
        self.db.polls = new_polls
        return deleted_polls

import time

game = GameInstance()
user = game.login_user(0)
combo = frozenset([FIRE, FIRE])
try:
    game.combine(user, combo)
except GameError as g:
    if g.type == "Not a combo":
        game.suggest_element(user, combo, Element("Inferno", user, time.time(), 5))
game.db.polls[0].votes += 4
game.check_polls()
game.combine(user, combo)
print(user.inv)
