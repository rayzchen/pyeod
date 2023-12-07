__all__ = [
    "parse_element_list",
    "build_info_embed",
    "generate_embed_list",
    "get_page_limit",
]


from pyeod import config
from pyeod.frontend.model import DiscordGameInstance
from pyeod.model import ColorPoll, Element, GameInstance, User
from discord import Embed, EmbedField
from typing import List
import math


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
    if instance.db.complexity_lock:
        raise InternalError("Complexity lock", "Complexity calculations in process")
    description = f"Element **#{element.id}**\n"
    if element.id in user.inv:
        description += "📫 **You have this.**"
    else:
        description += "📭 **You don't have this.**"
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

    if element.mark and element.marker is not None:
        marker = f"<@{element.marker.id}>"
        description += element.mark
    else:
        description += "None"

    if element.colorer:
        colorer = f"<@{element.colorer.id}>"

    if element.imager:
        imager = f"<@{element.imager.id}>"

    if element.iconer:
        iconer = f"<@{element.iconer.id}>"

    if element.extra_authors:
        collaborators = ", ".join([f"<@{i.id}>" for i in element.extra_authors])

    path = instance.db.get_path(element)
    if element.id in user.inv:
        # In case they didn't use the shortest path
        progress = "100%"
    else:
        progress = f"{len(set(path) & set(user.inv)) / len(path) * 100:.2f}%"

    fields = [
        EmbedField("🧙‍♂️ Creator", creator, True),
        EmbedField("👥 Collaborators", collaborators, True)
        if element.extra_authors
        else None,
        EmbedField("📅 Created At", timestamp, True),
        EmbedField("🌲 Tree Size", str(len(path)), True),
        EmbedField("🔀 Complexity", str(instance.db.complexities[element.id]), True),
        EmbedField("🔨 Made With", str(len(instance.db.combo_lookup[element.id])), True),
        EmbedField("🧰 Used In", str(len(instance.db.used_in_lookup[element.id])), True),
        EmbedField(
            "🔍 Found By", str(len(instance.db.found_by_lookup[element.id])), True
        ),
        EmbedField("🗣️ Marker", marker, True) if element.marker else None,
        EmbedField("🖌️ Color", ColorPoll.get_hex(element.color), True),
        EmbedField("🎨 Colorer", colorer, True) if element.colorer else None,
        EmbedField("🖼️ Imager", imager, True) if element.imager else None,
        EmbedField("📍 Iconer", iconer, True) if element.iconer else None,
        EmbedField("📂 Categories", "N/A", False),
        EmbedField("📊 Progress", progress, False),
    ]

    embed = Embed(
        title=element.name + " Info",
        description=description,
        fields=[field for field in fields if field is not None],
        color=element.color,
    )

    if element.image:
        embed.set_thumbnail(url=element.image)

    if element.icon:
        embed.title = " "
        embed.set_author(name=element.name + " Info", icon_url=element.icon)

    return embed


def generate_embed_list(
    lines: List[str], title: str, limit: int, color: int = config.embed_color
) -> List[Embed]:
    if not lines:
        embeds = [Embed(title=title, color=color)]
        return embeds

    embeds = []
    for i in range(math.ceil(len(lines) / limit)):
        embeds.append(
            Embed(
                title=title,
                description="\n".join(lines[i * limit : i * limit + limit]),
                color=color,
            )
        )
    return embeds


def get_page_limit(instance: DiscordGameInstance, channel_id: int) -> int:
    if channel_id in instance.channels.play_channels:
        return 30
    return 10
