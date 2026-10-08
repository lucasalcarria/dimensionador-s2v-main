# -*- coding: utf-8 -*-
"""Converte ícones de TRAÇO (SVG da Lucide — ISC —, da Tabler — MIT — e
desenhos próprios da marca) em operadores de desenho PDF e grava
`assets/icones_traco.json` (build-only).

Revisão de design B5: os ícones que destoavam da família de traço fino da
proposta (pilha de moedas e "%" da tabela da pág. 3; gráfico e calendário da
pág. 5; os sólidos das etapas e do cartão de projetos da pág. 4) são trocados
por ícones de traço na MESMA caixa do original, com a espessura de traço dos
vizinhos. A proposta lê o JSON e desenha (`proposta._icones_traco_pagina`);
ela não precisa deste script nem de internet.

    py ferramentas/icones_traco.py          # baixa os SVG e regrava o JSON

Sem dependências: o SVG é lido com xml.etree e os caminhos (inclusive arcos)
viram curvas de Bézier aqui mesmo. Coordenadas na grade do SVG (24 × 24, y para
baixo); quem desenha faz a escala e a inversão do eixo y.
"""
import json
import math
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'assets', 'icones_traco.json')
VERSAO = '0.469.0'
URL = 'https://cdn.jsdelivr.net/npm/lucide-static@{v}/icons/{n}.svg'
URL_TABLER = 'https://cdn.jsdelivr.net/npm/@tabler/icons@3.24.0/icons/outline/{n}.svg'

# Ícones PRÓPRIOS da marca, redesenhados em traço na mesma grade 24 × 24 (traço
# 2, pontas redondas) a partir dos ícones dos cartões da pág. 3, para conviver
# com a Lucide: painel = sol em meio-círculo com raios sobre um painel em
# perspectiva de 3 × 2 células; inversor = quadrado arredondado com a diagonal,
# a senoide (CA) e o "=" tracejado (CC).
MARCA = {
    'modulo': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M7.5 10.5a4.5 4.5 0 0 1 9 0"/>
      <path d="M12 3.2v1.6M6.6 5.4l1.1 1.1M17.4 5.4l-1.1 1.1M4.6 10.5h1.5M17.9 10.5h1.5"/>
      <path d="M6.2 12.8h11.6l3.4 7.6H2.8z"/>
      <path d="M10.1 12.8l-0.7 7.6M13.9 12.8l0.7 7.6M4.5 16.6h15"/>
    </svg>""",
    # drone visto de lado (proporção ~0,8, não achatado), como o ícone
    # original da etapa "visita técnica" (o
    # da Tabler é visto de cima e vira um "X" abstrato no tamanho da proposta)
    'drone': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M1.5 3.5h8M14.5 3.5h8"/>
      <path d="M5.5 3.5v4M18.5 3.5v4M5.5 7.5h13"/>
      <rect x="8" y="7.5" width="8" height="6" rx="2"/>
      <path d="M9.2 13.5l-1.8 7M14.8 13.5l1.8 7"/>
      <rect x="10.3" y="13.5" width="3.4" height="4.5" rx="1"/>
    </svg>""",
    # torre de transmissão em treliça (rede da concessionária)
    'torre': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M12 2.5L7.5 21.5M12 2.5l4.5 19"/>
      <path d="M4.5 6.5h15M6.5 10.5h11M8.9 14.5h6.2"/>
      <path d="M4.5 6.5V8M19.5 6.5V8M6.5 10.5V12M17.5 10.5V12"/>
      <path d="M11 6.5l3.1 4M13 6.5l-3.1 4M9.9 10.5l5.2 4M14.1 10.5l-5.2 4M8.9 14.5l7.3 7M15.1 14.5l-7.3 7"/>
    </svg>""",
    # bateria em pé com raio (como a do diagrama e dos cartões); larga o
    # bastante (14 × 18) para não destoar dos vizinhos quase quadrados
    'bateria': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <rect x="5" y="4" width="14" height="18" rx="2.2"/>
      <path d="M9.5 2h5"/>
      <path d="M13 8l-3.2 5.2h4.4L11 18.5"/>
    </svg>""",
    # string box: quadro com o triângulo de alerta e os bornes
    'stringbox': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <rect x="4.5" y="2.5" width="15" height="17" rx="2"/>
      <path d="M12 5.8l3.2 5.4H8.8z"/>
      <path d="M8.5 14.5h.01M12 14.5h.01M15.5 14.5h.01M8.5 17h.01M12 17h.01M15.5 17h.01"/>
      <path d="M8 19.5v2M16 19.5v2"/>
    </svg>""",
    # garantia de performance linear: eixos + linha DESCENDO com seta
    'degradacao': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M3 3v18h18"/>
      <path d="M7 8l4 4 3-2 5 5"/>
      <path d="M19 11v4h-4"/>
    </svg>""",
    'inversor': """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <rect x="3" y="3" width="18" height="18" rx="2.5"/>
      <path d="M3.8 20.2L20.2 3.8"/>
      <path d="M6 8.2c1-1.5 2-1.5 3 0s2 1.5 3 0"/>
      <path d="M13.5 15.2h4.5M13.5 17.8h1.6M16.4 17.8h1.6"/>
    </svg>""",
}

