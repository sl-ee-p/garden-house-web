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

## 3D viewer and model

`js/viewer3d.js` and `assets/model/sally.glb` are generated files, committed so the site has no build step.
Rebuild them from `tools/viewer/` (needs Node.js):

```bash
cd tools/viewer && npm install
npm run model   # downloads the original ALL-DIVIDE.glb from techs-gardenhouse.com and bakes assets/model/sally.glb
npm run build   # bundles viewer3d.js with three.js (MIT) into js/viewer3d.js
```

`prep-model.mjs` keeps the original geometry. It groups the parts into named materials (`structure`, `panel`, `glass`, `roof`, `metal`, `lining`) so the configurator can recolour them. It also drops the screws and nuts, merges the meshes and compresses them with meshopt, taking the model from 2 MB to about 270 KB.
