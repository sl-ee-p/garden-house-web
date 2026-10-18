/* Techs Garden House — Signature design only.
   1. Home: the 3D showcase loads the viewer when the section comes near,
      turns slowly (with a pause button), pins labels to the model and stops
      rendering while off screen.
   2. Configurator: switches to the 3D model at the first interaction when
      WebGL2 works.
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
          label: 'Modello 3D di Sally, telaio e pannelli bianchi, con porta vetrata e finestra verticale. Trascinalo per ruotarlo.',
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

  initShowcase();
  initConfigurator3d();
})();