# nome na proposta -> origem ('lucide:…', 'tabler:…' ou 'marca:…')
ICONES = {
    # pág. 3 e 5 (1º grupo do B5)
    'geracao': 'lucide:zap',                  # era a pilha de moedas
    'porcento': 'lucide:percent',
    'grafico': 'lucide:chart-no-axes-combined',
    'calendario': 'lucide:calendar-days',
    # pág. 4, etapas do projeto (eram sólidos)
    'drone': 'marca:drone',                   # a Lucide não tem; o da Tabler é visto de cima
    'contrato': 'lucide:file-pen-line',
    'projeto': 'lucide:monitor-cog',
    'homologacao': 'lucide:clipboard-list',
    'instalacao': 'lucide:hard-hat',
    'vistoria': 'lucide:arrow-right-left',
    'modulo': 'marca:modulo',
    # pág. 4, cartão de projetos realizados
    'local': 'lucide:map-pin',
    'inversor': 'marca:inversor',
    # padronização geral (todas as páginas na mesma família)
    'cliente': 'lucide:user',
    'uc': 'lucide:square-user',
    'escudo': 'lucide:shield-check',
    'folha': 'lucide:leaf',
    'casa': 'lucide:house',
    'conta': 'lucide:receipt-text',
    'sol': 'lucide:sun',
    'area': 'lucide:triangle-right',
    'furadeira': 'lucide:drill',
    'relogio': 'lucide:clock',
    'instagram': 'lucide:instagram',
    'email': 'lucide:mail',
    'whatsapp': 'tabler:brand-whatsapp',      # a Lucide não tem marcas
    'torre': 'marca:torre',
    'bateria': 'marca:bateria',
    'stringbox': 'marca:stringbox',
    'degradacao': 'marca:degradacao',
}


