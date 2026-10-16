# -*- coding: utf-8 -*-
"""
PDF da proposta de instalação de CARREGADOR VEICULAR (2 páginas).

Mesma ideia da proposta solar: a arte vem pronta em `assets/wallbox/fundo.pdf`
(o PDF do design com os campos "[...]" apagados por
`ferramentas/wallbox_fundo.py`) e os valores são escritos por cima, cada um na
posição e na fonte do colchete que ocupava. As posições abaixo foram LIDAS do
PDF do design (o build lista cada uma) — se o design mudar, releia, não chute.
"""
from __future__ import annotations

import io
import os

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

BASE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(BASE, 'assets', 'fonts')
FUNDO = os.path.join(BASE, 'assets', 'wallbox', 'fundo.pdf')

AZUL = Color(0, .301961, .580392)          # #004D94 — valores (como "7 DIAS")
CINZA = Color(.356863, .384314, .439216)   # texto corrido das notas
BRANCO = Color(1, 1, 1)
VERDE = Color(.031373, .611765, .513725)   # #089C83 — rótulos dos cartões

ESCURO = Color(.184314, .203922, .25098)   # texto corrido do painel (#2F3440)
CINZA_CX = Color(.952941, .968627, .972549)  # fundo do painel (#F3F7F8)

# Pág. 1 — a faixa do painel "PROTEÇÃO E ATERRAMENTO" da arte (38–557,28 ×
# 79,89–293,89 pt, cantos de 14 pt) foi APAGADA do fundo
# (`ferramentas/wallbox_fundo.py`) e é redesenhada aqui, SIMPLIFICADA, na
# metade direita; na esquerda vai a foto da CLAMPER Mobi, grande (pedido do
# usuário: a foto sob o logo da pág. 2 ficava pequena demais). Sem foto, o
# painel volta a ocupar a largura toda, em duas colunas.
FAIXA = dict(x0=38.0, x1=557.2756, y0=79.88976, y1=293.8898, raio=14.0)
VAO = 14.0                                   # entre a foto e o painel
# itens: (negrito azul, complemento) — um por "bolinha", duas linhas cada
ITENS_PROTECAO = [
    ('Circuito exclusivo', 'do quadro geral até o carregador'),
    ('Cabos de cobre', 'seção calculada pela NBR 5410'),
    ('Proteção CLAMPER Mobi', 'DR 30 mA, DPS e disjuntor num só quadro'),
    ('Aterramento', 'haste e condutor de proteção (PE) exclusivo'),
    ('Medição em campo', 'aterramento e teste do DR, com registro'),
    ('Padrão de entrada', 'verificação da carga e do disjuntor geral'),
]

# fonte do design → arquivo
_FONTES = {'Outfit-Bold': 'Outfit-Bold.ttf', 'WorkSans': 'WorkSans-Regular.ttf',
           'WorkSans-Bold': 'WorkSans-Bold.ttf'}

# campo: (página, x, y da linha de base, fonte, tamanho, cor,
#         alinhamento, largura máxima, nº máx. de linhas, entrelinha)
# alinhamento 'c' = x é o CENTRO. Largura máxima = até a divisória/borda.
CAMPOS = {
    # pág. 1 — faixa da capa (colunas separadas por divisórias em 168/320/452)
    'cliente':     (0, 68, 470.8898, 'WorkSans-Bold', 9, AZUL, 'l', 92, 3, 11.5),
    'local':       (0, 208, 470.8898, 'WorkSans-Bold', 9, AZUL, 'l', 104, 2, 11.5),
    'modelo':      (0, 360, 470.8898, 'WorkSans-Bold', 9, AZUL, 'l', 84, 3, 11.5),
    'potencia':    (0, 492, 470.8898, 'WorkSans-Bold', 9, AZUL, 'l', 64, 2, 11.5),
    # pág. 1 — cartões do escopo técnico (cartão de 38 a ~153 pt, etc.)
    'alimentacao': (0, 49, 318.8898, 'Outfit-Bold', 9.5, AZUL, 'l', 100, 1, 0),
    'corrente':    (0, 180.8189, 318.8898, 'Outfit-Bold', 9.5, AZUL, 'l', 100, 1, 0),
    'distancia':   (0, 444.4567, 318.8898, 'Outfit-Bold', 9.5, AZUL, 'l', 100, 1, 0),
    # pág. 2 — quadro azul do investimento (38–338 pt, centro 188)
    'valor':       (1, 188, 585.8898, 'Outfit-Bold', 34, BRANCO, 'c', 270, 1, 0),
    'parcelamento': (1, 188, 539.8898, 'WorkSans-Bold', 11.5, BRANCO, 'c', 270, 1, 0),
    # pág. 2 — cartões da direita (texto de 382 até a borda em ~550)
    'garantia':    (1, 382, 614.8898, 'Outfit-Bold', 9.5, AZUL, 'l', 160, 1, 0),
    'prazo':       (1, 382, 553.2898, 'Outfit-Bold', 9.5, AZUL, 'l', 160, 1, 0),
    # pág. 2 — "Referência:" da nota * e o aceite (linha de 70 a 250, centro 160)
    'referencia':  (1, 262.9495, 261.8898, 'WorkSans', 7.3, CINZA, 'l', 280, 1, 0),
    'cliente_aceite': (1, 160, 128.8898, 'WorkSans-Bold', 8.5, AZUL, 'c', 180, 1, 0),
}


