"""Per-operator recovery snapshot, written atomically beside the local database."""
from __future__ import annotations
import hashlib
import json
import os
from .. import config
from . import auth


def path():
    user = auth.current()
    key = str(user.id or user.username) if user else "single-operator"
    token = hashlib.sha256(key.encode()).hexdigest()[:20]
    return config.data_dir() / ("draft-" + token + ".json")


def read():
    target = path()
    if not target.exists():
        return None
    value = json.loads(target.read_text(encoding="utf-8"))
    if value.get("version") != 1 or not isinstance(value.get("fields"), dict):
        raise ValueError("The recovery file is not a supported draft")
    return value


def write(value):
    target = path()
    pending = target.with_suffix(".tmp")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, target)
