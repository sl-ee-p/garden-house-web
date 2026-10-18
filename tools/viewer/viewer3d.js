/* GardenHouse — interactive 3D preview of Sally for the configurator.
   Source for js/viewer3d.js (bundled with three.js by `npm run build`).
   Loaded on demand by js/main.js only when the visitor picks the 3D view.

   The model is the original techs-gardenhouse.com CAD export, baked by
   prep-model.mjs so that its materials name the configurable groups. */
import {
  WebGLRenderer, Scene, PerspectiveCamera, HemisphereLight, DirectionalLight,
  Box3, Vector3, Mesh, PlaneGeometry, MeshBasicMaterial, CanvasTexture, MathUtils,
} from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';

const START_AZIMUTH = MathUtils.degToRad(35); // same corner as the 2D drawing
const START_ELEVATION = MathUtils.degToRad(14);

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
  grad.addColorStop(0, 'rgba(0,0,0,.28)');
  grad.addColorStop(.6, 'rgba(0,0,0,.12)');
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

/**
 * Mount the viewer in `host` (an empty element). Resolves once the model is
 * on screen. `options.colors` = { structure, panel } as CSS hex strings.
 */
export async function mount(host, { modelUrl, colors, label }) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const renderer = new WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const canvas = renderer.domElement;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', label);
  canvas.style.touchAction = 'none';

  const scene = new Scene();
  scene.add(new HemisphereLight(0xffffff, 0x8a8a80, 2.4));
  const sun = new DirectionalLight(0xffffff, 1.9);
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

  const camera = new PerspectiveCamera(30, 1, 0.05, 60);
  const target = new Vector3(0, size.y * 0.45, 0);
  const startDistance = size.length() * 1.75;
  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(target);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.minDistance = size.length() * 0.9;
  controls.maxDistance = size.length() * 3;
  controls.minPolarAngle = MathUtils.degToRad(15);
  controls.maxPolarAngle = MathUtils.degToRad(88); // never below the ground

  function placeCamera(azimuth, elevation, distance) {
    camera.position.set(
      target.x + distance * Math.cos(elevation) * Math.sin(azimuth),
      target.y + distance * Math.sin(elevation),
      target.z + distance * Math.cos(elevation) * Math.cos(azimuth),
    );
    camera.lookAt(target);
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
    if (controls.update() || dirty) {
      renderer.render(scene, camera);
      dirty = false;
    }
  }

  const api = {
    canvas,
    setColors({ structure, panel }) {
      if (structure && materials.structure) materials.structure.color.set(structure);
      if (panel && materials.panel) materials.panel.color.set(panel);
      requestRender();
    },
    rotate,
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