def _registrar_fontes() -> None:
    for nome, arq in _FONTES.items():
        if nome not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nome, os.path.join(FONTS, arq)))


def _quebrar(txt: str, fonte: str, tam: float, larg: float) -> list:
    """Quebra por palavras; palavra maior que a largura fica sozinha na linha."""
    linhas, atual = [], ''
    for p in txt.split():
        teste = (atual + ' ' + p).strip()
        if atual and pdfmetrics.stringWidth(teste, fonte, tam) > larg:
            linhas.append(atual)
            atual = p
        else:
            atual = teste
    if atual:
        linhas.append(atual)
    return linhas


def _escrever(c, txt: str, x, y, fonte, tam, cor, alin, larg, max_lin, entre):
    """Escreve no lugar do colchete. Cabe numa linha → igual ao design. Senão,
    quebra em até `max_lin` linhas; se ainda não couber, reduz a letra (até 70 %)."""
    if not txt:
        return 0
    c.setFillColor(cor)
    t = tam
    while True:
        linhas = ([txt] if max_lin == 1 else _quebrar(txt, fonte, t, larg))
        larg_max = max(pdfmetrics.stringWidth(ln, fonte, t) for ln in linhas)
        if (len(linhas) <= max_lin and larg_max <= larg) or t <= tam * 0.7:
            break
        t = round(t - 0.25, 2)
    for i, ln in enumerate(linhas[:max_lin]):
        c.setFont(fonte, t)
        yy = y - i * (entre * t / tam)
        if alin == 'c':
            c.drawCentredString(x, yy, ln)
        else:
            c.drawString(x, yy, ln)
    return min(len(linhas), max_lin)


def _imagem(foto: bytes | None):
    """ImageReader da foto, ou None se não houver/for ilegível."""
    if not foto:
        return None
    from reportlab.lib.utils import ImageReader
    try:
        img = ImageReader(io.BytesIO(foto))
        img.getSize()
        return img
    except Exception:                                          # noqa: BLE001
        return None


def _foto_mobi(c, img, x0: float, x1: float, legenda: str) -> None:
    """Foto inteira (sem cortar nem distorcer), o maior possível na metade
    esquerda da faixa, com a legenda verde embaixo."""
    f = FAIXA
    y0 = f['y0'] + (16 if legenda else 0)        # espaço da legenda
    iw, ih = img.getSize()
    esc = min((x1 - x0) / iw, (f['y1'] - y0) / ih)
    w, h = iw * esc, ih * esc
    c.drawImage(img, (x0 + x1 - w) / 2, y0 + (f['y1'] - y0 - h) / 2, w, h,
                mask='auto')
    if legenda:
        _escrever(c, legenda, (x0 + x1) / 2, f['y0'] + 3, 'WorkSans-Bold', 9.5,
                  VERDE, 'c', x1 - x0, 1, 0)


