# Reference site analysis — techs-gardenhouse.com

Reviewed on 2026-10-18 by reading the live HTML of all four pages. The site is used here only as a content and structure reference. No code, copy, images or branding are reused.

## Purpose and audience

This is a product site for **Sally**, a modular, insulated garden house. It is designed in Italy and registered with ADI (Association for Industrial Design, Project Register prot. n.3880). The audience is Italian homeowners who want a low-maintenance, design-led outdoor room (studio, storage, hobby space) and who would like to choose its colors before buying. The site is in Italian.

## Pages and sections

| Page | Sections | Content types | Calls to action |
|---|---|---|---|
| **Home** `/` | Sticky nav · hero (product photo, "Nuova SALLY" heading) · product block "SALLY GARDEN HOUSE" with 8 selling points next to a texture/detail photo · footer | Photo, headings, short feature list | **Configura** (→ configurator), **Scheda tecnica** (PDF download) |
| **Galleria** | Section header (title + subtitle) · carousel of 5 photos with lightbox: exterior, interior with door, full interior, close garden view, wide garden view · footer | Photo gallery with captions | Open photo (lightbox) |
| **Configura** | Section header · 3D model viewer (three.js bundle) · color panel with two groups, *Struttura* and *Pannelli*, 9 swatches each · footer | Interactive 3D, color swatches | Pick colors (no follow-up action) |
| **Contatti** | Section header · "Contattaci" block with email · "Scarica la nostra brochure" block · footer | Text, mailto link, PDF | **Email**, **Scarica brochure** |
| **Footer** (all) | Brand + one-sentence pitch + email · "Link utili" (Home, Configura, Contatti) · ADI registration · © line | Text, links | — |

The 8 selling points are: fully customizable (size, frame color, panel color), no maintenance, insulated, 4 cm expanded-polyurethane panels, exclusive design, premium materials, usable 360°, available as an assembly kit.

The 9 configurator colors are: brown #8B4513, green #178048, light grey #9DA6A1, ochre #F4A300, white #F5F5F5, anthracite #2F4F4F, lilac #CFABD6, red #DB2612, sky blue #12C0E3. These match the first nine presets in the Garden House app (`lib/palette.dart`).

## What works

- **Clear, short funnel:** see the product → personalise it → get in touch. The redesign keeps this.
- **The configurator is the real differentiator.** Being able to recolor the house is the hook, and the app builds on it.
- **Strong, concrete selling points** (insulation, 4 cm panels, no maintenance, kit) and a credible trust signal (ADI registration).
- The navigation is small and focused. There are only four destinations.

## What looks dated or weak

- **Stack and weight:** Bootstrap 3, jQuery, bootsnav, owl-carousel, animate.css, Font Awesome and three icon-font stylesheets, plus a three.js bundle. That is a lot of payload for a handful of pages.
- **Markup problems:** the hero "Configura" `<button>` is never closed, so the two CTAs are nested. Navigation uses `onclick` buttons instead of links. There are inline styles everywhere, a commented-out dead menu item, and `lang="it"` with English-only alt text such as "sally" and "Garden House 2".
- **Accessibility:** color swatches are `<div>`s. They can't be reached with the keyboard and have no names (some have only a `title`). There is no skip link, no visible focus styling, and a carousel with no pause control. Every page has an `<h2>` but no `<h1>`.
- **Content hierarchy:** the hero has an empty paragraph. The feature list uses an `<h3>` per bullet. The home page never explains *what* Sally is in a sentence. Inner pages hard-code `margin-top: 95px` to clear the fixed nav.
- **Visuals:** generic template look (Poppins + Rufina, black nav bar on inner pages, inline color overrides). The page has no strong brand palette, little whitespace rhythm, and photos dropped in without art direction.
- **Configurator dead end:** after choosing colors there is no next step (quote request, share, summary).
- **Footer:** "Link utili" omits Galleria, and the © line is static.

## Redesign brief derived from this

1. Keep the 4 pages, their sections and their order. Fix the semantics: one `h1` per page, real lists, real links and buttons.
2. Replace the carousel with an accessible grid + `<dialog>` lightbox.
3. Replace the 3D viewer with a lightweight **inline-SVG configurator**. It uses radio-button swatches (keyboard accessible, with names from the app palette), shows a live summary, keeps the selection in a shareable URL hash, and adds a "Richiedi preventivo" email CTA so it is no longer a dead end.
4. Rewrite the copy in Italian with the same facts, and add one sentence explaining what Sally is.
5. Give each design branch its own art direction on the same content.
