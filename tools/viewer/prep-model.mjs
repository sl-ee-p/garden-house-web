// Bakes the original techs-gardenhouse.com model (ALL-DIVIDE.glb) into a small web
// model whose materials name the configurable groups: structure, panel, glass,
// roof, metal, lining. Hardware (screws, nuts) is dropped; meshes are merged per
// group and meshopt-compressed.
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
await doc.transform(
  prune(), dedup(), flatten(), join({ keepNamed: false }), weld(),
  prune(), quantize(), meshopt({ encoder: MeshoptEncoder, level: 'medium' }),
);
for (const e of root.listExtensionsUsed()) if (e.extensionName === 'KHR_materials_transmission') e.dispose();
await io.write(out, doc);
console.error('materials', root.listMaterials().map(m => m.getName()), 'meshes', root.listMeshes().length);
