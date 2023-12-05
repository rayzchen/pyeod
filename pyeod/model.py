from typing import Optional, Dict, Tuple, List, Union
from abc import ABCMeta, abstractmethod, abstractstaticmethod
import colorsys
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


class SavableMixin(metaclass=ABCMeta):
    @abstractmethod
    def convert_to_dict(self, data: dict) -> None:
        pass

    @staticmethod
    @abstractmethod
    def convert_from_dict(loader, data: dict) -> "SavableMixin":
        pass


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
        if imager == []:
            print(imager)
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
        print(rgb)
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
        # TODO: Convert all convert_from_dict to using .get as it's more robust and allows for defaults
        author = loader.users[data["author"]]
        marker = loader.users[data.get("marker")]
        colorer = loader.users[data.get("colorer")]
        imager = loader.users[data.get("imager")]
        iconer = loader.users[data.get("iconer")]
        extra_authors = [loader.users[i] for i in data.get("extra_authors", [])]
        element = Element(
            data["name"].strip(),
            author,
            data["created"],
            data["id"],
            data.get("mark", ""),
            marker,
            data.get("color", 0x0),
            colorer,
            extra_authors,
            data.get("image", ""),
            imager,
            data.get("icon", ""),
            iconer,
        )
        loader.elem_id_lookup[element.id] = element
        return element


class User(SavableMixin):
    __slots__ = ("inv", "active_polls", "id", "last_combo", "last_element")

    def __init__(
        self,
        inv: List[int],
        active_polls: int,
        id: int,
        last_combo: Tuple[Element, ...] = (),
        last_element: Optional[Element] = None,
    ) -> None:
        self.inv = inv
        self.active_polls = active_polls
        self.id = id
        self.last_combo = last_combo
        self.last_element = last_element

    def add_element(self, element: Element):
        # Error handled outside
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


def capitalize(name: str) -> str:
    if name.lower() != name:
        return name
    words = [word.capitalize() for word in name.split(" ")]
    return " ".join(words)


class ElementPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "combo",
        "result",
        "exists",
    )

    def __init__(
        self, author: User, combo: Tuple[Element, ...], result: str, exists: bool
    ) -> None:
        super(ElementPoll, self).__init__(author)
        self.combo = combo
        self.result = capitalize(result)
        self.exists = exists

    def resolve(self, database: "Database") -> Element:  # Return Element back
        if self.result.lower() not in database.elements:
            database.max_id += 1
            color = Element.get_color(self.combo)
            element = Element(
                self.result,
                self.author,
                round(time.time()),
                database.max_id,
                color=color,
            )
        else:
            element = database.elements[self.result.lower()]
        database.set_combo_result(self.combo, element)
        database.found_by_lookup[element.id].append(self.author.id)
        self.author.add_element(element)
        if self.author.last_combo == self.combo:
            self.author.last_combo = ()
            self.author.last_element = element
        return element

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "🆕 "
            if self.exists:
                msg += f"Combination"
            else:
                msg += f"Element"
            msg += f" - **{self.result}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) - "
            if self.exists:
                msg += f"Combination "
                msg += f"**\#{len(instance.db.combos) + 1}**"
            else:
                msg += f"Element "
                msg += f"**\#{instance.db.elements[self.result.lower()].id}**"
        else:
            msg += "❌ Poll Rejected - "
            if self.exists:
                msg += f"Combination"
            else:
                msg += f"Element"
            msg += f" - **{self.result}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        if self.exists:
            return "Combination"
        else:
            return "Element"

    def get_description(self) -> str:
        text = " + ".join([i.name for i in self.combo]) + " = " + self.result
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["combo"] = [elem.id for elem in self.combo]
        data["result"] = self.result
        data["exists"] = self.exists
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "ElementPoll":
        combo = []
        for elem in data["combo"]:
            if elem in loader.elem_id_lookup:
                combo.append(loader.elem_id_lookup[elem])
            else:
                # Perhaps saved broken poll
                print(
                    "Warning: dropping combo",
                    data["combo"],
                    "for element",
                    data["result"],
                    "in poll",
                )
                return None
        poll = ElementPoll(
            loader.users[data["author"]],
            tuple(loader.elem_id_lookup[elem] for elem in data["combo"]),
            data["result"],
            data["exists"],
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class MarkPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "marked_element",
        "mark",
    )

    def __init__(self, author: User, marked_element: Element, mark: str) -> None:
        super(MarkPoll, self).__init__(author)
        self.marked_element = marked_element
        self.mark = mark

    def resolve(self, database: "Database") -> str:
        self.marked_element.mark = self.mark
        self.marked_element.marker = self.author
        return self.mark

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += ":scroll: "  # Scroll emoji, not unicode cus for some reason it doesn't work
            msg += "Comment"
            msg += f" - **{self.marked_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Comment"
            msg += f" - **{self.marked_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Comment"

    def get_description(self) -> str:
        text = f"**{self.marked_element.name}**\n"
        text += (
            f"Old Comment: \n{self.marked_element.mark}\n\nNew Comment:\n{self.mark}"
        )
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["marked_element"] = self.marked_element.id
        data["mark"] = self.mark
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "MarkPoll":
        poll = MarkPoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["marked_element"]],
            data["mark"],
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class ColorPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "colored_element",
        "color",
    )

    def __init__(
        self, author: User, colored_element: Element, color: Union[int, str]
    ) -> None:
        super(ColorPoll, self).__init__(author)
        self.colored_element = colored_element
        if isinstance(color, str):
            self.color = self.get_int(color)
        else:
            self.color = color

    def resolve(self, database: "Database") -> int:
        self.colored_element.color = self.color
        self.colored_element.colorer = self.author
        return self.color

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "🎨 "
            msg += "Color"
            msg += (
                f" - **{self.colored_element.name}** (Lasted **{self.get_time()}** • "
            )
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Color"
            msg += (
                f" - **{self.colored_element.name}** (Lasted **{self.get_time()}** • "
            )
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Color"

    def get_description(self) -> str:
        text = f"**{self.colored_element.name}**\n"
        text += f"Old Color: \n{self.get_hex(self.colored_element.color)}\n"
        text += f"\nNew Color:\n{self.get_hex(self.color)}"
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def get_hex(self, color: int) -> str:
        rgb = [(color & 0xFF0000) >> 16, (color & 0x00FF00) >> 8, color & 0x0000FF]
        return "#" + "".join(hex(x)[2:].rjust(2, "0") for x in rgb)

    def get_int(self, color: str) -> int:
        rgb_str = [color[1:3], color[3:5], color[5:]]
        rgb = [0, 0, 0]
        for i in range(3):
            rgb[i] = int(rgb_str[i], 16)
        return (rgb[0] << 16) | (rgb[1] << 8) | (rgb[2])

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["colored_element"] = self.colored_element.id
        data["color"] = self.color
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "ColorPoll":
        poll = ColorPoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["colored_element"]],
            data["color"],
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class ImagePoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "imaged_element",
        "image",
    )

    def __init__(self, author: User, imaged_element: Element, image: str) -> None:
        super(ImagePoll, self).__init__(author)
        self.imaged_element = imaged_element
        self.image = image

    def resolve(self, database: "Database") -> int:
        self.imaged_element.image = self.image
        self.imaged_element.imager = self.author
        return self.image

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "🖼️ "
            msg += "Image"
            msg += f" - **{self.imaged_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Image"
            msg += f" - **{self.imaged_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Image"

    def get_description(self) -> str:
        text = f"**{self.imaged_element.name}**\n"
        text += (
            f"[Old Image]({self.imaged_element.image})"
            if self.imaged_element.image
            else ""
        )
        text += f"\nNew Image Suggested by <@{self.author.id}>:"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["imaged_element"] = self.imaged_element.id
        data["image"] = self.image
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "ImagePoll":
        poll = ImagePoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["imaged_element"]],
            data["image"],
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class IconPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "iconed_element",
        "icon",
    )

    def __init__(self, author: User, iconed_element: Element, icon: str) -> None:
        super(IconPoll, self).__init__(author)
        self.iconed_element = iconed_element
        self.icon = icon

    def resolve(self, database: "Database") -> int:
        self.iconed_element.icon = self.icon
        self.iconed_element.iconer = self.author
        return self.icon

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "📍 "
            msg += "Icon"
            msg += f" - **{self.iconed_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Icon"
            msg += f" - **{self.iconed_element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Icon"

    def get_description(self) -> str:
        text = f"**{self.iconed_element.name}**\n"
        text += (
            f"[Old Icon]({self.iconed_element.icon})"
            if self.iconed_element.icon
            else ""
        )
        text += f"\nNew Icon Suggested by <@{self.author.id}>:"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["iconed_element"] = self.iconed_element.id
        data["icon"] = self.icon
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "IconPoll":
        poll = IconPoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["iconed_element"]],
            data["icon"],
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class AddCollabPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "element",
        "extra_authors",
    )

    def __init__(
        self, author: User, element: Element, extra_authors: Tuple[User, ...]
    ) -> None:
        super(AddCollabPoll, self).__init__(author)
        self.element = element
        self.extra_authors = extra_authors

    def resolve(self, database: "Database") -> Tuple[User, ...]:
        self.element.extra_authors += self.extra_authors
        return self.extra_authors

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "👥 "
            msg += "Collab"
            msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Collab"
            msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Add Collaborators"

    def get_description(self) -> str:
        text = f"**{self.element.name}**\n"
        text += f"New collaborators: {', '.join([f'<@{i.id}>' for i in self.extra_authors])}"
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["element"] = self.element.id
        data["extra_authors"] = [i.id for i in self.extra_authors]
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "AddCollabPoll":
        poll = AddCollabPoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["element"]],
            tuple(loader.users[i] for i in data["extra_authors"]),
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class RemoveCollabPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "element",
        "extra_authors",
    )

    def __init__(
        self, author: User, element: Element, extra_authors: Tuple[User, ...]
    ) -> None:
        super(RemoveCollabPoll, self).__init__(author)
        self.element = element
        self.extra_authors = extra_authors

    def resolve(self, database: "Database") -> Tuple[User, ...]:
        for i in self.extra_authors:
            self.element.extra_authors.remove(i)
        return self.extra_authors

    def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "🚷 "
            msg += "Remove Collaborators"
            msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += f"Remove Collaborators"
            msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
            msg += f"By <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Remove Collaborators"

    def get_description(self) -> str:
        text = f"**{self.element.name}**\n"
        text += f"Remove Collaborators: {', '.join([f'<@{i.id}>' for i in self.extra_authors])}"
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["element"] = self.element.id
        data["extra_authors"] = [i.id for i in self.extra_authors]
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "RemoveCollabPoll":
        poll = RemoveCollabPoll(
            loader.users[data["author"]],
            loader.elem_id_lookup[data["element"]],
            tuple(loader.users[i] for i in data["extra_authors"]),
        )
        poll.votes = data["votes"]
        poll.creation_time = data["creation_time"]
        return poll


