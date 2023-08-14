from discord.ext import commands, bridge
from discord import User, NotFound
from pyeod.frontend import DiscordGameInstance, InstanceManager, ElementalBot


class Info(commands.Cog):
    def __init__(self, bot: ElementalBot):
        self.bot = bot

    # Don't use bridge command cus params
    @bridge.bridge_command(aliases=["c", "mark", "note"])
    async def comment(
        self, ctx: bridge.BridgeContext, *, marked_element: str, mark: str = None
    ):  # Sneaky use of args here
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        if ctx.is_app:
            if not mark:
                await ctx.respond("Please suggest a mark")
                return
            marked_element = marked_element.lower()
        else:
            split_msg = marked_element.split("|")
            if len(split_msg) < 2:
                await ctx.reply("Please separate each parameter with a |")
                return
            mark = split_msg[1].strip()
        if not server.db.has_element(marked_element):
            await ctx.respond("Not a valid element")
            return
        if len(mark) > 3000:
            await ctx.respond("Marks cannot be over 3000 characters in length")
            return
        element = server.db.elements[marked_element]
        poll = server.suggest_mark(user, element, mark)

        await self.bot.add_poll(
            server, poll, ctx, f"Suggested a new mark for {element.name}!"
        )

    @bridge.bridge_command(aliases=["acol"])
    async def add_collaborators(
        self,
        ctx: bridge.BridgeContext,
        *,
        element: str,
        collaborator1: User = None,
        collaborator2: User = None,
        collaborator3: User = None,
        collaborator4: User = None,
        collaborator5: User = None,
        collaborator6: User = None,
        collaborator7: User = None,
        collaborator8: User = None,
        collaborator9: User = None,
        collaborator10: User = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            element = element.lower()
            element = server.db.elements[element]
            for i in [
                collaborator1,
                collaborator2,
                collaborator3,
                collaborator4,
                collaborator5,
                collaborator6,
                collaborator7,
                collaborator8,
                collaborator9,
                collaborator10,
            ]:
                if i:
                    extra_authors.append(i.id)

        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("Please separate each parameter with a |")
                return
            element = split_msg[0].lower().strip()
            element = server.db.elements[element]
            for i in (
                split_msg[1]
                .strip()
                .replace(",", " ")
                .replace("|", " ")
                .replace("  ", " ")
                .replace("  ", " ")
                .split(" ")
            ):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond(
                        "Please only enter valid users, using the @<user> syntax separated by spaces"
                    )
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if (
                i not in [i.id for i in element.extra_authors]
                and element.author
                and i != element.author.id
                and i not in authors
                and i != self.bot.user.id
            ):
                authors.append(server.login_user(i))

        if len(authors) == 0:
            await ctx.reply(
                "Please make sure you entered a valid user created element and valid users!"
            )
            return
        if len(authors) + len(element.extra_authors) > 10:
            await ctx.respond("An element cannot have more than 10 collaborators")
            return
        poll = server.suggest_add_collaborators(user, element, authors)
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"Suggested to add those users as collaborators to {element.name}",
        )

    @bridge.bridge_command(aliases=["rcol"])
    async def remove_collaborators(
        self,
        ctx: bridge.BridgeContext,
        *,
        element: str,
        collaborator1: User = None,
        collaborator2: User = None,
        collaborator3: User = None,
        collaborator4: User = None,
        collaborator5: User = None,
        collaborator6: User = None,
        collaborator7: User = None,
        collaborator8: User = None,
        collaborator9: User = None,
        collaborator10: User = None,
    ):  # Dude fuck slash commands this is the only way to do this (i think)
        server = InstanceManager.current.get_or_create(
            ctx.guild.id, DiscordGameInstance
        )
        user = server.login_user(ctx.author.id)
        extra_authors = []
        if ctx.is_app:
            element = element.lower()
            element = server.db.elements[element]
            for i in [
                collaborator1,
                collaborator2,
                collaborator3,
                collaborator4,
                collaborator5,
                collaborator6,
                collaborator7,
                collaborator8,
                collaborator9,
                collaborator10,
            ]:
                if i:
                    extra_authors.append(i.id)

        else:
            split_msg = element.split("|")
            if len(split_msg) < 2:
                await ctx.respond("Please separate each parameter with a |")
                return
            element = split_msg[0].lower().strip()
            element = server.db.elements[element]
            for i in (
                split_msg[1]
                .strip()
                .replace(",", " ")
                .replace("|", " ")
                .replace("  ", " ")
                .replace("  ", " ")
                .split(" ")
            ):
                if not i:
                    continue
                id = int(i.replace("<@", "").replace(">", ""))
                try:
                    await self.bot.fetch_user(id)
                except NotFound:
                    await ctx.respond(
                        "Please only enter valid users, using the @<user> syntax separated by spaces"
                    )
                    return
                extra_authors.append(id)
        authors = []
        for i in extra_authors:
            if (
                i in [i.id for i in element.extra_authors]
                and element.author
                and i != element.author.id
                and i not in authors
                and i != self.bot.user.id
            ):
                authors.append(server.login_user(i))

        if len(authors) == 0:
            await ctx.reply(
                "Please make sure you entered a valid user created element and valid users already in the collaboration!"
            )
            return
        poll = server.suggest_remove_collaborators(user, element, authors)
        await self.bot.add_poll(
            server,
            poll,
            ctx,
            f"Suggested to remove those users as collaborators to {element.name}",
        )


def setup(client):
    client.add_cog(Info(client))
