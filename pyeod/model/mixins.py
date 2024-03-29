__all__ = [
    "SavableMixin",
    "SavableMixinMapping",
    "PlainSavableMixinMapping",
    "IntKeySavableMixinMapping",
    "CompressedIntKeySavableMixinMapping",
    "DefaultSavableMixinMapping",
]


from abc import ABCMeta, abstractmethod
from typing import Dict, Type, Tuple, Generic, TypeVar, Optional
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

    def set_mro(self, mro: Tuple[Type]):
        pass

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
        "DiscordGameInstance.channels": 4,
        "DiscordGameInstance.poll_msg_lookup": 5,
        "DiscordGameInstance.combo_limit": 6,
        "Element.name": 7,
        "Element.author": 8,
        "Element.created": 9,
        "Element.id": 10,
        "Element.mark": 11,
        "Element.marker": 12,
        "Element.color": 13,
        "Element.colorer": 14,
        "Element.extra_authors": 15,
        "Element.image": 16,
        "Element.imager": 17,
        "Element.icon": 18,
        "Element.iconer": 19,
        "User.id": 20,
        "User.inv": 21,
        "User.active_polls": 22,
        "User.created_combo_count": 23,
        "User.votes_cast_count": 24,
        "User.achievements": 25,
        "User.icon": 26,
        "Database.users": 27,
        "Database.elements": 28,
        "Database.starters": 29,
        "Database.combos": 30,
        "Database.polls": 31,
        "Database.categories": 32,
        "Poll.author": 33,
        "Poll.votes": 34,
        "Poll.creation_time": 35,
        "ElementPoll.combo": 36,
        "ElementPoll.result": 37,
        "ElementPoll.exists": 38,
        "MarkPoll.marked_element": 39,
        "MarkPoll.mark": 40,
        "ColorPoll.colored_element": 41,
        "ColorPoll.color": 42,
        "ImagePoll.imaged_element": 43,
        "ImagePoll.image": 44,
        "IconPoll.iconed_element": 45,
        "IconPoll.icon": 46,
        "AddCollabPoll.element": 47,
        "AddCollabPoll.extra_authors": 48,
        "RemoveCollabPoll.element": 49,
        "RemoveCollabPoll.extra_authors": 50,
        "ElementCategory.name": 51,
        "ElementCategory.elements": 52,
        "AddCategoryPoll.category": 53,
        "AddCategoryPoll.elements": 54,
        "RemoveCategoryPoll.category": 55,
        "RemoveCategoryPoll.elements": 56,
        "GameInstance.polls_rejected": 57,
        "DiscordGameInstance.commands_used": 58,
    }

    def __init__(self, mapping: Optional[Dict[KT, VT]] = None) -> None:
        super(IntKeySavableMixinMapping, self).__init__(mapping)
        self.mro = ()

    def get(self, key: str, default: VT = None) -> VT:
        return super().get(self.encode_key(key), default)

    def __setitem__(self, key: str, value: VT) -> None:
        self.mapping[self.encode_key(key)] = value

    def __contains__(self, key: str) -> bool:
        return self.encode_key(key) in self.mapping

    def set_mro(self, mro: Tuple[Type]):
        self.mro = mro

    def encode_key(self, key: str) -> int:
        if key == self.indicator:
            return self.indicator
        if self.mro:
            for type in self.mro:
                field = type.__name__ + "." + key
                if field in self.KEYS:
                    return self.KEYS[field]
            raise KeyError(self.mapping[self.indicator] + "." + key)
        else:
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


DefaultSavableMixinMapping = IntKeySavableMixinMapping