def _f(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.')


def _arco(x1, y1, rx, ry, fi, fa, fs, x2, y2):
    """Arco elíptico do SVG -> lista de Béziers cúbicas [(c1x,c1y,c2x,c2y,x,y)]."""
    if rx == 0 or ry == 0:
        return [(x1, y1, x2, y2, x2, y2)]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(fi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(num / den, 0)) * (-1 if fa == fs else 1)
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    n = max(1, math.ceil(abs(dt) / (math.pi / 2)))
    d = dt / n
    k = 4 / 3 * math.tan(d / 4)
    out = []
    for i in range(n):
        a1, a2 = t1 + i * d, t1 + (i + 1) * d

        def pt(a):
            ex, ey = rx * math.cos(a), ry * math.sin(a)
            return cp * ex - sp * ey + cx, sp * ex + cp * ey + cy

        def dv(a):
            ex, ey = -rx * math.sin(a), ry * math.cos(a)
            return cp * ex - sp * ey, sp * ex + cp * ey
        p1, p2 = pt(a1), pt(a2)
        d1, d2 = dv(a1), dv(a2)
        out.append((p1[0] + k * d1[0], p1[1] + k * d1[1],
                    p2[0] - k * d2[0], p2[1] - k * d2[1], p2[0], p2[1]))
    return out


def _caminho(d: str) -> str:
    """Atributo `d` de um <path> SVG -> operadores PDF (m/l/c/h)."""
    toks = re.findall(r'[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    ultc = None                     # último ponto de controle (S/T)
    ops = []

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v
    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in 'Zz':
                ops.append('h')
                x, y = sx, sy
                ultc = None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if C == 'M':
            x, y = ox + num(), oy + num()
            sx, sy = x, y
            ops.append(f'{_f(x)} {_f(y)} m')
            cmd = 'l' if rel else 'L'       # pares seguintes são linhas
            ultc = None
        elif C == 'L':
            x, y = ox + num(), oy + num()
            ops.append(f'{_f(x)} {_f(y)} l')
            ultc = None
        elif C == 'H':
            x = (x if rel else 0) + num()
            ops.append(f'{_f(x)} {_f(y)} l')
            ultc = None
        elif C == 'V':
            y = (y if rel else 0) + num()
            ops.append(f'{_f(x)} {_f(y)} l')
            ultc = None
        elif C == 'C':
            c1x, c1y = ox + num(), oy + num()
            c2x, c2y = ox + num(), oy + num()
            x, y = ox + num(), oy + num()
            ops.append(' '.join(_f(v) for v in (c1x, c1y, c2x, c2y, x, y)) + ' c')
            ultc = (c2x, c2y)
        elif C == 'S':
            c1x, c1y = (2 * x - ultc[0], 2 * y - ultc[1]) if ultc else (x, y)
            c2x, c2y = ox + num(), oy + num()
            x, y = ox + num(), oy + num()
            ops.append(' '.join(_f(v) for v in (c1x, c1y, c2x, c2y, x, y)) + ' c')
            ultc = (c2x, c2y)
        elif C in 'QT':
            if C == 'Q':
                qx, qy = ox + num(), oy + num()
            else:
                qx, qy = (2 * x - ultc[0], 2 * y - ultc[1]) if ultc else (x, y)
            nx, ny = ox + num(), oy + num()
            c1 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
            c2 = (nx + 2 / 3 * (qx - nx), ny + 2 / 3 * (qy - ny))
            x, y = nx, ny
            ops.append(' '.join(_f(v) for v in (*c1, *c2, x, y)) + ' c')
            ultc = (qx, qy)
        elif C == 'A':
            rx, ry, fi = num(), num(), num()
            fa, fs = int(num()), int(num())
            nx, ny = ox + num(), oy + num()
            for b in _arco(x, y, rx, ry, fi, fa, fs, nx, ny):
                ops.append(' '.join(_f(v) for v in b) + ' c')
            x, y = nx, ny
            ultc = None
        else:
            raise ValueError(f'comando SVG não tratado: {cmd}')
    return '\n'.join(ops)


def _elemento(el) -> str:
    tag = el.tag.split('}')[-1]
    g = lambda k, p=0.0: float(el.get(k, p))             # noqa: E731
    if tag == 'path':
        return _caminho(el.get('d'))
    if tag == 'line':
        return f"{_f(g('x1'))} {_f(g('y1'))} m\n{_f(g('x2'))} {_f(g('y2'))} l"
    if tag in ('polyline', 'polygon'):
        v = [float(t) for t in re.findall(r'-?[\d.]+', el.get('points'))]
        s = f'{_f(v[0])} {_f(v[1])} m\n' + '\n'.join(
            f'{_f(v[k])} {_f(v[k + 1])} l' for k in range(2, len(v), 2))
        return s + ('\nh' if tag == 'polygon' else '')
    if tag in ('circle', 'ellipse'):
        cx, cy = g('cx'), g('cy')
        rx = g('r') if tag == 'circle' else g('rx')
        ry = g('r') if tag == 'circle' else g('ry')
        return _caminho(f'M{cx + rx} {cy}A{rx} {ry} 0 1 1 {cx - rx} {cy}'
                        f'A{rx} {ry} 0 1 1 {cx + rx} {cy}Z')
    if tag == 'rect':
        x, y, w, h = g('x'), g('y'), g('width'), g('height')
        r = min(g('rx', g('ry')), w / 2, h / 2)
        if not r:
            return _caminho(f'M{x} {y}h{w}v{h}h{-w}Z')
        return _caminho(f'M{x + r} {y}h{w - 2 * r}a{r} {r} 0 0 1 {r} {r}'
                        f'v{h - 2 * r}a{r} {r} 0 0 1 {-r} {r}h{-(w - 2 * r)}'
                        f'a{r} {r} 0 0 1 {-r} {-r}v{-(h - 2 * r)}'
                        f'a{r} {r} 0 0 1 {r} {-r}Z')
    return ''


def _limites(ops: str):
    """Caixa EXATA (x0, y0, x1, y1) do desenho, na grade: as curvas são
    percorridas ponto a ponto (os pontos de controle de uma Bézier ficam fora
    da curva e inflariam a caixa). É a extensão do traço pelo seu eixo; quem
    desenha soma a espessura do traço para chegar à tinta visível."""
    xs, ys = [], []
    px = py = 0.0
    for linha in ops.split('\n'):
        partes = linha.split()
        if not partes:
            continue
        op, v = partes[-1], [float(a) for a in partes[:-1]]
        if op in ('m', 'l'):
            px, py = v[0], v[1]
            xs.append(px); ys.append(py)
        elif op == 'c':
            x1, y1, x2, y2, x3, y3 = v
            for i in range(1, 33):
                t = i / 32.0
                a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
                xs.append(a * px + b * x1 + c * x2 + d * x3)
                ys.append(a * py + b * y1 + c * y2 + d * y3)
            px, py = x3, y3
    return [min(xs), min(ys), max(xs), max(ys)]


def _silhueta(ops: str) -> float:
    """Área (na grade) da SILHUETA do desenho: o polígono convexo que um
    elástico esticado em volta dele formaria. É o que o olho lê como tamanho:
    uma moldura quadrada preenche o seu retângulo, uma "pessoa" deixa vazios."""
    pts = []
    px = py = 0.0
    for linha in ops.split('\n'):
        partes = linha.split()
        if not partes:
            continue
        op, v = partes[-1], [float(a) for a in partes[:-1]]
        if op in ('m', 'l'):
            px, py = v[0], v[1]
            pts.append((px, py))
        elif op == 'c':
            x1, y1, x2, y2, x3, y3 = v
            for i in range(1, 17):
                t = i / 16.0
                a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
                pts.append((a * px + b * x1 + c * x2 + d * x3,
                            a * py + b * y1 + c * y2 + d * y3))
            px, py = x3, y3
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in pts))
    if len(pts) < 3:
        return 0.0

    def giro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    baixo, cima = [], []
    for q in pts:                                   # casco convexo (Andrew)
        while len(baixo) >= 2 and giro(baixo[-2], baixo[-1], q) <= 0:
            baixo.pop()
        baixo.append(q)
    for q in reversed(pts):
        while len(cima) >= 2 and giro(cima[-2], cima[-1], q) <= 0:
            cima.pop()
        cima.append(q)
    casco = baixo[:-1] + cima[:-1]
    return abs(sum(casco[i][0] * casco[i - 1][1] - casco[i - 1][0] * casco[i][1]
                   for i in range(len(casco)))) / 2.0


