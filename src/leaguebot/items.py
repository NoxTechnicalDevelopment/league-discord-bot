# Item ID -> name lookup, sourced from Data Dragon's item.json.
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

with open(DATA_DIR / "items.json") as f:
    _ITEMS = json.load(f)["items"]


def item_name(item_id: int) -> str | None:
    # Returns the item's name, or None if the slot is empty (id 0) or unknown.
    if not item_id:
        return None
    return _ITEMS.get(str(item_id))