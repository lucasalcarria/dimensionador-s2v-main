# -*- coding: utf-8 -*-
"""
Geração do PDF da proposta.

Os fundos (assets/fundo.pdf) são as 5 páginas originais da planilha exportadas
em vetor, com os textos dinâmicos em branco. Este módulo desenha por cima:
  * cada campo dinâmico na posição exata medida em assets/layout.json;
  * o gráfico de consumo × geração da página 4 (matplotlib, vetorial).
Resultado idêntico ao layout original, gerado em menos de 1 segundo.
"""
from __future__ import annotations
import io
import json
import os

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import ContentStream, FloatObject, TextStringObject
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, 'assets')
FONTS = os.path.join(ASSETS, 'fonts')

_layout = None
_fontes_ok = False


def _carregar_layout():
    global _layout
    if _layout is None:
        with open(os.path.join(ASSETS, 'layout.json'), encoding='utf-8') as f:
            _layout = json.load(f)
    return _layout


_cards = None


def _desenhar_icones(c, icones, ox: float, oy: float) -> None:
    """Desenha em VETOR os ícones de um cartão (ou do bloco de garantias), por
    cima do PNG dele — que vem sem o ícone. Cada ícone traz a caixa onde a
    imagem original era desenhada (x, y = canto inferior-esquerdo, em pt, no
    sistema do próprio cartão) e o caminho na caixa unitária, com y PARA BAIXO.
    Gerados por ferramentas/vetor_icones.py — aqui é só ReportLab puro."""
    import re
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    for ic in icones or ():
        x0, y0, w, h = ox + ic['x'], oy + ic['y'], ic['w'], ic['h']
        c.setFillColor(HexColor('#' + ic['cor']))
        p = c.beginPath()
        for op, nums in re.findall(r'([MCLZ])([^MCLZ]*)', ic['p']):
            n = [float(v) for v in nums.split()]
            pt = [(x0 + n[i] * w, y0 + (1 - n[i + 1]) * h)
                  for i in range(0, len(n), 2)]
            if op == 'M':
                p.moveTo(*pt[0])
            elif op == 'L':
                for q in pt:
                    p.lineTo(*q)
            elif op == 'C':
                p.curveTo(*pt[0], *pt[1], *pt[2])
            elif op == 'Z':
                p.close()
        c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)


def _carregar_cards():
    """Metadados dos 6 cartões da página 3 (tiles + offsets de qtd/desc)."""
    global _cards
    if _cards is None:
        with open(os.path.join(ASSETS, 'cards', 'layout_cards.json'),
                  encoding='utf-8') as f:
            _cards = json.load(f)
    return _cards


_deco = None


def _carregar_deco():
    """Geometria dos elementos decorativos redesenhados em vetor."""
    global _deco
    if _deco is None:
        caminho = os.path.join(ASSETS, 'deco.json')
        if os.path.exists(caminho):
            with open(caminho, encoding='utf-8') as f:
                _deco = json.load(f)
        else:
            _deco = {}
    return _deco


def _redesenhar_timeline(c, page_h):
    """Cobre os 7 círculos deformados da 'ETAPAS DO PROJETO' (pág. 4) e os
    redesenha como círculos perfeitos e idênticos, ligados por uma linha limpa."""
    d = _carregar_deco().get('timeline_p4')
    if not d:
        return
    # cobre a faixa dos círculos originais (deixa os rótulos abaixo intactos)
    cob = d['cobrir']
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(cob['x0'], page_h - cob['bottom'],
           cob['x1'] - cob['x0'], cob['bottom'] - cob['top'], stroke=0, fill=1)
    # linha de ligação
    ln = d['linha']
    y = page_h - ln['y']
    c.setStrokeColor(HexColor('#' + ln['cor']))
    c.setLineWidth(ln['espessura'])
    c.line(ln['x0'], y, ln['x1'], y)
    # círculos perfeitos e idênticos
    c.setFillColor(HexColor('#' + d['cor']))
    r = d['raio']
    for cx in d['centros_x']:
        c.circle(cx, page_h - d['cy'], r, stroke=0, fill=1)


def _estender_cover(c, page_h):
    """Estende a foto das placas (capa) até a borda direita, eliminando a
    faixa branca entre a imagem e o fim da página."""
    d = _carregar_deco().get('cover_panel_p1')
    if not d:
        return
    caminho = os.path.join(ASSETS, d['arquivo'])
    if not os.path.exists(caminho):
        return
    x0 = d['x0_atual']
    x1 = d['x1_novo']
    top = d['top']
    bottom = d['bottom']
    # redesenha a foto ocupando de x0 até a borda direita (full bleed)
    c.drawImage(caminho, x0, page_h - bottom, width=x1 - x0,
                height=bottom - top, preserveAspectRatio=False, mask=None)


def _registrar_fontes():
    global _fontes_ok
    if _fontes_ok:
        return
    mapa = {
        ('Inter', True): 'Inter-Bold.ttf',
        ('Inter', False): 'Inter-Regular.ttf',
        ('Sora', True): 'Sora-Bold.ttf',
        ('Sora', False): 'Sora-Regular.ttf',
        ('JetBrainsMono', False): 'JetBrainsMono-Regular.ttf',   # cabeçalhos
    }
    for (fam, bold), arq in mapa.items():
        nome = _font_key(fam, bold)
        pdfmetrics.registerFont(TTFont(nome, os.path.join(FONTS, arq)))
    # o gráfico (matplotlib) usa Inter, a mesma fonte do resto da proposta
    inter = os.path.join(FONTS, 'Inter-Regular.ttf')
    if os.path.exists(inter):
        fm.fontManager.addfont(inter)
        plt.rcParams['font.family'] = 'Inter'
    _fontes_ok = True


def _font_key(fam: str, bold: bool) -> str:
    return f"{fam}-{'Bold' if bold else 'Regular'}"


_FORMAS = {}


def _forma_do_fundo(pagina: int, x: float, y: float):
    """(matriz, operadores) do ícone vetorial (Form XObject) que o fundo.pdf
    desenha com origem em (x, y) na `pagina` (1-based). Acha pela POSIÇÃO medida
    — o nome do XObject é um hash e muda se os ícones forem regerados."""
    import re
    chave = (pagina, round(x, 1), round(y, 1))
    if chave not in _FORMAS:
        pg = PdfReader(os.path.join(ASSETS, 'fundo.pdf')).pages[pagina - 1]
        dados = pg.get_contents().get_data().decode('latin-1')
        achado = None
        for m in re.finditer(r'([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) '
                             r'([-\d.]+) ([-\d.]+) cm\s*(/\S+) Do', dados):
            mt = [float(v) for v in m.groups()[:6]]
            if abs(mt[4] - x) < 0.5 and abs(mt[5] - y) < 0.5:
                xo = pg['/Resources']['/XObject'][m.group(7)].get_object()
                achado = (mt, xo.get_data().decode('latin-1'))
                break
        _FORMAS[chave] = achado
    return _FORMAS[chave]


# Painel das garantias (pág. 3, à direita da foto). A ÁREA é a do quadro:
# divisória x 331 → borda x 533,5; borda de cima 520,8 → de baixo 752 (medido).
# O painel inteiro (escudo + "GARANTIAS" + itens + anos) é redesenhado:
#  * `dx` centra na horizontal — o conteúdo (x 358–494) estava 6 pt à esquerda
#    do centro da área. Vale com e sem bateria.
#  * `dy` desce o grupo SEM bateria (3 itens): 11 pt = o "meio-termo" escolhido
#    pelo usuário entre o título no lugar original (0) e o centro exato (22).
GAR_AJUSTE = {'dx': 6.1, 'dy': 11.0}
CAMPOS_GARANTIA = {'gar_inversor', 'gar_instalacao', 'gar_modulos', 'gar_bateria'}
_TRECHOS = {}


def _trecho_do_fundo(pagina: int, inicio: str, fim: str):
    """Operadores de desenho do fundo.pdf entre `inicio` (inclusive, recuando
    até a linha de cor anterior) e o 1º `fim` depois dele. None se não achar."""
    chave = (pagina, inicio, fim)
    if chave not in _TRECHOS:
        dados = (PdfReader(os.path.join(ASSETS, 'fundo.pdf')).pages[pagina - 1]
                 .get_contents().get_data().decode('latin-1'))
        i = dados.find(inicio)
        if i < 0:
            _TRECHOS[chave] = None
        else:
            i = dados.rfind(' rg\n', 0, i)
            i = dados.rfind('\n', 0, i) + 1          # começo da linha de cor
            j = dados.find(fim, dados.find(inicio))
            _TRECHOS[chave] = None if j < 0 else dados[i:j + len(fim)]
    return _TRECHOS[chave]


