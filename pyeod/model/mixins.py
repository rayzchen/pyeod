__all__ = [
    "SavableMixin",
    "SavableMixinMapping",
    "PlainSavableMixinMapping",
    "IntKeySavableMixinMapping",
    "CompressedIntKeySavableMixinMapping",
    "DefaultSavableMixinMapping",
]


from abc import ABCMeta, abstractmethod
from typing import TypeVar, Dict, Generic, Optional
import gzip


class SavableMixin(metaclass=ABCMeta):
    @abstractmethod
    def convert_to_dict(self, data: dict) -> None:
        pass

    @staticmethod
    @abstractmethod
    def convert_from_dict(loader, data: dict) -> "SavableMixin":
        pass


KT = TypeVar("KT")
VT = TypeVar("VT")


class SavableMixinMapping(Generic[KT, VT], metaclass=ABCMeta):
    indicator: str
    subclasses = []

    def __init_subclass__(cls):
        super().__init_subclass__()
        SavableMixinMapping.subclasses.append(cls)

    def __init__(self, mapping: Optional[Dict[KT, VT]] = None) -> None:
        if mapping is None:
            self.mapping = {}
        else:
            self.mapping = mapping

    @abstractmethod
    def get(self, key: str, default: VT = None) -> VT:
        pass

    @abstractmethod
    def __setitem__(self, key: str, value: VT) -> None:
        pass

    @abstractmethod
    def __contains__(self, key: str) -> bool:
        pass


class PlainSavableMixinMapping(SavableMixinMapping[KT, VT]):
    indicator = "__type__"

    def get(self, key: KT, default: VT = None) -> VT:
        if key not in self.mapping and default == None:
            raise KeyError(key)
        value = self.mapping.get(key, default)
        return value

    def __setitem__(self, key: KT, value: VT) -> None:
        self.mapping[key] = value

    def __contains__(self, key: KT) -> bool:
        return key in self.mapping


class IntKeySavableMixinMapping(PlainSavableMixinMapping[int, VT]):
    indicator = "\x07IT\x07"  # \x07 untypable as elem name

    KEYS = {
        "GameInstance.db": 1,
        "GameInstance.vote_req": 2,
        "GameInstance.poll_limit": 3,
        "Element.name": 4,
        "Element.author": 5,
        "Element.created": 6,
        "Element.id": 7,
        "Element.mark": 8,
        "Element.marker": 9,
        "Element.color": 10,
        "Element.colorer": 11,
        "Element.extra_authors": 12,
        "Element.image": 13,
        "Element.imager": 14,
        "Element.icon": 15,
        "Element.iconer": 16,
        "User.id": 17,
        "User.inv": 18,
        "User.active_polls": 19,
        "Database.users": 20,
        "Database.elements": 21,
        "Database.starters": 22,
        "Database.combos": 23,
        "Database.polls": 24,
        "ElementPoll.author": 25,
        "ElementPoll.votes": 26,
        "ElementPoll.combo": 27,
        "ElementPoll.result": 28,
        "ElementPoll.exists": 29,
        "ElementPoll.creation_time": 30,
        "MarkPoll.author": 31,
        "MarkPoll.votes": 32,
        "MarkPoll.marked_element": 33,
        "MarkPoll.mark": 34,
        "MarkPoll.creation_time": 35,
        "ColorPoll.author": 36,
        "ColorPoll.votes": 37,
        "ColorPoll.colored_element": 38,
        "ColorPoll.color": 39,
        "ColorPoll.creation_time": 40,
        "ImagePoll.author": 41,
        "ImagePoll.votes": 42,
        "ImagePoll.imaged_element": 43,
        "ImagePoll.image": 44,
        "ImagePoll.creation_time": 45,
        "IconPoll.author": 46,
        "IconPoll.votes": 47,
        "IconPoll.iconed_element": 48,
        "IconPoll.icon": 49,
        "IconPoll.creation_time": 50,
        "AddCollabPoll:author": 51,
        "AddCollabPoll:votes": 52,
        "AddCollabPoll:element": 53,
        "AddCollabPoll:extra_authors": 54,
        "AddCollabPoll:creation_time": 55,
        "RemoveCollabPoll:author": 56,
        "RemoveCollabPoll:votes": 57,
        "RemoveCollabPoll:element": 58,
        "RemoveCollabPoll:extra_authors": 59,
        "RemoveCollabPoll:creation_time": 60,
        "DiscordGameInstance.db": 61,
        "DiscordGameInstance.vote_req": 62,
        "DiscordGameInstance.poll_limit": 63,
        "DiscordGameInstance.channels": 64,
        "DiscordGameInstance.poll_msg_lookup": 65,
        "User.created_combo_count": 66,
        "User.votes_cast_count": 67,
    }

    def get(self, key: str, default: VT = None) -> VT:
        return super().get(self.encode_key(key), default)

    def __setitem__(self, key: str, value: VT) -> None:
        self.mapping[self.encode_key(key)] = value

    def __contains__(self, key: str) -> bool:
        return self.encode_key(key) in self.mapping

    def encode_key(self, key: str) -> int:
        if key == self.indicator:
            return self.indicator
        type = self.mapping[self.indicator]
        return self.KEYS[type + "." + key]

class CompressedIntKeySavableMixinMapping(IntKeySavableMixinMapping[VT]):
    indicator = "\x07CIT\x07"  # \x07 untypable as elem name

    def get(self, key: str, default: VT = None) -> VT:
        value = super().get(key, default)
        if isinstance(value, bytes):
            value = gzip.decompress(value).decode("utf-8")
        return value

    def __setitem__(self, key: str, value: VT) -> None:
        if isinstance(value, str) and key != self.indicator:
            value = gzip.compress(value.encode("utf-8"), 9)
        self.mapping[self.encode_key(key)] = value


DefaultSavableMixinMapping = PlainSavableMixinMapping
