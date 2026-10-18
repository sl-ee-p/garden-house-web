/* GardenHouse — shared behaviour. No dependencies; every feature is optional
   and only runs when its markup is on the page. */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- Mobile navigation ---------- */
  function initNav() {
    var header = document.querySelector('[data-header]');
    var toggle = document.querySelector('[data-nav-toggle]');
    var nav = document.querySelector('[data-nav]');
    if (!header || !toggle || !nav) return;

    var desktop = window.matchMedia('(min-width: 48em)');

    function setOpen(open) {
      toggle.setAttribute('aria-expanded', String(open));
      header.classList.toggle('is-open', open);
      root.classList.toggle('nav-open', open);
    }

    toggle.addEventListener('click', function () {
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && header.classList.contains('is-open')) {
        setOpen(false);
        toggle.focus();
      }
    });

    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    desktop.addEventListener('change', function (e) {
      if (e.matches) setOpen(false);
    });
  }

  /* ---------- Header scroll state ----------
     Sets data-scrolled ("true"/"false") and data-scroll-dir ("up"/"down")
     on the header so designs can react in CSS. */
  function initHeaderScroll() {
    var header = document.querySelector('[data-header]');
    if (!header) return;
    var lastY = window.scrollY;
    var ticking = false;

    function update() {
      var y = window.scrollY;
      header.dataset.scrolled = String(y > 8);
      if (Math.abs(y - lastY) > 4) {
        header.dataset.scrollDir = y > lastY && y > 120 ? 'down' : 'up';
        lastY = y;
      }
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });
    update();
  }

  /* ---------- Reveal on scroll ----------
     Elements with [data-reveal] get .is-visible when they enter the viewport.
     The html.reveal-ready class is only set once this works, so content is
     never hidden if JS fails or motion is reduced. */
  function initReveal() {
    var items = document.querySelectorAll('[data-reveal]');
    if (!items.length || reduceMotion.matches || !('IntersectionObserver' in window)) return;

    root.classList.add('reveal-ready');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });

    items.forEach(function (el, i) {
      el.style.setProperty('--reveal-index', String(i % 4));
      io.observe(el);
    });
  }

  /* ---------- Gallery lightbox ---------- */
  function initLightbox() {
    var dialog = document.querySelector('[data-lightbox-dialog]');
    var links = Array.prototype.slice.call(document.querySelectorAll('[data-lightbox]'));
    if (!dialog || !links.length || typeof dialog.showModal !== 'function') return;

    var img = dialog.querySelector('[data-lightbox-img]');
    var caption = dialog.querySelector('[data-lightbox-caption]');
    var count = dialog.querySelector('[data-lightbox-count]');
    var current = 0;

    function show(index) {
      current = (index + links.length) % links.length;
      var link = links[current];
      var thumb = link.querySelector('img');
      var fig = link.closest('figure');
      var cap = fig && fig.querySelector('figcaption');
      img.src = link.getAttribute('href');
      img.alt = thumb ? thumb.alt : '';
      if (thumb) {
        img.setAttribute('width', thumb.getAttribute('width'));
        img.setAttribute('height', thumb.getAttribute('height'));
      }
      caption.textContent = cap ? cap.textContent.replace(/^\s*\d+\s*/, '').trim() : '';
      count.textContent = (current + 1) + ' / ' + links.length;
    }

    links.forEach(function (link, i) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        show(i);
        dialog.showModal();
        root.classList.add('lightbox-open');
      });
    });

    dialog.querySelector('[data-lightbox-prev]').addEventListener('click', function () { show(current - 1); });
    dialog.querySelector('[data-lightbox-next]').addEventListener('click', function () { show(current + 1); });
    dialog.querySelector('[data-lightbox-close]').addEventListener('click', function () { dialog.close(); });

    dialog.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(current - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); show(current + 1); }
    });

    // Click on the backdrop (the dialog element itself) closes it.
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) dialog.close();
    });

    dialog.addEventListener('close', function () {
      root.classList.remove('lightbox-open');
      links[current].focus();
    });
  }

  /* ---------- Configurator ---------- */
  function initConfigurator() {
    var form = document.querySelector('[data-configurator]');
    var house = document.querySelector('[data-house]');
    if (!form || !house) return;

    var desc = document.querySelector('[data-house-desc]');
    var summary = document.querySelector('[data-summary]');
    var quote = form.querySelector('[data-quote]');
    var parts = { struttura: 'Struttura', pannelli: 'Pannelli' };
    var cssVar = { struttura: '--house-structure', pannelli: '--house-panel' };

    function selected(part) {
      return form.querySelector('input[name="' + part + '"]:checked');
    }

    function label(input) {
      return input.closest('label').querySelector('.swatch__name').textContent.trim();
    }

    function render(updateHash) {
      var bits = [];
      var hash = [];
      Object.keys(parts).forEach(function (part) {
        var input = selected(part);
        if (!input) return;
        house.style.setProperty(cssVar[part], input.dataset.color);
        var name = label(input);
        bits.push(parts[part] + ' ' + name);
        hash.push(part + '=' + input.value);
        var current = form.querySelector('[data-current="' + part + '"]');
        if (current) current.textContent = name;
      });
      var text = bits.join(' · ');
      if (summary) summary.textContent = text;
      if (desc) desc.textContent = bits.join(', ') + '.';
      if (quote) {
        var body = 'Buongiorno,\nvorrei un preventivo per Sally con questa configurazione:\n' +
          bits.join('\n') + '\n\nGrazie.';
        quote.href = 'mailto:vailfabio05@gmail.com?subject=' +
          encodeURIComponent('Preventivo Sally') + '&body=' + encodeURIComponent(body);
      }
      if (updateHash && window.history.replaceState) {
        window.history.replaceState(null, '', '#' + hash.join('&'));
      }
    }

    // Restore a shared configuration from the URL hash, e.g. #struttura=verde&pannelli=bianco
    function applyHash() {
      window.location.hash.replace(/^#/, '').split('&').forEach(function (pair) {
        var kv = pair.split('=');
        if (!parts[kv[0]] || !kv[1]) return;
        var input = form.querySelector('input[name="' + kv[0] + '"][value="' + CSS.escape(kv[1]) + '"]');
        if (input) input.checked = true;
      });
    }
    applyHash();
    window.addEventListener('hashchange', function () { applyHash(); render(false); });

    form.addEventListener('change', function () { render(true); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    form.addEventListener('reset', function () {
      // Inputs reset after this event fires.
      window.setTimeout(function () {
        render(false);
        if (window.history.replaceState) {
          window.history.replaceState(null, '', window.location.pathname + window.location.search);
        }
      }, 0);
    });
    render(false);
  }

  /* ---------- Footer year ---------- */
  function initYear() {
    document.querySelectorAll('[data-year]').forEach(function (el) {
      el.textContent = String(new Date().getFullYear());
    });
  }

  initNav();
  initHeaderScroll();
  initReveal();
  initLightbox();
  initConfigurator();
  initYear();
})();
