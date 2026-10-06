# -*- coding: utf-8 -*-
"""Vetoriza os ícones da proposta (BUILD — não é usado pelo programa em si).

Os ícones vieram do design como PNG minúsculos (36 a 106 px) e, mostrados a
~38 pt, ficavam serrilhados: reamostrar não cria nitidez. Aqui cada ícone é
TRAÇADO em curvas (o mesmo princípio do "Image Trace" do Illustrator) e passa a
ser desenhado em vetor **dentro da mesma caixa** onde a imagem era desenhada —
então posição, tamanho, círculos e alinhamentos ficam idênticos por construção.

Duas entradas usam isto:
  * `vetorizar_fundo(pdf, nativos)` — troca, no `fundo.pdf` JÁ PRONTO, cada
    imagem-ícone por um desenho vetorial no lugar dela. É cirúrgico: o
    `fundo.pdf` atual tem ajustes feitos à mão depois do build (pág. 5) e NÃO
    pode ser reconstruído pelo conversor sem perdê-los.
  * `html_para_fundo.desenhar_svg(..., icones=[])` — nos cartões da pág. 3 o
    ícone sai do PNG e vira vetor gravado em `layout_cards.json`, que a
    proposta desenha por cima do cartão (`proposta._desenhar_icones`).

Formato de um ícone traçado: {'cor': 'RRGGBB', 'p': 'M x y C … Z …'} com
coordenadas na caixa unitária da imagem, x para a direita e **y para baixo**
(convenção de imagem). Precisa de `potracer`, `numpy` e `Pillow` — só no build.
"""
from __future__ import annotations

import base64
import hashlib
import io
import re

# ---- parâmetros do traçado (escolhidos olhando o resultado ampliado) --------
ALVO_PX = 1600      # reamostra até o lado maior ter ~1600 px antes de traçar
SUAVIZA_MAX = 1.0   # desfoque máximo, em pixels DA IMAGEM ORIGINAL: tira o
                    # degrau do pixel sem deslocar a borda (borda reta fica)
SUAVIZA_FRACAO = 0.25   # ... mas nunca mais que 1/4 da espessura do traço:
                    # em ícone de linha de 2 px, 1 px de desfoque FECHA as
                    # junções e as células viram manchas (aconteceu no painel)
MARGEM = 2          # px transparentes em volta: ícone que encosta na borda da
                    # imagem não vira "corcova" no traçado
DISPERSAO_MAX = 18  # ícone = uma cor só (logo em degradê e foto ficam raster)
LADO_MAX = 400      # ícone é pequeno; acima disso é foto/arte


def _rgba(dados: bytes):
    from PIL import Image
    return Image.open(io.BytesIO(dados)).convert('RGBA')


def eh_icone(dados: bytes) -> bool:
    """Ícone = tem transparência, é de uma cor só e é pequeno. Assim o logo S2V
    (degradê), as fotos e os logos dos bancos (sem transparência) ficam como
    estão."""
    import numpy as np
    img = _rgba(dados)
    if max(img.size) > LADO_MAX:
        return False
    a = np.asarray(img).astype(float)
    alfa = a[..., 3] / 255
    if alfa.min() >= 0.99:
        return False
    tinta = a[alfa > 0.6][:, :3]
    return len(tinta) > 0 and float(tinta.std(axis=0).max()) < DISPERSAO_MAX


def _cor(dados: bytes) -> str:
    import numpy as np
    a = np.asarray(_rgba(dados)).astype(float)
    tinta = a[a[..., 3] > 0.6 * 255][:, :3]
    return '%02X%02X%02X' % tuple(int(round(v)) for v in np.median(tinta, axis=0))


def _espessura_traco(alfa) -> float:
    """Espessura típica do traço, em px: 2 × área ÷ perímetro. Para traços
    longos e finos (o caso dos ícones de linha) área ≈ comprimento × espessura e
    perímetro ≈ 2 × comprimento."""
    import numpy as np
    m = np.asarray(alfa) > 127
    area = m.sum()
    perim = (np.abs(np.diff(m.astype(int), axis=0)).sum()
             + np.abs(np.diff(m.astype(int), axis=1)).sum())
    return float(2 * area / perim) if perim else 0.0


_cache: dict = {}


