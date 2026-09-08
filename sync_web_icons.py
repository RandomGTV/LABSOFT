"""Refresh the offline web icon catalog after editing assets/icons.json."""
import json
import re
from pathlib import Path
root = Path(__file__).resolve().parent
catalog = json.loads((root / "assets/icons.json").read_text(encoding="utf-8"))
for name in ("index.html", "web/index.html"):
    path = root / name
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(r"const ICON_PATHS = .*?;\n", lambda _: "const ICON_PATHS = " + json.dumps(catalog) + ";\n", text, count=1)
    if count != 1:
        raise RuntimeError(f"Icon catalog missing in {name}")
    path.write_text(text, encoding="utf-8")
