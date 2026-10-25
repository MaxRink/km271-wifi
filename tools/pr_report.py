#!/usr/bin/env python3
"""Generate the data sections and images of a PR body from the actual KiCad files.

Compares a git base revision with the working tree for each KiCad project and writes:
  * net/wiring diff (pin level, rename detection) + raw netlist diff
  * routing summary (tracks/vias, track length per changed net)
  * BOM diff (per refdes group) with cost and extended-part count (tools/lcsc_parts.json)
  * placement diff
  * images: schematic and PCB before/after/diff (+ zoomed crops of changed areas) and 3D renders
Run with KiCad's python (needs pcbnew and PIL), from the repo root:
  pr_report.py --base main --branch jlcpcb-ready --reasons tools/pr1_reasons.json \
      --out docs/pr-images/jlcpcb-ready --md /tmp/pr1_generated.md KM217-WiFi/KM217-WiFi EXTENSIONS/ETH_W5500/ETH_W5500
"""
import argparse, csv, difflib, json, math, os, re, shutil, subprocess, tempfile
from collections import defaultdict

import pcbnew
from PIL import Image, ImageChops, ImageDraw, ImageFont

REPO_URL = 'https://raw.githubusercontent.com/MaxRink/km271-wifi'
MODELS = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


# ---------------------------------------------------------------- data

