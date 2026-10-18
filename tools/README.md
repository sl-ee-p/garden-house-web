# QA tools (optional)

These scripts are **not needed to view the site**. They automate the checks used during development.

```bash
python3 -m venv .venv && .venv/bin/pip install playwright
.venv/bin/python -m playwright install chromium

.venv/bin/python tools/audit.py path/to/axe.min.js   # overflow, console, links, axe, interactions
.venv/bin/python tools/shoot.py docs/screenshots/<branch>   # desktop + mobile full-page shots
LIGHTHOUSE=lighthouse CHROME_PATH=/path/to/chrome .venv/bin/python tools/lighthouse.py
```

`axe.min.js` comes from the [axe-core](https://github.com/dequelabs/axe-core) package (MPL-2.0).
