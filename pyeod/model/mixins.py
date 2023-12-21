__all__ = [
    "SavableMixin",
    "SavableMixinMapping",
    "PlainSavableMixinMapping",
]


from abc import ABCMeta, abstractmethod
from typing import TypeVar, Dict, Generic, Optional


class SavableMixin(metaclass=ABCMeta):
    @abstractmethod
    def convert_to_dict(self, data: dict) -> None:
        pass

    @staticmethod
    @abstractmethod
    def convert_from_dict(loader, data: dict) -> "SavableMixin":
        pass


VT = TypeVar("VT")

class SavableMixinMapping(Generic[VT], metaclass=ABCMeta):
    indicator: str

    def __init__(self, mapping: Optional[Dict[str, VT]] = None) -> None:
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


class PlainSavableMixinMapping(SavableMixinMapping[VT]):
    indicator = "__type__"

    def get(self, key: str, default: VT = None) -> VT:
        if key not in self.mapping:
            raise KeyError(key)
        value = self.mapping.get(key, default)
        return value

    def __setitem__(self, key: str, value: VT) -> None:
        self.mapping[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.mapping
