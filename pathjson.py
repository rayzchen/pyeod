from pyeod.frontend import DiscordGameInstance
from pyeod.model import *
from pyeod.packer import save_instance
from datetime import datetime
import json


def get_user(instance, idstr):
    if not idstr:
        return None
    return instance.login_user(int(idstr))


with open("path.json", encoding="utf-8") as f:
    old_data = json.load(f)

data = {}
while len(data) < len(old_data):
    for k in old_data:
        if all(x < 5 or str(x) in data for x in old_data[k]["parents"]):
            data[k] = old_data[k]

instance = DiscordGameInstance()
duplicate_fix = {}

last_id = 4
for id in data:
    print(id)
    last_id = int(id)
    elemdata = data[id]
    user = instance.login_user(int(elemdata.get("creator", "")))
    combo = []
    for elemid in elemdata.get("parents", ""):
        if elemid in duplicate_fix:
            combo.append(instance.db.elem_id_lookup[duplicate_fix[elemid]])
        else:
            combo.append(instance.db.elem_id_lookup[elemid])
    poll = instance.suggest_element(user, combo, elemdata.get("name", ""))
    poll.votes += 3
    poll.id_override = int(id)
    assert instance.check_single_poll(poll)

    if int(id) not in instance.db.elem_id_lookup:
        # Glitched duplicate element
        duplicate_fix[int(id)] = instance.db.elements[
            elemdata.get("name", "").lower()
        ].id
        continue
    element = instance.db.elem_id_lookup[int(id)]
    element.image = elemdata.get("image", "")
    element.color = int(elemdata.get("color", 0))
    comment = elemdata.get("comment", "")
    element.mark = "" if comment == "None" else comment
    timestamp = elemdata.get("createdon", datetime.now().isoformat())
    created = datetime.fromisoformat(timestamp.split(".", 1)[0].split("Z", 1)[0])
    element.created = round(created.timestamp())
    element.marker = get_user(instance, elemdata.get("commenter", ""))
    element.colorer = get_user(instance, elemdata.get("colorer", ""))
    element.imager = get_user(instance, elemdata.get("imager", ""))

save_instance(instance, "1025815020296228934.eod").join()

print(duplicate_fix)
