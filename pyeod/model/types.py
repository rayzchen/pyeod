__all__ = [
    "Element",
    "User",
    "Poll",
    "Database",
    "Category",
    "ElementCategory",
]


from pyeod.errors import GameError, InternalError
from pyeod.model.mixins import SavableMixin
from aiorwlock import RWLock
from abc import abstractmethod
from typing import Dict, List, Tuple, Union, Optional
import time
import colorsys


class Element(SavableMixin):
    __slots__ = (
        "name",
        "author",
        "created",
        "id",
        "mark",
        "marker",
        "color",
        "colorer",
        "extra_authors",
        "image",
        "imager",
        "icon",
        "iconer",
    )

    def __init__(
        self,
        name: str,
        author: Optional["User"] = None,
        created: int = 0,
        id: int = 1,
        mark: str = "",
        marker: Optional["User"] = None,
        color: int = 0,
        colorer: Optional["User"] = None,
        extra_authors: Optional[List["User"]] = None,
        image: str = "",
        imager: Optional["User"] = None,
        icon: str = "",
        iconer: Optional["User"] = None,
    ) -> None:  # author:User
        self.name = name
        self.author = author
        self.created = created
        self.id = id
        self.mark = mark
        self.marker = marker
        self.color = color
        self.colorer = colorer
        self.image = image
        self.icon = icon
        self.iconer = iconer
        self.imager = imager
        if extra_authors is not None:
            self.extra_authors = extra_authors
        else:
            self.extra_authors = []

    def __repr__(self) -> str:
        return f"<Name: {self.name}, Id: {self.id}>"

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Element):
            return self.name < other.name
        return NotImplemented

    def get_hsv(self) -> Tuple[float, float, float]:
        rgb = [
            (self.color & 0xFF0000) >> 16,
            (self.color & 0x00FF00) >> 8,
            self.color & 0x0000FF,
        ]
        return colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)

    @staticmethod
    def get_color(combo: Tuple["Element", ...]) -> int:
        if any(element.color == 0 for element in combo):
            return 0
        colors = [element.get_hsv() for element in combo]
        out = [0.0, 0.0, 0.0]
        for i in range(3):
            for color in colors:
                out[i] += color[i]
            out[i] /= len(colors)
        rgb_float = list(colorsys.hsv_to_rgb(*out))
        rgb = [0, 0, 0]
        for i in range(3):
            rgb[i] = int(rgb_float[i] * 255)
        return (rgb[0] << 16) | (rgb[1] << 8) | (rgb[2])

    def convert_to_dict(self, data: dict) -> None:
        data["name"] = self.name.strip()
        # author can be None or 0
        data["author"] = self.author.id if self.author else self.author
        data["created"] = self.created
        data["id"] = self.id
        data["mark"] = self.mark
        data["marker"] = self.marker.id if self.marker is not None else None
        data["color"] = self.color
        data["colorer"] = self.colorer.id if self.colorer is not None else None
        data["extra_authors"] = [i.id for i in self.extra_authors]
        data["image"] = self.image
        data["imager"] = self.imager.id if self.imager is not None else None
        data["icon"] = self.icon
        data["iconer"] = self.iconer.id if self.iconer is not None else None

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "Element":
        extra_authors = [loader.users[i] for i in data.get("extra_authors", [])]
        element = Element(
            data.get("name").strip(),  # Must be present
            loader.users[data.get("author")],
            data.get("created", 0),
            data.get("id"),  # Must be present
            data.get("mark", ""),
            loader.users[data.get("marker")],
            data.get("color", 0x0),
            loader.users[data.get("colorer")],
            extra_authors,
            data.get("image", ""),
            loader.users[data.get("imager")],
            data.get("icon", ""),
            loader.users[data.get("iconer")],
        )
        loader.elem_id_lookup[element.id] = element
        return element


