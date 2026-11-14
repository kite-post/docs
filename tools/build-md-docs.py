# -*- coding: utf-8 -*-
"""Генерує markdown-версію документації з index.html.

index.html — джерело правди. Після правок у ньому запусти:

    python3 tools/build-md-docs.py

Скрипт перезаписує docs/**/*.md і docs/assets/*.svg; руками їх правити не варто —
наступна збірка все одно затре. Залежностей немає, лише стандартна бібліотека.
"""
import re, os, html as H, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'index.html')
OUT = os.path.join(ROOT, 'docs')
TOK = {'d-edge': '#5c6c88', 'd-accent': '#ff5a36', 'd-ink': '#e9eef6',
       'd-quiet': '#95a3bb', 'd-tint': '#1a2742',
       'f-body': 'Manrope, system-ui, -apple-system, Segoe UI, sans-serif'}
BG = '#0b1220'

TR = {'а':'a','б':'b','в':'v','г':'h','ґ':'g','д':'d','е':'e','є':'ie','ж':'zh','з':'z',
      'и':'y','і':'i','ї':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p',
      'р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
      'щ':'shch','ь':'','ю':'iu','я':'ia',"'":'','’':'','`':''}

def slug(s):
    s = s.lower()
    out = ''.join(TR.get(c, c) for c in s)
    out = re.sub(r'[^a-z0-9]+', '-', out)
    return out.strip('-')

# ---------- inline ----------
def inline(s):
    s = re.sub(r'<code>(.*?)</code>', lambda m: '`' + re.sub(r'<[^>]+>', '', m.group(1)) + '`', s, flags=re.S)
    s = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', s, flags=re.S)
    s = re.sub(r'<em>(.*?)</em>', r'*\1*', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s).replace(' ', ' ')
    s = s.replace('\\~', '~')
    return re.sub(r'[ \t]+', ' ', s).strip()

def cell(s):
    return inline(s).replace('|', '\\|')

# ---------- таблиці ----------
def table(block):
    heads = [cell(c) for c in re.findall(r'<th[^>]*>(.*?)</th>', block, re.S)]
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', block, re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if not tds:
            continue
        vals = []
        for td, raw in zip(tds, re.findall(r'<td([^>]*)>.*?</td>', tr, re.S)):
            v = cell(td)
            if 'id-cell' in raw and v and not v.startswith('`'):
                v = '`%s`' % v
            vals.append(v)
        rows.append(vals)
    n = max([len(heads)] + [len(r) for r in rows]) if rows or heads else 0
    heads += [''] * (n - len(heads))
    rows = [r + [''] * (n - len(r)) for r in rows]
    w = [max(len(heads[i]), *(len(r[i]) for r in rows)) if rows else len(heads[i]) for i in range(n)]
    w = [max(3, x) for x in w]
    line = lambda vals: '| ' + ' | '.join(v.ljust(w[i]) for i, v in enumerate(vals)) + ' |'
    out = [line(heads), '| ' + ' | '.join('-' * w[i] for i in range(n)) + ' |']
    out += [line(r) for r in rows]
    return '\n'.join(out)

# ---------- діаграми ----------
def svg_file(svg, caption, name):
    alt = re.search(r'aria-label="([^"]*)"', svg)
    alt = H.unescape(alt.group(1)) if alt else caption
    for k, v in TOK.items():
        svg = svg.replace('var(--%s)' % k, v)
    m = re.search(r'viewbox="0 0 ([\d.]+) ([\d.]+)"', svg, re.I)
    wd, ht = (m.group(1), m.group(2)) if m else ('760', '600')
    svg = re.sub(r'\sclass="[^"]*"', '', svg, count=1)
    svg = re.sub(r'viewbox=', 'viewBox=', svg, flags=re.I)
    svg = svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" ' % (wd, ht), 1)
    rect = '<rect x="0" y="0" width="%s" height="%s" rx="12" fill="%s"/>' % (wd, ht, BG)
    svg = re.sub(r'(<svg[^>]*>)', r'\1' + rect, svg, count=1)
    path = os.path.join(OUT, 'assets', name + '.svg')
    open(path, 'w', encoding='utf8').write(svg + '\n')
    return '![%s](../assets/%s.svg)\n\n*%s*' % (alt.replace(']', ')'), name, caption)

