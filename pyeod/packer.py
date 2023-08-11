from pyeod.model import Element, User, Poll, ElementPoll, Database, GameInstance
from pyeod.frontend import DiscordGameInstance
from pyeod import config
import simplejson
import msgpack
import functools
import os

types = [Element, User, Poll, ElementPoll, Database, GameInstance, DiscordGameInstance]
type_dict = {t.__name__: t for t in types}


class InstanceLoader:
    def __init__(self) -> None:
        self.users = {}
        self.elem_id_lookup = {}


def convert_to_dict(obj: object) -> dict:
    if type(obj) not in types:
        raise TypeError(f"Invalid type: {type(obj).__name__}")

    data = {"__type__": type(obj).__name__}
    obj.convert_to_dict(data)
    return data


def convert_from_dict(loader: InstanceLoader, data: dict) -> object:
    if "__type__" not in data:
        return data

    type = type_dict[data["__type__"]]
    return type.convert_from_dict(loader, data)


def save_instance(instance: GameInstance, filename: str) -> None:
    with open(os.path.join(config.package, "db", filename), "wb+") as f:
        msgpack.dump(instance, f, default=convert_to_dict)


if __name__ == "__main__":
    game = GameInstance()
    user = game.login_user(0)
    combo = ("fire", "fire")
    try:
        game.combine(user, combo)
    except Exception as g:
        if g.type == "Not a combo":
            game.suggest_element(user, combo, "Inferno")
    game.db.polls[0].votes += 4
    game.check_polls()

    dump = simplejson.dumps(game, default=convert_to_dict)
    loader = InstanceLoader()
    loaded_game = simplejson.loads(dump, object_hook=functools.partial(convert_from_dict, loader))
    dump2 = simplejson.dumps(loaded_game, default=convert_to_dict)
    print(dump)
    print(dump2)
