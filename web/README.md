# The web application

`index.html` in this folder is the LabSoft web app, and this folder is the
whole of what gets published. It is one self-contained file: no stylesheet,
no script, no image beside it. The only thing it fetches is the typeface,
from Google Fonts.

Everything else in the repository — the desktop program, its tests, the
laboratory's data, the design canvas — stays outside this folder and is never
deployed.

## Vercel

Two ways, and both are already configured:

* **Root Directory set to `web`** (Settings → General on the Vercel project).
  Vercel then sees only this folder, so it cannot mistake the desktop
  program's `main.py` for a web server. `web/vercel.json` applies.
* **Root Directory left at the repository root.** The `vercel.json` at the
  root builds `web/index.html` and serves nothing else.

Both use a `builds` array rather than the newer settings, because that is
what turns Vercel's automatic framework detection off. Detection is the thing
that kept finding `main.py` and trying to run the desktop app as a server.

## Editing

Edit this file and no other. There were six copies of this page in the
repository and they had already drifted apart -- git was serving a build
older than the one on the laboratory PC, with no visible difference in size.
This is the copy.