# ---------- тіло секції ----------
def convert(body, prefix):
    out, i, dia = [], 0, 0
    tokens = re.split(r'(<figure.*?</figure>|<div class="table-wrap"[^>]*><table>.*?</table></div>|<h3[^>]*>.*?</h3>|<ul>.*?</ul>|<ol>.*?</ol>|<p>.*?</p>)', body, flags=re.S)
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t.startswith('<h3'):
            out.append('## ' + inline(t))
        elif t.startswith('<p>'):
            out.append(inline(t))
        elif t.startswith('<ul>') or t.startswith('<ol>'):
            ordered = t.startswith('<ol>')
            items = re.findall(r'<li>(.*?)</li>', t, re.S)
            lines = []
            for n, it in enumerate(items, 1):
                mark = ('%d.' % n) if ordered else '-'
                lines.append('%s %s' % (mark, inline(it)))
            out.append('\n'.join(lines))
        elif t.startswith('<div class="table-wrap"'):
            out.append(table(t))
        elif t.startswith('<figure'):
            dia += 1
            svg = re.search(r'<svg.*?</svg>', t, re.S).group(0)
            cap = inline(re.search(r'<figcaption>(.*?)</figcaption>', t, re.S).group(1))
            out.append(svg_file(svg, cap, '%s-%d' % (prefix, dia)))
        i += 1
    return '\n\n'.join(out)

# ---------- розкладка ----------
GROUPS = [
    ('01-produkt',      'Продукт',        'Що це за система, для кого і як заробляє',            ['1', '2']),
    ('02-vymohy',       'Вимоги',         'Ролі, функціональні та нефункціональні вимоги',        ['3', '4']),
    ('03-arkhitektura', 'Архітектура',    'Сервіси, дані та стенд, на якому все це працює',       ['5', '6', '12']),
    ('04-domen',        'Домен',          'Життєвий цикл посилки і журнал подій',                 ['7', '8']),
    ('05-interfeisy',   'Інтерфейси',     'Зовнішній API і сканування',                           ['9', '10']),
    ('06-ai',           'AI',             'Моделі, прогнози і vision-конвеєр',                    ['11']),
    ('07-plan',         'План і довідка', 'Роадмап, глосарій та ухвалені рішення',                ['13', '14']),
]

def main():
    src = open(SRC, encoding='utf8').read()
    date = re.search(r'<span class="chip">([\d.]+)</span>', src).group(1)
    ver = inline(re.search(r'<span class="chip chip-accent">(.*?)</span>', src).group(1))
    os.makedirs(os.path.join(OUT, 'assets'), exist_ok=True)

    secs = {}
    for m in re.finditer(r'<section aria-labelledby="s(\d+)"[^>]*>(.*?)</section>', src, re.S):
        num, block = m.group(1), m.group(2)
        hm = re.search(r'<h2[^>]*><span class="h2-num">(\d+)</span><span class="h2-text">(.*?)</span></h2>', block, re.S)
        title = inline(hm.group(2))
        secs[num] = {'num': hm.group(1), 'title': title, 'body': block[hm.end():]}

    # шляхи
    order = []
    for folder, _, _, nums in GROUPS:
        for n in nums:
            s = secs[n]
            s['path'] = '%s/%s-%s.md' % (folder, s['num'], slug(s['title']))
            order.append(n)

    for idx, n in enumerate(order):
        s = secs[n]
        folder = s['path'].split('/')[0]
        os.makedirs(os.path.join(OUT, folder), exist_ok=True)
        body = convert(s['body'], '%s-%s' % (s['num'], slug(s['title']))[:40])
        prev = secs[order[idx - 1]] if idx else None
        nxt = secs[order[idx + 1]] if idx + 1 < len(order) else None
        rel = lambda t: ('../' + t['path']) if t['path'].split('/')[0] != folder else t['path'].split('/')[1]
        nav = []
        if prev:
            nav.append('[← %s · %s](%s)' % (prev['num'], prev['title'], rel(prev)))
        nav.append('[Зміст](../README.md)')
        if nxt:
            nav.append('[%s · %s →](%s)' % (nxt['num'], nxt['title'], rel(nxt)))
        head = '# %s · %s\n\n> **Kite** — документація поштової системи · %s · %s' % (s['num'], s['title'], ver, date)
        text = '%s\n\n%s\n\n---\n\n%s\n' % (head, body, ' · '.join(nav))
        text = re.sub(r'\n{3,}', '\n\n', text)
        open(os.path.join(OUT, s['path']), 'w', encoding='utf8').write(text)
        print('✓', s['path'])

    # зміст
    lead = inline(re.search(r'<section aria-labelledby="s1".*?<p>(.*?)</p>', src, re.S).group(1))
    r = ['# Kite — документація поштової системи', '',
         '> %s · станом на %s' % (ver, date), '', lead, '',
         'Та сама документація однією сторінкою — [index.html](../index.html) '
         '(відкрий у браузері). Нижче вона ж, розкладена по розділах.', '', '## Зміст', '']
    for folder, gtitle, gdesc, nums in GROUPS:
        r.append('### %s' % gtitle)
        r.append('')
        r.append('_%s_' % gdesc)
        r.append('')
        for n in nums:
            s = secs[n]
            r.append('- **[%s · %s](%s)**' % (s['num'], s['title'], s['path']))
        r.append('')
    r += ['## Діаграми', '',
          'Усі схеми лежать окремими SVG у [assets/](assets) і вставлені в тексті розділів.', '']
    open(os.path.join(OUT, 'README.md'), 'w', encoding='utf8').write('\n'.join(r))
    print('✓ README.md')

main()
