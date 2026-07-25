#!/usr/bin/env python3
"""Converte o HTML da proposta (layout entregue pelo design) em:

  assets/fundo.pdf    — arte vetorial + todos os textos FIXOS das 5 páginas
  assets/layout.json  — onde o programa escreve cada valor calculado
  assets/fonts/JetBrainsMono-*.ttf — fontes extraídas do próprio HTML

É uma ferramenta de BUILD: só precisa rodar quando chega um HTML novo.
O programa do dia a dia (`proposta.py`) usa apenas os arquivos gerados.

    python ferramentas/html_para_fundo.py ~/Downloads/proposta_s2v.html

Por que HTML e não um PDF pronto: o HTML traz as coordenadas exatas de cada
texto e cada desenho, então dá para separar o que é fundo (fixo) do que é
valor calculado (dinâmico) — que é justamente o que o programa preenche.
"""
import base64
import html as _html
import io
import json
import os
import re
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(RAIZ, 'assets')
FONTES_DIR = os.path.join(ASSETS, 'fonts')

# o HTML desenha a página em pixels de tela; o PDF trabalha em pontos
PX_POR_PT = 794 / 595.32
PAGINA = (595.32, 841.92)

# nome da fonte no HTML -> arquivo .ttf em assets/fonts
ARQ_FONTE = {
    ('Sora', False): 'Sora-Regular',
    ('Sora', True): 'Sora-Bold',
    ('Inter', False): 'Inter-Regular',
    ('Inter', True): 'Inter-Bold',
    ('JetBrains Mono', False): 'JetBrainsMono-Regular',
    ('JetBrains Mono', True): 'JetBrainsMono-Bold',
}

# Onde fica a linha de base do texto dentro da caixa do CSS.
# Regra do navegador com `line-height:1`:
#     base = topo + [ (1 − (asc+desc)/upem) / 2 + asc/upem ] × tamanho
# Os números abaixo saem das métricas das próprias fontes embutidas no HTML.
K_BASE = {'Sora': 0.84000, 'Inter': 0.86377, 'JetBrains Mono': 0.86000}


# --------------------------------------------------------------- fontes
def _extrair_fontes_do_html(bruto: str) -> None:
    """Salva a JetBrains Mono (que o projeto ainda não tinha) como .ttf."""
    faltando = [n for (f, b), n in ARQ_FONTE.items()
                if not os.path.exists(os.path.join(FONTES_DIR, n + '.ttf'))]
    if not faltando:
        return
    from fontTools.ttLib import TTFont as FTFont
    from fontTools.varLib import instancer
    achadas = re.findall(
        r"@font-face\{font-family:'([^']+)';src:url\(data:font/woff2;base64,"
        r"([^)]+)\)", bruto)
    for familia, b64 in achadas:
        for negrito, peso in ((False, 400), (True, 700)):
            nome = ARQ_FONTE.get((familia, negrito))
            if not nome or nome not in faltando:
                continue
            f = FTFont(io.BytesIO(base64.b64decode(b64)))
            if 'fvar' in f:
                f = instancer.instantiateVariableFont(f, {'wght': peso})
            f.flavor = None
            destino = os.path.join(FONTES_DIR, nome + '.ttf')
            f.save(destino)
            print(f'  fonte gerada: {os.path.basename(destino)}')


def _registrar_fontes() -> None:
    for nome in set(ARQ_FONTE.values()):
        pdfmetrics.registerFont(
            TTFont(nome, os.path.join(FONTES_DIR, nome + '.ttf')))


def _fonte(familia: str, negrito: bool) -> str:
    return ARQ_FONTE[(familia, negrito)]


# ------------------------------------------------------------ leitura do HTML
def _estilo(css: str) -> dict:
    d = {}
    m = re.search(r"font-family:'([^']+)'", css)
    if m:
        d['fam'] = m.group(1)
    m = re.search(r'font-weight:(\d+)', css)
    if m:
        d['bold'] = int(m.group(1)) >= 600
    m = re.search(r'font-size:([\d.]+)px', css)
    if m:
        d['fs'] = float(m.group(1))
    m = re.search(r'color:(#[0-9A-Fa-f]{6})', css)
    if m:
        d['cor'] = m.group(1)
    return d


def _texto_puro(frag: str) -> str:
    return _html.unescape(re.sub(r'<[^>]+>', '', frag))


def ler_paginas(caminho: str) -> list[dict]:
    """Devolve, por página: o SVG da arte e a lista de trechos de texto."""
    bruto = open(caminho, encoding='utf-8').read()
    _extrair_fontes_do_html(bruto)
    paginas = []
    for pedaco in re.split(r'<div class="page"', bruto)[1:]:
        svg = re.search(r'(?s)<svg.*?</svg>', pedaco).group(0)
        blocos = []
        for m in re.finditer(r'(?s)<div class="t" style="([^"]*)">(.*?)</div>',
                             pedaco):
            css, conteudo = m.group(1), m.group(2)
            base_est = _estilo(css)
            esq = float(re.search(r'left:([\d.]+)px', css).group(1))
            topo = float(re.search(r'top:([\d.]+)px', css).group(1))
            trechos = []
            if '<span' in conteudo:
                for sm in re.finditer(r'(?s)<span style="([^"]*)">(.*?)</span>',
                                      conteudo):
                    est = dict(base_est)
                    est.update(_estilo(sm.group(1)))
                    trechos.append((_texto_puro(sm.group(2)), est))
            else:
                trechos.append((_texto_puro(conteudo), base_est))
            trechos = [(t, e) for t, e in trechos if t.strip()]
            if not trechos:
                continue
            # a linha de base é a mesma para todos os trechos da linha
            alturas = [K_BASE[e['fam']] * e['fs'] for _, e in trechos]
            alturas.append(K_BASE[base_est['fam']] * base_est['fs'])
            blocos.append({'x': esq / PX_POR_PT,
                           'base': (topo + max(alturas)) / PX_POR_PT,
                           'topo': topo / PX_POR_PT,
                           'trechos': [(t, {'fam': e['fam'], 'bold': e['bold'],
                                            'fs': e['fs'] / PX_POR_PT,
                                            'cor': e.get('cor', '#000000')})
                                       for t, e in trechos]})
        paginas.append({'svg': svg, 'blocos': blocos})
    return paginas


