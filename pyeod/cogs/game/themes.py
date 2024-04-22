from pyeod import config
from pyeod.frontend import ElementalBot, InstanceManager
from pyeod.frontend.utils import get_current_theme
from pyeod.model.types import GameError
from discord import Embed, User
from discord.ext import bridge, commands
from typing import Optional
from random import shuffle, seed
from datetime import datetime, timedelta

def turn_theme_str_to_embed(theme_emojis:str, theme_name:str, theme_description:str) -> Embed:
    theme_emoji1, theme_emoji2 = theme_emojis.split(",")
    #Turn to multiline fstring
    
    start_date = datetime(2024, 1, 1)

    next_week_start = start_date + timedelta(days=-start_date.weekday(), weeks=((datetime.now() - start_date).days // 7 + 1))

    unix_timestamp = int(next_week_start.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    theme_description = f"""{(theme_emoji1 + theme_emoji2) * 10}
{(theme_emoji2 + theme_emoji1) * 10}
# {theme_name}

### {theme_description}

_ _
{(theme_emoji2 + theme_emoji1) * 10}
{(theme_emoji1 + theme_emoji2) * 10}

Next theme <t:{unix_timestamp}:R>"""
    embed = Embed(
        title="Current theme",
        description=theme_description,
        color=config.EMBED_COLOR,
    )
    embed.set_footer(text="Do /add_category #weeklytheme to add your element to the weekly theme category")
    return embed

class Themes(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot
    
    @bridge.bridge_command()
    @bridge.guild_only()
    async def weekly_theme(self, ctx: bridge.BridgeContext):
        """Gives the current weekly theme"""
        server = InstanceManager.current.get_or_create(ctx.guild.id)
        await ctx.respond(embed=turn_theme_str_to_embed(*get_current_theme(server, ctx.guild.id)))

def setup(client):
    client.add_cog(Themes(client))