from pyeod.model import (
    Element,
    User,
    Poll,
    ElementPoll,
    Database,
    GameInstance,
    MarkPoll,
    AddCollabPoll,
    RemoveCollabPoll,
)
from pyeod.frontend import DiscordGameInstance
from pyeod import config
import msgpack
import functools
import os
import copy
import multiprocessing

types = [
    Element,
    User,
    Poll,
    ElementPoll,
    Database,
    GameInstance,
    DiscordGameInstance,
    MarkPoll,
    AddCollabPoll,
    RemoveCollabPoll,
]
type_dict = {t.__name__: t for t in types}


class InstanceLoader:
    def __init__(self) -> None:
        self.users = {None: None, 0: 0}
        self.elem_id_lookup = {}


warned_types = []


def convert_to_dict(obj: object) -> dict:
    if type(obj) not in types and type(obj).__name__ not in warned_types:
        warned_types.append(type(obj).__name__)
        print(f"Warning: type {type(obj).__name__} saved but not in type_dict")

    data = {"__type__": type(obj).__name__}
    obj.convert_to_dict(data)
    return data


def convert_from_dict(loader: InstanceLoader, data: dict) -> object:
    if "__type__" not in data:
        return data

    type = type_dict[data["__type__"]]
    return type.convert_from_dict(loader, data)


def multiprocess_save(instance: GameInstance, filename: str) -> None:
    with open(os.path.join(config.package, "db", filename), "wb+") as f:
        msgpack.dump(instance, f, default=convert_to_dict)


def save_instance(instance: GameInstance, filename: str) -> multiprocessing.Process:
    instance2 = copy.copy(instance)  # don't deepcopy, no need
    old_db = instance2.db
    instance2.db = Database.__new__(Database)
    instance2.db.elements = old_db.elements
    instance2.db.starters = old_db.starters
    instance2.db.combos = old_db.combos
    instance2.db.users = old_db.users
    instance2.db.polls = old_db.polls
    process = multiprocessing.Process(
        target=multiprocess_save, args=(instance2, filename)
    )
    process.start()
    return process


def load_instance(file: str) -> GameInstance:
    with open(file, "rb") as f:
        loader = InstanceLoader()
        hook = functools.partial(convert_from_dict, loader)
        return msgpack.load(f, strict_map_key=False, object_hook=hook)


if __name__ == "__main__":
    import simplejson

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
    loaded_game = simplejson.loads(
        dump, object_hook=functools.partial(convert_from_dict, loader)
    )
    dump2 = simplejson.dumps(loaded_game, default=convert_to_dict)
    print(dump)
    print(dump2)