class Database(SavableMixin):
    # TODO: requires __slots__? only one instance of Database per GameInstance

    def __init__(
        self,
        elements: Dict[str, Element],
        starters: Tuple[Element, ...],
        combos: Dict[Tuple[int, ...], Element],
        users: Dict[int, User],
        polls: List[Poll],
    ) -> None:
        self.elements = elements
        self.starters = starters
        self.combos = combos
        self.users = users
        self.polls = polls
        self.complexity_lock = False

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
            elem: [] for elem in self.elem_id_lookup
        }
        for combo, result in combos.items():
            self.combo_lookup[result.id].append(combo)
            for elem in combo:
                if combo not in self.used_in_lookup[elem]:
                    self.used_in_lookup[elem].append(combo)

        self.found_by_lookup: Dict[int, List[int]] = {
            elem: [] for elem in self.elem_id_lookup
        }
        for user in self.users.values():
            for elem in user.inv:
                self.found_by_lookup[elem].append(user.id)

    def calculate_infos(self) -> None:
        self.complexity_lock = True
        # Ordered set but using dict
        self.complexities: Dict[int, int] = {elem.id: 0 for elem in self.starters}
        self.min_elem_tree: Dict[int, Tuple[int, ...]] = {
            elem.id: () for elem in self.starters
        }
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
                for elem_id in unseen:
                    assert elem_id not in self.complexities
                    element = self.elem_id_lookup[elem_id]
                    self.elements.pop(element.name.lower())
                    self.combo_lookup.pop(elem_id)
                    self.used_in_lookup.pop(elem_id)
                    self.elem_id_lookup.pop(elem_id)
                    self.found_by_lookup.pop(elem_id)
                unseen.clear()
        self.complexity_lock = False

    def get_complexity(self, elem_id: int) -> Union[int, None]:
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
        else:
            return None

    def check_colors(self):
        for element in self.elements.values():
            if element.colorer is not None:
                continue
            if 0 < element.color < 0xFFFFFF:
                continue
            if not self.combo_lookup[element.id]:
                continue

            combo = [self.elem_id_lookup[x] for x in self.combo_lookup[element.id][0]]
            element.color = Element.get_color(combo)

    def update_element_info(self, element: Element, combo: Tuple[int, ...]) -> None:
        if self.complexity_lock:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        new_complexity = max(self.complexities[x] for x in combo)
        if new_complexity < self.complexities[element.id]:
            self.complexities[element.id] = new_complexity
            self.min_elem_tree[element.id] = combo

    def get_path(self, element: Element) -> List[int]:
        if self.complexity_lock:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        path = []
        visited = set()
        stack = [element.id]
        while stack:
            node = stack[-1]
            if node not in visited:
                if (
                    not self.min_elem_tree[node]
                    or self.min_elem_tree[node][-1] in visited
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
        )
        database.calculate_infos()
        return database

    def add_element(self, element: Element):
        if element.name.lower() not in self.elements:
            self.elements[element.name.lower()] = element
            self.elem_id_lookup[element.id] = element
            self.combo_lookup[element.id] = []
            self.used_in_lookup[element.id] = []
            self.found_by_lookup[element.id] = []

    def has_element(self, element: str) -> bool:
        return element.lower() in self.elements

    def get_combo_result(self, combo: Tuple[Element, ...]) -> Union[Element, None]:
        sorted_combo = tuple(sorted(elem.id for elem in combo))
        if sorted_combo in self.combos:
            return self.combos[sorted_combo]
        return None

    def set_combo_result(self, combo: Tuple[Element, ...], result: Element) -> None:
        if self.complexity_lock:
            raise InternalError("Complexity lock", "Complexity calculations in process")
        sorted_combo = tuple(sorted(elem.id for elem in combo))
        if sorted_combo in self.combos:
            raise InternalError("Combo exists", "That combo already exists")
        if result.name.lower() not in self.elements:
            self.add_element(result)
        self.combos[sorted_combo] = result
        self.combo_lookup[result.id].append(sorted_combo)
        if result.id not in self.complexities:
            if self.get_complexity(result.id) is None:
                raise InternalError(
                    "Failed getting complexity",
                    "No combo found with existing complexity",
                )
        else:
            self.update_element_info(result, sorted_combo)
        for elem in sorted_combo:
            if sorted_combo not in self.used_in_lookup[elem]:
                self.used_in_lookup[elem].append(sorted_combo)

    def convert_to_dict(self, data: dict) -> None:
        # Users MUST be first to be saved or loaded
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
        starters = tuple(loader.elem_id_lookup[elem] for elem in data["starters"])
        combos = {}
        for combo_ids in data["combos"]:
            key = tuple(int(id) for id in combo_ids.split(","))
            if data["combos"][combo_ids] in loader.elem_id_lookup:
                combos[key] = loader.elem_id_lookup[data["combos"][combo_ids]]
            else:
                print(
                    "Warning: dropping combo",
                    key,
                    "for element",
                    data["combos"][combo_ids],
                )
        users = {int(id): user for id, user in data["users"].items()}

        polls = [poll for poll in data["polls"] if poll is not None]
        return Database(
            {elem.name.lower(): elem for elem in data["elements"]},
            starters,
            combos,
            users,
            polls,
        )