# ------------------------------------------------------------- desenho do SVG
_NUM = re.compile(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?')


def _transforma(attrs: str):
    """Só aparece `translate(a,b) scale(s)` neste HTML."""
    m = re.search(r'transform="([^"]*)"', attrs)
    if not m:
        return 0.0, 0.0, 1.0
    t = re.search(r'translate\(([-\d.]+),([-\d.]+)\)', m.group(1))
    s = re.search(r'scale\(([-\d.]+)\)', m.group(1))
    return (float(t.group(1)) if t else 0.0,
            float(t.group(2)) if t else 0.0,
            float(s.group(1)) if s else 1.0)


def _attr(attrs: str, nome: str, padrao=None):
    m = re.search(rf'\b{nome}="([^"]*)"', attrs)
    return m.group(1) if m else padrao


def _cor(v):
    return None if v in (None, 'none', '') or v.startswith('url(') else HexColor(v)


# Vários ícones vieram no HTML como imagens de 48 px mostradas em ~38 pt, ou
# seja ~90 dpi: na tela e no papel a borda vira escadinha. Não dá para inventar
# detalhe que não existe, mas dá para reamostrar com um filtro bom, trocando o
# degrau duro por uma transição suave. Acima deste limite a imagem já está boa.
DPI_MINIMO = 220
DPI_ALVO = 600
# só vale para ícone: foto reamostrada não fica melhor e faz o PDF explodir
ICONE_MAX_PX = 128
ICONE_MAX_PT = 60


def _tinta_do_elemento(tag: str, attrs: str):
    """Área realmente pintada por um elemento, em pontos da página."""
    tx, ty, esc = _transforma(attrs)

    def pg(x0, y0, x1, y1):
        return (tx + esc * x0, ty + esc * y0, tx + esc * x1, ty + esc * y1)

    if tag == 'image':
        x = float(_attr(attrs, 'x', '0'))
        y = float(_attr(attrs, 'y', '0'))
        w = float(_attr(attrs, 'width', '0'))
        h = float(_attr(attrs, 'height', '0'))
        dados = base64.b64decode(_attr(attrs, 'href', '').split(',', 1)[1])
        return _tinta_da_imagem(dados, pg(x, y, x + w, y + h))
    if tag == 'path':
        subs = _pontos_do_path(_attr(attrs, 'd', ''))
        pts = [s['ini'] for s in subs] + [p if k == 'L' else p[2]
                                          for s in subs for k, p in s['seg']]
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return pg(min(xs), min(ys), max(xs), max(ys))
    if tag == 'circle':
        cx = float(_attr(attrs, 'cx', '0'))
        cy = float(_attr(attrs, 'cy', '0'))
        r = float(_attr(attrs, 'r', '0'))
        return pg(cx - r, cy - r, cx + r, cy + r)
    return None


def medir_icone(svg: str, zona) -> tuple | None:
    """Junta a tinta de TODOS os elementos do ícone (ele costuma ser vários
    traços) e devolve a área que o olho enxerga: primeiro pixel colorido à
    esquerda, à direita, em cima e embaixo. O branco em volta não conta."""
    zx0, zy0, zx1, zy1 = zona
    caixas = []
    for m in re.finditer(r'<(path|image|circle)\b([^>]*?)/?>', svg):
        b = _tinta_do_elemento(m.group(1), m.group(2))
        if not b:
            continue
        mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if zx0 <= mx <= zx1 and zy0 <= my <= zy1:
            caixas.append(b)
    if not caixas:
        return None
    return (min(b[0] for b in caixas), min(b[1] for b in caixas),
            max(b[2] for b in caixas), max(b[3] for b in caixas))


def _tinta_da_imagem(dados: bytes, caixa) -> tuple:
    """Recorta a caixa da imagem até o primeiro pixel colorido de cada lado —
    esquerda, direita, cima e baixo. O cruzamento das duas linhas do meio é o
    centro real do ícone; o branco (ou o transparente) em volta não conta.
    Devolve em pontos da página."""
    from PIL import Image
    x0, y0, x1, y1 = caixa
    img = Image.open(io.BytesIO(dados)).convert('RGBA')
    alfa = img.split()[-1]
    bb = alfa.getbbox()
    if bb and bb == (0, 0, img.width, img.height):
        # imagem sem transparência: o que sobra é o branco de fundo
        cinza = img.convert('L').point(lambda v: 255 if v < 245 else 0)
        bb = cinza.getbbox() or bb
    if not bb:
        return caixa
    w, h = x1 - x0, y1 - y0
    return (x0 + bb[0] / img.width * w, y0 + bb[1] / img.height * h,
            x0 + bb[2] / img.width * w, y0 + bb[3] / img.height * h)


def _suavizar(dados: bytes, larg_pt: float) -> bytes:
    """Reamostra ícones de baixa resolução para tirar o serrilhado."""
    from PIL import Image
    if not 0 < larg_pt <= ICONE_MAX_PT:
        return dados
    img = Image.open(io.BytesIO(dados))
    dpi = img.width / (larg_pt / 72.0)
    if dpi >= DPI_MINIMO or max(img.size) > ICONE_MAX_PX:
        return dados
    fator = min(8, max(2, round(DPI_ALVO / dpi)))
    img = img.convert('RGBA').resize(
        (img.width * fator, img.height * fator), Image.LANCZOS)
    saida = io.BytesIO()
    img.save(saida, 'PNG')
    return saida.getvalue()


def _pontos_do_path(d: str):
    """Converte o atributo `d` em uma lista de subcaminhos de pontos.
    Este HTML usa só M, L, C, H, V e Z — todos absolutos."""
    subs, atual, pos = [], None, (0.0, 0.0)
    for cmd, corpo in re.findall(r'([MLCHVZmlchvz])([^MLCHVZmlchvz]*)', d):
        n = [float(x) for x in _NUM.findall(corpo)]
        c = cmd.upper()
        if c == 'M':
            for i in range(0, len(n), 2):
                pos = (n[i], n[i + 1])
                if i == 0:
                    if atual:
                        subs.append(atual)
                    atual = {'ini': pos, 'seg': [], 'fecha': False}
                else:
                    atual['seg'].append(('L', pos))
        elif c == 'L':
            for i in range(0, len(n), 2):
                pos = (n[i], n[i + 1])
                atual['seg'].append(('L', pos))
        elif c == 'H':
            for x in n:
                pos = (x, pos[1])
                atual['seg'].append(('L', pos))
        elif c == 'V':
            for y in n:
                pos = (pos[0], y)
                atual['seg'].append(('L', pos))
        elif c == 'C':
            for i in range(0, len(n), 6):
                p = ((n[i], n[i + 1]), (n[i + 2], n[i + 3]), (n[i + 4], n[i + 5]))
                pos = p[2]
                atual['seg'].append(('C', p))
        elif c == 'Z':
            if atual:
                atual['fecha'] = True
                subs.append(atual)
                pos = atual['ini']
                atual = None
    if atual:
        subs.append(atual)
    return subs


def desenhar_svg(c, svg: str, pular=lambda tag, attrs, bbox: False,
                 origem=(0.0, 0.0), tamanho=None, ajustes=()) -> None:
    """Redesenha a arte da página no canvas. `pular` filtra elementos.

    `origem`/`tamanho` permitem recortar um pedaço da página (usado para tirar
    cada cartão da pág. 3 em separado, já que eles se reagrupam).
    `ajustes` reduz/aumenta ícones específicos sem sair do lugar (ver AJUSTES)."""
    ox, oy = origem
    _, alt = tamanho or PAGINA

    def y(v):
        return alt - (v - oy)

    def ajuste_de(tinta):
        """Escala, pivô e deslocamento a aplicar num elemento.

        Tudo é medido pela TINTA (o primeiro pixel colorido de cada lado), não
        pela caixa do arquivo: vários PNGs têm margem transparente, e usar a
        caixa deixava o ícone visualmente torto. A escala gira em torno do
        centro da tinta — assim o ícone encolhe sem sair do lugar — e
        `centro_x`/`centro_y`, quando existem, levam esse centro ao alvo."""
        mx, my = (tinta[0] + tinta[2]) / 2, (tinta[1] + tinta[3]) / 2
        for a in ajustes:
            x0, y0, x1, y1 = a['zona']
            if not (x0 <= mx <= x1 and y0 <= my <= y1):
                continue
            esc_a = a.get('escala', 1.0)
            dx = a.get('dx', 0.0)
            dy = a.get('dy', 0.0)
            if 'centro_x' in a:
                dx += a['centro_x'] - mx
            if 'centro_y' in a:
                dy += a['centro_y'] - my
            return esc_a, (mx, my), dx, dy
        return 1.0, (0.0, 0.0), 0.0, 0.0

    for m in re.finditer(r'<(path|image|rect|circle|line)\b([^>]*?)/?>', svg):
        tag, attrs = m.group(1), m.group(2)
        tx, ty, esc = _transforma(attrs)
        aj = [1.0, (0.0, 0.0), 0.0, 0.0]   # preenchido ao saber a bbox

        def T(p):
            s, (ax, ay), dx, dy = aj
            px = tx + esc * p[0]
            py = ty + esc * p[1]
            return (ax + s * (px - ax) + dx - ox, ay + s * (py - ay) + dy)

        def X(v):
            s, (ax, _), dx, _dy = aj
            return ax + s * (v - ax) + dx - ox

        def Y(v):
            s, (_, ay), _dx, dy = aj
            return ay + s * (v - ay) + dy

        preenche = _cor(_attr(attrs, 'fill'))
        traco = _cor(_attr(attrs, 'stroke'))
        larg = float(_attr(attrs, 'stroke-width', '1') or 1) * esc
        opac = float(_attr(attrs, 'stroke-opacity', '1') or 1)
        if opac == 0:
            traco = None

        if tag == 'path':
            d = _attr(attrs, 'd', '')
            subs = _pontos_do_path(d)
            xs = [q[0] for s in subs for q in
                  [s['ini']] + [pt if k == 'L' else pt[2] for k, pt in s['seg']]]
            ys = [q[1] for s in subs for q in
                  [s['ini']] + [pt if k == 'L' else pt[2] for k, pt in s['seg']]]
            bbox = (tx + esc * min(xs), ty + esc * min(ys),
                    tx + esc * max(xs), ty + esc * max(ys))                 if xs else (0, 0, 0, 0)
            if pular(tag, attrs, bbox) or not (preenche or traco):
                continue
            aj[:] = ajuste_de(bbox)      # em vetor, o contorno já é a tinta
            larg *= aj[0]
            p = c.beginPath()
            for s in subs:
                px, py = T(s['ini'])
                p.moveTo(px, y(py))
                for tipo, dado in s['seg']:
                    if tipo == 'L':
                        qx, qy = T(dado)
                        p.lineTo(qx, y(qy))
                    else:
                        (a, b, e) = [T(q) for q in dado]
                        p.curveTo(a[0], y(a[1]), b[0], y(b[1]), e[0], y(e[1]))
                if s['fecha']:
                    p.close()
            if preenche:
                c.setFillColor(preenche)
            if traco:
                c.setStrokeColor(traco)
                c.setLineWidth(larg)
                c.setLineCap({'round': 1, 'square': 2}.get(
                    _attr(attrs, 'stroke-linecap'), 0))
                c.setLineJoin({'round': 1, 'bevel': 2}.get(
                    _attr(attrs, 'stroke-linejoin'), 0))
            # ATENÇÃO: no ReportLab FILL_EVEN_ODD=0 e FILL_NON_ZERO=1 — o
            # inverso do que a intuição sugere. Trocar os dois abre buracos
            # onde dois traços do mesmo desenho se sobrepõem (era o que fazia
            # aparecer um ponto branco na junção das setas da pág. 2).
            par = (FILL_EVEN_ODD if _attr(attrs, 'fill-rule') == 'evenodd'
                   else FILL_NON_ZERO)
            c.drawPath(p, stroke=1 if traco else 0, fill=1 if preenche else 0,
                       fillMode=par)

        elif tag == 'image':
            x0 = float(_attr(attrs, 'x', '0'))
            y0 = float(_attr(attrs, 'y', '0'))
            w = float(_attr(attrs, 'width', '0'))
            h = float(_attr(attrs, 'height', '0'))
            caixa = (tx + esc * x0, ty + esc * y0,
                     tx + esc * (x0 + w), ty + esc * (y0 + h))
            if pular(tag, attrs, caixa):
                continue
            dados = base64.b64decode(_attr(attrs, 'href', '').split(',', 1)[1])
            aj[:] = ajuste_de(_tinta_da_imagem(dados, caixa))
            img = ImageReader(io.BytesIO(_suavizar(dados, w * esc * aj[0])))
            ex, ey = T((x0, y0 + h))          # canto inferior-esquerdo no SVG
            c.drawImage(img, ex, y(ey), width=w * esc * aj[0],
                        height=h * esc * aj[0], mask='auto',
                        preserveAspectRatio=False)

        elif tag == 'rect':
            x0 = float(_attr(attrs, 'x', '0'))
            y0 = float(_attr(attrs, 'y', '0'))
            w = float(_attr(attrs, 'width', '0'))
            h = float(_attr(attrs, 'height', '0'))
            if pular(tag, attrs, (x0, y0, x0 + w, y0 + h)):
                continue
            grad = _attr(attrs, 'fill', '')
            if grad.startswith('url('):
                paradas = re.findall(
                    r'<stop offset="([\d.]+)" stop-color="(#[0-9A-Fa-f]{6})"',
                    svg)
                c.saveState()
                p = c.beginPath()
                p.rect(X(x0), y(Y(y0 + h)), w, h)
                c.clipPath(p, stroke=0, fill=0)
                c.linearGradient(X(x0), y(Y(y0 + h)), X(x0) + w, y(Y(y0 + h)),
                                 [HexColor(cor) for _, cor in paradas],
                                 [float(o) for o, _ in paradas])
                c.restoreState()
            elif preenche:
                c.setFillColor(preenche)
                c.rect(X(x0), y(Y(y0 + h)), w, h, stroke=0, fill=1)

        elif tag == 'circle':
            cx = float(_attr(attrs, 'cx', '0'))
            cy = float(_attr(attrs, 'cy', '0'))
            r = float(_attr(attrs, 'r', '0'))
            if pular(tag, attrs, (cx - r, cy - r, cx + r, cy + r)):
                continue
            if preenche:
                c.setFillColor(preenche)
            if traco:
                c.setStrokeColor(traco)
                c.setLineWidth(larg)
            c.circle(X(cx), y(Y(cy)), r, stroke=1 if traco else 0,
                     fill=1 if preenche else 0)

        elif tag == 'line':
            x1 = float(_attr(attrs, 'x1', '0'))
            y1 = float(_attr(attrs, 'y1', '0'))
            x2 = float(_attr(attrs, 'x2', '0'))
            y2 = float(_attr(attrs, 'y2', '0'))
            if pular(tag, attrs, (min(x1, x2), min(y1, y2),
                                  max(x1, x2), max(y1, y2))):
                continue
            if traco:
                c.setStrokeColor(traco)
                c.setLineWidth(larg)
                c.line(X(x1), y(Y(y1)), X(x2), y(Y(y2)))


# ------------------------------------------------------------ campos dinâmicos
# (página, topo aproximado, x aproximado) -> nome do campo em resultado['textos']
# O texto que está no HTML é só uma AMOSTRA (o caso NEUZA); o que importa aqui
# é a posição, a fonte e a cor.
CAMPOS = {
    (1, 668, 69): 'nome_proper',
    (1, 668, 214): 'uc_numero',
    (1, 668, 319): 'endereco',
    (1, 668, 480): 'kwp_txt',
    (1, 691, 319): 'cidade',

    (3, 267, 339): 'mod_qtd',
    (3, 299, 341): 'mod_desc',
    (3, 267, 462): 'estr_qtd',
    (3, 299, 468): 'estr_desc',
    (3, 361, 339): 'inv_qtd',
    (3, 383, 350): 'inv_titulo',
    (3, 394, 345): 'inv_desc',
    (3, 361, 462): 'sb_qtd',
    (3, 394, 465): 'sb_desc',
    (3, 456, 339): 'bat_qtd',
    (3, 489, 345): 'bat_desc',
    (3, 268, 226): 'kwp_txt',
    (3, 306, 226): 'consumo_txt',
    (3, 343, 226): 'geracao_txt',
    (3, 380, 226): 'area_txt',
    (3, 418, 226): 'compensa_txt',
    (3, 592, 396): 'gar_inversor',
    (3, 632, 396): 'gar_instalacao',
    (3, 673, 396): 'gar_modulos',
    (3, 715, 396): 'gar_bateria',

    (5, 253, 218): 'valor_venda',
    (5, 527, 436): 'payback_txt',
    (5, 543, 55): 'fatura_sem',
    (5, 543, 167): 'fatura_com',
    (5, 543, 277): 'economia_mensal',
    (5, 577, 436): 'retorno_25',
    (5, 607, 35): 'disclaimer_data',
    (5, 626, 436): 'validade_txt',
    (5, 738, 108): 'nome_upper',
}

# campos que podem ocupar mais de uma linha quando o texto é comprido (a fonte
# só diminui depois de esgotar as linhas). A cidade fica logo abaixo, então o
# endereço tem 2 linhas; nome e cidade, 2 também.
LINHAS = {'nome_proper': 2, 'endereco': 2, 'cidade': 2, 'uc_numero': 2}

# alinhamento de cada campo (l = pela esquerda, c = centralizado)
ALINHA = {
    'mod_desc': 'c', 'estr_desc': 'c', 'inv_titulo': 'c', 'inv_desc': 'c',
    'sb_desc': 'c', 'bat_desc': 'c',
    'nome_upper': 'c', 'fatura_sem': 'c', 'fatura_com': 'c',
    'economia_mensal': 'c', 'valor_venda': 'c',
}

# largura disponível para cada campo (o texto encolhe se passar disso). Na capa
# as colunas ficam entre divisores em x 177,5 / 282,6 / 445,4 — daí as larguras.
LARGURA = {
    'nome_proper': 104, 'uc_numero': 60, 'endereco': 122, 'cidade': 122,
    'kwp_txt': 105,
    'mod_desc': 118, 'estr_desc': 118, 'inv_titulo': 118, 'inv_desc': 118,
    'sb_desc': 118, 'bat_desc': 118,
    'consumo_txt': 110, 'geracao_txt': 110, 'area_txt': 110,
    'compensa_txt': 110,
    'gar_inversor': 150, 'gar_instalacao': 150, 'gar_modulos': 150,
    'gar_bateria': 150,
    'valor_venda': 260, 'payback_txt': 118, 'retorno_25': 118,
    'nome_upper': 190, 'fatura_sem': 105, 'fatura_com': 105,
    'economia_mensal': 105, 'disclaimer_data': 300, 'validade_txt': 118,
}

# textos do HTML que a página 4 NÃO deve trazer no fundo:
# o gráfico inteiro é redesenhado pelo programa com os dados do cliente
GRAFICO = (78.74, 195.24, 519.54, 374.72)

# Os 6 cartões do "KIT GERADOR" (pág. 3). Saem do fundo e viram peças soltas,
# porque precisam se reagrupar quando falta string box e/ou bateria.
# (nome, x, topo) — todos com 111,05 × 84,08 pt.
CARD_W, CARD_H = 111.05, 84.08
CARTOES = [
    ('modulos', 330.64, 228.98),
    ('estrutura', 454.04, 228.98),
    ('inversor', 330.64, 323.93),
    ('stringbox', 454.04, 323.93),
    ('bateria', 330.90, 418.68),
    ('homolog', 454.30, 418.68),
]
# Nome do slot de cada campo dentro do cartão. O título só é variável no cartão
# do inversor (HÍBRIDO / ON GRID …); nos outros ele já vem impresso no tile.
SLOT_NO_CARTAO = {'inv_titulo': 'titulo'}

# Folga em volta de cada tile. Sem ela a borda cinza do cartão cai exatamente na
# beirada do recorte e metade do traço se perde — a borda "some" de um lado.
MARGEM_TILE = 3.0

# A tabela de números à esquerda (POTÊNCIA … COBERTURA) vai de y 253,14 a 440,77.
# Quando o bloco de cartões fica mais curto (sem string box nem bateria) ele
# desce para ficar centrado com ela, em vez de sobrar espaço embaixo.
TABELA_CENTRO_Y = (253.14 + 440.77) / 2

# Onde fica o centro da TINTA do ícone dentro do cartão. Medido nos cartões
# 4, 5 e 6 (string box, bateria, homologação), que já vinham certos: 18,71 /
# 18,12 / 17,56 pt da borda esquerda. Os cartões 1, 2 e 3 vinham a 25–27 pt
# porque seus PNGs têm bastante margem transparente.
ICONE_CENTRO_DX = 18.13

# Ajustes finos de ícone, por página. `escala` encolhe em torno do centro da
# tinta; `centro_x`/`centro_y` levam esse centro a uma posição exata.
AJUSTES = {
    2: [
        # o raio verde estava 2 pt à direita do centro da bateria que o envolve
        {'zona': (401.93, 508.82, 414.30, 528.12), 'centro_x': 406.13},
    ],
    3: [
        # cartões 1, 2 e 3: encolhem e vão para a mesma coluna dos demais
        {'zona': (336.03, 229.55, 378.40, 268.09), 'escala': 0.80,
         'centro_x': round(330.64 + ICONE_CENTRO_DX, 2)},
        {'zona': (455.84, 224.42, 503.14, 271.80), 'escala': 0.72,
         'centro_x': round(454.04 + ICONE_CENTRO_DX, 2)},
        {'zona': (334.08, 323.13, 377.08, 362.25), 'escala': 0.80,
         'centro_x': round(330.64 + ICONE_CENTRO_DX, 2)},
        # lista de garantias — já estão todos na coluna 371,19; só encolhem
        {'zona': (352.03, 570.18, 390.35, 609.30), 'escala': 0.80},   # inversor
        {'zona': (352.24, 612.39, 390.14, 650.93), 'escala': 0.80},   # módulos
        {'zona': (358.08, 658.59, 384.27, 684.92), 'escala': 0.90},   # perform.
    ],
}

# Textos fixos que precisaram de um empurrão. (página, topo, x) -> (dx, dy).
# O título GARANTIAS estava a 29 pt do escudo. Vai para x 396,9, a mesma
# coluna dos rótulos logo abaixo (INVERSOR, MÓDULOS…): o vão cai para 13 pt e
# o bloco inteiro passa a ter uma margem esquerda só.
DESLOC_TEXTO = {(3, 543.5, 412.6): (396.9 - 412.6, 0.0)}

# Bloco das 3 garantias fixas (inversor / módulos / performance linear). Vira
# uma peça solta porque desce quando não há a 4ª linha, a da bateria.
# título do bloco de cartões — vira dinâmico p/ descer junto com eles
TITULO_KIT = 'KIT GERADOR FOTOVOLTAICO'
GARANTIAS_ZONA = {'x0': 348.0, 'top': 566.0, 'x1': 531.0, 'bottom': 688.0}
# centraliza as 3 linhas no espaço que as 4 ocupavam (572,18 … 727,57)
GARANTIAS_DESLOC = round(((727.57 - 572.18) - (682.92 - 572.18)) / 2, 2)

# banda de fotos da pág. 3 (módulo à esquerda, inversor à direita)
FOTOS_P3 = {
    'cobrir': {'x0': 76.0, 'x1': 322.0, 'top': 523.0, 'bottom': 749.0},
    'modulo': {'x0': 80.28, 'x1': 194.69, 'top': 526.10, 'bottom': 746.49},
    'inversor': {'x0': 199.36, 'x1': 317.13, 'top': 576.54, 'bottom': 721.31},
}


def _regiao_cartoes():
    x0 = min(x for _, x, _ in CARTOES)
    y0 = min(t for _, _, t in CARTOES)
    return {'x0': x0, 'top': y0,
            'x1': max(x for _, x, _ in CARTOES) + CARD_W,
            'bottom': max(t for _, _, t in CARTOES) + CARD_H}


def _nas_garantias(bbox) -> bool:
    """As 3 linhas fixas de GARANTIAS (sem o título e sem a linha da bateria)."""
    g = GARANTIAS_ZONA
    mx, my = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return g['x0'] <= mx <= g['x1'] and g['top'] <= my <= g['bottom']


def _no_cartao(bbox) -> bool:
    """Pelo CENTRO, não pelo contorno: alguns ícones estouram um pouco a
    moldura do cartão (o da estrutura de fixação começa 2,5 pt acima dela)."""
    r = _regiao_cartoes()
    mx, my = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return r['x0'] <= mx <= r['x1'] and r['top'] <= my <= r['bottom']


def _campo_de(pagina: int, topo: float, x: float):
    for (p, t, cx), nome in CAMPOS.items():
        if p == pagina and abs(t - topo) < 3 and abs(cx - x) < 4:
            return nome
    return None


def _no_grafico(bbox) -> bool:
    x0, y0, x1, y1 = bbox
    gx0, gy0, gx1, gy1 = GRAFICO
    return (x0 >= gx0 - 1 and x1 <= gx1 + 1
            and y0 >= gy0 - 1 and y1 <= gy1 + 1)


# ------------------------------------------------- cartões soltos da página 3
def _gerar_cartoes(pag3: dict) -> dict:
    """Cada cartão vira um PNG de 600 dpi + a posição dos textos que o programa
    escreve dentro dele. É o que permite reagrupar sem deixar buracos."""
    import pypdfium2 as pdfium

    destino = os.path.join(ASSETS, 'cards')
    os.makedirs(destino, exist_ok=True)
    mg = MARGEM_TILE
    tw, th = CARD_W + 2 * mg, CARD_H + 2 * mg
    reg = _regiao_cartoes()
    meta = {'regiao': {'x0': reg['x0'] - mg, 'top': reg['top'] - mg,
                       'x1': reg['x1'] + mg, 'bottom': reg['bottom'] + mg},
            'slots': [[x, t] for _, x, t in CARTOES],
            'margem': mg,
            'alinhar': {'centro_y': round(TABELA_CENTRO_Y, 2),
                        'top_min': min(t for _, _, t in CARTOES)},
            'cards': {}}

    for nome, cx0, ctop in CARTOES:
        def fora(tag, attrs, bbox, _c=(cx0, ctop)):
            mx, my = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            return not (_c[0] <= mx <= _c[0] + CARD_W
                        and _c[1] <= my <= _c[1] + CARD_H)

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(tw, th))
        c.setFillColor(HexColor('#FFFFFF'))
        c.rect(0, 0, tw, th, stroke=0, fill=1)
        desenhar_svg(c, pag3['svg'], fora, origem=(cx0 - mg, ctop - mg),
                     tamanho=(tw, th), ajustes=AJUSTES[3])

        info = {'w': tw, 'h': th}
        for b in pag3['blocos']:
            texto, est = b['trechos'][0]
            fonte = _fonte(est['fam'], est['bold'])
            larg = pdfmetrics.stringWidth(texto, fonte, est['fs'])
            if not (cx0 - 1 <= b['x'] and b['x'] + larg <= cx0 + CARD_W + 1
                    and ctop <= b['topo'] <= ctop + CARD_H):
                continue
            campo = _campo_de(3, b['topo'], b['x'])
            if campo:            # valor calculado: guarda a posição, não pinta
                chave = SLOT_NO_CARTAO.get(
                    campo, 'qtd' if campo.endswith('_qtd') else 'desc')
                spec = {'dbaseline': round(b['base'] - ctop, 2),
                        'size': round(est['fs'], 2), 'bold': est['bold'],
                        'color': est['cor'].lstrip('#').upper(),
                        'font': est['fam'],
                        'algn': ALINHA.get(campo, 'l'),
                        'max_w': LARGURA.get(campo)}
                if spec['algn'] == 'c':
                    spec['cx'] = round(b['x'] + larg / 2 - cx0, 2)
                else:
                    spec['dx'] = round(b['x'] - cx0, 2)
                info[chave] = spec
                continue
            c.setFont(fonte, est['fs'])           # rótulo fixo do cartão
            c.setFillColor(HexColor(est['cor']))
            c.drawString(b['x'] - cx0 + mg, th - (b['base'] - ctop) - mg, texto)
        c.showPage()
        c.save()

        buf.seek(0)
        pag = pdfium.PdfDocument(buf.read())[0]
        pag.render(scale=600 / 72).to_pil().convert('RGB').save(
            os.path.join(destino, f'{nome}.png'))
        meta['cards'][nome] = info

    # o título "KIT GERADOR FOTOVOLTAICO" vira dinâmico: quando o bloco encurta
    # (só 4 cartões) ele desce junto com os cartões, acompanhando a tabela
    for b in pag3['blocos']:
        texto, est = b['trechos'][0]
        if texto.strip().upper() == TITULO_KIT:
            meta['titulo'] = {'text': texto, 'x': round(b['x'], 2),
                              'base': round(b['base'], 2),
                              'size': round(est['fs'], 2), 'bold': est['bold'],
                              'color': est['cor'].lstrip('#').upper(),
                              'font': est['fam']}
            break

    meta['garantias'] = _gerar_garantias(pag3, destino)
    with open(os.path.join(destino, 'layout_cards.json'), 'w',
              encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta


def _gerar_garantias(pag3: dict, destino: str) -> dict:
    """As 3 garantias fixas viram uma peça só, que desce quando falta a linha
    da bateria — assim as três ficam centradas no quadro em vez de encostadas
    no alto."""
    import pypdfium2 as pdfium

    g = GARANTIAS_ZONA
    w, h = g['x1'] - g['x0'], g['bottom'] - g['top']
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(0, 0, w, h, stroke=0, fill=1)
    desenhar_svg(c, pag3['svg'], lambda t, a, bb: not _nas_garantias(bb),
                 origem=(g['x0'], g['top']), tamanho=(w, h), ajustes=AJUSTES[3])
    for b in pag3['blocos']:
        texto, est = b['trechos'][0]
        fonte = _fonte(est['fam'], est['bold'])
        larg = pdfmetrics.stringWidth(texto, fonte, est['fs'])
        caixa = (b['x'], b['topo'], b['x'] + larg, b['topo'] + est['fs'])
        if not _nas_garantias(caixa) or _campo_de(3, b['topo'], b['x']):
            continue                       # os "10 ANOS" são valores, não rótulo
        c.setFont(fonte, est['fs'])
        c.setFillColor(HexColor(est['cor']))
        c.drawString(b['x'] - g['x0'], h - (b['base'] - g['top']), texto)
    c.showPage()
    c.save()
    buf.seek(0)
    pdfium.PdfDocument(buf.read())[0].render(scale=600 / 72).to_pil().convert(
        'RGB').save(os.path.join(destino, 'garantias.png'))
    return {'x0': g['x0'], 'top': g['top'], 'w': w, 'h': h,
            'desloc_sem_bateria': GARANTIAS_DESLOC}


# ------------------------------------------------------------------- principal
def converter(caminho_html: str) -> None:
    paginas = ler_paginas(caminho_html)
    if len(paginas) != 5:
        raise SystemExit(f'esperava 5 páginas, achei {len(paginas)}')
    _registrar_fontes()

    larg, alt = PAGINA
    c = canvas.Canvas(os.path.join(ASSETS, 'fundo.pdf'), pagesize=PAGINA)
    campos, achados = [], set()

    for n, pag in enumerate(paginas, 1):
        if n == 4:      # o gráfico é redesenhado com os dados do cliente
            pular = lambda tag, attrs, bbox: _no_grafico(bbox)
        elif n == 3:    # cartões e garantias são estampados à parte: se movem
            pular = lambda tag, attrs, bbox: (_no_cartao(bbox)
                                              or _nas_garantias(bbox))
        else:
            pular = lambda tag, attrs, bbox: False
        desenhar_svg(c, pag['svg'], pular, ajustes=AJUSTES.get(n, ()))

        for b in pag['blocos']:
            campo = _campo_de(n, b['topo'], b['x'])
            texto, est = b['trechos'][0]
            fonte = _fonte(est['fam'], est['bold'])

            if campo:
                largura = pdfmetrics.stringWidth(texto, fonte, est['fs'])
                base = alt - b['base']
                desc = pdfmetrics.getDescent(fonte, est['fs'])
                asc = pdfmetrics.getAscent(fonte, est['fs'])
                reg = {
                    'page': n, 'field': campo,
                    'box': {'x0': round(b['x'], 2),
                            'y0': round(base + desc, 2),
                            'x1': round(b['x'] + largura, 2),
                            'y1': round(base + asc, 2)},
                    'style': {'size': round(est['fs'], 2), 'bold': est['bold'],
                              'color': est['cor'].lstrip('#').upper(),
                              'font': est['fam']},
                    'algn': ALINHA.get(campo, 'l'),
                    'max_w': LARGURA.get(campo),
                    'linhas': LINHAS.get(campo, 1),
                }
                if reg['algn'] == 'c':
                    reg['cx'] = round(b['x'] + largura / 2, 2)
                if campo in ('gar_inversor', 'gar_instalacao', 'gar_modulos'):
                    # descem junto com o bloco quando não há linha de bateria
                    reg['desloca_sem_bateria'] = GARANTIAS_DESLOC
                campos.append(reg)
                achados.add(campo)
                continue

            caixa = (b['x'], b['topo'], b['x'] + 1, b['topo'] + est['fs'])
            if n == 4 and _no_grafico(caixa):
                continue  # rótulos do gráfico: o programa redesenha
            if n == 3 and (_no_cartao(caixa) or _nas_garantias(caixa)):
                continue  # rótulos dos cartões/garantias: vão dentro do tile
            if n == 3 and texto.strip().upper() == TITULO_KIT:
                continue  # título do kit: desenhado dinâmico (segue os cartões)

            dx, dy = 0.0, 0.0
            for (pg, tp, px), (adx, ady) in DESLOC_TEXTO.items():
                if pg == n and abs(tp - b['topo']) < 3 and abs(px - b['x']) < 4:
                    dx, dy = adx, ady
            x = b['x'] + dx
            for texto, est in b['trechos']:
                fonte = _fonte(est['fam'], est['bold'])
                c.setFont(fonte, est['fs'])
                c.setFillColor(HexColor(est['cor']))
                c.drawString(x, alt - b['base'] - dy, texto)
                x += pdfmetrics.stringWidth(texto, fonte, est['fs'])
        c.showPage()
    c.save()

    faltando = set(CAMPOS.values()) - achados
    if faltando:
        print('  ATENÇÃO — campos não localizados no HTML:', sorted(faltando))

    layout = {
        'fields': campos,
        'chart_rect_pt_top': list(GRAFICO),
        'page_size': [larg, alt],
        'cards_p3': {
            'regiao': _regiao_cartoes(),
            # linha "BATERIA DE LÍTIO" da lista de GARANTIAS: some junto com a
            # bateria (ícone em 364,1–378,1 × 699,8–727,6; texto a partir de 396,9)
            'gar_bateria_zona': {'x0': 348.0, 'x1': 531.0,
                                 'top': 692.0, 'bottom': 736.0},
        },
    }
    with open(os.path.join(ASSETS, 'layout.json'), 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)

    meta = _gerar_cartoes(paginas[2])

    caminho_deco = os.path.join(ASSETS, 'deco.json')
    with open(caminho_deco, encoding='utf-8') as f:
        deco = json.load(f)
    # a arte nova já vem com a foto da capa sangrada e a timeline com círculos
    # perfeitos — os remendos vetoriais do fundo antigo não são mais precisos
    deco.pop('timeline_p4', None)
    deco.pop('cover_panel_p1', None)
    deco['fotos_p3'] = dict(deco.get('fotos_p3', {}), page=3, **FOTOS_P3)
    with open(caminho_deco, 'w', encoding='utf-8') as f:
        json.dump(deco, f, ensure_ascii=False, indent=1)

    print(f'  fundo.pdf   : 5 páginas')
    print(f'  layout.json : {len(campos)} campos dinâmicos')
    print(f'  cards/      : {len(meta["cards"])} cartões')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    converter(sys.argv[1])