def tracar(dados: bytes) -> dict:
    """PNG de um ícone -> {'cor', 'p'} em vetor (caixa unitária, y para baixo)."""
    chave = hashlib.sha1(dados).hexdigest()
    if chave in _cache:
        return _cache[chave]
    import numpy as np
    import potrace
    from PIL import Image, ImageFilter

    img = _rgba(dados)
    w, h = img.size
    alfa = img.split()[-1]
    # margem transparente + reamostragem boa + desfoque de 1 px original
    pad = Image.new('L', (w + 2 * MARGEM, h + 2 * MARGEM), 0)
    pad.paste(alfa, (MARGEM, MARGEM))
    f = max(1, round(ALVO_PX / max(w, h)))
    big = pad.resize((pad.width * f, pad.height * f), Image.LANCZOS)
    sig = float(min(SUAVIZA_MAX, SUAVIZA_FRACAO * _espessura_traco(alfa)))
    if sig > 0:
        big = big.filter(ImageFilter.GaussianBlur(sig * f))
    # Ponto de corte que PRESERVA A ÁREA: a área pintada do vetor tem de ser
    # igual à tinta total da imagem (soma da transparência). Em traço grosso
    # isso cai perto de 50 %; em traço de 1–2 px o vizinho com transparência
    # parcial alta entraria inteiro num corte fixo em 50 % e a linha engrossaria
    # — com este corte ela fica com a espessura que a imagem mostra.
    arr = np.asarray(big)
    tinta = float(np.asarray(pad).astype(float).sum()) / 255 * f * f
    frac = min(max(tinta / arr.size, 0.0), 1.0)
    corte = float(np.percentile(arr, 100 * (1 - frac))) if frac > 0 else 127
    corte = min(max(corte, 64), 230)       # trava de segurança
    # potracer: False = tinta
    caminho = potrace.Bitmap(arr <= corte).trace(
        turdsize=4 * f, alphamax=1.0, opticurve=True, opttolerance=0.2)

    def uv(p):
        return ((p.x / f - MARGEM) / w, (p.y / f - MARGEM) / h)

    partes = []
    for curva in caminho:
        x, y = uv(curva.start_point)
        partes.append(f'M{x:.4f} {y:.4f}')
        for seg in curva.segments:
            if seg.is_corner:
                cx, cy = uv(seg.c)
                ex, ey = uv(seg.end_point)
                partes.append(f'L{cx:.4f} {cy:.4f}L{ex:.4f} {ey:.4f}')
            else:
                a1, b1 = uv(seg.c1)
                a2, b2 = uv(seg.c2)
                ex, ey = uv(seg.end_point)
                partes.append(f'C{a1:.4f} {b1:.4f} {a2:.4f} {b2:.4f} '
                              f'{ex:.4f} {ey:.4f}')
        partes.append('Z')
    icone = {'cor': _cor(dados), 'p': ''.join(partes)}
    _cache[chave] = icone
    return icone


def _comandos(p: str):
    """'M x y C … L … Z' -> [(op, [números])]"""
    for op, nums in re.findall(r'([MCLZ])([^MCLZ]*)', p):
        yield op, [float(v) for v in nums.split()]


def operadores_pdf(icone: dict) -> bytes:
    """Operadores de conteúdo PDF que pintam o ícone na caixa unitária
    (y para CIMA, como no espaço de uma imagem: a 1ª linha da imagem é o topo)."""
    r, g, b = (int(icone['cor'][i:i + 2], 16) / 255 for i in (0, 2, 4))
    out = [f'{r:.4f} {g:.4f} {b:.4f} rg']
    for op, n in _comandos(icone['p']):
        if op == 'M':
            out.append(f'{n[0]:.4f} {1 - n[1]:.4f} m')
        elif op == 'L':
            for i in range(0, len(n), 2):
                out.append(f'{n[i]:.4f} {1 - n[i + 1]:.4f} l')
        elif op == 'C':
            out.append(f'{n[0]:.4f} {1 - n[1]:.4f} {n[2]:.4f} {1 - n[3]:.4f} '
                       f'{n[4]:.4f} {1 - n[5]:.4f} c')
        elif op == 'Z':
            out.append('h')
    out.append('f*')        # par-ímpar: furos (o miolo do círculo) ficam vazados
    return '\n'.join(out).encode('ascii')


