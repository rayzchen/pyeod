from typing import Optional, Tuple, List, Union, Dict, Type, TypeVar
from pyeod.model import (
    Database,
    Element,
    GameInstance,
    InternalError,
    User,
    Poll,
)
from discord import Embed, EmbedField, ButtonStyle
from discord.ext import pages, bridge
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
        # active_polls: Optional[Dict[int, Poll]] = [],
        poll_msg_lookup: Optional[Dict[int, Poll]] = None,
        starter_elements: Optional[Tuple[Element, ...]] = None,
    ) -> None:
        super().__init__(db, vote_req, poll_limit, starter_elements)
        if channels is None:
            self.channels = ChannelList()
        else:
            self.channels = channels
        if poll_msg_lookup is None:
            self.poll_msg_lookup = {}
        else:
            self.poll_msg_lookup = poll_msg_lookup

    def convert_to_dict(self, data: dict) -> None:
        super(DiscordGameInstance, self).convert_to_dict(data)
        data["channels"] = {
            "news": self.channels.news_channel,
            "voting": self.channels.voting_channel,
            "play": self.channels.play_channels,
        }
        data["poll_msg_lookup"] = {}
        for id, poll in self.poll_msg_lookup.items():
            # In case poll is deleted while saving, shouldn't cause too much issue
            # TODO: asyncio lock for accessing db?
            if poll in self.db.polls:
                data["poll_msg_lookup"][id] = self.db.polls.index(poll)

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "DiscordGameInstance":
        lookup = {}
        for id, poll_idx in data.get("poll_msg_lookup", {}).items():
            lookup[id] = data["db"].polls[poll_idx]
        return DiscordGameInstance(
            data["db"],
            data["vote_req"],
            data["poll_limit"],
            ChannelList(
                data["channels"]["news"],
                data["channels"]["voting"],
                data["channels"]["play"],
            ),
            lookup,
        )

    def convert_poll_to_embed(self, poll: Poll):
        embed = Embed(title=poll.get_title(), description=poll.get_description())
        # Ray: You can change your vote, if you suggested this poll, downvote it to delete it
        # Ray: Shorter footer is neater?
        # Cheesy: How do new users know how to delete polls tho?
        embed.set_footer(text="You can change your vote")
        return embed


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


async def build_info_embed(
    instance: GameInstance, element: Element, user: User
) -> Embed:
    description = f"Element **#{element.id}**\n"
    if element.id in user.inv:
        description += "**You have this.**"
    else:
        description += "**You don't have this.**"
    description += "\n\n**Mark**\n"

    if element.author is None:
        creator = "The Big Bang"
    elif element.author == 0:
        creator = "<@0>"
    else:
        creator = f"<@{element.author.id}>"

    if element.created == 0:
        timestamp = "The Dawn Of Time"
    else:
        timestamp = f"<t:{element.created}>"

    if element.mark:
        marker = f"<@{element.marker.id}>"
        description += element.mark
    else:
        description += "None"

    if element.extra_authors:
        collaborators = ", ".join([f"<@{i.id}>" for i in element.extra_authors])

    fields = [
        EmbedField("Creator", creator, True),
        EmbedField("Collaborators", collaborators, True)
        if element.extra_authors
        else None,
        EmbedField("Created At", timestamp, True),
        EmbedField("Tree Size", len(instance.db.get_path(element)), True),
        EmbedField("Complexity", instance.db.complexities[element.id], True),
        EmbedField("Made With", len(instance.db.combo_lookup[element.id]), True),
        EmbedField("Used In", len(instance.db.used_in_lookup[element.id]), True),
        EmbedField("Found By", len(instance.db.found_by_lookup[element.id]), True),
        EmbedField("Comment", element.mark, True) if element.mark else None,
        EmbedField("Commenter", marker, True) if element.mark else None,
        EmbedField("Colorer", "N/A", True),
        EmbedField("Imager", "N/A", True),
        EmbedField("Categories", "N/A", False),
    ]

    return Embed(
        title=element.name + " Info",
        description=description,
        fields=[field for field in fields if field is not None],
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
    if not lines:
        embeds = [Embed(title=title)]
        return embeds

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


class ElementalBot(bridge.AutoShardedBot):
    async def add_poll(
        self,
        server: DiscordGameInstance,
        poll: Poll,
        ctx: bridge.BridgeContext,
        suggestion_message: str,
    ):
        if server.vote_req == 0:
            server.check_polls()
            news_channel = await self.fetch_channel(server.channels.news_channel)
            await news_channel.send(poll.get_news_message(server))
        else:
            voting_channel = await self.fetch_channel(server.channels.voting_channel)
            msg = await voting_channel.send(embed=server.convert_poll_to_embed(poll))
            server.poll_msg_lookup[msg.id] = poll
        await ctx.reply(suggestion_message)
        if server.vote_req != 0:  # Adding reactions after just feels snappier
            await msg.add_reaction("\U0001F53C")  # ⬆️ Emoji
            await msg.add_reaction("\U0001F53D")