def netlist(sch, tmp, tag):
    out = os.path.join(tmp, tag + '.net')
    sh('kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, sch)
    txt = open(out).read()
    nets = {}
    for m in re.finditer(r'\(net\s*\(code "?\d+"?\)\s*\(name "([^"]*)"\)(.*?)(?=\(net\s*\(code|\Z)', txt, re.S):
        nets[m.group(1)] = frozenset('%s.%s' % p for p in re.findall(r'\(ref "([^"]*)"\)\s*\(pin "([^"]*)"\)', m.group(2)))
    return nets


def refs_of(pins):
    return {p.split('.')[0] for p in pins}


def reason_for(pins, reasons):
    rs = [reasons[r] for r in sorted(refs_of(pins)) if r in reasons]
    return '; '.join(dict.fromkeys(rs)) or 'follows symbol/part change'


def fmt_pins(pins, limit=12):
    p = sorted(pins, key=lambda s: (s.split('.')[0], s))
    return ', '.join(p) if len(p) <= limit else ', '.join(p[:limit]) + ' … (%d pins)' % len(p)


def net_diff(old, new, reasons):
    rows, renamed_new = [], set()
    for o in sorted(set(old) - set(new)):
        match = [n for n in set(new) - set(old) if new[n] == old[o]]
        if match:
            renamed_new.add(match[0])
            rows.append((o + ' → ' + match[0], 'renamed', fmt_pins(old[o]), 'same pins', reason_for(old[o], reasons)))
        else:
            rows.append((o, 'removed', fmt_pins(old[o]), '—', reason_for(old[o], reasons)))
    for n in sorted(set(new) - set(old) - renamed_new):
        rows.append((n, 'added', '—', fmt_pins(new[n]), reason_for(new[n], reasons)))
    for n in sorted(set(old) & set(new)):
        if old[n] != new[n]:
            lost, gained = old[n] - new[n], new[n] - old[n]
            change = ('−' + fmt_pins(lost) if lost else '') + (' / ' if lost and gained else '') + \
                     ('+' + fmt_pins(gained) if gained else '')
            rows.append((n, 'pins changed', '%d pins' % len(old[n]), change, reason_for(lost | gained, reasons)))
    raw = list(difflib.unified_diff(
        ['%s: %s' % (n, ' '.join(sorted(old[n]))) for n in sorted(old)],
        ['%s: %s' % (n, ' '.join(sorted(new[n]))) for n in sorted(new)], 'base', 'head', lineterm='', n=0))
    return rows, raw


def bom(sch, tmp, tag):
    out = os.path.join(tmp, tag + '_bom.csv')
    sh('kicad-cli', 'sch', 'export', 'bom', '--group-by', '',
       '--fields', 'Reference,Value,Footprint,LCSC,MPN,${DNP}', '--labels', 'Reference,Value,Footprint,LCSC,MPN,DNP',
       '-o', out, sch)
    return {r['Reference']: r for r in csv.DictReader(open(out))}


def compress_refs(refs):
    def key(r):
        m = re.match(r'([A-Za-z#]+)(\d+)', r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)
    return ', '.join(sorted(refs, key=key))


def bom_diff(old, new, reasons, checks):
    groups = defaultdict(list)
    keys = ('Value', 'Footprint', 'MPN', 'LCSC', 'DNP')
    for r in sorted(set(old) | set(new)):
        o = tuple(old[r][k] for k in keys) if r in old else None
        n = tuple(new[r][k] for k in keys) if r in new else None
        if o != n:
            groups[(o, n)].append(r)
    rows = []
    for (o, n), refs in groups.items():
        def show(t):
            if t is None:
                return '—'
            v, fp, mpn, lcsc, dnp = t
            return '%s, %s%s%s%s' % (v, fp.split(':')[-1], ', ' + mpn if mpn else '', ', **' + lcsc + '**' if lcsc else '',
                                     ' (DNP)' if dnp else '')
        rs = [reasons[r] for r in refs if r in reasons]
        cs = [checks[r] for r in refs if r in checks]
        default = 'LCSC code added (JLC assembly)' if o and n and o[3] != n[3] and o[:3] == n[:3] else 'part change'
        rows.append((compress_refs(refs), show(o), show(n), '; '.join(dict.fromkeys(rs)) or default,
                     '; '.join(dict.fromkeys(cs)) or ('LCSC data checked' if n and n[3] else '—')))
    return rows


def bom_cost(b, parts, qty=5):
    cost, ext, basic, missing = 0.0, set(), set(), set()
    for r in b.values():
        if r['DNP'] or not r['LCSC'].startswith('C'):
            continue
        p = parts.get(r['LCSC'])
        if not p:
            missing.add(r['LCSC'])
            continue
        cost += p['price'] * qty
        (ext if p['type'] == 'extended' else basic).add(r['LCSC'])
    return cost, ext, basic, missing


def placement(bo, bn):
    of = {f.GetReference(): f for f in bo.GetFootprints()}
    nf = {f.GetReference(): f for f in bn.GetFootprints()}

    def d(f):
        return '%.2f, %.2f, %g°, %s, %s' % (f.GetPosition().x / 1e6, f.GetPosition().y / 1e6, f.GetOrientationDegrees(),
                                         'B' if f.IsFlipped() else 'F', f.GetFPIDAsString().split(':')[-1])
    rows = []
    for r in sorted(set(of) | set(nf)):
        a, b = of.get(r), nf.get(r)
        if a is None:
            rows.append((r, 'added', '—', d(b)))
        elif b is None:
            rows.append((r, 'removed', d(a), '—'))
        elif d(a) != d(b):
            rows.append((r, 'moved/changed', d(a), d(b)))
    return rows


def routing(bo, bn, nets):
    def stats(b):
        tl, vc = defaultdict(float), defaultdict(int)
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_VIA':
                vc[t.GetNetname()] += 1
            elif t.GetClass() in ('PCB_TRACK', 'PCB_ARC'):
                tl[t.GetNetname()] += t.GetLength() / 1e6
        n_tr = sum(1 for t in b.GetTracks() if t.GetClass() != 'PCB_VIA')
        return tl, vc, n_tr, sum(vc.values())
    to, vo, nto, nvo = stats(bo)
    tn, vn, ntn, nvn = stats(bn)
    rows = []
    for n in sorted(nets):
        if (round(to.get(n, 0), 1), vo.get(n, 0)) != (round(tn.get(n, 0), 1), vn.get(n, 0)):
            rows.append((n, '%.1f' % to.get(n, 0), '%.1f' % tn.get(n, 0), vo.get(n, 0), vn.get(n, 0)))
    return (nto, ntn, nvo, nvn), rows


# ---------------------------------------------------------------- images

def svg2png(svg, png, width):
    sh('rsvg-convert', '-w', str(width), '-b', 'white', '-o', png, svg)


def ink(img):
    g = img.convert('L')
    return g.point(lambda v: 255 if v < 235 else 0)


def diff_images(before, after, out_prefix, width):
    a, b = Image.open(before).convert('RGB'), Image.open(after).convert('RGB')
    if a.size != b.size:
        b = b.resize(a.size)
    ia, ib = ink(a), ink(b)
    changed = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 40 else 0)
    removed = ImageChops.multiply(ia, ImageChops.invert(ib))
    added = ImageChops.multiply(ib, ImageChops.invert(ia))
    recolored = ImageChops.multiply(changed, ImageChops.multiply(ia, ib))
    base = Image.blend(Image.new('RGB', a.size, 'white'), a.convert('L').convert('RGB'), 0.35)
    base.paste((220, 30, 30), mask=removed)
    base.paste((20, 160, 40), mask=added)
    base.paste((30, 90, 230), mask=recolored)
    base.save(out_prefix + '_diff.png')
    mask = ImageChops.lighter(ImageChops.lighter(removed, added), recolored)
    return regions(mask), a.size


