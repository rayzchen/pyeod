__all__ = ["SavableMixin"]


from abc import ABCMeta, abstractmethod


class SavableMixin(metaclass=ABCMeta):
    @abstractmethod
    def convert_to_dict(self, data: dict) -> None:
        pass

    @staticmethod
    @abstractmethod
    def convert_from_dict(loader, data: dict) -> "SavableMixin":
        pass
