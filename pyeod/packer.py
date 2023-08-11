from pyeod.model import Element, User, Poll, ElementPoll, Database, GameInstance
from pyeod.frontend import DiscordGameInstance
import simplejson

types = [Element, User, Poll, ElementPoll, Database, GameInstance, DiscordGameInstance]
type_dict = {t.__name__ for t in types}


def convert_to_dict(obj: object) -> dict:
    if type(obj) not in types:
        raise TypeError(f"Invalid type: {type(obj).__name__}")

    data = {"__type__": type(obj).__name__}
    obj.convert_to_dict(data)
    return data


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
    print(simplejson.dumps(game, default=convert_to_dict))