def _garantias_painel(c, gr, page_h, com_bateria: bool):
    dx = GAR_AJUSTE['dx']
    dy = 0.0 if com_bateria else GAR_AJUSTE['dy']
    # ícone da bateria: desenho vetorial solto no fundo (contorno + raio)
    bat = _trecho_do_fundo(3, 'n 375.58 117.26 m', '\nf\n') if com_bateria else ''
    forma = _forma_do_fundo(3, 358.76, 278.27)
    if forma is None or bat is None:          # arte diferente: não mexe em nada
        bat, forma, dx = '', None, 0.0
    if forma is None and com_bateria:
        c.setFillColor(HexColor('#FFFFFF'))
        c.rect(gr['x0'], page_h - (gr['top'] + gr['h']),
               gr['w'], gr['h'], stroke=0, fill=1)
    if forma is not None:
        # apaga o painel (sem encostar na divisória, na borda nem no canto)
        c.setFillColor(HexColor('#FFFFFF'))
        c.rect(334.0, page_h - 749.0, 186.0, 749.0 - 524.0, stroke=0, fill=1)
        # cabeçalho, medido no fundo.pdf: escudo na caixa 24,85 × 29,5 em
        # (358,76; 278,27); "GARANTIAS" Sora Bold 11,846 #089C83 em (396,90; 288,46)
        familia = 'escudo' in _carregar_icones_traco()
        if familia:                    # ícones da família (ver ICONES_TRACO)
            _icone(c, 'escudo', *GAR_ICONE(gr, dx, dy, -17.1, page_h, 'escudo'), LADO_M, VERDE,
                   grupo=GAR_NOMES)
        else:
            mt, ops = forma
            c.saveState()
            c.transform(mt[0], mt[1], mt[2], mt[3], mt[4] + dx, mt[5] - dy)
            c._code.append(ops)
            c.restoreState()
        c.setFillColor(HexColor('#089C83'))
        c.setFont(_font_key('Sora', True), 11.84642)
        c.drawString(396.9002 + dx, 288.4583 - dy, 'GARANTIAS')
        if bat:
            # 4ª linha: ícone + "BATERIA DE LÍTIO" (Sora Bold 7,948 #004D94)
            if familia:
                _icone(c, 'bateria', *GAR_ICONE(gr, dx, dy, 147.7, page_h, 'bateria'), LADO_M, VERDE,
                       grupo=GAR_NOMES)
            else:
                c.saveState()
                c.translate(dx, 0)
                c._code.append(bat)
                c.restoreState()
            c.setFillColor(HexColor('#004D94'))
            c.setFont(_font_key('Sora', True), 7.947597)
            c.drawString(396.855 + dx, 130.5321, 'BATERIA DE LÍTIO')
    # os 3 itens (tile + ícones), cortados antes da borda direita
    x0, y0 = gr['x0'] + dx, page_h - (gr['top'] + dy + gr['h'])
    c.saveState()
    p = c.beginPath()
    p.rect(334.0, y0, 520.0 - 334.0, gr['h'])
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(os.path.join(ASSETS, 'cards', 'garantias.png'), x0, y0,
                width=gr['w'], height=gr['h'], mask='auto',
                preserveAspectRatio=False)
    c.restoreState()
    if forma is not None and 'degradacao' in _carregar_icones_traco():
        # o da performance vem "impresso" no PNG (x 8–39, topo 90–121 no tile)
        c.setFillColor(HexColor('#FFFFFF'))
        c.rect(x0 + 8.0, y0 + gr['h'] - 121.0, 31.0, 31.0, stroke=0, fill=1)
        for nome, rel in (('inversor', 23.74), ('modulo', 64.57),
                          ('degradacao', 105.65)):
            _icone(c, nome, *GAR_ICONE(gr, dx, dy, rel, page_h, nome), LADO_M, VERDE,
                   grupo=GAR_NOMES)
    else:
        _desenhar_icones(c, gr.get('icones'), x0, y0)


GAR_NOMES = ('escudo', 'inversor', 'modulo', 'degradacao', 'bateria')


def GAR_ICONE(gr, dx, dy, rel_topo, page_h, nome):
    """Centro (x, y de baixo) de um ícone das garantias: antes da coluna de
    texto (x 48,9 no tile, a mesma de "GARANTIAS") com o espaço padrão, e cada
    linha `rel_topo` pt abaixo do topo do tile (medido: escudo −17,1; inversor
    23,74; módulos 64,57; performance 105,65; bateria 147,7)."""
    return (gr['x0'] + dx + _cx_coluna(48.9, LADO_M, GAR_NOMES),
            page_h - (gr['top'] + dy + rel_topo))


# ÍCONES — UMA FAMÍLIA SÓ (revisão de design B5, pedido do usuário: "mesma
# família, mesmas espessuras"). Todos os ícones da proposta são de TRAÇO, da
# Lucide (+ Tabler p/ o WhatsApp e desenhos da marca na mesma grade), lidos de
# assets/icones_traco.json (ferramentas/icones_traco.py). Sistema de linhas:
#   * traço de ícone ........ 1,5 pt (ícones pequenos, até 16 pt: 1,1 pt)
#   * anel de círculo ....... 1,98 pt (o mesmo dos círculos cinza da arte)
#   * bordas de cartão ...... 0,99 pt · divisórias e ligações ... 0,74 pt
# Cada entrada: pág., ícone, centro x, centro y (no TOPO), lado útil (pt),
# cor, o que apagar do original (retângulo x0,y0,x1,y1 no topo ou disco
# ('c', cx, cy, r)) e, opcional, `aro` = raio do anel a desenhar em volta.
# Centros/caixas MEDIDOS no fundo.pdf ou na página renderizada.
TRACO_ICONE, TRACO_ICONE_PEQ, TRACO_ARO = 1.5, 1.1, 1.98
VERDE, AZUL = '#089C83', '#004D94'
# TAMANHO = EXTREMIDADE DA TINTA (pedido do usuário): o "lado" de um ícone é a
# sua MAIOR dimensão visível — do primeiro ao último ponto de tinta, já com a
# espessura do traço —, em todos os casos.
#   M = 26 pt (faixa da capa, tabela, cartões, garantias, retorno da pág. 5)
#   P = 15 pt (rodapé da capa, cartão de projetos)
#   dentro de círculo = 0,60 × diâmetro do círculo
#   (22/14/0,52 ficou pequeno demais para o usuário depois da regra por grupo)
# ESPAÇOS medidos na TINTA: ícone -> texto 10 pt (M) / 6 pt (P); na faixa da
# capa, divisória -> tinta do ícone = metade do espaço entre colunas.
LADO_M, LADO_P, GAP_M, GAP_P, NO_CIRCULO = 26.0, 15.0, 10.0, 6.0, 0.60


def _gap(lado):
    return GAP_P if lado <= 15 else GAP_M


def _tinta(nome, lado, area):
    """(escala, largura, altura de tinta) do ícone com caixa de tinta de ÁREA
    `area`²: resolve (gw·k + t)(gh·k + t) = area², com os limites exatos do
    desenho (JSON) e o traço da família."""
    ic = _carregar_icones_traco().get(nome) or {}
    lx0, ly0, lx1, ly1 = ic.get('limites') or (2, 2, 22, 22)
    gw, gh, t = lx1 - lx0, ly1 - ly0, _traco_de(lado)
    a, b, cc = gw * gh, t * (gw + gh), t * t - area * area
    k = (-b + (b * b - 4 * a * cc) ** 0.5) / (2 * a)
    return k, gw * k + t, gh * k + t


_AREA_GRUPO = {}


def _dims(nome, lado, grupo=None):
    """(escala, largura e altura da TINTA em pt) — o "retângulo azul".

    Sem grupo: a maior dimensão de tinta = `lado`.
    Com grupo (pedido do usuário: ícones de um mesmo grupo harmônicos, sem
    distorcer): todos têm o mesmo TAMANHO PERCEBIDO — ponto médio entre a área
    do retângulo de tinta e a da silhueta — e o maior lado do grupo é `lado`
    (nenhum fica mais alto ou mais largo que os outros)."""
    ic = _carregar_icones_traco().get(nome) or {}
    lx0, ly0, lx1, ly1 = ic.get('limites') or (2, 2, 22, 22)
    gw, gh, t = lx1 - lx0, ly1 - ly0, _traco_de(lado)
    if not grupo or len(grupo) < 2:
        k = (lado - t) / max(gw, gh)
        return k, gw * k + t, gh * k + t
    chave = (tuple(sorted(set(grupo))), lado)
    if chave not in _AREA_GRUPO:
        # tamanho PERCEBIDO de cada desenho (na grade): ponto médio (média
        # geométrica) entre a área do retângulo e a da SILHUETA — uma moldura
        # quadrada (99 % do retângulo) pesa mais que uma "pessoa" (75 %) com o
        # mesmo retângulo. Todos do grupo ficam com o mesmo tamanho percebido;
        # depois o grupo inteiro é escalado para o maior lado ser `lado`.
        base = {}
        for n in chave[0]:
            d = _carregar_icones_traco().get(n) or {}
            a0, b0, a1, b1 = d.get('limites') or (2, 2, 22, 22)
            ret = (a1 - a0) * (b1 - b0)
            sil = d.get('silhueta') or ret
            base[n] = ((ret * sil) ** 0.5) ** -0.5, max(a1 - a0, b1 - b0)
        c = (lado - t) / max(kb * longo for kb, longo in base.values())
        _AREA_GRUPO[chave] = {n: c * kb for n, (kb, _) in base.items()}
    k = _AREA_GRUPO[chave].get(nome)
    if k is None:
        k = (lado - t) / max(gw, gh)
    return k, gw * k + t, gh * k + t


