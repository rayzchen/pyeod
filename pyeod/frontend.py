from typing import Optional, Tuple, List
from pyeod.model import Database, Element, GameInstance

class ChannelList:
    def __init__(
        self,
        news_channel: int = 0,
        voting_channel: int = 0,
        play_channels: Optional[List[int]] = None
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
        channels: Optional[ChannelList] = None
    ) -> None:
        super().__init__(starter_elements, db, vote_req, poll_limit)
        if channels is None:
            self.channels = ChannelList()
        else:
            self.channels = channels