class User(SavableMixin):
    __slots__ = (
        "id",
        "inv",
        "active_polls",
        "created_combo_count",
        "votes_cast_count",
        "achievements",
        "icon",
        "last_combo",
        "last_element",
    )

    def __init__(
        self,
        id: int,
        inv: List[int],
        active_polls: int = 0,
        created_combo_count: int = 0,
        votes_cast_count: int = 0,
        achievements: List[List[int]] = [],
        icon: int = 0,
    ) -> None:
        self.id = id
        self.inv = inv
        self.active_polls = active_polls
        self.created_combo_count = created_combo_count
        self.votes_cast_count = votes_cast_count
        self.achievements = achievements
        self.icon = icon
        self.last_combo = ()
        self.last_element = None

    def add_element(self, element: Element):
        # Error handled outside
        if element.id not in self.inv:
            self.inv.append(element.id)

    def convert_to_dict(self, data: dict) -> None:
        data["id"] = self.id
        data["inv"] = self.inv
        data["active_polls"] = self.active_polls
        data["created_combo_count"] = self.created_combo_count
        data["votes_cast_count"] = self.votes_cast_count
        data["achievements"] = self.achievements
        data["icon"] = self.icon

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "User":
        user = User(
            data.get("id"),  # Must be present
            data.get("inv", []),
            data.get("active_polls", 0),
            data.get("created_combo_count", 0),
            data.get("votes_cast_count", 0),
            data.get("achievements", []),
            data.get("icon", 0),
        )
        for i in user.achievements:
            i[0] = int(i[0])
            i[1] = int(i[1])
        loader.users[user.id] = user
        return user


class Poll(SavableMixin):
    __slots__ = ("author", "votes", "accepted", "creation_time")

    def __init__(self, author: User) -> None:
        self.author = author
        self.votes = 0
        self.accepted = False
        self.creation_time = round(time.time())

    @abstractmethod
    def resolve(self, database: "Database"):
        pass

    def get_time(self):
        duration = round(time.time()) - self.creation_time
        duration, seconds = divmod(duration, 60)
        duration, minutes = divmod(duration, 60)
        duration, hours = divmod(duration, 24)
        weeks, days = divmod(duration, 7)

        string = f"{seconds}s"
        if minutes:
            string = f"{minutes}m{string}"
        if hours:
            string = f"{hours}h{string}"
        if days:
            string = f"{days}d{string}"
        if weeks:
            string = f"{weeks}w{string}"
        return string

    @abstractmethod
    def get_news_message(self, instance: "GameInstance") -> str:
        pass

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} by {self.author.id} polling at {self.votes} | {self.creation_time}>"


class Category(SavableMixin):
    __slots__ = ("name")

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def has_element(self, element: Element, database: "Database") -> bool:
        pass

    async def get_elements(self, database: "Database") -> Tuple[Element, ...]:
        # in most cases, it is better to override this method
        elements = []
        for element in database.elements.items():
            if await self.has_element(element, database):
                elements.append(element)
        return tuple(elements)


class ElementCategory(Category):
    __slots__ = ("name", "elements")

    def __init__(self, name: str, elements: Tuple[Element, ...]) -> None:
        self.name = name
        self.elements = list(elements)

    async def has_element(self, element: Element, database: "Database") -> bool:
        return element in self.elements

    async def get_elements(self, database: "Database") -> Tuple[Element, ...]:
        # Faster and less redundant, tuples are immutable anyways
        return tuple(self.elements)

    def convert_to_dict(self, data: dict) -> None:
        data["name"] = self.name
        data["elements"] = [e.id for e in self.elements]

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "ElementCategory":
        # python>=3.7 only
        deduplicated = list(dict.fromkeys(data.get("elements")))
        elements = [loader.elem_id_lookup[e] for e in deduplicated]
        return ElementCategory(data.get("name"), elements)