def _cx_antes(x_texto, lado, nome, grupo=None):
    """Centro x de um ícone cuja TINTA (retângulo azul) termina `_gap` antes
    do texto — o espaço é medido na tinta, sem margens vazias."""
    return x_texto - _gap(lado) - _dims(nome, lado, grupo)[1] / 2.0


def _cx_coluna(x_texto, lado, nomes):
    """Centro x comum de uma LISTA de ícones (tabela, garantias…): todos no
    mesmo eixo; a tinta do mais largo termina `_gap` antes do texto."""
    larg = max(_dims(n, lado, nomes)[1] for n in nomes)
    return x_texto - _gap(lado) - larg / 2.0


def _traco_de(lado):
    return TRACO_ICONE_PEQ if lado <= 15 else TRACO_ICONE


def _I(pg, nome, cx, cy, lado, cor, apaga, aro=None, grupo=None):
    """Um ícone de posição fixa. `cx` pode ser ('antes', x do texto): o centro
    é calculado na hora, pela largura de tinta do ícone (ver _cx_antes)."""
    return dict(pg=pg, nome=nome, cx=cx, cy=cy, lado=lado, cor=cor,
                apaga=apaga, aro=aro, grupo=grupo)


def _ret(cx, cy, meia):
    return (cx - meia, cy - meia, cx + meia, cy + meia)


ICONES_TRACO = (
    # pág. 1 — os 4 pilares: anel verde (Ø 38,4) + ícone de meio diâmetro
    [_I(1, n, 72.7, cy, NO_CIRCULO * 38.4, VERDE, _ret(72.7, cy, 20.4), aro=19.2 - TRACO_ARO / 2,
        grupo='pilares')
     for n, cy in (('escudo', 399.72), ('geracao', 463.42), ('folha', 527.02),
                   ('grafico', 590.72))]
    # pág. 1 — a faixa cliente/UC/local/sistema é dinâmica: ver _faixa_capa
    # pág. 1 — o rodapé de contatos também é distribuído: ver _rodape_capa
    # pág. 2 — diagrama: 9 círculos de anel cinza (Ø 56,8); apaga o miolo
    + [_I(2, n, cx, cy, NO_CIRCULO * 56.8, AZUL, ('c', cx, cy, 25.8), grupo='diagrama')
       for n, cx, cy in (('torre', 304.30, 293.23), ('casa', 414.40, 293.23),
                         ('conta', 523.06, 293.13), ('modulo', 298.26, 423.17),
                         ('inversor', 406.16, 423.12), ('casa', 516.65, 423.00),
                         ('bateria', 406.10, 517.95), ('conta', 406.10, 607.85),
                         ('torre', 516.65, 608.40))]
    # pág. 2 — faixa "ENERGIA LIMPA…": folha em anel verde (Ø 41)
    + [_I(2, 'folha', 97.15, 714.15, NO_CIRCULO * 41.0, VERDE, (74.0, 691.0, 121.0, 737.0),
          aro=20.5 - TRACO_ARO / 2)]
    # pág. 3 — tabela (azul, M): centrados ENTRE a borda da tabela (37,45 +
    # meio traço) e os rótulos (x 76,55) — mesmo espaço dos dois lados
    + [_I(3, n, ('coluna', 76.55, 'tabela', 37.94), cy, LADO_M, AZUL, apaga, grupo='tabela')
       for n, cy, apaga in (('sol', 272.79, (45.7, 261.9, 67.1, 283.7)),
                            ('torre', 310.39, (45.7, 297.4, 67.1, 323.3)),
                            ('geracao', 347.43, (45.7, 336.4, 67.1, 358.4)),
                            ('area', 384.77, (45.7, 373.8, 67.1, 395.8)),
                            ('porcento', 422.51, (45.7, 411.5, 67.1, 433.5)))]
    # pág. 4 — ETAPAS: miolo dos círculos de anel cinza (Ø 39,4, cy 701,5)
    + [_I(4, n, cx, 701.5, NO_CIRCULO * 39.4, AZUL, ('c', cx, 701.5, 17.0), grupo='etapas')
       for n, cx in zip(('drone', 'contrato', 'projeto', 'homologacao',
                         'instalacao', 'vistoria', 'modulo'),
                        (66.32, 141.65, 216.99, 292.27, 367.50, 442.84, 518.12))]
    # pág. 4 — cartão de projetos realizados (P), antes do texto (x 370,61)
    + [_I(4, n, ('coluna', 370.61, 'projetos'), cy, LADO_P, VERDE, apaga,
          grupo='projetos')
       for n, cy, apaga in (('local', 544.4, (338.2, 535.9, 364.0, 552.5)),
                            ('geracao', 570.2, (338.2, 560.0, 364.0, 579.6)),
                            ('modulo', 595.1, (338.2, 585.8, 364.0, 603.9)),
                            ('inversor', 620.0, (338.2, 610.8, 364.0, 630.6)))]
    # pág. 5 — coluna do retorno (M): centrados entre a borda do cartão
    # (392,36 + meio traço) e o texto (x 436,67)
    + [_I(5, n, ('coluna', 436.67, 'retorno', 392.85), cy, LADO_M, VERDE, apaga,
          grupo='retorno')
       for n, cy, apaga in (('relogio', 528.39, (403.6, 517.9, 427.5, 538.9)),
                            ('grafico', 577.65, (403.6, 567.2, 427.5, 588.1)),
                            ('calendario', 627.07, (403.6, 616.6, 427.5, 637.5)))]
)
# cartões da pág. 3 (posição varia com o reagrupamento): ícone por cartão,
# centro no sistema do TILE (x a partir da esquerda, y a partir do topo)
ICONE_CARTAO = {'modulos': 'modulo', 'estrutura': 'furadeira',
                'inversor': 'inversor', 'stringbox': 'stringbox',
                'bateria': 'bateria', 'homolog': 'homologacao'}
CARTAO_ICONE_C, CARTAO_ICONE_LADO = (21.2, 22.0), LADO_M
# bateria e homologação têm o ícone antigo "impresso" no PNG: apaga-se esta área
# (só esses dois — nos outros o PNG já vem sem ícone). A área fica DENTRO da
# curva do canto da borda (moldura a 3 pt do tile, raio ~11): ícone antigo em
# x 11,0–32,7 × y 7,1–37,1; apagar mais que isso cortava o contorno do cartão.
CARTAO_ICONE_APAGA = (10.5, 6.5, 33.5, 38.0)
CARTAO_ICONE_IMPRESSO = ('bateria', 'homolog')
_ICONES_TRACO = None


# conferência (ferramentas/previa.py --caixas): se for uma lista, cada ícone
# desenhado é anotado aqui — página, centro, tamanho e anel — para a ferramenta
# medir a tinta na imagem renderizada. Na proposta normal fica None.
_REGISTRO_ICONES = None


def _icone(c, nome, cx, cyb, lado, cor, aro=None, grupo=None):
    """Desenha o ícone de traço `nome` centrado em (cx, cyb) — y de BAIXO —
    com `lado` pt para a área útil (2..22 da grade 24) e o traço da família."""
    ic = _carregar_icones_traco().get(nome)
    if not ic:
        return False
    if _REGISTRO_ICONES is not None:
        _REGISTRO_ICONES.append(dict(pag=c.getPageNumber(), nome=nome, cx=cx,
                                     cyb=cyb, lado=lado, aro=aro, grupo=grupo))
    traco = _traco_de(lado)
    c.saveState()
    c.setStrokeColor(HexColor(cor))
    c.setLineCap(1)
    c.setLineJoin(1)
    if aro:
        c.setLineWidth(TRACO_ARO)
        c.circle(cx, cyb, aro, stroke=1, fill=0)
    # tamanho óptico (ver _dims), centrado no meio do desenho
    lx0, ly0, lx1, ly1 = ic.get('limites') or (2, 2, 22, 22)
    k = _dims(nome, lado, grupo)[0]
    mx, my = (lx0 + lx1) / 2.0, (ly0 + ly1) / 2.0
    c.transform(k, 0, 0, -k, cx - mx * k, cyb + my * k)   # y do SVG desce
    c.setLineWidth(traco / k)
    c._code.append(ic['ops'] + ' S')
    c.restoreState()
    return True


def _carregar_icones_traco() -> dict:
    global _ICONES_TRACO
    if _ICONES_TRACO is None:
        try:
            with open(os.path.join(ASSETS, 'icones_traco.json'), encoding='utf-8') as f:
                _ICONES_TRACO = json.load(f)
        except OSError:
            _ICONES_TRACO = {}
    return _ICONES_TRACO


def _nomes_do_grupo(rotulo):
    """Nomes dos ícones de um grupo de ICONES_TRACO (mesmo rótulo)."""
    if not rotulo:
        return None
    return tuple(o['nome'] for o in ICONES_TRACO if o['grupo'] == rotulo)