def main():
    saida = {'_fonte': f'Lucide v{VERSAO} (ISC), Tabler 3.24 (MIT) e desenhos '
                       f'da marca — gerado por ferramentas/icones_traco.py; '
                       f'não editar à mão'}
    for nome, origem in ICONES.items():
        fonte, n = origem.split(':', 1)
        if fonte == 'marca':
            raiz = ET.fromstring(MARCA[n])
        else:
            url = (URL if fonte == 'lucide' else URL_TABLER).format(v=VERSAO, n=n)
            with urllib.request.urlopen(url, timeout=20) as r:
                raiz = ET.fromstring(r.read())
        # o Tabler traz um retângulo "invisível" de 24 × 24 (stroke="none")
        partes = [_elemento(el) for el in raiz.iter()
                  if el is not raiz and el.get('stroke') != 'none'
                  and el.tag.split('}')[-1] != 'title']
        ops = '\n'.join(p for p in partes if p)
        saida[nome] = {'origem': origem, 'grade': 24, 'ops': ops,
                       'limites': [round(v, 3) for v in _limites(ops)],
                       'silhueta': round(_silhueta(ops), 2)}
        print(f'{nome:12s} <- {origem:32s} limites {saida[nome]["limites"]}')
    with open(SAIDA, 'w', encoding='utf-8') as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print('gravado', os.path.relpath(SAIDA, RAIZ))


if __name__ == '__main__':
    main()
