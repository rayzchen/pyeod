__all__ = [
    "ElementPoll",
    "MarkPoll",
    "ColorPoll",
    "ImagePoll",
    "IconPoll",
    "AddCollabPoll",
    "RemoveCollabPoll",
    "AddCategoryPoll",
    "RemoveCategoryPoll",
]


from pyeod.errors import InternalError, GameError
from pyeod.model.types import Element, Poll, User, Database, ElementCategory
from discord import Embed  # I have sinned but our news message structure is weird
from typing import Tuple, Union
import time


class ElementPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "combo",
        "result",
        "exists",
        "id_override",
    )

    def __init__(
        self, author: User, combo: Tuple[Element, ...], result: str, exists: bool
    ) -> None:
        super(ElementPoll, self).__init__(author)
        self.combo = combo
        self.result = result
        self.exists = exists
        self.id_override = None

    async def resolve(self, database: Database) -> Element:  # Return Element back
        async with database.element_lock.writer:
            if self.result.lower() not in database.elements:
                if self.id_override is not None:
                    if self.id_override in database.elem_id_lookup:
                        raise InternalError(
                            "Override ID in use", "Cannot use overridden ID"
                        )
                    if self.id_override > database.max_id:
                        database.max_id = self.id_override
                    selected_id = self.id_override
                else:
                    database.max_id += 1
                    selected_id = database.max_id
                color = Element.get_color(self.combo)
                element = Element(
                    self.result,
                    self.author,
                    round(time.time()),
                    selected_id,
                    color=color,
                )
            else:
                element = database.elements[self.result.lower()]
            await database.set_combo_result(self.combo, element)
            try:
                await database.give_element(self.author, element)
            except GameError:
                # User suggested combo for element they already have
                pass
            if self.author.last_combo == self.combo:
                self.author.last_combo = ()
                self.author.last_element = element
            self.author.created_combo_count += 1
        return element

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "🆕 "
                if self.exists:
                    msg += "Combination"
                else:
                    msg += "Element"
                msg += f" - **{self.result}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) - "
                if self.exists:
                    msg += "Combination "
                    msg += f"**\\#{len(instance.db.combos) + 1}**"
                else:
                    msg += "Element "
                    msg += f"**\\#{instance.db.elements[self.result.lower()].id}**"
            else:
                msg += "❌ Poll Rejected - "
                if self.exists:
                    msg += "Combination"
                else:
                    msg += "Element"
                msg += f" - **{self.result}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
            return msg

    def get_title(self) -> str:
        return "Combination" if self.exists else "Element"

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
    def convert_from_dict(loader, data: dict) -> Union["ElementPoll", None]:
        combo = []
        for elem in data.get("combo"):  # Must be present
            if elem in loader.elem_id_lookup:
                combo.append(loader.elem_id_lookup[elem])
            else:
                # Perhaps saved broken poll
                print(
                    "Warning: dropping combo",
                    data.get("combo"),
                    "for element",
                    data.get("result"),
                    "in poll",
                )
                return None
        poll = ElementPoll(
            loader.users[data.get("author")],
            tuple(loader.elem_id_lookup[elem] for elem in data.get("combo")),
            data.get("result"),
            # Doesn't strictly need to be stored so not necessary to be present
            data.get("exists", False),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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

    async def resolve(self, database: Database) -> str:
        async with database.element_lock.writer:
            self.marked_element.mark = self.mark
            self.marked_element.marker = self.author
            return self.mark

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += ":scroll: "  # Scroll emoji, not unicode cus for some reason it doesn't work
                msg += "Mark"
                msg += f" - **{self.marked_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "❌ Poll Rejected - "
                msg += "Mark"
                msg += f" - **{self.marked_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
            return msg

    def get_title(self) -> str:
        return "Mark"

    def get_description(self) -> str:
        text = f"**{self.marked_element.name}**\n"
        text += f"Old Mark: \n{self.marked_element.mark}\n\nNew Mark:\n{self.mark}"
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("marked_element")],
            data.get("mark", ""),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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
            self.color = ColorPoll.get_int(color)
        else:
            self.color = color

    async def resolve(self, database: Database) -> int:
        async with database.element_lock.writer:
            self.colored_element.color = self.color
            self.colored_element.colorer = self.author
            return self.color

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "🎨 "
                msg += "Color"
                msg += f" - **{self.colored_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "❌ Poll Rejected - "
                msg += "Color"
                msg += f" - **{self.colored_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
            return msg

    def get_title(self) -> str:
        return "Color"

    def get_description(self) -> str:
        text = f"**{self.colored_element.name}**\n"
        text += f"Old Color: \n{ColorPoll.get_hex(self.colored_element.color)}\n"
        text += f"\nNew Color:\n{ColorPoll.get_hex(self.color)}"
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    @staticmethod
    def get_hex(color: int) -> str:
        rgb = [(color & 0xFF0000) >> 16, (color & 0x00FF00) >> 8, color & 0x0000FF]
        return "#" + "".join(hex(x)[2:].rjust(2, "0") for x in rgb)

    @staticmethod
    def get_int(color: str) -> int:
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("colored_element")],
            data.get("color", 0),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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

    async def resolve(self, database: Database) -> str:
        async with database.element_lock.writer:
            self.imaged_element.image = self.image
            self.imaged_element.imager = self.author
            return self.image

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "🖼️ "
                msg += "Image"
                msg += f" - **{self.imaged_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
                embed = Embed(
                    title="New Image", image=self.image, color=self.imaged_element.color
                )
                return msg, embed
            else:
                msg += "❌ Poll Rejected - "
                msg += "Image"
                msg += f" - **{self.imaged_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("imaged_element")],
            data.get("image", ""),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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

    async def resolve(self, database: Database) -> str:
        async with database.element_lock.writer:
            self.iconed_element.icon = self.icon
            self.iconed_element.iconer = self.author
            return self.icon

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "📍 "
                msg += "Icon"
                msg += f" - **{self.iconed_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "❌ Poll Rejected - "
                msg += "Icon"
                msg += f" - **{self.iconed_element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("iconed_element")],
            data.get("icon", ""),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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

    async def resolve(self, database: Database) -> Tuple[User, ...]:
        async with database.element_lock.writer:
            self.element.extra_authors += self.extra_authors
            return self.extra_authors

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "👥 "
                msg += "Collab"
                msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "❌ Poll Rejected - "
                msg += "Collab"
                msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("element")],
            tuple(loader.users[i] for i in data.get("extra_authors")),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
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

    async def resolve(self, database: Database) -> Tuple[User, ...]:
        async with database.element_lock.writer:
            for i in self.extra_authors:
                self.element.extra_authors.remove(i)
            return self.extra_authors

    async def get_news_message(self, instance: "GameInstance") -> str:
        async with instance.db.element_lock.reader:
            msg = ""
            if self.accepted:
                msg += "🚷 "
                msg += "Remove Collaborators"
                msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "❌ Poll Rejected - "
                msg += "Remove Collaborators"
                msg += f" - **{self.element.name}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
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
            loader.users[data.get("author")],
            loader.elem_id_lookup[data.get("element")],
            tuple(loader.users[i] for i in data.get("extra_authors")),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
        return poll


class AddCategoryPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "category",
        "elements",
    )

    def __init__(
        self, author: User, category: str, elements: Tuple[Element, ...]
    ) -> None:
        super(AddCategoryPoll, self).__init__(author)
        self.category = category
        self.elements = elements

    async def resolve(self, database: Database) -> Tuple[Element, ...]:
        # Extra lookup table checks in case of mismatch
        async with database.category_lock.reader:
            if self.category.lower() not in database.categories:
                database.categories[self.category] = ElementCategory(self.category, self.elements)
                for element in self.elements:
                    if self.category not in database.category_lookup[element.id]:
                        database.category_lookup[element.id].append(category.name)
            else:
                category = database.categories[self.category.lower()]
                if not isinstance(category, ElementCategory):
                    return
                for element in self.elements:
                    if element not in category.elements:
                        category.elements.append(element)
                    if category.name not in database.category_lookup[element.id]:
                        database.category_lookup[element.id].append(category.name)

    async def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            msg += "📂 "
            msg += f"Added **{len(self.elements)}** element"
            if len(self.elements) > 1:
                msg += "s"
            msg += f" to category **{self.category}** (Lasted **{self.get_time()}** • "
            msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += "Add to category "
            msg += f"**{self.category}** (Lasted **{self.get_time()}** • "
            msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Categorize"

    def get_description(self) -> str:
        text = f"**{self.category}**\n\n"
        text += f"Elements:"
        for element in self.elements[:10]:
            text += f"\n**{element.name}**"
        if len(self.elements) > 10:
            text += f"\nand {len(self.elements) - 10} more..."
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["category"] = self.category
        data["elements"] = [e.id for e in self.elements]
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "AddCategoryPoll":
        poll = AddCategoryPoll(
            loader.users[data.get("author")],
            data.get("category"),
            tuple(loader.elem_id_lookup[e] for e in data.get("elements")),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
        return poll


class RemoveCategoryPoll(Poll):
    __slots__ = (
        "author",
        "votes",
        "accepted",
        "creation_time",
        "category",
        "elements",
        "deleted",  # not a saved attribute
    )

    def __init__(
        self, author: User, category: str, elements: Tuple[Element, ...]
    ) -> None:
        super(RemoveCategoryPoll, self).__init__(author)
        self.elements = elements
        self.category = category
        self.deleted = False

    async def resolve(self, database: Database) -> Tuple[Element, ...]:
        async with database.category_lock.reader:
            if self.category.lower() not in database.categories:
                return
            category = database.categories[self.category.lower()]
            if not isinstance(category, ElementCategory):
                return
            for element in self.elements:
                if element in category.elements:
                    category.elements.remove(element)
                if category.name in database.category_lookup[element.id]:
                    database.category_lookup[element.id].remove(category.name)
            if not category.elements:
                self.deleted = True
                database.categories.pop(self.category.lower())

    async def get_news_message(self, instance: "GameInstance") -> str:
        msg = ""
        if self.accepted:
            if self.deleted:
                msg += "📂 "
                msg += f"Deleted category **{self.category}**"
                msg += f" (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
            else:
                msg += "📂 "
                msg += f"Removed **{len(self.elements)}** element"
                if len(self.elements) > 1:
                    msg += "s"
                msg += f" from category **{self.category}** (Lasted **{self.get_time()}** • "
                msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>)"
        else:
            msg += "❌ Poll Rejected - "
            msg += "Remove from category "
            msg += f"**{self.category}** (Lasted **{self.get_time()}** • "
            msg += f"By {instance.get_icon(self.author.icon)} <@{self.author.id}>) "
        return msg

    def get_title(self) -> str:
        return "Uncategorize"

    def get_description(self) -> str:
        text = f"**{self.category}**\n\n"
        text += f"Elements:"
        for element in self.elements[:10]:
            text += f"\n**{element.name}**"
        if len(self.elements) > 10:
            text += f"\nand {len(self.elements) - 10} more..."
        text += f"\n\nSuggested by <@{self.author.id}>"
        return text

    def convert_to_dict(self, data: dict) -> None:
        data["author"] = self.author.id
        data["votes"] = self.votes
        data["category"] = self.category
        data["elements"] = [e.id for e in self.elements]
        data["creation_time"] = self.creation_time

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "RemoveCategoryPoll":
        poll = RemoveCategoryPoll(
            loader.users[data.get("author")],
            data.get("category"),
            tuple(loader.elem_id_lookup[e] for e in data.get("elements")),
        )
        poll.votes = data.get("votes", 0)
        poll.creation_time = data.get("creation_time", round(time.time()))
        return poll