class Database(SavableMixin):
    # TODO: requires __slots__? only one instance of Database per GameInstance

    def __init__(
        self,
        elements: Dict[str, Element],
        starters: Tuple[Element, ...],
        combos: Dict[Tuple[int, ...], Element],
        users: Dict[int, User],
        polls: List[Poll],
        categories: Dict[int, Category],
    ) -> None:
        self.elements = elements
        self.starters = starters
        self.combos = combos
        self.users = users
        self.polls = polls
        self.categories = categories

        self.complexity_lock = RWLock()
        self.element_lock = RWLock()  # covers both elements and combos
        self.category_lock = RWLock()
        self.user_lock = RWLock()
        self.poll_lock = RWLock()

        notfound = []
        self.elem_id_lookup = {elem.id: elem for elem in self.elements.values()}
        self.max_id = max(self.elem_id_lookup)
        for user in self.users.values():
            for i in range(len(user.inv) - 1, -1, -1):  # iterate backwards
                if user.inv[i] in notfound:
                    user.inv.pop(i)
                elif user.inv[i] not in self.elem_id_lookup:
                    elem = user.inv.pop(i)
                    notfound.append(elem)
                    print(f"Warning: dropping element {elem} from invs")

        self.combo_lookup: Dict[int, List[Tuple[int, ...]]] = {
            elem: [] for elem in self.elem_id_lookup
        }
        self.used_in_lookup: Dict[int, List[Tuple[int, ...]]] = {
            elem: set() for elem in self.elem_id_lookup
        }
        missing_combos = []
        for combo, result in self.combos.items():
            if len(notfound):
                if result.id in notfound or any(x in notfound for x in combo):
                    missing_combos.append((combo, result))
                    continue
            self.combo_lookup[result.id].append(combo)
            for elem in combo:
                self.used_in_lookup[elem].add(combo)
        for combo, result in missing_combos:
            print("Warning: dropping combo", combo, "result", result)
            self.combos.pop(combo)

        self.found_by_lookup: Dict[int, List[int]] = {
            elem: set() for elem in self.elem_id_lookup
        }
        for user in self.users.values():
            for elem in user.inv:
                self.found_by_lookup[elem].add(user.id)

        self.created_by_lookup: Dict[int, List[int]] = {user: [] for user in self.users}
        self.created_by_lookup[0] = []  # Glitched elements
        self.created_by_lookup[None] = []  # Starter elements
        for elem in self.elements.values():
            author = elem.author.id if elem.author else elem.author
            self.created_by_lookup[author].append(elem.id)

        self.complexities = {}
        self.min_elem_tree = {}

    async def acquire_all_locks(self):
        await self.complexity_lock.reader.acquire()
        await self.element_lock.reader.acquire()
        await self.user_lock.reader.acquire()
        await self.poll_lock.reader.acquire()

    def release_all_locks(self):
        self.complexity_lock.reader.release()
        self.element_lock.reader.release()
        self.user_lock.reader.release()
        self.poll_lock.reader.release()

    def set_starter_infos(self) -> None:
        for elem in self.starters:
            self.complexities[elem.id] = 0
            self.min_elem_tree[elem.id] = ()
        self.path_lookup = {elem.id: {elem.id} for elem in self.starters}
        self.category_lookup = {elem.id: set() for elem in self.starters}

    async def calculate_infos(self) -> None:
        async with self.complexity_lock.writer:
            async with self.element_lock.reader:
                for elem in self.starters:
                    self.complexities[elem.id] = 0
                    self.min_elem_tree[elem.id] = ()

                unseen = set(self.elem_id_lookup)
                for elem in self.starters:
                    unseen.remove(elem.id)
                while len(unseen) != 0:
                    for elem_id in unseen:
                        complexity = self.get_complexity(elem_id)
                        if complexity is not None:
                            unseen.remove(elem_id)
                            break
                    else:
                        print("Warning: Dropping elements:", unseen)
                        self.element_lock.reader.release()
                        async with self.element_lock.writer:
                            for elem_id in unseen:
                                assert elem_id not in self.complexities
                                element = self.elem_id_lookup[elem_id]
                                self.elements.pop(element.name.lower())
                                self.combo_lookup.pop(elem_id)
                                self.used_in_lookup.pop(elem_id)
                                self.elem_id_lookup.pop(elem_id)
                                self.found_by_lookup.pop(elem_id)
                        await self.element_lock.reader.acquire()
                        break

                self.path_lookup = {elem: set() for elem in self.elem_id_lookup}
                for elem in sorted(
                    self.complexities, key=lambda x: self.complexities[x]
                ):
                    for ingredient in self.min_elem_tree[elem]:
                        if not self.path_lookup[elem]:
                            self.path_lookup[elem] = self.path_lookup[ingredient].copy()
                            continue
                        if ingredient in self.path_lookup[elem]:
                            continue
                        for item in self.path_lookup[ingredient]:
                            self.path_lookup[elem].add(item)
                    self.path_lookup[elem].add(elem)

            async with self.category_lock.writer:
                self.category_lookup: Dict[int, set] = {
                    elem: set() for elem in self.elem_id_lookup
                }
                for elem in self.elements.values():
                    for category in self.categories.values():
                        if await category.has_element(elem, self):
                            self.category_lookup[elem.id].add(category.name)

    def get_complexity(self, elem_id: int) -> Union[int, None]:
        """
        Get complexity of element by ID, and add to the minimum element tree.
        ``self.complexity_lock.writer`` must be held.

        """
        combos = self.combo_lookup[elem_id]
        min_complexity = None
        for combo in combos:
            if not all(x in self.complexities for x in combo):
                continue

            complexities = [self.complexities[x] for x in combo]
            if min_complexity is None or max(complexities) + 1 < min_complexity:
                min_complexity = max(complexities) + 1
                min_combo = combo

        if min_complexity is not None:
            self.complexities[elem_id] = min_complexity
            self.min_elem_tree[elem_id] = min_combo
            return min_complexity
        return None

    async def check_suggested_combos(self):
        async with self.user_lock.writer:
            for user in self.users.values():
                created = len(self.created_by_lookup[user.id])
                if created > user.created_combo_count:
                    user.created_combo_count = created

    async def check_colors(self):
        async with self.element_lock.writer:
            for element in self.elements.values():
                if element.colorer is not None:
                    continue
                if 0 < element.color < 0xFFFFFF:
                    continue
                if not self.combo_lookup[element.id]:
                    continue

                combo = [
                    self.elem_id_lookup[x] for x in self.combo_lookup[element.id][0]
                ]
                element.color = Element.get_color(combo)

    async def update_element_info(
        self, element: Element, combo: Tuple[int, ...]
    ) -> None:
        async with self.complexity_lock.writer:
            new_complexity = max(self.complexities[x] for x in combo)
            if new_complexity < self.complexities[element.id]:
                self.complexities[element.id] = new_complexity
                self.min_elem_tree[element.id] = combo

    async def give_element(self, user: User, element: Element) -> None:
        if element.id in user.inv:
            raise GameError(
                "Already have element",
                f"You made {element.name}, but you already have it",
                {"element": element},
            )
        async with self.element_lock.writer:
            self.found_by_lookup[element.id].add(user.id)
            user.add_element(element)

    def give_element_unsafe(self, user: User, element: int) -> None:
        if element not in user.inv:
            self.found_by_lookup[element].add(user.id)
            user.inv.append(element)

    async def get_path(self, element: Element) -> List[int]:
        return await self.get_path_ids([element.id])

    async def get_path_ids(self, elements: List[int]) -> List[int]:
        if self.complexity_lock.reader.locked:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        async with self.complexity_lock.reader:
            path = []
            visited = set()
            stack = elements.copy()
            while stack:
                node = stack[-1]
                if node not in visited:
                    # Insufficient to only check min_elem_tree[node][-1]
                    if not self.min_elem_tree[node] or all(
                        x in visited for x in self.min_elem_tree[node]
                    ):
                        stack.pop()
                        visited.add(node)
                        path.append(node)
                    else:
                        for child in reversed(self.min_elem_tree[node]):
                            if child not in visited:
                                stack.append(child)
                else:
                    stack.pop()
        return path

    @staticmethod
    def new_db(starter_elements: Tuple[Element, ...]) -> "Database":
        database = Database(
            elements={i.name.lower(): i for i in starter_elements},
            starters=starter_elements,
            combos={},
            users={},
            polls=[],
            categories={},
        )
        database.set_starter_infos()
        return database

    async def add_element(self, element: Element):
        async with self.element_lock.writer:
            if element.name.lower() not in self.elements:
                self.elements[element.name.lower()] = element
                self.elem_id_lookup[element.id] = element
                self.combo_lookup[element.id] = []
                self.used_in_lookup[element.id] = set()
                self.found_by_lookup[element.id] = set()
                self.created_by_lookup[element.author.id].append(element.id)
        async with self.category_lock.writer:
            for category in self.categories.values():
                if not isinstance(category, ElementCategory):
                    if category.has_element(element):
                        self.category_lookup[element].add(category.name)

    async def has_element(self, element: str) -> bool:
        async with self.element_lock.reader:
            return element.lower() in self.elements

    async def get_combo_result(
        self, combo: Tuple[Element, ...]
    ) -> Union[Element, None]:
        async with self.element_lock.reader:
            sorted_combo = tuple(sorted(elem.id for elem in combo))
            if sorted_combo in self.combos:
                return self.combos[sorted_combo]
            return None

    async def set_combo_result(
        self, combo: Tuple[Element, ...], result: Element
    ) -> None:
        async with self.element_lock.writer:
            sorted_combo = tuple(sorted(elem.id for elem in combo))
            if sorted_combo in self.combos:
                raise InternalError("Combo exists", "That combo already exists")
            if result.name.lower() not in self.elements:
                await self.add_element(result)
            self.combos[sorted_combo] = result
            self.combo_lookup[result.id].append(sorted_combo)
        async with self.complexity_lock.writer:
            if result.id not in self.complexities:
                if self.get_complexity(result.id) is None:
                    raise InternalError(
                        "Failed getting complexity",
                        "No combo found with existing complexity",
                    )
                self.path_lookup[result.id] = set(await self.get_path(result))
            else:
                await self.update_element_info(result, sorted_combo)
        async with self.element_lock.writer:
            for elem in sorted_combo:
                self.used_in_lookup[elem].add(sorted_combo)

    def convert_to_dict(self, data: dict) -> None:
        # Users MUST be first to be saved or loaded
        data["users"] = self.users
        data["elements"] = list(self.elements.values())
        data["starters"] = [elem.id for elem in self.starters]
        combos = {}
        for combo in self.combos:
            combo_ids = ",".join(str(elem) for elem in combo)
            combos[combo_ids] = self.combos[combo].id
        data["combos"] = combos
        data["polls"] = self.polls
        data["categories"] = list(self.categories.values())

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "Database":
        try:
            starters = tuple(loader.elem_id_lookup[elem] for elem in data.get("starters"))
        except KeyError as e:
            #Really bad error that somehow happened
            raise InternalError("Starters not found", "Starters not found") from e
        combos = {}
        for combo_ids, combo_result in data.get("combos").items():
            key = tuple(int(id) for id in combo_ids.split(","))
            if combo_result in loader.elem_id_lookup:
                combos[key] = loader.elem_id_lookup[combo_result]
            else:
                print(
                    "Warning: dropping combo",
                    key,
                    "for element",
                    combo_result,
                )
        users = {int(id): user for id, user in data.get("users", []).items()}
        polls = [poll for poll in data.get("polls", []) if poll is not None]
        categories = {cat.name.lower(): cat for cat in data.get("categories", [])}
        return Database(
            {elem.name.lower(): elem for elem in data.get("elements")},
            starters,
            combos,
            users,
            polls,
            categories,
        )
