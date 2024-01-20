__all__ = ["ChannelList", "DiscordGameInstance", "InstanceManager"]

from pyeod import config
from pyeod.errors import InternalError
from pyeod.model import (
    ColorPoll,
    Database,
    Element,
    GameInstance,
    IconPoll,
    ImagePoll,
    Poll,
)
from discord import Embed
from typing import Dict, List, Tuple, Union, TypeVar, Optional
from contextlib import contextmanager


class ChannelList:
    def __init__(
        self,
        news_channel: Optional[int] = None,
        voting_channel: Optional[int] = None,
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
        self.upvoters = {id: set() for id in self.poll_msg_lookup}
        self.downvoters = {id: set() for id in self.poll_msg_lookup}
        self.processing_polls = set()

    def convert_to_dict(self, data: dict) -> None:
        super(DiscordGameInstance, self).convert_to_dict(data)
        data["channels"] = {
            "news": self.channels.news_channel,
            "voting": self.channels.voting_channel,
            "play": self.channels.play_channels,
        }
        lookup = {}
        for id, poll in self.poll_msg_lookup.items():
            # In case poll is deleted while saving, shouldn't cause too much issue
            # TODO: asyncio lock for accessing db?
            if poll in self.db.polls:
                lookup[id] = self.db.polls.index(poll)
        data["poll_msg_lookup"] = lookup

    @staticmethod
    def convert_from_dict(loader, data: dict) -> "DiscordGameInstance":
        db = data.get("db")
        lookup = data.get("poll_msg_lookup", {})
        if len(lookup) == len(db.polls):
            for id, poll_idx in lookup.items():
                lookup[id] = db.polls[poll_idx]
        else:
            lookup = {}
            db.polls.clear()
        if "channels" in data:
            channels = data.get("channels")
            channel_list = ChannelList(
                channels.get("news"),
                channels.get("voting"),
                channels.get("play"),
            )
        else:
            channel_list = ChannelList()
        return DiscordGameInstance(
            db,
            data.get("vote_req", 4),
            data.get("poll_limit", 20),
            channel_list,
            lookup,
        )

    async def convert_poll_to_embed(self, poll: Poll):
        embed = Embed(
            title=poll.get_title(),
            description=poll.get_description(),
            color=config.EMBED_COLOR,
        )
        if isinstance(poll, ImagePoll):
            embed.set_image(url=poll.image)
        if isinstance(poll, IconPoll):
            embed.set_image(url=poll.icon)
        if isinstance(poll, ColorPoll):
            embed.color = poll.color
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
        self.creation_lock = False

    @property
    def prevent_creation(self):
        @contextmanager
        def decorator():
            original = self.creation_lock
            self.creation_lock = True
            try:
                yield self
            finally:
                self.creation_lock = original

        return decorator

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

    def remove_instance(self, id: int) -> None:
        if id not in self.instances:
            raise InternalError(
                "Instance not found", "The requested GameInstance not found"
            )
        self.instances.pop(id)

    def get_or_create(self, id: int) -> DiscordGameInstance:
        if not self.has_instance(id):
            if self.creation_lock:
                raise InternalError(
                    "Creation lock",
                    "Instance loading ongoing, cannot create new instance",
                )
            instance = DiscordGameInstance()
            self.add_instance(id, instance)
        else:
            instance = self.get_instance(id)
        return instance
