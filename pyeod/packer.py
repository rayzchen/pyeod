from pyeod import config
from pyeod.frontend import DiscordGameInstance
from pyeod.model import (
    AddCollabPoll,
    ColorPoll,
    Database,
    Element,
    ElementPoll,
    GameInstance,
    IconPoll,
    ImagePoll,
    MarkPoll,
    DefaultSavableMixinMapping,
    RemoveCollabPoll,
    SavableMixin,
    SavableMixinMapping,
    User,
)
import msgpack
from typing import Dict, List, Type, Union
import os
import copy
import asyncio
import functools
import threading
import multiprocessing

types: List[Type[SavableMixin]] = [
    Element,
    User,
    ElementPoll,
    Database,
    GameInstance,
    DiscordGameInstance,
    MarkPoll,
    ColorPoll,
    AddCollabPoll,
    RemoveCollabPoll,
    ImagePoll,
    IconPoll,
]
type_dict: Dict[str, Type[SavableMixin]] = {t.__name__: t for t in types}


class InstanceLoader:
    def __init__(self) -> None:
        self.users: Dict[Union[int, None], Union[User, int, None]] = {None: None, 0: 0}
        self.elem_id_lookup: Dict[int, Element] = {}


warned_types = []


def convert_to_dict(
    obj: SavableMixin,
    mapping_type: Type[SavableMixinMapping] = DefaultSavableMixinMapping,
) -> dict:
    if type(obj) not in types and type(obj).__name__ not in warned_types:
        warned_types.append(type(obj).__name__)
        print(f"Warning: type {type(obj).__name__} saved but not in type_dict")

    data = mapping_type()
    data[mapping_type.indicator] = type(obj).__name__
    obj.convert_to_dict(data)
    return data.mapping


def convert_from_dict(
    loader: InstanceLoader,
    mapping_type: Type[SavableMixinMapping],
    data: Dict[str, str],
) -> Union[SavableMixin, dict]:
    if mapping_type.indicator not in data:
        return data

    data = mapping_type(data)
    type = type_dict[data.get(mapping_type.indicator)]
    return type.convert_from_dict(loader, data)


def multiprocess_save(instance: GameInstance, filename: str) -> None:
    data = msgpack.dumps(instance, default=convert_to_dict)
    os.makedirs(os.path.join(config.package, "db"), exist_ok=True)
    with open(os.path.join(config.package, "db", filename), "wb+") as f:
        f.write(data)


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
        data = f.read()

    # Assuming the outer dict has <16 elements and the type key is <32 chars
    indicator_check = data[1:33]
    mapping_type = None
    for cls in SavableMixinMapping.subclasses:
        packed_key = msgpack.packb(cls.indicator)
        if indicator_check.startswith(packed_key):
            mapping_type = cls
            break
    if mapping_type is None:
        print(
            "Warning: could not find suitable mapping type to use, defaulting to DefaultSavableMixinMapping"
        )
        mapping_type = DefaultSavableMixinMapping

    loader = InstanceLoader()
    hook = functools.partial(convert_from_dict, loader, mapping_type)
    instance: GameInstance = msgpack.loads(data, strict_map_key=False, object_hook=hook)
    # Free up some unneeded local variables
    del loader, hook, data

    def wrapper(loop):
        task1 = asyncio.run_coroutine_threadsafe(
            instance.db.check_colors(), loop=loop
        )
        task2 = asyncio.run_coroutine_threadsafe(
            instance.db.check_suggested_combos(), loop=loop
        )
        task3 = asyncio.run_coroutine_threadsafe(
            instance.db.calculate_infos(), loop=loop
        )
        task1.result()
        task2.result()
        task3.result()
        print("Finished calculating complexity for", os.path.basename(file))

    loop = asyncio.get_event_loop()
    t = threading.Thread(target=wrapper, args=(loop,), daemon=True)
    t.start()
    return instance


async def test_function():
    from pyeod.model.instance import generate_test_game
    import simplejson

    def pair_hook(d):
        # Restore integer keys
        out = {}
        for k, v in d:
            if isinstance(k, str) and k.isdecimal():
                out[int(k)] = v
            else:
                out[k] = v
        return out

    game = await generate_test_game()

    dump = simplejson.dumps(game, default=convert_to_dict)
    loader = InstanceLoader()
    hook = functools.partial(convert_from_dict, loader, DefaultSavableMixinMapping)
    loaded_game = simplejson.loads(
        dump, object_hook=hook, object_pairs_hook=pair_hook
    )
    dump2 = simplejson.dumps(loaded_game, default=convert_to_dict)
    print(dump)
    print(dump2)


if __name__ == "__main__":
    asyncio.run(test_function())