def regions(mask, block=12, pad=50, maxn=8):
    w, h = mask.size
    sw, shh = (w + block - 1) // block, (h + block - 1) // block
    small = mask.resize((sw, shh), Image.BOX).load()
    seen, boxes = set(), []
    for y in range(shh):
        for x in range(sw):
            if small[x, y] > 8 and (x, y) not in seen:
                stack, pts = [(x, y)], []
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    pts.append((cx, cy))
                    for nx in range(cx - 3, cx + 4):
                        for ny in range(cy - 3, cy + 4):
                            if 0 <= nx < sw and 0 <= ny < shh and (nx, ny) not in seen and small[nx, ny] > 8:
                                seen.add((nx, ny))
                                stack.append((nx, ny))
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                boxes.append([min(xs) * block - pad, min(ys) * block - pad, (max(xs) + 1) * block + pad,
                              (max(ys) + 1) * block + pad])
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    boxes = [[max(0, b[0]), max(0, b[1]), min(w, b[2]), min(h, b[3])] for b in boxes]
    boxes.sort(key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
    return boxes[:maxn]


def crops(before, after, diff, boxes, out_prefix, labels):
    imgs = [Image.open(p).convert('RGB') for p in (before, after, diff)]
    font = ImageFont.load_default()
    files = []
    for i, b in enumerate(boxes):
        parts = [im.crop(tuple(b)) for im in imgs]
        scale = max(1.0, 420.0 / max(1, parts[0].height))
        parts = [p.resize((int(p.width * scale), int(p.height * scale))) for p in parts]
        W = sum(p.width for p in parts) + 40
        H = parts[0].height + 26
        canvas = Image.new('RGB', (W, H), 'white')
        d = ImageDraw.Draw(canvas)
        x = 10
        for p, t in zip(parts, ('before', 'after', 'diff (red removed, green added, blue changed)')):
            canvas.paste(p, (x, 22))
            d.text((x, 4), t, fill='black', font=font)
            x += p.width + 10
        f = '%s_crop%d.png' % (out_prefix, i + 1)
        canvas.save(f)
        files.append((f, labels(b)))
    return files


def sch_symbols(sch):
    out = []
    txt = open(sch).read()
    for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]*"\)\n\t\t\(at ([-\d.]+) ([-\d.]+)[^\n]*\n(.*?)\n\t\)', txt, re.S):
        r = re.search(r'\(property "Reference" "([^"#][^"]*)"', m.group(3))
        if r:
            out.append((r.group(1), float(m.group(1)), float(m.group(2))))
    return out


def side_by_side(files, out, titles):
    ims = [Image.open(f).convert('RGB') for f in files]
    h = max(i.height for i in ims)
    canvas = Image.new('RGB', (sum(i.width for i in ims) + 10 * (len(ims) + 1), h + 24), 'white')
    d = ImageDraw.Draw(canvas)
    x = 10
    for im, t in zip(ims, titles):
        canvas.paste(im, (x, 22))
        d.text((x, 4), t, fill='black', font=ImageFont.load_default())
        x += im.width + 10
    canvas.save(out)