def _painel_protecao(c, x0: float, x1: float, colunas: int) -> None:
    """O painel "PROTEÇÃO E ATERRAMENTO" no estilo da arte (fundo #F3F7F8,
    ícone de terra, título verde 11 pt, bolinhas verdes com ✓ branco), mas com
    6 itens curtos: negrito azul + uma linha de complemento."""
    f = FAIXA
    c.setFillColor(CINZA_CX)
    c.roundRect(x0, f['y0'], x1 - x0, f['y1'] - f['y0'], f['raio'], stroke=0, fill=1)
    # ícone de terra e título (mesmas medidas da arte, a partir da borda)
    c.setStrokeColor(VERDE)
    c.setLineWidth(1.4)
    ix = x0 + 26                                  # eixo do ícone (arte: 64)
    for xa, ya, xb, yb in ((0, 277.8898, 0, 266.8898), (-10, 266.8898, 10, 266.8898),
                           (-6.5, 262.8898, 6.5, 262.8898), (-3, 258.8898, 3, 258.8898)):
        c.line(ix + xa, ya, ix + xb, yb)
    _escrever(c, 'PROTEÇÃO E ATERRAMENTO', x0 + 48, 269.8898, 'WorkSans-Bold', 11,
              VERDE, 'l', x1 - x0 - 60, 1, 0)
    # itens em `colunas` colunas, de cima para baixo
    por_col = -(-len(ITENS_PROTECAO) // colunas)
    larg_col = (x1 - x0 - 14) / colunas
    for i, (negrito, resto) in enumerate(ITENS_PROTECAO):
        col, lin = divmod(i, por_col)
        bx = x0 + 14 + col * larg_col             # bolinha (arte: 52,5–63,5)
        # mesma faixa vertical (239,9 → 109,9) com 1 ou 2 colunas
        base = 239.8898 - lin * (130.0 / max(por_col - 1, 1))
        c.setFillColor(VERDE)
        c.circle(bx + 6, base + 3, 5.5, stroke=0, fill=1)
        c.setStrokeColor(BRANCO)
        c.setLineWidth(1.3)
        pth = c.beginPath()
        pth.moveTo(bx + 3.4, base + 3)
        pth.lineTo(bx + 5.4, base + 1)
        pth.lineTo(bx + 8.8, base + 5.2)
        c.drawPath(pth, stroke=1, fill=0)
        tx, larg = bx + 17, larg_col - 31
        _escrever(c, negrito, tx, base, 'WorkSans-Bold', 8.4, AZUL, 'l', larg, 1, 0)
        _escrever(c, resto, tx, base - 10.5, 'WorkSans', 8.4, ESCURO, 'l', larg, 1, 0)


def _faixa_protecao(c, foto: bytes | None, legenda: str) -> None:
    f = FAIXA
    img = _imagem(foto)
    if img is None:                               # sem foto: painel inteiro
        _painel_protecao(c, f['x0'], f['x1'], 2)
        return
    meio = (f['x0'] + f['x1']) / 2
    _foto_mobi(c, img, f['x0'], meio - VAO / 2, legenda)
    _painel_protecao(c, meio + VAO / 2, f['x1'], 1)


def gerar(textos: dict, destino: str, foto: bytes | None = None) -> None:
    """Grava a proposta em `destino` a partir de `wallbox.calcular(...)['textos']`.
    `foto` = imagem da CLAMPER Mobi (pág. 1, metade esquerda da faixa de
    proteção); sem ela, o painel de proteção ocupa a largura toda."""
    _registrar_fontes()
    valores = dict(textos)
    valores['cliente_aceite'] = textos.get('cliente', '')
    # LOCAL: logradouro na 1ª linha, cidade logo abaixo (como no design)
    local = [ln for ln in (textos.get('local'), textos.get('cidade')) if ln]

    fundo = PdfReader(FUNDO)
    camadas = []
    for pag in range(len(fundo.pages)):
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(float(fundo.pages[pag].mediabox.width),
                                         float(fundo.pages[pag].mediabox.height)))
        for campo, (p, x, y, fonte, tam, cor, alin, larg, max_lin, entre) in \
                CAMPOS.items():
            if p != pag:
                continue
            if campo == 'local':        # cidade logo abaixo do logradouro
                n = 0
                for ln in local:
                    n += _escrever(c, ln, x, y - n * entre, fonte, tam, cor,
                                   alin, larg, max_lin, entre)
                continue
            _escrever(c, valores.get(campo) or '', x, y, fonte, tam, cor, alin,
                      larg, max_lin, entre)
        if pag == 0:
            _faixa_protecao(c, foto, textos.get('mobi_legenda', ''))
        c.save()
        camadas.append(PdfReader(io.BytesIO(buf.getvalue())).pages[0])

    saida = PdfWriter(clone_from=FUNDO)
    for pag, camada in zip(saida.pages, camadas):
        pag.merge_page(camada)
    saida.add_metadata({'/Title': 'Proposta Comercial - Carregador Veicular - '
                                  'S2V Engenharia', '/Author': 'S2V Engenharia'})
    with open(destino, 'wb') as f:
        saida.write(f)