def _icones_traco_pagina(c, pagina, page_h):
    """Apaga cada ícone antigo da página e desenha o da família no lugar.
    Sem o JSON (ou sem o ícone nele) o original fica intocado."""
    icones = _carregar_icones_traco()
    for it in ICONES_TRACO:
        if it['pg'] != pagina or it['nome'] not in icones:
            continue
        c.setFillColor(HexColor('#FFFFFF'))
        ap = it['apaga']
        if ap[0] == 'c':                             # disco (miolo de círculo)
            c.circle(ap[1], page_h - ap[2], ap[3], stroke=0, fill=1)
        else:
            x0, y0, x1, y1 = ap
            c.rect(x0, page_h - y1, x1 - x0, y1 - y0, stroke=0, fill=1)
        grupo = _nomes_do_grupo(it['grupo'])
        cx = it['cx']
        if isinstance(cx, tuple) and cx[0] == 'antes':   # ícone solto antes do texto
            cx = _cx_antes(cx[1], it['lado'], it['nome'], grupo)
        elif isinstance(cx, tuple) and len(cx) > 3:      # LISTA dentro de quadro:
            cx = (cx[1] + cx[3]) / 2.0                   # centro entre borda e texto
        elif isinstance(cx, tuple):                      # ícone de uma LISTA
            cx = _cx_coluna(cx[1], it['lado'], grupo)
        _icone(c, it['nome'], cx, page_h - it['cy'], it['lado'],
               it['cor'], it['aro'], grupo)


# Notas de rodapé reescritas quando o texto da arte não vale para o projeto.
# Medidas no fundo.pdf (Inter Regular, cinza #434F5C, base de cada linha):
#  * pág. 3 (*): x 44,01, 7,498 pt, bases 378,53 e 369,61 — "radiação solar de
#    Maringá e região" só é verdade no perfil 3.8;
#  * pág. 5 (**): x 35,16, 7,948 pt, bases 207,94 e 198,50 — "iluminação
#    pública, tipo de conexão" é conceito do grupo B.
NOTA_P3 = dict(x=44.0117, size=7.497733, bases=(378.5318, 369.6095), larg=276.5)
NOTA_P5 = dict(x=35.1644, size=7.947597, bases=(207.9447, 198.4976), larg=333.5)


def _reescrever_nota(c, nota, texto):
    """Apaga as linhas da nota e escreve `texto` nas mesmas bases, quebrado na
    largura da linha original mais longa (encolhe se não couber em 2 linhas)."""
    fonte = _font_key('Inter', False)
    b1, b2 = nota['bases']
    passo = b1 - b2
    larg = nota.get('larg') or 300.0
    linhas, size = _ajustar_em_caixa(texto, fonte, nota['size'], larg, 2)
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(nota['x'] - 1, b2 - 3.0, larg + 4, passo + nota['size'] + 3.5,
           stroke=0, fill=1)
    c.setFillColor(HexColor('#434F5C'))
    c.setFont(fonte, size)
    for i, linha in enumerate(linhas):
        c.drawString(nota['x'], b1 - i * passo, linha)


# Cartões da pág. 5 no GRUPO A: ganham uma 4ª linha sob o "AO MÊS" ("DEMANDA E
# TAXAS: R$ …" / "NN % A MENOS NA ENERGIA"). Com ela o bloco de textos ficaria
# 6,25 pt abaixo do centro, então o miolo inteiro é redesenhado mais alto.
# Medidas: cartões x 40,2–142,8 · 150,6–253,2 · 261,1–363,8, borda 507,0 → 589,0
# (centro 548,3); conteúdo de 526,8 a 582,3. Títulos e "AO MÊS" vêm da arte
# (Inter Bold 5,923, bases 310,84 e 270,50); os valores (campos fatura_sem…)
# sobem o mesmo GA_DY no laço de campos.
GA_DY = 6.25
GA_CARTOES = (
    # x0, x1, centro, fundo, cor do texto, título (x da arte), "AO MÊS" (x), chave
    (40.2, 142.8, 91.5, '#FFFFFF', '#004D94', ('CONTA SEM S2V ENGENHARIA', 46.18604),
     79.85086, 'ga_fixo_sem'),
    (150.6, 253.2, 201.9, '#FFFFFF', '#004D94', ('CONTA COM S2V ENGENHARIA', 155.9528),
     190.2925, 'ga_fixo_com'),
    (261.1, 363.8, 312.45, '#089C83', '#FFFFFF', ('ECONOMIA', 294.0611),
     299.6844, 'ga_reducao'),
)
# campo do valor de cada cartão -> a 4ª linha dele. O cartão só sobe GA_DY se
# TIVER a 4ª linha (sem redução de energia a mostrar, o de economia fica como na
# arte — subir sem motivo o deixava descentrado).
GA_CAMPOS = {'fatura_sem': 'ga_fixo_sem', 'fatura_com': 'ga_fixo_com',
             'economia_mensal': 'ga_reducao'}


def _cartoes_grupo_a(c, textos, page_h):
    fonte = _font_key('Inter', True)
    for x0, x1, cx, fundo, cor, (tit, xt), xa, chave in GA_CARTOES:
        if not textos.get(chave):
            continue                       # sem 4ª linha: cartão como na arte
        # apaga o miolo sem tocar nos cantos arredondados (raio ~11: de 507 a
        # 518 e de 578 a 589 a curva entra; fora disso pode ir quase à borda —
        # o título da arte é mais largo que o cartão menos 6 pt de cada lado)
        c.setFillColor(HexColor(fundo))
        c.rect(x0 + 2, page_h - 577.0, (x1 - x0) - 4, 577.0 - 518.0,
               stroke=0, fill=1)
        c.rect(x0 + 6, page_h - 583.0, (x1 - x0) - 12, 583.0 - 577.0,
               stroke=0, fill=1)
        c.setFillColor(HexColor(cor))
        c.setFont(fonte, 5.923209)
        c.drawString(xt, 310.8377 + GA_DY, tit)
        c.drawString(xa, 270.4999 + GA_DY, 'AO MÊS')
        c.setFont(fonte, 5.4)
        c.drawCentredString(cx, page_h - 581.2 + GA_DY, textos[chave])


NOTA2_B = ('** Estes valores são referências, e podem sofrer alterações de acordo '
           'com a iluminação pública, tipo de conexão, e simultaneidade de '
           'consumo do cliente.')
NOTA2_A = ('** Estes valores são referências, e podem sofrer alterações de acordo '
           'com a demanda medida, o consumo na ponta e a simultaneidade de '
           'consumo do cliente.')


def _notas_p5(c, textos, grupo_a):
    """Notas de rodapé da pág. 5. A arte traz * (bases 236,74/227,29) e **
    (207,94/198,50), com uma folga de ~1 linha entre elas. No grupo A a ** muda
    de texto. Se a UC já tem usina, entra a *** ("a economia é adicional"):
    as folgas viram iguais e menores (6 pt) para as três caberem acima do
    título "ACEITE DA PROPOSTA" — ** sobe para 211,84/202,39, *** em 186,94."""
    usina = textos.get('nota_usina')
    if not usina:
        if grupo_a:
            _reescrever_nota(c, NOTA_P5, NOTA2_A)
        return
    c.setFillColor(HexColor('#FFFFFF'))                # apaga a ** da arte
    c.rect(34.0, 195.5, 337.0, 22.0, stroke=0, fill=1)
    _reescrever_nota(c, dict(NOTA_P5, bases=(211.84, 202.39)),
                     NOTA2_A if grupo_a else NOTA2_B)
    c.setFillColor(HexColor('#434F5C'))
    c.setFont(_font_key('Inter', False), NOTA_P5['size'])
    c.drawString(NOTA_P5['x'], 186.94, usina)


# FAIXA DA CAPA (cliente · UC · local · sistema) — colunas de LARGURA IGUAL
# sempre que possível (pedido do usuário): o espaço entre colunas é fixo
# (FAIXA_ESPACO, divisória no meio) e as 4 colunas dividem o resto por igual;
# só a coluna cujo conteúdo (ícone + espaço + texto) não cabe na parte igual
# cresce, e as demais repartem o que sobra — nunca menores que o próprio
# conteúdo ("encher por igual"). A 1ª encosta na margem esquerda (37,45) e a
# última termina na direita (558,84, fim da régua verde). Medidas da arte:
# rótulos Inter Bold 10,497 verde com base 660,99; valores (campos do layout)
# Inter Bold 9,9; divisórias de 647,63 a 704,86 (topo). Se nem o conteúdo
# cabe, o texto mais largo quebra antes (a largura máxima dele encolhe).
FAIXA = (('cliente', 'CLIENTE', ('nome_proper',)),
         ('uc', 'UC', ('uc_numero',)),
         ('local', 'LOCAL', ('endereco', 'cidade')),
         ('geracao', 'SISTEMA', ('kwp_txt',)))
FAIXA_X0, FAIXA_X1, FAIXA_ESPACO = 37.45, 558.84, 2 * GAP_M   # divisória→tinta = tinta→texto
FAIXA_NOMES = tuple(f[0] for f in FAIXA)