# ------------------------------------------------------------ ícones do HTML
def nativos_do_html(caminho_html: str) -> list[bytes]:
    """Os PNGs dos ícones como vieram no HTML do design (sem repetição)."""
    s = open(caminho_html, encoding='utf-8').read()
    vistos, out = set(), []
    for href in re.findall(r'<image\b[^>]*?href="data:image/[^;]+;base64,([^"]+)"', s):
        if href in vistos:
            continue
        vistos.add(href)
        dados = base64.b64decode(href)
        if eh_icone(dados):
            out.append(dados)
    return out


def _casar(img_pdf, nativos: list[bytes]):
    """Qual ícone nativo deu origem a esta imagem do PDF? O conversor só
    reamostra por um fator INTEIRO, então as dimensões são múltiplas exatas;
    o conteúdo confirma (alfa reduzido ao tamanho nativo bate)."""
    import numpy as np
    from PIL import Image
    W, H = img_pdf.size
    a_pdf = img_pdf.convert('RGBA').split()[-1]
    melhor, erro_min = None, 1e9
    for dados in nativos:
        nat = _rgba(dados)
        w, h = nat.size
        if W % w or H % h or W // w != H // h:
            continue
        red = np.asarray(a_pdf.resize((w, h), Image.BOX)).astype(float)
        erro = float(np.abs(red - np.asarray(nat.split()[-1]).astype(float)).mean())
        if erro < erro_min:
            melhor, erro_min = dados, erro
    return melhor if erro_min < 20 else None


def _imagem_do_pdf(obj):
    """Imagem RGB + máscara de transparência (SMask) de um XObject -> PIL RGBA."""
    from PIL import Image
    try:
        w, h = int(obj['/Width']), int(obj['/Height'])
        rgb = Image.frombytes('RGB', (w, h), obj.get_data())
        sm = obj['/SMask'].get_object()
        alfa = Image.frombytes('L', (int(sm['/Width']), int(sm['/Height'])),
                               sm.get_data())
        if alfa.size != (w, h):
            alfa = alfa.resize((w, h))
        rgb.putalpha(alfa)
        return rgb
    except Exception:                                           # noqa: BLE001
        return None


def vetorizar_fundo(caminho_pdf: str, nativos: list[bytes]) -> list[str]:
    """Troca, no PDF pronto, cada imagem-ícone por um desenho vetorial no lugar
    dela. O operador `Do` e a matriz que posiciona a imagem ficam intactos: só o
    CONTEÚDO do objeto muda (de imagem para formulário vetorial com caixa 0..1),
    então posição e tamanho são exatamente os de antes."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               FloatObject, NameObject)

    w = PdfWriter(clone_from=PdfReader(caminho_pdf))
    trocados, ja = [], {}
    for n, pg in enumerate(w.pages, 1):
        xo = (pg.get('/Resources') or {}).get('/XObject')
        if not xo:
            continue
        xo = xo.get_object()
        for nome in list(xo.keys()):
            obj = xo[nome].get_object()
            if obj.get('/Subtype') != '/Image' or '/SMask' not in obj:
                continue
            ref = xo[nome].indirect_reference if hasattr(xo[nome], 'indirect_reference') else None
            chave = (ref.idnum if ref else id(obj))
            if chave not in ja:
                img = _imagem_do_pdf(obj)
                nat = _casar(img, nativos) if img else None
                if nat is None:
                    ja[chave] = None
                    continue
                form = DecodedStreamObject()
                form.set_data(operadores_pdf(tracar(nat)))
                form.update({
                    NameObject('/Type'): NameObject('/XObject'),
                    NameObject('/Subtype'): NameObject('/Form'),
                    NameObject('/BBox'): ArrayObject([FloatObject(0), FloatObject(0),
                                                      FloatObject(1), FloatObject(1)]),
                    NameObject('/Resources'): DictionaryObject(),
                })
                ja[chave] = w._add_object(form)
            if ja[chave] is not None:
                xo[NameObject(nome)] = ja[chave]
                trocados.append(f'pág. {n} {nome}')
    with open(caminho_pdf, 'wb') as f:
        w.write(f)
    return trocados
