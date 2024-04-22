__all__ = [
    "parse_element_list",
    "get_multiplier",
    "build_info_embed",
    "generate_embed_list",
    "prepare_file",
    "get_page_limit",
    "get_current_theme",
    "get_theme_category_name",
]


from pyeod import config
from pyeod.errors import InternalError
from pyeod.frontend.model import DiscordGameInstance
from pyeod.model import ColorPoll, Element, GameInstance, User
from pyeod.utils import calculate_difficulty
from discord import Embed, EmbedField, EmbedFooter, File
from io import BytesIO, StringIO
from typing import List, Union, Optional
import gzip
import math
import random
from datetime import datetime


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

    categories = []
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

themes = [
    ':flag_black:,:flag_white:#Flags#Flags are how nations identify themselves, show off your vexillological knowledge by making country flags as elements!',
    ':brown_square:,:green_square:#Minecraft Recipes#Minecraft is the best selling game of all time, show your enjoyment of mining and crafting by making minecraft crafting recipes as combos!',
    ':people_wrestling:,:person_bouncing_ball:#Sports#Sports are the best way to show off your skills in sports, show off your ability to play sports by making sports as elements!',
    ':musical_keyboard:,:musical_note:#Music#Music is like pictures but for your ears, show off how good your ears are by making songs and albums as elements!',
    ':alembic:,:test_tube:#Chemistry#Chemistry is all about mixing up strange liquids and seeing what they make, make chemical reactions as combos and molecules as elements!',
    ':pancakes:,:bacon:#Food#Food is like music but for your tongue, show off your strong salivary glands by making foods as elements!',
    ':wrench:,:hammer:#Tools#Tools are used to fix broken things, show off how not broken you are by making tools as elements!',
    ':octagonal_sign:,:vertical_traffic_light:#Traffic Laws#Traffic laws are how you don\'t die while driving, show off how safe you are by making traffic codes as elements!',
    ':ringed_planet:,:comet:#Planets#Planets are things in space, show your extensive space knowledge by making planets as elements!',
    ':anatomical_heart:,:lungs:#Body Parts#Body parts are the squishy bits inside your flesh, show you have the most body parts by making body parts as elements!',
    ':rainbow:,:paintbrush:#Colors#Colors are like food but for your eyes, show off how many colors you can see by making colors as elements!',
    ':exploding_head:,:thinking:#Fun Facts#Fun facts are like facts but with less sadness, show off how much useless knowledge you\'ve gleaned by making fun facts as combos!',
    ':red_square:,:rightarrow:#Youtube#Youtube is the video version of books, make youtube videos and channels as elements!',
    ':game_die:,:slot_machine:#Random#Gambling is AWESOME, use /random_combination to make random combos!',
    ':lotus:,:sunflower:#Flowers#Flowers are natures version of color, show your love for flowers by making flowers as elements!',
    ':snowflake:,:snowman:#Winter#Winter is the best time of the year, show off how cold you are by making winter as elements!',
    ':cupcake:,:cake:#Deserts#Deserts are like drugs but less cool, show off how much you love sugar by making desert recipes as combos!',
    ':tada:,:confetti_ball:#Holidays#Holidays are when we get to stop being forced to work in this capitalistic world simply to survive, show off your celebration skills by making holidays as elements!',
    ':video_game:,:desktop:#Video Games#Video games help us escape reality, show how much you love not touching grass by making video games as elements!',
    ':chart_with_upwards_trend:,:chart_with_downwards_trend:#Financial Crashes#Financial crashes are when the economy collapses due to the greed of the few, show your love for the economy by making financial crashes as combos!',
    ':1234:,:hash:#Numbers#Numbers are the best way to show off your ability to count, show off how many numbers you can count by making numbers as elements!',
    ]

def get_current_theme(instance: DiscordGameInstance, guild_id:int) -> tuple[str, str, str]:
    themes.sort()
    random.seed(guild_id)
    random.shuffle(themes)
    return themes[(datetime.now() - datetime(2024, 1, 1)).days // 7 % len(themes)].split("#")

def get_theme_category_name(instance:DiscordGameInstance, guild_id:int) -> str:
    return f"#{get_current_theme(instance, guild_id)[1]}"