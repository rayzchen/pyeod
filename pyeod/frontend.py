from typing import Optional, Tuple, List, Union, Dict, Type, TypeVar
from pyeod.model import Database, Element, GameInstance, InternalError, User
from discord import Client, Embed, EmbedField, ButtonStyle
from discord.ext import pages
import math


class ChannelList:
    def __init__(
        self,
        news_channel: int = None,
        voting_channel: int = None,
        play_channels: Optional[List[int]] = None,
    ) -> None:
        self.news_channel = news_channel
        self.voting_channel = voting_channel
        if play_channels is None:
            self.play_channels = []
        else:
            self.play_channels = play_channels


class DiscordGameInstance(GameInstance):
    # TODO: override serialization function to include channels attribute
    def __init__(
        self,
        db: Optional[Database] = None,
        vote_req: int = 0,
        poll_limit: int = 21,
        channels: Optional[ChannelList] = None,
        starter_elements: Optional[Tuple[Element, ...]] = None,
    ) -> None:
        super().__init__(db, vote_req, poll_limit, starter_elements)
        if channels is None:
            self.channels = ChannelList()
        else:
            self.channels = channels

    def convert_to_dict(self, data: dict) -> None:
        super(DiscordGameInstance, self).convert_to_dict(data)
        data["channels"] = {
            "news": self.channels.news_channel,
            "voting": self.channels.voting_channel,
            "play": self.channels.play_channels,
        }

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "DiscordGameInstance":
        return DiscordGameInstance(
            data["db"],
            data["vote_req"],
            data["poll_limit"],
            ChannelList(
                data["channels"]["news"],
                data["channels"]["voting"],
                data["channels"]["play"],
            ),
        )


InstT = TypeVar("InstT", bound=GameInstance)


class InstanceManager:
    current: Union["InstanceManager", None] = None

    def __init__(
        self, instances: Optional[Dict[int, DiscordGameInstance]] = None
    ) -> None:
        InstanceManager.current = self
        if instances is not None:
            self.instances = instances
        else:
            self.instances = {}

    def __contains__(self, id: int) -> bool:
        return self.has_instance(id)

    def __getitem__(self, id: int) -> DiscordGameInstance:
        return self.get_instance(id)

    def add_instance(self, id: int, instance: DiscordGameInstance) -> None:
        if id in self.instances:
            raise InternalError(
                "Instance overwrite", "GameInstance already exists with given ID"
            )
        self.instances[id] = instance

    def has_instance(self, id: int) -> bool:
        return id in self.instances

    def get_instance(self, id: int) -> DiscordGameInstance:
        if id not in self.instances:
            raise InternalError(
                "Instance not found", "The requested GameInstance not found"
            )
        return self.instances[id]

    def get_or_create(self, id: int, type: Type[InstT]) -> InstT:
        if not self.has_instance(id):
            instance = type()
            self.add_instance(id, instance)
        else:
            instance = self.get_instance(id)
        return instance


def parse_element_list(content: str) -> List[str]:
    #! TEMP COMBO PARSING SOLUTION
    # Will change to be more robust later, works for now
    elements = []
    if "\n" in content:
        elements = content.split("\n")
    elif "+" in content:
        elements = content.split("+")
    else:
        elements = content.split(",")
    stripped_elements = [item.strip() for item in elements if item]
    return stripped_elements


async def build_info_embed(instance: GameInstance, element: Element, user: User) -> Embed:
    description = f"Element **#{element.id}**\n"
    if element.id in user.inv:
        description += "**You have this.**"
    else:
        description += "**You don't have this.**"
    description += "\n\n**Mark**\n"
    # TODO: add mark

    if element.author is not None:
        creator = f"<@{element.author.id}>"
    else:
        creator = "The Big Bang"

    if element.created == 0:
        timestamp = "The Dawn Of Time"
    else:
        timestamp = f"<t:{element.created}>"

    return Embed(
        title=element.name + " Info",
        description=description,
        fields=[
            EmbedField("Creator", creator, True),
            EmbedField("Created At", timestamp, True),
            EmbedField("Tree Size", len(instance.db.paths[element.id]), True),
            EmbedField("Complexity", instance.db.complexities[element.id], True),
            EmbedField("Made With", len(instance.db.combo_lookup[element.id]), True),
            EmbedField("Used In", "N/A", True),
            EmbedField("Found By", "N/A", True),
            EmbedField("Commenter", "N/A", True),
            EmbedField("Colorer", "N/A", True),
            EmbedField("Imager", "N/A", True),
            EmbedField("Categories", "N/A", False),
        ],
    )


class FooterPaginator(pages.Paginator):
    def __init__(self, page_list, footer_text: str = "") -> None:
        buttons = [
            pages.PaginatorButton("prev", "◀", style=ButtonStyle.blurple),
            pages.PaginatorButton("next", "▶", style=ButtonStyle.blurple),
        ]
        super(FooterPaginator, self).__init__(
            page_list,
            show_indicator=False,
            author_check=False,
            use_default_buttons=False,
            loop_pages=True,
            custom_buttons=buttons,
        )
        self.footer_text = footer_text

    def update_buttons(self):
        buttons = super(FooterPaginator, self).update_buttons()
        page = self.pages[self.current_page]
        if isinstance(page, Embed):
            footer = f"Page {self.current_page + 1}/{self.page_count + 1}"
            if self.footer_text:
                footer += " • " + self.footer_text
            page.set_footer(text=footer)
        return buttons


def generate_embed_list(lines: List[str], title: str, limit: int) -> List[Embed]:
    embeds = []
    for i in range(math.ceil(len(lines) / limit)):
        embeds.append(
            Embed(
                title=title,
                description="\n".join(lines[i * limit : i * limit + limit]),
            )
        )
    return embeds


def get_page_limit(instance: DiscordGameInstance, channel_id: int) -> int:
    if channel_id in instance.channels.play_channels:
        return 30
    return 10