def localize_models(pcb, outdir):
    """Same-named copy of board + project in outdir (keeps text variables), with ${KICADn_3DMODEL_DIR} and
    ${KIPRJMOD} resolved to absolute paths so kicad-cli renders every model. Returns the board copy path."""
    src = os.path.dirname(os.path.abspath(pcb))
    os.makedirs(outdir, exist_ok=True)
    txt = re.sub(r'\$\{KICAD\d+_3DMODEL_DIR\}', MODELS, open(pcb).read()).replace('${KIPRJMOD}', src)
    out = os.path.join(outdir, os.path.basename(pcb))
    open(out, 'w').write(txt)
    pro = pcb[:-len('.kicad_pcb')] + '.kicad_pro'
    if os.path.exists(pro):
        shutil.copy(pro, out[:-len('.kicad_pcb')] + '.kicad_pro')
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--branch', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--md', required=True)
    ap.add_argument('--reasons', default=None)
    ap.add_argument('projects', nargs='+')
    a = ap.parse_args()
    cfg = json.load(open(a.reasons)) if a.reasons else {}
    parts = json.load(open(os.path.join(os.path.dirname(__file__), 'lcsc_parts.json')))
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    url = '%s/%s/%s' % (REPO_URL, a.branch, a.out)
    sec = {'nets': [], 'bom': [], 'place': [], 'img': []}
    for proj in a.projects:
        name = os.path.basename(proj)
        pdir = os.path.dirname(proj)
        reasons = cfg.get(name, {}).get('reasons', {})
        checks = cfg.get(name, {}).get('datasheet', {})
        # baseline project tree
        bdir = os.path.join(tmp, 'base')
        os.makedirs(bdir, exist_ok=True)
        arch = subprocess.run(['git', 'archive', a.base, pdir], check=True, capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', bdir], input=arch, check=True)
        base = os.path.join(bdir, proj)
        for k in sec:
            sec[k].append('#### %s\n' % name)
        md = sec['nets']

        # 3. nets
        on, nn = netlist(base + '.kicad_sch', tmp, name + '_base'), netlist(proj + '.kicad_sch', tmp, name + '_head')
        rows, raw = net_diff(on, nn, reasons)
        if rows:
            md.append('| Net | Change | Old pins | New pins / delta | Reason |\n|---|---|---|---|---|')
            md += ['| `%s` | %s | %s | %s | %s |' % r for r in rows]
        else:
            md.append('No net changes.')
        md.append('\n<details><summary>Raw netlist diff (%d lines)</summary>\n\n```diff\n%s\n```\n</details>\n' % (
            len(raw), '\n'.join(raw) if raw else '(identical)'))
        bo, bn = pcbnew.LoadBoard(base + '.kicad_pcb'), pcbnew.LoadBoard(proj + '.kicad_pcb')
        changed_nets = {r[0].split(' → ')[-1] for r in rows} | {r[0].split(' → ')[0] for r in rows}
        (nto, ntn, nvo, nvn), rrows = routing(bo, bn, changed_nets | {n.GetNetname() for n in []})
        md.append('**Routing:** tracks %d → %d (%+d), vias %d → %d (%+d).\n' % (nto, ntn, ntn - nto, nvo, nvn, nvn - nvo))
        if rrows:
            md.append('| Changed net | Track length before (mm) | after (mm) | Vias before | after |\n|---|---|---|---|---|')
            md += ['| `%s` | %s | %s | %s | %s |' % r for r in rrows]
        md.append('')

        # 4. BOM
        md = sec['bom']
        ob, nbm = bom(base + '.kicad_sch', tmp, name + '_base'), bom(proj + '.kicad_sch', tmp, name + '_head')
        brows = bom_diff(ob, nbm, reasons, checks)
        co, eo, bso, mo = bom_cost(ob, parts)
        cn, en, bsn, mn = bom_cost(nbm, parts)
        if brows:
            md.append('| Refdes | Old (value, footprint, MPN, LCSC) | New | Reason | Datasheet check |\n|---|---|---|---|---|')
            md += ['| %s | %s | %s | %s | %s |' % r for r in brows]
        else:
            md.append('No BOM changes.')
        md.append('\nParts cost (LCSC unit prices × 5 boards, fitted parts): base %s → head **$%.2f**; '
                  'extended parts %s → **%d**, basic %s → %d%s.\n' % (
                      '$%.2f' % co if (eo or bso) else 'n/a (no LCSC codes)', cn,
                      len(eo) if (eo or bso) else 'n/a', len(en), len(bso) if (eo or bso) else 'n/a', len(bsn),
                      ('; unknown price: ' + ', '.join(sorted(mn))) if mn else ''))

        # 5. placement
        md = sec['place']
        prows = placement(bo, bn)
        if prows:
            md.append('| Refdes | Change | Old | New |\n|---|---|---|---|')
            md += ['| %s | %s | %s | %s |' % r for r in prows]
        else:
            md.append('No placement changes.')
        md.append('')

        # 6. images
        md = sec['img']
        img = lambda f: os.path.join(a.out, '%s_%s' % (name, f))
        # schematic
        for tag, src in (('before', base), ('after', proj)):
            d = os.path.join(tmp, 'sch_' + tag + name)
            sh('kicad-cli', 'sch', 'export', 'svg', '-o', d, src + '.kicad_sch')
            svg = [f for f in sorted(os.listdir(d)) if f.endswith('.svg')][0]
            svg2png(os.path.join(d, svg), img('sch_%s.png' % tag), 3000)
            vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', open(os.path.join(d, svg)).read()).group(1).split()]
        boxes, size = diff_images(img('sch_before.png'), img('sch_after.png'), img('sch'), 3000)
        syms = sch_symbols(proj + '.kicad_sch') + sch_symbols(base + '.kicad_sch')
        sx = size[0] / vb[2]

        def sch_label(b):
            refs = sorted({r for r, x, y in syms if b[0] <= (x - vb[0]) * sx <= b[2] and b[1] <= (y - vb[1]) * sx <= b[3]})
            hit = [reasons[r] for r in refs if r in reasons]
            return (', '.join(refs) or 'labels/wires') + (': ' + '; '.join(dict.fromkeys(hit)) if hit else '')
        sc = crops(img('sch_before.png'), img('sch_after.png'), img('sch_diff.png'), boxes, img('sch'), sch_label)
        md.append('**Schematic** ([before](%s/%s_sch_before.png) / after):\n\n![](%s/%s_sch_after.png)\n' % (url, name, url, name))
        md.append('**Schematic diff** (red removed, green added, blue changed): ![](%s/%s_sch_diff.png)\n' % (url, name))
        for f, lab in sc:
            md.append('*Schematic change: %s*\n\n![](%s/%s)\n' % (lab, url, os.path.basename(f)))
        # pcb layers
        # footprints that changed on the PCB: placement, reference text, or pad nets
        of_ = {f.GetReference(): f for f in bo.GetFootprints()}

        def pcb_sig(f):
            r = f.Reference()
            return (r.GetPosition().x, r.GetPosition().y, r.IsVisible(), r.GetTextHeight(),
                    tuple(sorted((p.GetNumber(), p.GetNetname()) for p in f.Pads())))
        pcb_changed = {r for r, *_ in prows} | {f.GetReference() for f in bn.GetFootprints()
                                               if f.GetReference() in of_ and pcb_sig(f) != pcb_sig(of_[f.GetReference()])}
        fps = [(f.GetReference(), f.GetPosition().x / 1e6, f.GetPosition().y / 1e6) for f in bn.GetFootprints()
               if f.GetReference() in pcb_changed] + \
              [(f.GetReference(), f.GetPosition().x / 1e6, f.GetPosition().y / 1e6) for f in bo.GetFootprints()
               if f.GetReference() in pcb_changed]
        # zone fills removed: refilled pours would otherwise mark the whole board as changed
        unfilled = {}
        for tag, src in (('before', base), ('after', proj)):
            d = os.path.join(tmp, 'unfilled_' + tag + name)
            os.makedirs(d, exist_ok=True)
            ub = pcbnew.LoadBoard(src + '.kicad_pcb')
            for z in ub.Zones():
                z.UnFill()
            unfilled[tag] = os.path.join(d, os.path.basename(src) + '.kicad_pcb')
            ub.Save(unfilled[tag])
            if os.path.exists(src + '.kicad_pro'):
                shutil.copy(src + '.kicad_pro', unfilled[tag][:-len('.kicad_pcb')] + '.kicad_pro')
        for side, layers in (('front', 'F.Cu,F.SilkS,Edge.Cuts'), ('back', 'B.Cu,B.SilkS,Edge.Cuts')):
            for tag in ('before', 'after'):
                svg = os.path.join(tmp, '%s_%s_%s.svg' % (name, side, tag))
                sh('kicad-cli', 'pcb', 'export', 'svg', '--mode-single', '--page-size-mode', '1', '--exclude-drawing-sheet',
                   '--layers', layers, '-o', svg, unfilled[tag])
                svg2png(svg, img('pcb_%s_%s_full.png' % (side, tag)), 3000)
                vbp = [float(v) for v in re.search(r'viewBox="([^"]+)"', open(svg).read()).group(1).split()]
            # crop both to the board area
            ebb = bn.GetBoardEdgesBoundingBox()
            s = 3000 / vbp[2]
            box = (int((ebb.GetLeft() / 1e6 - vbp[0] - 2) * s), int((ebb.GetTop() / 1e6 - vbp[1] - 2) * s),
                   int((ebb.GetRight() / 1e6 - vbp[0] + 2) * s), int((ebb.GetBottom() / 1e6 - vbp[1] + 2) * s))
            for tag in ('before', 'after'):
                full = img('pcb_%s_%s_full.png' % (side, tag))
                Image.open(full).crop(box).save(img('pcb_%s_%s.png' % (side, tag)))
                os.remove(full)
            boxes, _ = diff_images(img('pcb_%s_before.png' % side), img('pcb_%s_after.png' % side), img('pcb_' + side), 0)

            def pcb_label(b, box=box, s=s, vbp=vbp):
                refs = sorted({r for r, x, y in fps if b[0] <= (x - vbp[0]) * s - box[0] <= b[2]
                               and b[1] <= (y - vbp[1]) * s - box[1] <= b[3]})
                hit = [reasons[r] for r in refs if r in reasons]
                return (', '.join(refs) or 'board silkscreen texts / tracks') + (': ' + '; '.join(dict.fromkeys(hit)) if hit else '')
            pc = crops(img('pcb_%s_before.png' % side), img('pcb_%s_after.png' % side), img('pcb_%s_diff.png' % side),
                       boxes, img('pcb_' + side), pcb_label)
            md.append('**PCB %s (copper without pours + silk + edge): before | after | diff**\n' % side)
            md.append('| before | after | diff |\n|---|---|---|\n| ![](%s/%s_pcb_%s_before.png) | ![](%s/%s_pcb_%s_after.png) '
                      '| ![](%s/%s_pcb_%s_diff.png) |\n' % (url, name, side, url, name, side, url, name, side))
            for f, lab in pc:
                md.append('*PCB %s change: %s*\n\n![](%s/%s)\n' % (side, lab, url, os.path.basename(f)))
        # renders
        for tag, src in (('before', base), ('after', proj)):
            loc = localize_models(src + '.kicad_pcb', os.path.join(tmp, 'render_' + tag + name))
            for view, extra in (('top', ['--side', 'top']), ('bottom', ['--side', 'bottom']),
                                ('iso', ['--side', 'top', '--perspective', '--rotate', '-40,0,30', '--zoom', '0.9'])):
                sh('kicad-cli', 'pcb', 'render', *extra, '-w', '1600', '-h', '1000', '--quality', 'high',
                   '-o', img('render_%s_%s.png' % (view, tag)), loc)
        md.append('**3D renders**\n\n| view | before | after |\n|---|---|---|')
        for view in ('top', 'bottom', 'iso'):
            md.append('| %s | ![](%s/%s_render_%s_before.png) | ![](%s/%s_render_%s_after.png) |' % (
                view, url, name, view, url, name, view))
        md.append('')
    titles = {'nets': '### 3. Wiring / net diff (pin level, vs `%s`)' % a.base, 'bom': '### 4. BOM diff',
              'place': '### 5. Placement diff (x mm, y mm, rotation, side, footprint)',
              'img': '### 6. Images (schematic, PCB before/after/diff, 3D renders)'}
    out = []
    for k in ('nets', 'bom', 'place', 'img'):
        out.append(titles[k] + '\n')
        out += sec[k]
    open(a.md, 'w').write('\n'.join(out))
    shutil.rmtree(tmp, ignore_errors=True)
    print('wrote', a.md)


if __name__ == '__main__':
    main()