def _faixa_capa(c, textos, lay, page_h):
    """Desenha rótulos, ícones e divisórias da faixa e devolve, por campo, o
    x e a largura máxima com que o laço de campos deve escrever o valor."""
    campos = {f['field']: f for f in lay['fields'] if f['page'] == 1}
    f_rot = _font_key('Inter', True)
    # largura máxima de partida de cada texto (a faixa é dinâmica, então são
    # folgadas; se faltar espaço o laço abaixo aperta o mais largo, que quebra
    # em linhas em vez de encolher a letra)
    larg_max = {'nome_proper': 130.0, 'uc_numero': 110.0, 'endereco': 150.0,
                'cidade': 150.0, 'kwp_txt': 105.0}

    def largura_texto(campo):
        f = campos.get(campo)
        v = textos.get(campo)
        if not f or not v:
            return 0.0
        st = f['style']
        fonte = _font_key(st['font'], st['bold'])
        linhas, size = _ajustar_em_caixa(str(v), fonte, st['size'],
                                         larg_max[campo], f.get('linhas', 1))
        return max(pdfmetrics.stringWidth(l, fonte, size) for l in linhas)

    util = FAIXA_X1 - FAIXA_X0 - FAIXA_ESPACO * (len(FAIXA) - 1)
    for _ in range(12):
        conteudo = []
        for ic, rot, cs in FAIXA:
            tw = max([pdfmetrics.stringWidth(rot, f_rot, 10.497)]
                     + [largura_texto(k) for k in cs])
            conteudo.append(_dims(ic, LADO_M, FAIXA_NOMES)[1] + GAP_M + tw)
        if sum(conteudo) <= util:
            break
        k = max(larg_max, key=larg_max.get)          # aperta o mais largo
        larg_max[k] *= 0.9
    # "encher por igual": W tal que soma(max(conteúdo, W)) = útil
    resto, livres = util, list(range(len(FAIXA)))
    while True:
        W = resto / len(livres)
        grandes = [i for i in livres if conteudo[i] > W]
        if not grandes:
            break
        for i in grandes:
            resto -= conteudo[i]
            livres.remove(i)
        if not livres:
            break
    larguras = [max(cw, W) if livres else cw for cw in conteudo]
    espaco = FAIXA_ESPACO
    # apaga a faixa da arte (rótulos, ícones e divisórias), acima da régua
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(34.0, page_h - 716.0, 528.0, 716.0 - 644.0, stroke=0, fill=1)
    ovr, x = {}, FAIXA_X0
    for i, ((ic, rot, cs), w) in enumerate(zip(FAIXA, larguras)):
        # a TINTA do ícone (retângulo azul) começa no início da coluna, a meio
        # espaço da divisória, com o topo no topo das maiúsculas do rótulo
        # (653,36); o texto vem GAP_M depois da tinta — sem margens vazias
        _, iw, ih = _dims(ic, LADO_M, FAIXA_NOMES)
        _icone(c, ic, x + iw / 2, page_h - (653.36 + ih / 2), LADO_M, VERDE,
               grupo=FAIXA_NOMES)
        xt = x + iw + GAP_M
        c.setFillColor(HexColor(VERDE))
        c.setFont(f_rot, 10.497)
        c.drawString(xt, page_h - 660.99, rot)
        for k in cs:
            ovr[k] = (xt, larg_max.get(k))
        x += w
        if i < len(FAIXA) - 1:                       # divisória no meio do espaço
            xd = x + espaco / 2
            c.setStrokeColor(HexColor(VERDE))
            c.setLineWidth(0.74)
            c.line(xd, page_h - 647.63, xd, page_h - 704.86)
            x += espaco
    return ovr


# RODAPÉ DA CAPA (telefone · Instagram · e-mail · endereço) — DISTRIBUÍDO:
# cada item é ícone P + 6 pt + texto; o 1º começa na margem (37,34), o último
# termina na direita (558,84) e os espaços entre itens são iguais. Textos da
# arte: Inter 7,948 cinza #434F5C, base 782,13 (topo).
RODAPE = (('whatsapp', '(44) 9 9881-5835'), ('instagram', '@s2v.engenharia'),
          ('email', 'contato@s2vengenharia.com'),
          ('local', 'Av. Pedro Taques, 2577 Sala 08 - Maringá/PR'))


def _rodape_capa(c, page_h):
    fonte, tam, base = _font_key('Inter', False), 7.947597, 782.13
    itens = []
    nomes = tuple(r[0] for r in RODAPE)
    for ic, txt in RODAPE:                          # medido na tinta
        _, iw, ih = _dims(ic, LADO_P, nomes)
        itens.append((ic, txt, iw, ih, pdfmetrics.stringWidth(txt, fonte, tam)))
    total = sum(iw + GAP_P + tw for _, _, iw, _, tw in itens)
    espaco = (FAIXA_X1 - 37.34 - total) / (len(itens) - 1)
    c.setFillColor(HexColor('#FFFFFF'))              # apaga ícones e textos da arte
    c.rect(32.0, page_h - 789.0, 532.0, 789.0 - 769.0, stroke=0, fill=1)
    x = 37.34
    for ic, txt, iw, ih, tw in itens:
        # ícone centrado na altura das maiúsculas do texto (base − 2,9)
        _icone(c, ic, x + iw / 2, page_h - (base - 2.9), LADO_P, VERDE,
               grupo=nomes)
        c.setFillColor(HexColor('#434F5C'))
        c.setFont(fonte, tam)
        c.drawString(x + iw + GAP_P, page_h - base, txt)
        x += iw + GAP_P + tw + espaco


# ------------------------------------------------------------------ gráfico
COR_CONSUMO = '#004D94'
COR_GERACAO = '#089C83'
COR_TEXTO = '#434F5C'
COR_GRADE = '#F2F2F2'
COR_EIXO = '#D9D9D9'


def _unidade_eixo(vmax: float) -> float:
    """Passo 'redondo' semelhante ao automático do Excel (~6 divisões)."""
    if vmax <= 0:
        return 100.0
    bruto = vmax / 6.0
    import math
    mag = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 5, 10):
        if bruto <= m * mag:
            return m * mag
    return 10 * mag


COR_PONTA = '#7FA6C9'      # o azul da marca a 50 % (tinta clara do #004D94)


