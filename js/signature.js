/* Techs Garden House — Signature design only.
   1. Home: the 3D showcase loads the viewer when the section comes near,
      turns slowly (with a pause button), pins labels to the model and stops
      rendering while off screen.
   2. Configurator: switches to the 3D model at the first interaction when
      WebGL2 works.
   3. Home: the page turns from white to black as the 3D model scrolls in.
   Runs after js/main.js (both deferred, in order). */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function webgl2() {
    try {
      return !!(window.WebGL2RenderingContext && document.createElement('canvas').getContext('webgl2'));
    } catch (e) {
      return false;
    }
  }

  function initShowcase() {
    var section = document.querySelector('[data-showcase]');
    if (!section || !('IntersectionObserver' in window) || !('ResizeObserver' in window)) return;
    var host = section.querySelector('[data-showcase-canvas]');
    var poster = section.querySelector('[data-showcase-poster]');
    var status = section.querySelector('[data-showcase-status]');
    var tools = section.querySelector('[data-showcase-tools]');
    var pause = section.querySelector('[data-showcase-pause]');
    var pauseLabel = pause.querySelector('.visually-hidden');
    var reset = section.querySelector('[data-showcase-reset]');
    var labels = {};
    section.querySelectorAll('[data-anchor]').forEach(function (el) { labels[el.dataset.anchor] = el; });
    var viewer = null;
    var onScreen = false;

    function fail() {
      section.classList.add('is-failed');
      poster.textContent = 'Il modello 3D non è disponibile su questo dispositivo. Lo trovi anche nel configuratore.';
      status.textContent = '';
    }

    function setPaused(paused) {
      pause.setAttribute('aria-pressed', String(paused));
      pauseLabel.textContent = paused ? 'Riprendi la rotazione automatica' : 'Ferma la rotazione automatica';
      if (viewer) viewer.setTurntable(!paused);
    }

    function place(points) {
      points.forEach(function (p) {
        var el = labels[p.id];
        if (!el) return;
        var x = Math.round(p.x);
        var y = Math.round(p.y);
        // The dot (9px) sits on the anchor: at the start, end or top of the label.
        el.style.transform = el.dataset.side === 'left'
          ? 'translate(' + (x + 5) + 'px,' + y + 'px) translate(-100%, -50%)'
          : el.dataset.side === 'below'
            ? 'translate(' + (x - 5) + 'px,' + (y - 5) + 'px)'
            : 'translate(' + (x - 5) + 'px,' + y + 'px) translateY(-50%)';
        el.classList.toggle('is-visible', p.visible);
      });
    }

    function load() {
      if (!webgl2()) { fail(); return; }
      poster.textContent = 'Caricamento del modello 3D…';
      import('./viewer3d.js').then(function (mod) {
        return mod.mount(host, {
          modelUrl: 'assets/model/sally.glb',
          colors: { structure: '#F5F5F5', panel: '#e9e4db' },
          label: 'Modello 3D, telaio e pannelli bianchi, con porta vetrata e punto luce verticale.',
          turntable: !reduceMotion.matches,
          onRender: place
        });
      }).then(function (v) {
        viewer = v;
        section.classList.add('is-live');
        tools.hidden = false;
        setPaused(reduceMotion.matches);
        // Grabbing the model stops the turntable inside the viewer: reflect it.
        viewer.canvas.addEventListener('pointerdown', function () { setPaused(true); });
        if (!onScreen) viewer.stop();
      }).catch(fail);
    }

    pause.addEventListener('click', function () {
      setPaused(pause.getAttribute('aria-pressed') !== 'true');
    });
    reset.addEventListener('click', function () { if (viewer) viewer.reset(); });

    var started = false;
    new IntersectionObserver(function (entries) {
      onScreen = entries[0].isIntersecting;
      if (onScreen && !started) { started = true; load(); }
      if (viewer) { if (onScreen) viewer.start(); else viewer.stop(); }
    }, { rootMargin: '300px 0px' }).observe(section);
  }

  // Switch on the visitor's first sign of life (pointer, touch, scroll or key)
  // so the 3D download and WebGL setup never compete with the first paint.
  function initConfigurator3d() {
    var group = document.querySelector('[data-view-switch]');
    var button = group && group.querySelector('[data-view="3d"]');
    if (!button || !webgl2()) return;
    var events = ['pointermove', 'pointerdown', 'touchstart', 'wheel', 'scroll', 'keydown'];
    var chose = false;
    group.addEventListener('click', function () { chose = true; });
    function go() {
      events.forEach(function (e) { window.removeEventListener(e, go, true); });
      if (!chose && button.getAttribute('aria-pressed') !== 'true') button.click();
    }
    events.forEach(function (e) { window.addEventListener(e, go, { capture: true, passive: true }); });
  }

  // --t (0 white, 1 black) follows the scroll position, so the transition
  // runs the same way up and down. The target ramps while the top of the 3D
  // section moves from the bottom of the viewport to 20% from the top, eased
  // at both ends (smoothstep); the shown value glides towards it (time-based,
  // ~0.3 s whatever the frame rate) so fast flicks and jumpy wheels still fade
  // instead of stepping.
  function initThemeScroll() {
    var section = document.querySelector('[data-theme-turn]');
    if (!section) return;
    var root = document.documentElement;
    var glide = !reduceMotion.matches;
    var shown = -1;
    var running = false;
    var last = 0;

    function target() {
      var vh = window.innerHeight;
      var x = (vh - section.getBoundingClientRect().top) / (vh * 0.8);
      x = Math.min(1, Math.max(0, x));
      return x * x * (3 - 2 * x);
    }
    function set(t) {
      shown = t;
      root.style.setProperty('--t', t.toFixed(4));
    }
    function step(now) {
      var goal = target();
      var dt = Math.min(now - last, 250);
      last = now;
      var next = glide && shown >= 0 ? shown + (goal - shown) * (1 - Math.exp(-dt / 90)) : goal;
      if (Math.abs(goal - next) < 0.002) next = goal;
      if (next !== shown) set(next);
      running = next !== goal;
      if (running) window.requestAnimationFrame(step);
    }
    function queue() {
      if (!running) { running = true; last = performance.now(); window.requestAnimationFrame(step); }
    }
    set(target());
    root.classList.add('theme-scroll');
    window.addEventListener('scroll', queue, { passive: true });
    window.addEventListener('resize', queue);
  }

  initThemeScroll();
  initShowcase();
  initConfigurator3d();
})();
