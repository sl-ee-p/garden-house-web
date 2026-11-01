/* GardenHouse — interactive 3D preview of Sally for the configurator.
   Source for js/viewer3d.js (bundled with three.js by `npm run build`).
   Loaded on demand by js/main.js only when the visitor picks the 3D view.

   The model is the original techs-gardenhouse.com CAD export, baked by
   prep-model.mjs so that its materials name the configurable groups.
   Signature branch: studio environment lighting, real glass in the window and
   door, the brochure panel finishes as textures, an optional slow turntable
   and screen positions for HTML labels. */
import {
  WebGLRenderer, Scene, PerspectiveCamera, HemisphereLight, DirectionalLight,
  Box3, Vector3, Mesh, PlaneGeometry, MeshBasicMaterial, CanvasTexture, MathUtils,
  MeshPhysicalMaterial, PMREMGenerator, ACESFilmicToneMapping, SRGBColorSpace, DoubleSide,
  BufferAttribute, TextureLoader, MirroredRepeatWrapping,
} from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';

const START_AZIMUTH = MathUtils.degToRad(35); // same corner as the 2D drawing
const START_ELEVATION = MathUtils.degToRad(14);

// Label anchors in the original model's coordinates (metres): a point on the
// surface and the outward normal, so a label hides when its face turns away.
const ANCHORS = {
  finestra: { at: [-0.678, 1.25, 0.905], normal: [0, 0, 1] },
  porta: { at: [0.34, 1.6, 0.905], normal: [0, 0, 1] },
  pannelli: { at: [1.31, 1.1, 0.2], normal: [1, 0, 0] },
};

// Real size (metres) of one panel texture: a plain half-board face, between a
// joint and the board's central groove, which repeat every 25 cm up the wall.
const TEXTURE_WIDTH = 0.6;
const TEXTURE_HEIGHT = 0.25;

// The CAD export has no UVs: project each panel triangle on the wall it faces
// (box mapping in world space), so the finish runs across the boards at scale.
// Each 25 cm row starts at its own point of the texture, like boards cut from
// different planks, so knots and grain don't line up row after row.
function addPanelUVs(mesh) {
  mesh.updateWorldMatrix(true, false);
  const geo = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry;
  mesh.geometry = geo;
  const pos = geo.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  const a = new Vector3(); const b = new Vector3(); const c = new Vector3();
  const n = new Vector3(); const e = new Vector3();
  for (let i = 0; i < pos.count; i += 3) {
    a.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
    b.fromBufferAttribute(pos, i + 1).applyMatrix4(mesh.matrixWorld);
    c.fromBufferAttribute(pos, i + 2).applyMatrix4(mesh.matrixWorld);
    n.subVectors(b, a).cross(e.subVectors(c, a));
    const ax = Math.abs(n.x); const ay = Math.abs(n.y); const az = Math.abs(n.z);
    const row = Math.floor((a.y + b.y + c.y) / 3 / TEXTURE_HEIGHT);
    const wall = ax > az ? Math.sign(n.x) + 3 : Math.sign(n.z);
    const shift = (Math.sin(row * 12.9898 + wall * 78.233) * 43758.5453) % 1; // stable pseudo-random
    [a, b, c].forEach((p, k) => {
      let u; let v;
      if (ay > ax && ay > az) { u = p.x; v = p.z; } else if (ax > az) { u = p.z; v = p.y; } else { u = p.x; v = p.y; }
      uv[(i + k) * 2] = u / TEXTURE_WIDTH + shift * 4;
      uv[(i + k) * 2 + 1] = v / TEXTURE_HEIGHT;
    });
  }
  geo.setAttribute('uv', new BufferAttribute(uv, 2));
}

export function supported() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGL2RenderingContext && c.getContext('webgl2'));
  } catch (e) {
    return false;
  }
}

