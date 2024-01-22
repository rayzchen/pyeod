__all__ = [
    "parse_element_list",
    "get_multiplier",
    "build_info_embed",
    "generate_embed_list",
    "prepare_file",
    "get_page_limit",
]


from pyeod import config
from pyeod.errors import InternalError
from pyeod.frontend.model import DiscordGameInstance
from pyeod.model import ColorPoll, Element, GameInstance, User
from pyeod.utils import calculate_difficulty
from discord import Embed, EmbedField, File, EmbedFooter
from io import BytesIO, StringIO
from typing import Optional, List, Union
import gzip
import math


def parse_element_list(content: str, delimiter: Optional[str] = None) -> List[str]:
    if delimiter is None:
        delimiters = [
            "\n",
            "+",
            ",",
            "plus",  # consistency with EoDE
        ]
    else:
        delimiters = [delimiter]
    elements = None
    for delimiter in delimiters:
        if delimiter in content:
            elements = content.split(delimiter)
            break
    if elements is None:
        elements = [content]
    stripped_elements = [item.strip() for item in elements if item.strip()]
    return stripped_elements


def get_multiplier(text, fallback=None):
    number = text.split(" ", 1)[0][1:]
    if number.isdecimal():
        multiplier = int(number)
        if " " in text:
            element = text.split(" ", 1)[1].strip()
        elif fallback is not None:
            element = fallback
        else:
            multiplier = 1
            element = text
        return element.strip(), multiplier
    return text.strip(), 1


async def build_info_embed(
    instance: GameInstance, element: Element, user: User
) -> Embed:
    if instance.db.complexity_lock.reader.locked:
        raise InternalError("Complexity lock", "Complexity calculations in process")

    description = f"Element **#{element.id}**\n"
    if element.id in user.inv:
        description += "📫 **You have this.**"
    else:
        description += "📭 **You don't have this.**"
    description += "\n\n**Mark**\n"

    if element.author is None:
        creator = "The Big Bang"
        icon = "♾️"
    elif element.author == 0:
        creator = "<@0>"
        icon = instance.get_icon(0)
    else:
        creator = f"<@{element.author.id}>"
        icon = instance.get_icon(element.author.icon)

    if element.created == 0:
        timestamp = "The Dawn Of Time"
    else:
        timestamp = f"<t:{element.created}>"

    tree_size = len(instance.db.path_lookup[element.id])

    async with instance.db.element_lock.reader:
        complexity = instance.db.complexities[element.id]
        made_with = len(instance.db.combo_lookup[element.id])
        used_in = len(instance.db.used_in_lookup[element.id])
        found_by = len(instance.db.found_by_lookup[element.id])

    if element.mark:
        description += element.mark
    else:
        description += "None"

    if element.marker is not None:
        marker = f"<@{element.marker.id}>"

    if element.colorer:
        colorer = f"<@{element.colorer.id}>"

    if element.imager:
        imager = f"<@{element.imager.id}>"

    if element.iconer:
        iconer = f"<@{element.iconer.id}>"

    if element.extra_authors:
        collaborators = ", ".join([f"<@{i.id}>" for i in element.extra_authors])

    if element.id in user.inv:
        # In case they didn't use the shortest path
        progress = "100.00%"
    else:
        progress_set = instance.db.path_lookup[element.id] & set(user.inv)
        progress = f"{len(progress_set) / tree_size * 100:.2f}%"

    categories = sorted(instance.db.category_lookup[element.id])
    if len(categories) < 4:
        if not categories:
            category_list = "N/A"
        else:
            category_list = ", ".join(categories)
    else:
        category_list = ", ".join(categories[:3])
        category_list += " and " + str(len(categories) - 3) + " more..."

    fields = [
        EmbedField(f"{icon} Creator", creator, True),
        EmbedField("👥 Collaborators", collaborators, True)
        if element.extra_authors
        else None,
        EmbedField("📅 Created At", timestamp, True),
        EmbedField("🌲 Tree Size", f"{tree_size:,}", True),
        EmbedField("📶 Element Tier", f"{complexity:,}", True),
        EmbedField(
            "\U0001F4DB Difficulty",
            f"{calculate_difficulty(tree_size, complexity):,.2f}",
            True,
        ),
        EmbedField("🔨 Made With", str(made_with), True),
        EmbedField("🧰 Used In", str(used_in), True),
        EmbedField("🔍 Found By", str(found_by), True),
        EmbedField("🗣️ Marker", marker, True) if element.marker else None,
        EmbedField("🖌️ Color", ColorPoll.get_hex(element.color), True),
        EmbedField("🎨 Colorer", colorer, True) if element.colorer else None,
        EmbedField("🖼️ Imager", imager, True) if element.imager else None,
        EmbedField("📍 Iconer", iconer, True) if element.iconer else None,
        EmbedField("📊 Progress", progress, True),
        EmbedField("📂 Categories", category_list, False),
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
    lines: List[str],
    title: str,
    limit: int,
    color: int = config.EMBED_COLOR,
    thumbnail: str = None,
    footer: str = "",
) -> List[Embed]:
    if not lines:
        embeds = [Embed(title=title, color=color, thumbnail=thumbnail)]
        return embeds

    if footer:
        footer_object = EmbedFooter(footer)
    else:
        footer_object = None
    embeds: List[Embed] = []
    for i in range(math.ceil(len(lines) / limit)):
        embeds.append(
            Embed(
                title=title,
                description="\n".join(lines[i * limit : i * limit + limit]),
                color=color,
                thumbnail=thumbnail,
                footer=footer_object,
            )
        )
    return embeds


def prepare_file(fp: Union[StringIO, BytesIO], filename: str):
    if isinstance(fp, StringIO):
        encoded = fp.getvalue().encode("utf-8")
    else:
        encoded = fp.getvalue()
    if len(encoded) > 25 * 1024 * 1024:
        fp = BytesIO(gzip.compress(encoded, 9))
        filename += ".gz"
    return File(fp=fp, filename=filename)


def get_page_limit(instance: DiscordGameInstance, channel_id: int) -> int:
    if channel_id in instance.channels.play_channels:
        return 30
    return 10
