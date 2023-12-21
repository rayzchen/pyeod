__all__ = ["ModelBaseError", "InternalError", "GameError"]


class ModelBaseError(Exception):
    def __init__(
        self, type: str, message: str = "No Message Provided", meta: dict = None
    ) -> None:
        self.type = type
        self.message = message
        # Used to transfer useful error info
        self.meta = meta if meta is not None else {}


class InternalError(ModelBaseError):
    pass


class GameError(ModelBaseError):
    pass