// A soft round contact shadow under the house (no real-time shadows needed).
function groundShadow(width, depth) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(0,0,0,.34)');
  grad.addColorStop(.55, 'rgba(0,0,0,.12)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const mesh = new Mesh(
    new PlaneGeometry(width * 1.6, depth * 1.9),
    new MeshBasicMaterial({ map: new CanvasTexture(c), transparent: true, depthWrite: false }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = 0.002;
  return mesh;
}

// Two soft diagonal light streaks: a flat pane reflects too little of the
// studio to read as glass on its own.
function glassSheen() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 256, 256);
  grad.addColorStop(0, 'rgba(255,255,255,.10)');
  grad.addColorStop(.32, 'rgba(255,255,255,0)');
  grad.addColorStop(.40, 'rgba(255,255,255,.22)');
  grad.addColorStop(.47, 'rgba(255,255,255,0)');
  grad.addColorStop(.55, 'rgba(255,255,255,.09)');
  grad.addColorStop(.60, 'rgba(255,255,255,0)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = '#000';
  g.fillRect(0, 0, 256, 256);
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  return tex;
}

/**
 * Mount the viewer in `host` (an empty element). Resolves once the model is
 * on screen. `options.colors` = { structure, panel } as CSS hex strings.
 * `options.turntable` starts a slow rotation that stops at the first touch.
 * `options.onRender(points)` receives the screen position of each anchor
 * ({ id, x, y, visible }, in CSS pixels of the canvas) after every frame.
 */
