#!/usr/bin/env python3
"""SEO block + English pages for Techs Garden House.

The Italian pages in the repo root are the source of truth. This script

  1. (re)writes the SEO block of each Italian page (title, description,
     canonical, hreflang, Open Graph, JSON-LD) between the markers
     <!-- seo:start --> and <!-- seo:end -->, adds the language switch to the
     header (all idempotent);
  2. generates en/*.html from the Italian pages: translated text, assets
     re-rooted with "../", page links mapped to the English file names;
  3. writes sitemap.xml and robots.txt.

Run from anywhere:  python3 tools/seo_i18n.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://www.techs-gardenhouse.com'
OG_IMAGE = SITE + '/assets/img/og-1200x630.jpg'
EMAIL = 'vailfabio05@gmail.com'

# key -> (italian file, english file, italian url, english url)
PAGES = {
    'index':     ('index.html',     'en/index.html',     '/',               '/en/'),
    'gallery':   ('galleria.html',  'en/gallery.html',   '/galleria.html',  '/en/gallery.html'),
    'configure': ('configura.html', 'en/configure.html', '/configura.html', '/en/configure.html'),
    'contact':   ('contatti.html',  'en/contact.html',   '/contatti.html',  '/en/contact.html'),
}
IT2EN_FILE = {v[0]: Path(v[1]).name for v in PAGES.values()}

META = {
    'index': {
        'it': ('Casetta da giardino coibentata in alluminio · Techs Garden House',
               'Casetta da giardino di design in alluminio, coibentata con pannelli da 4 cm, senza manutenzione, con serramenti a doppio vetro camera. 16 finiture, kit da montare. Progetto registrato ADI.'),
        'en': ('Insulated aluminium garden house · Techs Garden House',
               'Designer aluminium garden house, insulated with 4 cm panels, maintenance-free, with double-glazed aluminium windows. 16 panel finishes, delivered as a kit. ADI-registered design.'),
    },
    'gallery': {
        'it': ('Galleria foto della casetta da giardino · Techs Garden House',
               'Foto della casetta da giardino Techs Garden House: bordo piscina, in giardino, sul patio e gli interni a pannelli coibentati.'),
        'en': ('Garden house photo gallery · Techs Garden House',
               'Photos of the Techs Garden House: by the pool, in the garden, on the patio, plus the insulated panel interior.'),
    },
    'configure': {
        'it': ('Configuratore 3D casetta da giardino · Techs Garden House',
               'Configura la tua casetta da giardino: scegli il colore RAL della struttura e una delle 16 finiture dei pannelli, guarda il modello 3D e richiedi un preventivo.'),
        'en': ('3D garden house configurator · Techs Garden House',
               'Configure your garden house: pick the RAL colour of the frame and one of 16 panel finishes, view the 3D model and request a quote.'),
    },
    'contact': {
        'it': ('Contatti e preventivo casetta da giardino · Techs Garden House',
               'Scrivi a Techs Garden House per un preventivo, informazioni su misure, finiture e montaggio della tua casetta da giardino, o scarica la brochure.'),
        'en': ('Contact and quote for your garden house · Techs Garden House',
               'Write to Techs Garden House for a quote, or for information on sizes, finishes and assembly of your garden house. Download the brochure.'),
    },
}

BREADCRUMB = {
    'gallery':   {'it': 'Galleria', 'en': 'Gallery'},
    'configure': {'it': 'Configura', 'en': 'Configure'},
    'contact':   {'it': 'Contatti', 'en': 'Contact'},
}

# ------------------------------------------------------------------ English
# Exact-substring replacements, applied longest first, on the Italian HTML.
TR = {
    # chrome
    'Vai al contenuto': 'Skip to content',
    'aria-label="Principale"': 'aria-label="Main"',
    '>Galleria<': '>Gallery<', '>Contatti<': '>Contact<', '>Configura<': '>Configure<',
    '>Esplora<': '>Explore<',
    'Brochure (PDF)': 'Brochure (PDF, Italian)',
    'Design registrato': 'Registered design',
    'Il progetto è depositato presso l’ADI, Associazione per il Disegno Industriale, nel Registro dei progetti con prot. n. 3880.':
        'The design is filed with ADI, the Italian Association for Industrial Design, in its design register, no. 3880.',
    'ADI, Associazione per il Disegno Industriale': 'ADI, the Italian Association for Industrial Design',
    'Techs Garden House è una nuova concezione di spazio outdoor: una struttura di design che unisce tecnologia, comfort e integrazione con l’ambiente.':
        'Techs Garden House is a new idea of outdoor space: a designer structure that combines technology, comfort and integration with its surroundings.',
    'Tutti i diritti riservati.': 'All rights reserved.',
    'Torna su ↑': 'Back to top ↑',
    # home: hero
    'La casetta bianca con porta vetrata e punto luce verticale in un giardino, accanto a un albero e a una siepe':
        'The white garden house with a glazed door and a vertical light window, in a garden next to a tree and a hedge',
    'Il tuo stile,': 'Your style,', 'il tuo nuovo': 'your new', '>giardino<': '>garden<',
    'Casetta da giardino coibentata, in alluminio e pannelli da 4 cm: una struttura di design che unisce tecnologia, comfort e integrazione con l’ambiente. Per giardini, terrazze, hospitality e spazi privati di alto livello.':
        'An insulated aluminium garden house with 4 cm panels: a designer structure that combines technology, comfort and integration with its surroundings. For gardens, terraces, hospitality and high-end private spaces.',
    'Configura la tua casetta': 'Configure your garden house',
    'Scarica la brochure': 'Download the brochure',
    '>Scopri<': '>Discover<',
    # home: creds
    'Techs Garden House in sintesi': 'Techs Garden House at a glance',
    'Pannelli in poliuretano espanso': 'Expanded polyurethane panels',
    'Giorni l’anno, coibentata': 'Days a year, insulated',
    'Manutenzione richiesta': 'Maintenance required',
    'Finiture per i pannelli': 'Panel finishes',
    'Sfruttabile per ogni uso': 'Usable for any purpose',
    '>A partire da<': '>Starting from<',
    # home: manifesto
    'Una nuova concezione di spazio outdoor': 'A new idea of outdoor space',
    '>Il progetto<': '>The project<',
    'Non una semplice struttura da esterno, ma un <em>ambiente modulare e personalizzabile</em> che trasforma ogni spazio in un luogo da vivere tutto l’anno.':
        'Not just an outdoor structure, but a <em>modular, customisable environment</em> that turns any space into a place to live in all year round.',
    'Materiali innovativi, soluzioni tecnologiche integrate e un’estetica contemporanea rendono Techs Garden House un elemento architettonico distintivo, capace di valorizzare qualsiasi contesto.':
        'Innovative materials, integrated technology and a contemporary look make Techs Garden House a distinctive architectural element that enhances any setting.',
    'Una nuova esperienza outdoor, dove natura e innovazione convivono in perfetto equilibrio.':
        'A new outdoor experience, where nature and innovation live in perfect balance.',
    'La casetta grigio antracite con porta vetrata e punto luce verticale, su una pedana in legno accanto a una piscina, con divani da esterno e fiori viola':
        'The anthracite-grey garden house with a glazed door and a vertical light window, on a wooden deck beside a swimming pool, with outdoor sofas and purple flowers',
    'Dove si inserisce': 'Where it fits',
    '>Giardini<': '>Gardens<', '>Piscine<': '>Pools<', '>Terrazze<': '>Terraces<', '>Hospitality<': '>Hospitality<',
    # home: pillars
    'Principi progettuali': 'Design principles',
    'Design architettonico distintivo': 'Distinctive architectural design',
    'Linee moderne, eleganza minimal e massima cura dei dettagli rendono Techs Garden House un vero elemento di arredo architettonico.':
        'Modern lines, minimal elegance and great attention to detail make Techs Garden House a true piece of architectural furnishing.',
    'Ogni struttura è progettata per integrarsi armoniosamente con l’ambiente circostante, valorizzando giardini, piscine, terrazze e spazi hospitality. Un’estetica contemporanea che unisce bellezza, funzionalità e prestigio.':
        'Every structure is designed to blend harmoniously with its surroundings, enhancing gardens, pools, terraces and hospitality spaces. A contemporary look that combines beauty, function and prestige.',
    'Progetto registrato ADI · n. 3880': 'ADI-registered design · no. 3880',
    'Tecnologia e comfort integrati': 'Integrated technology and comfort',
    'Illuminazione, chiusure, optional e soluzioni tecniche sono progettati per garantire comfort in ogni stagione.':
        'Lighting, closures, options and technical solutions are designed to ensure comfort in every season.',
    'Le strutture Techs Garden House offrono uno spazio protetto, funzionale e altamente tecnologico, ideale sia per il relax privato sia per contesti professionali e ricettivi.':
        'Techs Garden House structures offer a protected, functional and highly technological space, ideal for private relaxation as well as for professional and hospitality settings.',
    'Un ambiente da vivere 365 giorni l’anno': 'A space to live in 365 days a year',
    'Modularità e personalizzazione': 'Modularity and customisation',
    'Ogni progetto è configurabile in base allo spazio e alle esigenze del cliente. Dimensioni, finiture, accessori e soluzioni tecniche possono essere personalizzati per creare un ambiente unico e su misura.':
        'Every project can be configured to the space and the client’s needs. Sizes, finishes, accessories and technical solutions can be customised to create a unique, tailor-made environment.',
    'Dalla residenza privata agli spazi contract e hospitality, Techs Garden House si adatta a ogni contesto con soluzioni esclusive.':
        'From private homes to contract and hospitality spaces, Techs Garden House adapts to every setting with exclusive solutions.',
    'Scopri le 16 finiture': 'Discover the 16 finishes',
    # home: showcase
    '>Modello 3D<': '>3D model<',
    'Guardala da <strong>ogni lato</strong>': 'See it from <strong>every side</strong>',
    'Il modello originale, con la porta vetrata e il punto luce verticale.':
        'The original model, with the glazed door and the vertical light window.',
    '>Pannelli<': '>Panels<',
    'Poliuretano espanso, 4 cm': 'Expanded polyurethane, 4 cm',
    'Serramenti in alluminio': 'Aluminium windows',
    'Doppio vetro camera termica': 'Double-glazed thermal cavity',
    '>Manutenzione<': '>Maintenance<', '>Nessuna<': '>None<',
    '>Finiture<': '>Finishes<', '16 per i pannelli': '16 for the panels',
    '>Altezza<': '>Height<', '2,5 metri': '2.5 metres',
    'Scegli colori e finiture': 'Choose colours and finishes',
    'Modello 3D interattivo': 'Interactive 3D model',
    '>Porta vetrata<': '>Glazed door<', '>Punto luce<': '>Light window<',
    'Pannelli coibentati 4 cm': 'Insulated panels, 4 cm',
    'Ferma la rotazione automatica': 'Stop the automatic rotation',
    'Torna alla vista iniziale': 'Back to the initial view',
    # home: finishes
    '>La materia<': '>The material<',
    'Scopri la nostra <strong>gamma di colori</strong>': 'Discover our <strong>range of colours</strong>',
    'Sedici finiture per i pannelli: superfici lisce, goffrate o Polygrain e due essenze di noce, con doga centrale (passo 250&nbsp;mm) oppure a piano unico (passo 500&nbsp;mm).':
        'Sixteen panel finishes: smooth, embossed or Polygrain surfaces and two walnut woods, with a central groove (250&nbsp;mm pitch) or a single flat face (500&nbsp;mm pitch).',
    'Le foto mostrano i pannelli reali. I colori a schermo possono variare leggermente: chiedici i campioni.':
        'The photos show the real panels. On-screen colours may vary slightly: ask us for samples.',
    'Provale sulla tua casetta': 'Try them on your garden house',
    # home: features
    'Perché Techs Garden House': 'Why Techs Garden House',
    'Pensata per durare, <strong>bella da vivere</strong>': 'Built to last, <strong>lovely to live in</strong>',
    'Totalmente personalizzabile': 'Fully customisable',
    'Dimensioni, finiture, accessori e colori: ogni progetto nasce su misura.': 'Sizes, finishes, accessories and colours: every project is made to measure.',
    'Nessuna manutenzione': 'No maintenance',
    'Niente vernici da rinnovare né legno da trattare, stagione dopo stagione.': 'No paint to renew and no wood to treat, season after season.',
    '>Coibentata<': '>Insulated<',
    'Fresca d’estate, riparata d’inverno: uno spazio da vivere 365 giorni l’anno.': 'Cool in summer, sheltered in winter: a space to live in 365 days a year.',
    'Pannelli da 4&nbsp;cm': '4&nbsp;cm panels',
    'In poliuretano espanso, leggeri, rigidi e isolanti.': 'Expanded polyurethane: light, rigid and insulating.',
    'Design esclusivo': 'Exclusive design',
    'Linee essenziali, progetto depositato presso l’ADI.': 'Clean lines, design filed with ADI.',
    'Materiali premium': 'Premium materials',
    'Componenti scelti per durare nel tempo, senza compromessi.': 'Components chosen to last, without compromise.',
    'Sfruttabile a 360°': 'Usable in 360°',
    'Studio, relax, hobby, deposito o ospitalità: decidi tu.': 'Studio, relaxing, hobbies, storage or hospitality: you decide.',
    'Disponibile in kit': 'Available as a kit',
    'Arriva pronta da montare, con istruzioni chiare.': 'Arrives ready to assemble, with clear instructions.',
    # home: finale
    'La casetta grigio scuro con telaio in acciaio, la porta vetrata illuminata e il punto luce verticale, di notte su un terreno roccioso sotto la Via Lattea':
        'The dark-grey garden house with a steel frame, the lit glazed door and the vertical light window, at night on rocky ground under the Milky Way',
    'Oltre la porta,': 'Beyond the door,', 'nuovi spazi': 'new spaces',
    'Parla con noi': 'Talk to us',
    # gallery
    'Dentro</span> e fuori': 'Inside</span> and out',
    'Bordo piscina, in giardino, sul patio di casa. Apri ogni foto per vederla a tutto schermo.':
        'By the pool, in the garden, on the home patio. Open any photo to see it full screen.',
    'Foto della galleria': 'Gallery photos',
    '(apri ingrandimento)': '(open enlarged view)',
    'La casetta bianca con porta vetrata e punto luce verticale, su un patio in pietra': 'The white garden house with a glazed door and a vertical light window, on a stone patio',
    'Interno della casetta con pareti a pannelli bianchi, visto verso la porta vetrata': 'Inside the garden house, with white panel walls, looking towards the glazed door',
    'La casetta in giardino vista da vicino, con il vialetto in pietra davanti': 'The garden house seen up close, with the stone path in front',
    'Interno vuoto e luminoso della casetta, con pannelli bianchi e punto luce laterale': 'Bright, empty interior of the garden house, with white panels and a side light window',
    'La casetta sullo sfondo di un ampio prato, sotto un cielo azzurro': 'The garden house in the background of a wide lawn, under a blue sky',
    '>Sul patio<': '>On the patio<', '>Interno con porta<': '>Interior with door<',
    '>In giardino, da vicino<': '>In the garden, up close<', '>Interno completo<': '>Full interior<',
    '>In giardino, vista larga<': '>In the garden, wide view<',
    'Foto della casetta montata e immagine della brochure.': 'Photos of the assembled garden house and an image from the brochure.',
    'Prova colori e finiture nel configuratore': 'Try colours and finishes in the configurator',
    'Foto ingrandita': 'Enlarged photo', 'Foto precedente': 'Previous photo', 'Foto successiva': 'Next photo', 'aria-label="Chiudi"': 'aria-label="Close"',
    # contact
    'Parliamo del</span> tuo spazio': 'Let’s talk about</span> your space',
    'Misure, finiture, accessori o montaggio: raccontaci cosa hai in mente e ti aiutiamo a scegliere la configurazione giusta.':
        'Sizes, finishes, accessories or assembly: tell us what you have in mind and we will help you choose the right configuration.',
    'Modi per contattarci': 'Ways to contact us',
    '<dt>Sito web</dt>': '<dt>Website</dt>', '<dt>Documenti</dt>': '<dt>Documents</dt>',
    '>Brochure</a>': '>Brochure (PDF, Italian)</a>',
    'Scrivici una email': 'Send us an email',
    'subject=Informazioni': 'subject=Information',
    'Configura prima la tua casetta': 'Configure your garden house first',
    'Progetto depositato presso l’ADI, Registro dei progetti prot. n. 3880.': 'Design filed with ADI, design register no. 3880.',
    # configurator
    '>Configuratore<': '>Configurator<',
    'Configura la</span> tua casetta': 'Configure</span> your garden house',
    'Tipo di anteprima': 'Preview type', '>Disegno<': '>Drawing<',
    'Anteprima della casetta': 'Garden house preview',
    'Struttura RAL 9010, pannelli Doga centrale goffrato RAL 9010.': 'Frame RAL 9010, panels Central groove embossed RAL 9010.',
    'Ruota a sinistra': 'Rotate left', 'Ruota a destra': 'Rotate right',
    'Scegli struttura e pannelli': 'Choose frame and panels',
    '>Struttura <': '>Frame <', '>Pannelli <': '>Panels <',
    'Struttura, profili, tetto e cornici di porta e punto luce.': 'Frame, profiles, roof and the frames of the door and the light window.',
    'Le 16 finiture della brochure: doga centrale (passo 250) o piano (passo 500).': 'The 16 finishes from the brochure: central groove (250 pitch) or flat (500 pitch).',
    'Bianco Grigio (simil RAL 9002)': 'White Grey (similar to RAL 9002)',
    'Struttura RAL 9010 · Pannelli Doga centrale goffrato RAL 9010': 'Frame RAL 9010 · Panels Central groove embossed RAL 9010',
    'Richiedi preventivo': 'Request a quote',
    'subject=Preventivo': 'subject=Quote',
    '>Ripristina<': '>Reset<',
    'I colori a schermo sono indicativi: su richiesta ti inviamo i campioni dei pannelli. Dimensioni, accessori e altre tinte si definiscono insieme nel preventivo.':
        'On-screen colours are indicative: on request we send you panel samples. Sizes, accessories and other colours are defined together in the quote.',
}

FINISH_WORDS = [
    ('Doga centrale', 'Central groove'), ('doga centrale', 'central groove'),
    ('Piano', 'Flat'), ('piano', 'flat'),
    ('liscio', 'smooth'), ('Liscio', 'Smooth'), ('goffrato', 'embossed'), ('Goffrato', 'Embossed'),
    ('polygrain', 'Polygrain'), ('Noce chiaro', 'Light walnut'), ('Noce scuro', 'Dark walnut'),
    ('passo', 'pitch'),
]


def finish(s):
    for a, b in FINISH_WORDS:
        s = s.replace(a, b)
    return s


def translate(html):
    # panel finish names, codes and alt texts
    html = re.sub(r'alt="Pannello ([^,"]+), ([^"]+)"',
                  lambda m: 'alt="%s panel, %s"' % (finish(m.group(1)).capitalize(), finish(m.group(2))), html)
    html = re.sub(r'(<span class="finish__(?:name|code)">)([^<]+)',
                  lambda m: m.group(1) + finish(m.group(2)), html)
    html = re.sub(r'(<span class="swatch__name">)((?:Piano|Doga)[^<]+)',
                  lambda m: m.group(1) + finish(m.group(2)), html)
    for it in sorted(TR, key=len, reverse=True):
        html = html.replace(it, TR[it])
    return html


# ------------------------------------------------------------------ SEO block
def esc(s):
    return s.replace('&', '&amp;').replace('"', '&quot;')


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '</script>'


def graph(key, lang):
    url = SITE + PAGES[key][2 if lang == 'it' else 3]
    title, desc = META[key][lang]
    org = {'@type': 'Organization', '@id': SITE + '/#org', 'name': 'Techs Garden House', 'url': SITE + '/',
           'logo': SITE + '/assets/favicon.png', 'email': EMAIL,
           'description': META['index'][lang][1]}
    site = {'@type': 'WebSite', '@id': SITE + '/#site', 'url': SITE + '/', 'name': 'Techs Garden House',
            'inLanguage': ['it', 'en'], 'publisher': {'@id': SITE + '/#org'}}
    nodes = [org, site]
    page_type = {'contact': 'ContactPage', 'gallery': 'ImageGallery'}.get(key, 'WebPage')
    nodes.append({'@type': page_type, '@id': url + '#page', 'url': url, 'name': title, 'description': desc,
                  'inLanguage': lang, 'isPartOf': {'@id': SITE + '/#site'}, 'primaryImageOfPage': {'@type': 'ImageObject', 'url': OG_IMAGE}})
    if key in ('index', 'configure'):
        nodes.append({
            '@type': 'Product', '@id': SITE + '/#product',
            'name': 'Techs Garden House',
            'description': META['index'][lang][1],
            'image': [OG_IMAGE], 'brand': {'@type': 'Brand', 'name': 'Techs Garden House'},
            'category': 'Casette da giardino' if lang == 'it' else 'Garden houses',
            'material': 'Alluminio, poliuretano espanso' if lang == 'it' else 'Aluminium, expanded polyurethane',
            'manufacturer': {'@id': SITE + '/#org'},
        })
    if key != 'index':
        home = SITE + PAGES['index'][2 if lang == 'it' else 3]
        nodes.append({'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': home},
            {'@type': 'ListItem', 'position': 2, 'name': BREADCRUMB[key][lang], 'item': url}]})
    return {'@context': 'https://schema.org', '@graph': nodes}


def seo_block(key, lang):
    it_url = SITE + PAGES[key][2]
    en_url = SITE + PAGES[key][3]
    url = it_url if lang == 'it' else en_url
    title, desc = META[key][lang]
    locale, alt_locale = ('it_IT', 'en_GB') if lang == 'it' else ('en_GB', 'it_IT')
    return '\n'.join([
        '  <!-- seo:start (generated by tools/seo_i18n.py) -->',
        '  <title>%s</title>' % esc(title),
        '  <meta name="description" content="%s">' % esc(desc),
        '  <link rel="canonical" href="%s">' % url,
        '  <link rel="alternate" hreflang="it" href="%s">' % it_url,
        '  <link rel="alternate" hreflang="en" href="%s">' % en_url,
        '  <link rel="alternate" hreflang="x-default" href="%s">' % it_url,
        '  <meta name="robots" content="index, follow, max-image-preview:large">',
        '  <meta property="og:type" content="website">',
        '  <meta property="og:site_name" content="Techs Garden House">',
        '  <meta property="og:locale" content="%s">' % locale,
        '  <meta property="og:locale:alternate" content="%s">' % alt_locale,
        '  <meta property="og:title" content="%s">' % esc(title),
        '  <meta property="og:description" content="%s">' % esc(desc),
        '  <meta property="og:url" content="%s">' % url,
        '  <meta property="og:image" content="%s">' % OG_IMAGE,
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <meta name="twitter:title" content="%s">' % esc(title),
        '  <meta name="twitter:description" content="%s">' % esc(desc),
        '  <meta name="twitter:image" content="%s">' % OG_IMAGE,
        '  ' + jsonld(graph(key, lang)),
        '  <!-- seo:end -->',
    ])


SEO_RE = re.compile(r'  <!-- seo:start.*?<!-- seo:end -->', re.S)


def put_seo(html, key, lang):
    block = seo_block(key, lang)
    if SEO_RE.search(html):
        return SEO_RE.sub(lambda m: block, html, count=1)
    html = re.sub(r'\s*<title>.*?</title>', '', html, count=1, flags=re.S)
    html = re.sub(r'\s*<meta name="description"[^>]*>', '', html, count=1)
    return re.sub(r'(<meta name="viewport"[^>]*>)', lambda m: m.group(1) + '\n' + block, html, count=1)


# ------------------------------------------------------------------ Italian source edits
HERO_LEAD_OLD = 'Una struttura di design che unisce tecnologia, comfort e integrazione con l’ambiente. Per giardini'
HERO_LEAD_NEW = ('Casetta da giardino coibentata, in alluminio e pannelli da 4 cm: una struttura di design che unisce '
                 'tecnologia, comfort e integrazione con l’ambiente. Per giardini')


def lang_switch(href, label_lang):
    name, lang, aria = (('EN', 'en', 'English version') if label_lang == 'en' else ('IT', 'it', 'Versione italiana'))
    return ('          <li class="site-nav__item site-nav__item--lang"><a class="site-nav__link" href="%s" hreflang="%s" lang="%s" aria-label="%s">%s</a></li>\n'
            % (href, lang, lang, aria, name))


def italian(key):
    path = ROOT / PAGES[key][0]
    html = path.read_text(encoding='utf-8')
    html = put_seo(html, key, 'it')
    if key == 'index':
        html = html.replace(HERO_LEAD_OLD, HERO_LEAD_NEW)
        html = re.sub(r'    <section class="faq".*?</section>\n\n', '', html, flags=re.S)  # no FAQ section on the page
    html = re.sub(r'          <li class="site-nav__item site-nav__item--lang">.*\n', '', html)
    en_href = 'en/' if key == 'index' else 'en/' + Path(PAGES[key][1]).name
    html = html.replace('          <li class="site-nav__item site-nav__item--cta">',
                        lang_switch(en_href, 'en') + '          <li class="site-nav__item site-nav__item--cta">', 1)
    path.write_text(html, encoding='utf-8')
    return html


def english(key, it_html):
    html = translate(it_html)
    html = html.replace('<html lang="it">', '<html lang="en" data-root="../">', 1)
    html = put_seo(html, key, 'en')
    # page links -> English file names, then re-root assets
    for it_name, en_name in IT2EN_FILE.items():
        html = re.sub(r'href="%s(#[^"]*)?"' % re.escape(it_name), lambda m: 'href="%s%s"' % (en_name, m.group(1) or ''), html)
    html = re.sub(r'(?<![\w./-])(assets|css|js)/', r'../\1/', html)
    # the language switch of the English page points back to Italian
    it_href = '../' if key == 'index' else '../' + PAGES[key][0]
    html = re.sub(r'          <li class="site-nav__item site-nav__item--lang">.*\n',
                  lambda m: lang_switch(it_href, 'it'), html)
    out = ROOT / PAGES[key][1]
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding='utf-8')


def crawl_files():
    urls = []
    for key, (_, _, it_url, en_url) in PAGES.items():
        urls.append('  <url>\n    <loc>%s%s</loc>\n    <xhtml:link rel="alternate" hreflang="it" href="%s%s"/>\n'
                    '    <xhtml:link rel="alternate" hreflang="en" href="%s%s"/>\n'
                    '    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>\n    <priority>%s</priority>\n  </url>'
                    % (SITE, it_url, SITE, it_url, SITE, en_url, SITE, it_url, '1.0' if key == 'index' else '0.7'))
        urls.append('  <url>\n    <loc>%s%s</loc>\n    <xhtml:link rel="alternate" hreflang="it" href="%s%s"/>\n'
                    '    <xhtml:link rel="alternate" hreflang="en" href="%s%s"/>\n'
                    '    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>\n    <priority>%s</priority>\n  </url>'
                    % (SITE, en_url, SITE, it_url, SITE, en_url, SITE, it_url, '0.9' if key == 'index' else '0.6'))
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + '\n'.join(urls) + '\n</urlset>\n', encoding='utf-8')
    (ROOT / 'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % SITE, encoding='utf-8')


def main():
    for key in PAGES:
        english(key, italian(key))
    crawl_files()
    print('ok:', ', '.join(v[1] for v in PAGES.values()))


if __name__ == '__main__':
    sys.exit(main())
