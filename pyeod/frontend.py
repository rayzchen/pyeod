from typing import Optional, Tuple, List, Union, Dict, Type, TypeVar
from pyeod.model import Database, Element, GameInstance, InternalError
from discord import TextChannel


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
        starter_elements: Optional[Tuple[Element, ...]] = None,
        db: Optional[Database] = None,
        vote_req: int = 4,
        poll_limit: int = 21,
        channels: Optional[ChannelList] = None,
    ) -> None:
        super().__init__(starter_elements, db, vote_req, poll_limit)
        if channels is None:
            self.channels = ChannelList()
        else:
            self.channels = channels


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