export async function mount(host, { modelUrl, colors, label, turntable = false, onRender = null }) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const renderer = new WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.outputColorSpace = SRGBColorSpace;
  const canvas = renderer.domElement;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', label);
  canvas.style.touchAction = 'none';

  const scene = new Scene();
  // Soft studio reflections for the glass and the powder-coated frame.
  const pmrem = new PMREMGenerator(renderer);
  const studio = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  scene.environment = studio;
  scene.environmentIntensity = 0.45;
  scene.add(new HemisphereLight(0xffffff, 0x7a7a70, 1.4));
  const sun = new DirectionalLight(0xfff6e8, 2.3);
  sun.position.set(4, 6, 5);
  scene.add(sun);

  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(modelUrl);
  const model = gltf.scene;
  const box = new Box3().setFromObject(model);
  const size = box.getSize(new Vector3());
  const center = box.getCenter(new Vector3());
  model.position.set(-center.x, -box.min.y, -center.z); // stand on the ground, centred
  scene.add(model, groundShadow(size.x, size.z));

  const materials = {};
  model.traverse((o) => { if (o.isMesh) materials[o.material.name] = o.material; });
  if (materials.structure) { materials.structure.roughness = 0.42; materials.structure.metalness = 0.15; }
  if (materials.panel) {
    materials.panel.roughness = 0.55;
    model.traverse((o) => { if (o.isMesh && o.material === materials.panel) addPanelUVs(o); });
  }
  if (materials.glass) {
    // Dark, reflective glazing like the brochure photos.
    const glass = new MeshPhysicalMaterial({
      name: 'glass', color: 0x0a1312, metalness: 0, roughness: 0.02,
      transparent: true, opacity: 0.86, clearcoat: 1, clearcoatRoughness: 0.02,
      envMap: studio, envMapIntensity: 1.25, side: DoubleSide, depthWrite: false,
    });
    glass.emissive.set(0xffffff);
    glass.emissiveMap = glassSheen();
    glass.emissiveIntensity = 0.8;
    model.traverse((o) => { if (o.isMesh && o.material === materials.glass) o.material = glass; });
    materials.glass.dispose();
    materials.glass = glass;
  }

  const anchors = Object.entries(ANCHORS).map(([id, a]) => ({
    id,
    at: new Vector3(...a.at).add(model.position),
    normal: new Vector3(...a.normal),
  }));
  const projected = new Vector3();
  const toCamera = new Vector3();
  function reportAnchors() {
    if (!onRender) return;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    onRender(anchors.map((a) => {
      projected.copy(a.at).project(camera);
      toCamera.copy(camera.position).sub(a.at).normalize();
      return {
        id: a.id,
        x: (projected.x + 1) / 2 * w,
        y: (1 - projected.y) / 2 * h,
        visible: toCamera.dot(a.normal) > 0.25,
      };
    }));
  }

  const camera = new PerspectiveCamera(30, 1, 0.05, 60);
  const target = new Vector3(0, size.y * 0.45, 0);
  const startDistance = size.length() * 2.05;
  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.minDistance = size.length() * 0.9;
  controls.maxDistance = size.length() * 3;
  controls.maxPolarAngle = MathUtils.degToRad(88); // never below the ground
  // Never above the roof: the camera stays under the roof plane at every zoom
  // (so the roof itself is never visible). Horizontal rotation stays free.
  const maxRise = size.y * 0.97 - target.y;
  function limitElevation() {
    const dist = camera.position.distanceTo(controls.target);
    controls.minPolarAngle = Math.acos(Math.min(1, maxRise / dist));
  }
  controls.autoRotateSpeed = 0.55;
  const setTurntable = (on) => { controls.autoRotate = on && !reduceMotion.matches; };
  setTurntable(turntable);
  controls.addEventListener('start', () => setTurntable(false));

  function placeCamera(azimuth, elevation, distance) {
    camera.position.set(
      target.x + distance * Math.cos(elevation) * Math.sin(azimuth),
      target.y + distance * Math.sin(elevation),
      target.z + distance * Math.cos(elevation) * Math.cos(azimuth),
    );
    camera.lookAt(target);
    limitElevation();
    controls.update();
  }
  placeCamera(START_AZIMUTH, START_ELEVATION, startDistance);

  let dirty = true;
  const requestRender = () => { dirty = true; };
  controls.addEventListener('change', requestRender);

  function resize() {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    requestRender();
  }
  const ro = new ResizeObserver(resize);
  ro.observe(host);

  // Animated azimuth step for the rotate buttons (keyboard-friendly).
  let spin = null;
  function rotate(direction) {
    const step = direction * MathUtils.degToRad(45);
    const from = controls.getAzimuthalAngle();
    const polar = controls.getPolarAngle();
    const dist = camera.position.distanceTo(controls.target);
    if (reduceMotion.matches) {
      placeCamera(from + step, Math.PI / 2 - polar, dist);
      requestRender();
      return;
    }
    spin = { from, to: from + step, polar, dist, t0: performance.now() };
  }

  function frame(now) {
    if (spin) {
      const t = Math.min(1, (now - spin.t0) / 450);
      const e = 1 - Math.pow(1 - t, 3);
      placeCamera(spin.from + (spin.to - spin.from) * e, Math.PI / 2 - spin.polar, spin.dist);
      if (t === 1) spin = null;
      dirty = true;
    }
    limitElevation();
    if (controls.update() || dirty) {
      renderer.render(scene, camera);
      reportAnchors();
      dirty = false;
    }
  }

  // Panel finishes: photo textures from the brochure, loaded once each.
  const loader = new TextureLoader();
  const textures = {};
  let wantedTexture = '';
  function loadTexture(url) {
    if (!textures[url]) {
      textures[url] = loader.loadAsync(url).then((tex) => {
        tex.colorSpace = SRGBColorSpace;
        tex.wrapS = tex.wrapT = MirroredRepeatWrapping;
        tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
        return tex;
      });
    }
    return textures[url];
  }
  function setPanelTexture(url, color) {
    const mat = materials.panel;
    wantedTexture = url || '';
    if (!url) {
      if (mat.map) { mat.map = null; mat.needsUpdate = true; }
      mat.color.set(color);
      return;
    }
    // Keep the flat colour until the texture arrives, so the switch never flashes white.
    if (!mat.map) mat.color.set(color);
    loadTexture(url).then((tex) => {
      if (wantedTexture !== url) return;
      if (!mat.map) mat.needsUpdate = true;
      mat.map = tex;
      mat.color.set(0xffffff);
      requestRender();
    }).catch(() => { if (wantedTexture === url) { mat.map = null; mat.needsUpdate = true; mat.color.set(color); requestRender(); } });
  }

  const api = {
    canvas,
    camera,
    roofY: size.y,
    // `panelTexture` (optional) is the URL of the finish's texture; `panel` stays
    // the flat fallback colour while it loads or if it fails.
    setColors({ structure, panel, panelTexture }) {
      if (structure && materials.structure) materials.structure.color.set(structure);
      if (panel && materials.panel) setPanelTexture(panelTexture, panel);
      requestRender();
    },
    rotate,
    setTurntable,
    reset() {
      spin = null;
      placeCamera(START_AZIMUTH, START_ELEVATION, startDistance);
      requestRender();
    },
    start() { resize(); renderer.setAnimationLoop(frame); },
    stop() { renderer.setAnimationLoop(null); },
  };

  api.setColors(colors);
  host.appendChild(canvas);
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.display = 'block';
  api.start();
  return api;
}
