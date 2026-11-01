// Bakes the original techs-gardenhouse.com model (ALL-DIVIDE.glb) into a small web
// model whose materials name the configurable groups: structure, panel, glass,
// roof, metal, lining. Hardware (screws, nuts) is dropped; meshes are merged per
// group and meshopt-compressed.
// Signature branch: the CAD export has no glazing (its only glass is a stray
// sliver on the back wall), so the sliver is dropped and real panes are added
// in the window and in the top half of the door.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, flatten, join, weld, prune, quantize, meshopt } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';

const [src, out] = process.argv.slice(2);
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(src);
const root = doc.getRoot();

const mats = {};
const mk = (name, rgb, rough = .7, metal = 0) => {
  mats[name] = doc.createMaterial(name).setBaseColorFactor([...rgb, 1]).setRoughnessFactor(rough).setMetallicFactor(metal);
};
mk('structure', [.03, .08, .08]); mk('panel', [.91, .91, .91]); mk('glass', [.55, .7, .78], .1);
mk('roof', [.35, .36, .37], .5, .3); mk('metal', [.6, .6, .62], .4, .6); mk('lining', [.82, .82, .8]);
mats.glass.setAlphaMode('BLEND').setBaseColorFactor([.42, .6, .7, .55]);

// Openings measured on ALL-DIVIDE.glb (metres, world space). Window: inside the
// CS-PUNTO-LUCE frame. Door: between the CS-S-PORTA jambs and header, above the
// two lower leaf panels (CS-P-006/007). Each pane runs 1 cm into the frame so no
// gap shows at the edges.
const PANES = [
  { name: 'pane-window', min: [-0.753, 0.478, 0.868], max: [-0.602, 1.967, 0.874] },
  { name: 'pane-door', min: [-0.014, 1.035, 0.876], max: [0.693, 1.905, 0.882] },
];

function box(name, [x0, y0, z0], [x1, y1, z1]) {
  const faces = [ // normal, then four corners counter-clockwise seen from outside
    [[1, 0, 0], [[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]]],
    [[-1, 0, 0], [[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]]],
    [[0, 1, 0], [[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]]],
    [[0, -1, 0], [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]]],
    [[0, 0, 1], [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]],
    [[0, 0, -1], [[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]]],
  ];
  const pos = [], nor = [], uv = [], idx = [];
  faces.forEach(([n, quad], f) => {
    for (const v of quad) { pos.push(...v); nor.push(...n); }
    uv.push(0, 1, 1, 1, 1, 0, 0, 0); // for the viewer's glass sheen
    idx.push(f * 4, f * 4 + 1, f * 4 + 2, f * 4, f * 4 + 2, f * 4 + 3);
  });
  const buffer = root.listBuffers()[0];
  const acc = (type, arr) => doc.createAccessor().setType(type).setArray(arr).setBuffer(buffer);
  const prim = doc.createPrimitive()
    .setAttribute('POSITION', acc('VEC3', new Float32Array(pos)))
    .setAttribute('NORMAL', acc('VEC3', new Float32Array(nor)))
    .setAttribute('TEXCOORD_0', acc('VEC2', new Float32Array(uv)))
    .setIndices(acc('SCALAR', new Uint16Array(idx)))
    .setMaterial(mats.glass);
  return doc.createNode(name).setMesh(doc.createMesh(name).addPrimitive(prim));
}

const parentOf = new Map();
for (const n of root.listNodes()) for (const c of n.listChildren()) parentOf.set(c, n);
function group(node, prim) {
  if (prim.getMaterial()?.getName() === 'ClearYellow') return 'glass';
  for (let n = node; n; n = parentOf.get(n)) {
    const name = n.getName();
    if (/^CS-P-/.test(name)) return 'panel';
    if (/^(CS-S|CS-SKELETON|CS-TRAVERSA|CS-PUNTO-LUCE|CS-TAPPO-TETTO)/.test(name)) return 'structure';
    if (/^GLAMET/.test(name)) return 'roof';
    if (/^UT06/.test(name)) return 'lining';
  }
  return 'metal';
}
const count = {};
const assigned = new Map(); // primitive -> group, to catch meshes shared across groups
for (const n of root.listNodes()) {
  let mesh = n.getMesh(); if (!mesh) continue;
  const groups = mesh.listPrimitives().map(p => group(n, p));
  if (mesh.listPrimitives().some((p, i) => assigned.has(p) && assigned.get(p) !== groups[i])) {
    mesh = mesh.clone(); n.setMesh(mesh);
  }
  mesh.listPrimitives().forEach((p, i) => {
    if (groups[i] === 'glass') { p.dispose(); return; } // the stray sliver
    count[groups[i]] = (count[groups[i]] || 0) + 1;
    assigned.set(p, groups[i]);
    p.setMaterial(mats[groups[i]]);
  });
}
console.error('primitives per group', count);
// Hardware (screws, nuts, washers) is invisible at viewer scale: drop it.
for (const n of root.listNodes()) {
  if (/^(ROPLAM|VINOX|DINOX|PINOX|DZNC|VZNC|IZNC)/.test(n.getName())) n.dispose();
}
for (const t of root.listTextures()) t.dispose();
// Only the panes keep UVs (for the viewer's glass sheen); prune() would drop
// them since no texture uses them, so strip the others here and keep attributes.
for (const mesh of root.listMeshes()) for (const p of mesh.listPrimitives()) {
  for (const s of p.listSemantics()) if (s !== 'POSITION' && s !== 'NORMAL') p.setAttribute(s, null);
}
const scene = root.listScenes()[0];
for (const p of PANES) scene.addChild(box(p.name, p.min, p.max));
await doc.transform(
  prune({ keepAttributes: true }), dedup(), flatten(), join({ keepNamed: false }), weld(),
  prune({ keepAttributes: true }), quantize(), meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
);
for (const e of root.listExtensionsUsed()) if (e.extensionName === 'KHR_materials_transmission') e.dispose();
await io.write(out, doc);
console.error('materials', root.listMaterials().map(m => m.getName()), 'meshes', root.listMeshes().length);