def _pdf_grafico(consumo_mensal: list[float], geracao_mensal: list[float],
                 w_pt: float, h_pt: float, ponta_mensal=None) -> bytes:
    """Gera o gráfico da página 4 como PDF vetorial transparente.

    `consumo_mensal` são os 12 meses como o usuário digitou: quando ele usou o
    consumo médio rápido os doze vêm iguais e a barra sai reta; quando digitou
    mês a mês, ela acompanha a variação."""
    import math
    meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
             'jul', 'ago', 'set', 'out', 'nov', 'dez']
    fig = plt.figure(figsize=(w_pt / 72.0, h_pt / 72.0))
    # frações medidas no layout novo: a área do gráfico vai de x 130,16 a 508,65
    # e de y 349,96 (zero) a 230,08 (topo), dentro do retângulo 78,74–519,54 ×
    # 195,24–374,72 pt. Assim as barras caem exatamente sobre a arte da página.
    ax = fig.add_axes([0.11665, 0.13796, 0.85864, 0.66794])

    vmax = max(list(consumo_mensal) + list(geracao_mensal) + [1.0])
    passo = _unidade_eixo(vmax)
    ymax = math.ceil(vmax / passo) * passo

    xs = range(12)
    # gapWidth 219 %, overlap −27 % (chart1.xml)
    bw = 1.0 / (2 + 0.27 + 2.19)
    off = bw * 1.27 / 2
    if ponta_mensal and any(ponta_mensal):
        # grupo A: a barra de consumo em duas partes — fora ponta embaixo, no
        # azul da marca, e a ponta em cima, no mesmo azul mais claro
        fora = [max(consumo_mensal[m] - ponta_mensal[m], 0.0) for m in range(12)]
        ax.bar([x - off for x in xs], fora, width=bw,
               color=COR_CONSUMO, label='Consumo fora ponta', zorder=3)
        ax.bar([x - off for x in xs], list(ponta_mensal), width=bw, bottom=fora,
               color=COR_PONTA, label='Consumo ponta', zorder=3)
        ncol_leg = 3
    else:
        ax.bar([x - off for x in xs], list(consumo_mensal), width=bw,
               color=COR_CONSUMO, label='Consumo', zorder=3)
        ncol_leg = 2
    ax.bar([x + off for x in xs], geracao_mensal, width=bw,
           color=COR_GERACAO, label='Geração', zorder=3)

    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(0, ymax)
    ax.set_yticks([passo * i for i in range(int(ymax / passo) + 1)])
    # o rótulo tem ~46 pt à esquerda do eixo: "600 kWh" cabe, "1000 kWh" não
    # (saía cortado como "000 kWh"). A partir de 1.000 o eixo passa a MWh.
    def _rot(v):
        if ymax >= 1000:
            return f'{v / 1000:g}'.replace('.', ',') + ' MWh'
        return f'{v:g} kWh'
    ax.set_yticklabels([_rot(passo * i)
                        for i in range(int(ymax / passo) + 1)])
    ax.set_xticks(list(xs))
    ax.set_xticklabels(meses)
    ax.tick_params(axis='both', length=0, labelsize=9.9, colors=COR_TEXTO,
                   pad=5)
    ax.grid(axis='y', color=COR_GRADE, linewidth=0.74, zorder=0)
    for nome, sp in ax.spines.items():
        if nome == 'bottom':          # a linha do zero é cinza, como na arte
            sp.set_color(COR_EIXO)
            sp.set_linewidth(0.99)
        else:
            sp.set_visible(False)

    leg = fig.legend(loc='upper center', bbox_to_anchor=(0.5096, 0.9451),
                     ncol=ncol_leg, frameon=False, fontsize=9.9,
                     handlelength=0.9, handleheight=0.9, columnspacing=1.4,
                     handletextpad=0.5)
    for t in leg.get_texts():
        t.set_color(COR_TEXTO)

    buf = io.BytesIO()
    fig.savefig(buf, format='pdf', transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _quebrar(valor, fonte, size, max_w):
    """Quebra o texto em linhas que cabem em `max_w`, cortando nos espaços."""
    linhas, atual = [], ''
    for palavra in str(valor).split(' '):
        teste = f'{atual} {palavra}'.strip()
        if not atual or pdfmetrics.stringWidth(teste, fonte, size) <= max_w:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _ajustar_em_caixa(valor, fonte, size, max_w, linhas_max=1, min_ratio=0.62):
    """Encaixa o texto na área reservada do layout.

    Primeiro tenta o tamanho normal; se não couber, vai diminuindo a fonte e,
    quando o campo permite mais de uma linha, quebra nos espaços. Só corta com
    reticências se nem no menor tamanho couber — assim o nome de um cliente
    comprido nunca invade a coluna do lado."""
    valor = str(valor)
    if not max_w:
        return [valor], size
    piso = size * min_ratio
    s = size
    while s >= piso:
        linhas = _quebrar(valor, fonte, s, max_w)
        if (len(linhas) <= linhas_max
                and all(pdfmetrics.stringWidth(l, fonte, s) <= max_w
                        for l in linhas)):
            return linhas, s
        s -= 0.25
    s = piso
    linhas = _quebrar(valor, fonte, s, max_w)
    if len(linhas) > linhas_max:
        linhas = linhas[:linhas_max]
    ultima = linhas[-1]
    if pdfmetrics.stringWidth(ultima, fonte, s) > max_w \
            or len(_quebrar(valor, fonte, s, max_w)) > linhas_max:
        while len(ultima) > 1 and pdfmetrics.stringWidth(
                ultima + '…', fonte, s) > max_w:
            ultima = ultima[:-1].rstrip()
        linhas[-1] = ultima + '…'
    return linhas, s


def _texto_ajustado(c, valor, fonte, size, min_ratio, max_w):
    """Encolhe a fonte até caber em max_w; se não couber, corta com reticências.
    Retorna (valor, size)."""
    if max_w:
        while size > size * 0 + min_ratio and \
                pdfmetrics.stringWidth(valor, fonte, size) > max_w:
            size -= 0.25
        if pdfmetrics.stringWidth(valor, fonte, size) > max_w:
            while len(valor) > 1 and pdfmetrics.stringWidth(
                    valor + '…', fonte, size) > max_w:
                valor = valor[:-1].rstrip()
            valor += '…'
    return valor, size


def _desenhar_campo_cartao(c, spec, x0, top, valor, page_h):
    """Desenha qtd/desc de um cartão dado o topo-esq (x0, top) do tile."""
    if not valor:
        return
    fonte = _font_key(spec['font'], spec['bold'])
    size = spec['size']
    valor, size = _texto_ajustado(c, str(valor), fonte, size,
                                  spec['size'] * 0.62, spec.get('max_w'))
    baseline = page_h - (top + spec['dbaseline'])
    c.setFont(fonte, size)
    c.setFillColor(HexColor('#' + spec['color']))
    if spec.get('algn') == 'c':
        c.drawCentredString(x0 + spec['cx'], baseline, valor)
    elif spec.get('algn') == 'r':
        c.drawRightString(x0 + spec['dx'] + (spec.get('max_w') or 0),
                          baseline, valor)
    else:
        c.drawString(x0 + spec['dx'], baseline, valor)


def _slots_dinamicos(meta, n):
    """Posições (x0_ou_'centro', top) dos `n` cartões presentes.

    As linhas ficam SEMPRE nas posições medidas dos slots — fiéis à arte e,
    principalmente, alinhadas aos ícones da 1ª linha (painel/furadeira), que são
    parte do fundo e não podem se mover. Os cartões preenchem de cima para baixo,
    sem buracos (string box e/ou bateria ausentes já saem de `ordem`). A única
    diferença em relação à planilha: quando a última linha fica com um único
    cartão (n ímpar), ele é centralizado entre as duas colunas, para não deixar
    um "buraco" à direita. Assim os cartões ficam sempre agrupados e alinhados."""
    slots6 = meta['slots']
    pos = [(s[0], s[1]) for s in slots6[:n]]
    if n % 2 == 1:                       # última linha com um só cartão → centro
        pos[-1] = ('centro', slots6[n - 1][1])
    # Bloco mais curto (sem string box nem bateria) desce para ficar centrado
    # com a tabela de números ao lado, em vez de sobrar espaço embaixo.
    desloc = 0.0
    al = meta.get('alinhar')
    if al:
        mg = meta.get('margem', 0.0)
        alt = meta['cards']['modulos']['h'] - 2 * mg      # altura da moldura
        topo = min(t for _, t in pos)
        base = max(t for _, t in pos) + alt
        d = max(0.0, al['centro_y'] - (topo + base) / 2.0)
        if d > 0.5:
            desloc = d
            pos = [(x, t + desloc) for x, t in pos]
    return pos, desloc


def _desenhar_cards_p3(c, canvas_imagem, textos, resultado, page_h):
    """Redesenha o bloco de 6 cartões da página 3, agrupando os presentes sem
    deixar buracos quando string box e/ou bateria estão ausentes.

    `canvas_imagem(nome_tile, x0, top, w, h)` desenha o tile PNG do cartão.
    """
    meta = _carregar_cards()
    cards = meta['cards']
    reg = meta['regiao']

    ocultar = set(resultado.get('ocultar_cartoes') or [])

    # ordem natural; remove os cartões ausentes → sem lacunas
    ordem = ['modulos', 'estrutura', 'inversor']
    if 'stringbox' not in ocultar:
        ordem.append('stringbox')
    if 'bateria' not in ocultar:
        ordem.append('bateria')
    ordem.append('homolog')

    # textos de cada cartão (qtd, desc)
    # (quantidade, descrição, título). O título só varia no cartão do inversor.
    texto_de = {
        'modulos': ('mod_qtd', 'mod_desc', None),
        'estrutura': ('estr_qtd', 'estr_desc', None),
        'inversor': ('inv_qtd', 'inv_desc', 'inv_titulo'),
        'stringbox': ('sb_qtd', 'sb_desc', None),
        'bateria': ('bat_qtd', 'bat_desc', None),
        'homolog': (None, None, None),
    }

    # 1) limpa a região dos cartões (fundo branco da página). O topo em
    #    `regiao.top` (258) é proposital: os ícones da 1ª linha (painel/furadeira)
    #    são parte do fundo, logo acima, e devem permanecer — por isso a 1ª linha
    #    fica sempre na posição medida (ver _slots_dinamicos).
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(reg['x0'], page_h - reg['bottom'],
           reg['x1'] - reg['x0'], reg['bottom'] - reg['top'],
           stroke=0, fill=1)

    # 2) estampa cada cartão presente na posição calculada e escreve qtd/desc
    pos, desloc = _slots_dinamicos(meta, len(ordem))
    # o título "KIT GERADOR FOTOVOLTAICO" desce junto com o bloco (só 4 cartões)
    tit = meta.get('titulo')
    if tit:
        fonte = _font_key(tit['font'], tit['bold'])
        c.setFont(fonte, tit['size'])
        c.setFillColor(HexColor('#' + tit['color']))
        c.drawString(tit['x'], page_h - (tit['base'] + desloc), tit['text'])
    centro_x = (reg['x0'] + reg['x1']) / 2.0
    mg = meta.get('margem', 0.0)
    for i, nome in enumerate(ordem):
        px, stop = pos[i]
        m = cards[nome]
        # o tile tem uma folga em volta para a borda cinza não ser cortada;
        # `sx0`/`stop` são a moldura, então a estampa recua a folga
        sx0 = (centro_x - m['w'] / 2.0 + mg) if px == 'centro' else px
        canvas_imagem(nome, sx0 - mg, stop - mg, m['w'], m['h'])
        fq, fd, ft = texto_de[nome]
        if ft and 'titulo' in m:
            _desenhar_campo_cartao(c, m['titulo'], sx0, stop,
                                   textos.get(ft), page_h)
        if fq and 'qtd' in m:
            _desenhar_campo_cartao(c, m['qtd'], sx0, stop, textos.get(fq), page_h)
        if fd and 'desc' in m:
            # string box padrão usa a descrição "Projeto aprovado COPEL" que já
            # vem no tile; só escreve se houver descrição própria
            if nome == 'stringbox' and not resultado.get('sb_custom'):
                pass
            else:
                _desenhar_campo_cartao(c, m['desc'], sx0, stop,
                                       textos.get(fd), page_h)


def _desenhar_fotos_p3(c, imagens, page_h):
    """Cobre as fotos genéricas (módulo/inversor) chapadas no fundo da pág. 3 e
    desenha, no lugar, as imagens que o usuário colou na tela.

    `imagens` é um dict de bytes: {'modulo': b'…', 'inversor': b'…'} — qualquer
    uma pode faltar. Se NENHUMA foto for colada, não cobre nada: mantém a arte
    genérica do fundo (assim a proposta nunca sai com um vão branco). Havendo ao
    menos uma foto, cobre a área das duas e desenha as coladas — cada uma
    encaixada mantendo a proporção e centralizada no seu espaço; as GARANTIAS (à
    direita) e o quadro do card não são tocados. Geometria em assets/deco.json."""
    imagens = {k: v for k, v in (imagens or {}).items() if v}
    if not imagens:
        return
    d = _carregar_deco().get('fotos_p3')
    if not d:
        return
    cb = d['cobrir']
    c.setFillColor(HexColor('#FFFFFF'))
    c.rect(cb['x0'], page_h - cb['bottom'], cb['x1'] - cb['x0'],
           cb['bottom'] - cb['top'], stroke=0, fill=1)
    for chave in ('modulo', 'inversor'):
        dados = imagens.get(chave)
        slot = d.get(chave)
        if not dados or not slot:
            continue
        try:
            img = ImageReader(io.BytesIO(dados))
        except Exception:          # imagem inválida: mantém o espaço em branco
            continue
        w = slot['x1'] - slot['x0']
        h = slot['bottom'] - slot['top']
        c.drawImage(img, slot['x0'], page_h - (slot['top'] + h),
                    width=w, height=h, preserveAspectRatio=True,
                    anchor='c', mask='auto')


# ------------------------------------------------------------------ overlay
# bandeira de cartão (bloco único de logos VISA/AmEx/Master/Elo/Hipercard) na
# coluna CARTÃO DE CRÉDITO da pág. 5 — vem levemente à esquerda no fundo.
_LOGO_BANDEIRAS = '/FormXob.0bba7f3951b1bf95c99742fb24b11694'


def _cm_antes(ops, idx):
    """Retorna o operando-lista do `cm` imediatamente anterior ao índice idx."""
    for j in range(idx - 1, -1, -1):
        oj = ops[j][1]
        oj = oj.decode() if isinstance(oj, bytes) else oj
        if oj == 'cm':
            return ops[j][0]
    return None


def _ajustar_cartao_p5(page, pdf, dx: float) -> None:
    """Pág. 5, editando o fluxo do fundo (página já anexada ao writer):
      1. APAGA de vez o texto "EM ATÉ 12X + TAXA DA MAQUININHA" (esvazia o Tj);
      2. desce a seção OPÇÕES DE PARCELAMENTO 2pt (SECAO): bordas dos dois quadros
         cinza (traços), 12 logos, títulos "CARTÃO DE CRÉDITO"/"FINANCIAMENTO" e o
         próprio "OPÇÕES" (este 2pt a mais, pois já vinha 2pt abaixo);
      3. centra o bloco de bandeiras no quadro: +dx em x e +BANDEIRAS_DY em y
         (10 = +12 p/ alinhar o centro ao dos logos do financiamento −2 da seção).
    O "RETORNO FINANCEIRO" volta à posição original (não é mais deslocado): subi-lo
    antes o afastava da própria seção (conteúdo logo abaixo)."""
    SECAO = -2.0            # a seção de parcelamento inteira desce 2pt
    BANDEIRAS_DY = 10.0     # +12 (centra) −2 (acompanha a seção)
    cs = ContentStream(page.get_contents(), pdf)
    ops = cs.operations
    ult_tm = None
    path = []              # ops de construção de caminho desde a última limpeza
    for idx, (operandos, op) in enumerate(ops):
        o = op.decode() if isinstance(op, bytes) else op
        if o == 'Tm':
            ult_tm = operandos
        elif o in ('m', 'l', 'c', 're'):
            path.append((operandos, o))
        elif o in ('S', 's'):                     # traço fechado
            ys = [float(od[1]) for od, oo in path]  # 1º y de cada op basta p/ faixa
            if ys and 383 < min(ys) and max(ys) < 490:   # borda de um quadro cinza
                for od, oo in path:
                    iy = [1] if oo == 're' else range(1, len(od), 2)
                    for i in iy:
                        od[i] = FloatObject(float(od[i]) + SECAO)
            path = []
        elif o in ('f', 'f*', 'F', 'B', 'B*', 'b', 'b*', 'n'):
            path = []
        elif o == 'Tj' and 'MAQUININHA' in str(operandos[0]):
            operandos[0] = TextStringObject('')
        elif o == 'Tj' and 'PARCELAMENTO' in str(operandos[0]) and ult_tm:
            ult_tm[5] = FloatObject(float(ult_tm[5]) + SECAO - 2.0)   # OPÇÕES: −4 total
        elif o == 'Tj' and ('CART' in str(operandos[0])
                            or 'FINANCIAMENTO' in str(operandos[0])) and ult_tm:
            ult_tm[5] = FloatObject(float(ult_tm[5]) + SECAO)         # títulos dos quadros
        elif o == 'Do':
            cm = _cm_antes(ops, idx)
            if cm is None:
                continue
            if str(operandos[0]) == _LOGO_BANDEIRAS:
                cm[4] = FloatObject(float(cm[4]) + dx)
                cm[5] = FloatObject(float(cm[5]) + BANDEIRAS_DY)
            elif 383 < float(cm[5]) < 490:                            # logos do financiamento
                cm[5] = FloatObject(float(cm[5]) + SECAO)
    page.replace_contents(cs)


def gerar_proposta(resultado: dict, caminho_saida: str,
                   textos_extra: dict | None = None,
                   imagens: dict | None = None) -> str:
    """Monta o PDF final da proposta a partir do `resultado` de engine.calcular().
    `textos_extra` permite sobrescrever qualquer texto (usado nos testes).
    `imagens` traz as fotos coladas do módulo/inversor (bytes) para a pág. 3."""
    _registrar_fontes()
    lay = _carregar_layout()
    textos = dict(resultado['textos'])
    if textos_extra:
        textos.update(textos_extra)

    page_w, page_h = lay['page_size']
    ocultar = set(resultado.get('ocultar_cartoes') or [])
    cards = lay.get('cards_p3', {})
    # campos da página 3 que agora são desenhados pelo renderizador de cartões
    CAMPOS_CARTAO = {'mod_qtd', 'mod_desc', 'estr_qtd', 'estr_desc',
                     'inv_qtd', 'inv_titulo', 'inv_desc', 'sb_qtd', 'sb_desc',
                     'bat_qtd', 'bat_desc'}

    # 1) overlay de textos (reportlab)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    for pagina in range(1, 6):
        _icones_traco_pagina(c, pagina, page_h)     # ícones: uma família só
        local = textos.get('irrad_local', 'Maringá')
        if pagina == 3 and local != 'Maringá':
            onde = f'de {local} e região' if local else 'da região do projeto'
            _reescrever_nota(c, NOTA_P3,
                             f'* Valor calculado com base na média histórica de '
                             f'radiação solar {onde}, e sujeito a variação em '
                             f'função das condições climáticas.')
        if pagina == 5 and textos.get('ga_fixo_sem'):
            _cartoes_grupo_a(c, textos, page_h)
        if pagina == 5:
            _notas_p5(c, textos, resultado.get('tem_grupo_a'))
        faixa_ovr = {}
        if pagina == 1:
            # capa: estende a foto das placas até a borda direita
            _estender_cover(c, page_h)
            faixa_ovr = _faixa_capa(c, textos, lay, page_h)
            _rodape_capa(c, page_h)
        if pagina == 3:
            # bloco de cartões: agrupa os presentes sem lacunas
            def _stamp(nome, x0, top, w, h):
                caminho = os.path.join(ASSETS, 'cards', f'{nome}.png')
                c.drawImage(caminho, x0, page_h - (top + h), width=w, height=h,
                            mask='auto', preserveAspectRatio=False)
                # ícone do cartão: o da família (traço), no centro medido do
                # ícone original; bateria/homologação o trazem "impresso" no PNG
                ic = ICONE_CARTAO.get(nome)
                if ic and ic in _carregar_icones_traco():
                    if nome in CARTAO_ICONE_IMPRESSO:
                        ax0, ay0, ax1, ay1 = CARTAO_ICONE_APAGA
                        c.setFillColor(HexColor('#FFFFFF'))
                        c.rect(x0 + ax0, page_h - (top + ay1), ax1 - ax0,
                               ay1 - ay0, stroke=0, fill=1)
                    _icone(c, ic, x0 + CARTAO_ICONE_C[0],
                           page_h - (top + CARTAO_ICONE_C[1]),
                           CARTAO_ICONE_LADO, VERDE,
                           grupo=tuple(ICONE_CARTAO.values()))
                else:          # sem o JSON: o ícone vetorizado antigo
                    _desenhar_icones(c, _carregar_cards()['cards'].get(nome, {})
                                     .get('icones'), x0, page_h - (top + h))
            _desenhar_cards_p3(c, _stamp, textos, resultado, page_h)

            # fotos do módulo/inversor coladas na tela (cobrem a arte genérica
            # chapada no fundo — sempre, mesmo sem imagem)
            _desenhar_fotos_p3(c, imagens, page_h)

            # garantia da bateria: some com a linha quando não há bateria.
            # Apaga ANTES de estampar o bloco das 3 fixas, senão comeria o pé
            # dele — que, sem bateria, desce justamente para essa faixa.
            if 'bateria' in ocultar:
                gz = cards.get('gar_bateria_zona')
                if gz:
                    c.setFillColor(HexColor('#FFFFFF'))
                    c.rect(gz['x0'], page_h - gz['bottom'],
                           gz['x1'] - gz['x0'], gz['bottom'] - gz['top'],
                           stroke=0, fill=1)

            # bloco das garantias (redesenhado inteiro, ver _garantias_painel)
            gr = _carregar_cards().get('garantias')
            if gr:
                _garantias_painel(c, gr, page_h, 'bateria' not in ocultar)
            # Grupo A: "demanda" lá é a de kW, que o solar NÃO cobre. O rótulo
            # fixo "COBERTURA DA DEMANDA" (Sora Bold 8,92 #089C83, x 76,55,
            # base 416,35 — medido no fundo.pdf) é coberto de branco e reescrito.
            if resultado.get('tem_grupo_a'):
                c.setFillColor(HexColor('#FFFFFF'))
                c.rect(76.0, 414.0, 128.5, 11.0, stroke=0, fill=1)
                c.setFillColor(HexColor('#089C83'))
                c.setFont(_font_key('Sora', True), 8.9223)
                c.drawString(76.5518, 416.3517, 'COBERTURA DO CONSUMO')
        if pagina == 4:
            # redesenha a timeline de etapas com círculos perfeitos
            _redesenhar_timeline(c, page_h)
        if pagina == 5:
            # o cabeçalho da arte diz "04 | PROPOSTA COMERCIAL" também aqui (veio
            # assim do design). Só o dígito "4" é coberto e reescrito como "5":
            # JetBrains Mono 10,947 #004D94, origem x 44,057 base 793,968 —
            # medido no fundo.pdf; fonte monoespaçada, a largura não muda.
            c.setFillColor(HexColor('#FFFFFF'))
            c.rect(44.0, 792.8, 6.2, 10.0, stroke=0, fill=1)
            c.setFillColor(HexColor('#004D94'))
            c.setFont(_font_key('JetBrainsMono', False), 10.947)
            c.drawString(44.057, 793.968, '5')
            # quadro azul do "à vista": o original é #004D94 x[168,4;426,1]
            # y[520,5;611,2] (raio ~11). Redesenho MAIOR e um pouco mais ALTO por
            # cima do original — mesma cor/raio, então casa sem emenda — para o
            # bloco de textos (valor · À VISTA · ou · condição) ficar centrado
            # nele. O "À VISTA" queimado no fundo (baseline 534,6) some coberto e
            # é reescrito MENOR; abaixo dele um "ou" discreto antes da condição.
            c.setFillColor(HexColor('#004D94'))
            c.roundRect(168.4, 510.0, 257.7, 102.0, 11, stroke=0, fill=1)  # topo 612 fixo
            # "À VISTA" e "ou" em cinza claro (#D9D9D9, a cor do quadro dos logos),
            # mais discretos que o branco do valor/condição.
            c.setFillColor(HexColor('#D9D9D9'))
            c.setFont(_font_key('Sora', False), 10.5)      # 1px menor
            c.drawCentredString(297.25, 557.0, 'À VISTA')
            c.setFont(_font_key('Sora', False), 9.5)       # "ou" discreto
            c.drawCentredString(297.25, 542.0, 'ou')
        # capa: a cidade vem logo abaixo da ÚLTIMA linha do endereço, com o mesmo
        # passo (1,2 × fonte) do nome do cliente. Antes ela ficava sempre 2
        # linhas abaixo (lugar reservado p/ endereço longo) e, com endereço de
        # uma linha, sobrava uma linha em branco no meio.
        ENCADEADO = {'cidade': 'endereco'} if pagina == 1 else {}
        proxima = {}                       # campo -> baseline da linha seguinte
        for f in lay['fields']:
            if f['page'] != pagina:
                continue
            if pagina == 3 and f['field'] in CAMPOS_CARTAO:
                continue  # tratados por _desenhar_cards_p3
            if f['field'] == 'gar_bateria' and 'bateria' in ocultar:
                continue
            valor = textos.get(f['field'])
            if not valor:
                continue
            valor = str(valor)
            st = f['style']
            fonte = _font_key(st['font'], st['bold'])
            box = f['box']
            max_w = f.get('max_w')
            if f['field'] in faixa_ovr:      # faixa da capa: posição dinâmica
                xo, mw = faixa_ovr[f['field']]
                box = dict(box, x0=xo)
                max_w = mw or max_w
            linhas, size = _ajustar_em_caixa(
                valor, fonte, st['size'], max_w, f.get('linhas', 1))
            desc = pdfmetrics.getDescent(fonte, size)      # negativo, em pt
            baseline = box['y0'] - desc
            # anos das garantias: seguem o painel redesenhado
            dx_campo = GAR_AJUSTE['dx'] if f['field'] in CAMPOS_GARANTIA else 0.0
            if textos.get(GA_CAMPOS.get(f['field'], '')):
                baseline += GA_DY          # cartão do grupo A com 4ª linha: mais alto
            sub = (textos.get('consumo_postos')
                   if f['field'] == 'consumo_txt' else None)
            if sub:
                # grupo A: valor + sublinha "ponta · fora ponta", o PAR centrado
                # na célula (linhas da tabela em 290 e 328 no topo -> centro 309)
                baseline = page_h - 309.0 + 1.2
            if f.get('desloca_sem_bateria') and 'bateria' in ocultar:
                baseline -= GAR_AJUSTE['dy']
            pai = ENCADEADO.get(f['field'])
            if pai and pai in proxima:
                baseline = proxima[pai]
            elif pai:                      # endereço vazio: a cidade sobe p/ o lugar dele
                fp = next((x for x in lay['fields']
                           if x['page'] == pagina and x['field'] == pai), None)
                if fp:
                    baseline = fp['box']['y0'] - desc
            c.saveState()
            c.translate(dx_campo, 0)
            c.setFont(fonte, size)
            c.setFillColor(HexColor('#' + st['color']))
            algn = f.get('algn', 'l')
            for n_linha, texto_linha in enumerate(linhas):
                y_linha = baseline - n_linha * size * 1.2
                if algn == 'c':
                    c.drawCentredString(
                        f.get('cx', (box['x0'] + box['x1']) / 2),
                        y_linha, texto_linha)
                elif algn == 'r':
                    c.drawRightString(box['x1'], y_linha, texto_linha)
                else:
                    c.drawString(box['x0'], y_linha, texto_linha)
            if sub:
                c.setFont(_font_key('Inter', False), 6.0)
                c.setFillColor(HexColor('#434F5C'))
                c.drawString(box['x0'], baseline - 8.6, sub)
            c.restoreState()
            proxima[f['field']] = baseline - len(linhas) * size * 1.2
        c.showPage()
    c.save()
    buf.seek(0)
    overlay = PdfReader(buf)

    # 2) gráfico da página 4
    rx0, rtop, rx1, rbot = lay['chart_rect_pt_top']
    gw, gh = rx1 - rx0, rbot - rtop
    consumo_mes = (resultado.get('consumo_mensal')
                   or [resultado['consumo_medio']] * 12)
    graf_pdf = PdfReader(io.BytesIO(_pdf_grafico(
        consumo_mes, resultado['geracao_mensal'], gw, gh,
        resultado.get('consumo_ponta_mensal'))))
    graf_page = graf_pdf.pages[0]

    # 3) mescla com o fundo
    fundo = PdfReader(os.path.join(ASSETS, 'fundo.pdf'))
    out = PdfWriter()
    for i, page in enumerate(fundo.pages):
        page.merge_page(overlay.pages[i])
        if i == 3:  # página 4 — posiciona o gráfico
            ty = page_h - rbot
            page.merge_transformed_page(
                graf_page, Transformation().translate(tx=rx0, ty=ty))
        out.add_page(page)
        if i == 4:  # página 5 — centra logos, apaga texto, desce a seção 2pt
            _ajustar_cartao_p5(out.pages[i], out, dx=5.1)

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with open(caminho_saida, 'wb') as f:
        out.write(f)
    return caminho_saida