AIR = Element("Air", id=1)
EARTH = Element("Earth", id=2)
FIRE = Element("Fire", id=3)
WATER = Element("Water", id=4)
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
    def normalize_starter(self, element: Element) -> Element:
        starter = self.db.elements[element.name.lower()]
        assert starter in self.db.starters
        return starter

    def login_user(self, user_id: int) -> User:
        if user_id not in self.db.users:
            inv = [elem.id for elem in self.db.starters]
            self.db.users[user_id] = User(inv, 0, user_id)
        return self.db.users[user_id]

    def check_element(self, element_name: str, user: Optional[User] = None) -> Element:
        if not self.db.has_element(element_name):
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

    def check_elements(
        self, element_name_list: List[str], user: Optional[User] = None
    ) -> Tuple[Element]:
        elements = []
        not_in_inv = []
        for i in element_name_list:
            try:
                elements.append(self.check_element(i, user))
            except GameError as g:
                if g.type == "Not in inv":
                    not_in_inv.append(g.meta["element"])
                else:
                    raise g
        if not_in_inv:
            raise GameError(
                "Not in inv",
                "The user does not have the element requested",
                {"elements": not_in_inv, "user": user},
            )
        return tuple(elements)

    def combine(self, user: User, combo: Tuple[str, ...]) -> Element:
        element_combo = self.check_elements(combo, user)
        user.last_combo = tuple(sorted(element_combo))
        result = self.db.get_combo_result(element_combo)
        if result is None:
            raise GameError("Not a combo", "That combo does not exist")
        user.last_element = result
        if result.id in user.inv:
            raise GameError(
                "Already have element",
                f"You made {result.name}, but you already have it",
                {"element": result},
            )
        self.db.found_by_lookup[result.id].append(user.id)
        user.add_element(result)
        user.last_element = result
        return result

    def suggest_poll(self, poll: Poll) -> Poll:
        if poll.author.active_polls > self.poll_limit:
            raise GameError("Too many active polls")
        self.db.polls.append(poll)
        poll.author.active_polls += 1
        return poll

    def suggest_element(
        self, user: User, combo: Tuple[Element, ...], result: str
    ) -> ElementPoll:
        poll = ElementPoll(user, combo, result, self.db.has_element(result))
        self.suggest_poll(poll)
        return poll

    def check_polls(self) -> List[Poll]:
        new_polls = []
        deleted_polls = []
        for poll in self.db.polls:
            if poll.votes >= self.vote_req:
                # Poll was accepted
                poll.accepted = True
                try:
                    poll.resolve(self.db)
                except InternalError as e:
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

    def check_single_poll(self, poll: Poll) -> bool:
        if poll.votes >= self.vote_req:
            # Poll was accepted
            poll.accepted = True
            try:
                poll.resolve(self.db)
            except InternalError as e:
                # Sometimes occurs when poll is accepted twice
                pass
            poll.author.active_polls -= 1
            self.db.polls.remove(poll)
            return True
        elif poll.votes <= -self.vote_req:
            # Poll was denied
            poll.author.active_polls -= 1
            self.db.polls.remove(poll)
            return True
        else:
            return False

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
            game.suggest_element(
                user, tuple(game.check_element(name) for name in combo), "inferno"
            )
    game.db.polls[0].votes += 4
    game.check_polls()
    print(user.inv)
