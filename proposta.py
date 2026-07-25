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


def _pdf_grafico(consumo_mensal: list[float], geracao_mensal: list[float],
                 w_pt: float, h_pt: float) -> bytes:
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
    ax.bar([x - off for x in xs], list(consumo_mensal), width=bw,
           color=COR_CONSUMO, label='Consumo', zorder=3)
    ax.bar([x + off for x in xs], geracao_mensal, width=bw,
           color=COR_GERACAO, label='Geração', zorder=3)

    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(0, ymax)
    ax.set_yticks([passo * i for i in range(int(ymax / passo) + 1)])
    ax.set_yticklabels([f'{passo * i:g} kWh'
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
                     ncol=2, frameon=False, fontsize=9.9,
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
    al = meta.get('alinhar')
    if al:
        mg = meta.get('margem', 0.0)
        alt = meta['cards']['modulos']['h'] - 2 * mg      # altura da moldura
        topo = min(t for _, t in pos)
        base = max(t for _, t in pos) + alt
        desloc = max(0.0, al['centro_y'] - (topo + base) / 2.0)
        if desloc > 0.5:
            pos = [(x, t + desloc) for x, t in pos]
    return pos


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
    pos = _slots_dinamicos(meta, len(ordem))
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
        if pagina == 1:
            # capa: estende a foto das placas até a borda direita
            _estender_cover(c, page_h)
        if pagina == 3:
            # bloco de cartões: agrupa os presentes sem lacunas
            def _stamp(nome, x0, top, w, h):
                caminho = os.path.join(ASSETS, 'cards', f'{nome}.png')
                c.drawImage(caminho, x0, page_h - (top + h), width=w, height=h,
                            mask='auto', preserveAspectRatio=False)
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

            # bloco das 3 garantias fixas: desce quando não há a 4ª linha
            gr = _carregar_cards().get('garantias')
            if gr:
                dg = gr['desloc_sem_bateria'] if 'bateria' in ocultar else 0.0
                c.setFillColor(HexColor('#FFFFFF'))
                c.rect(gr['x0'], page_h - (gr['top'] + gr['h'] + dg),
                       gr['w'], gr['h'] + dg, stroke=0, fill=1)
                c.drawImage(os.path.join(ASSETS, 'cards', 'garantias.png'),
                            gr['x0'], page_h - (gr['top'] + dg + gr['h']),
                            width=gr['w'], height=gr['h'], mask='auto',
                            preserveAspectRatio=False)
        if pagina == 4:
            # redesenha a timeline de etapas com círculos perfeitos
            _redesenhar_timeline(c, page_h)
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
            linhas, size = _ajustar_em_caixa(
                valor, fonte, st['size'], f.get('max_w'), f.get('linhas', 1))
            desc = pdfmetrics.getDescent(fonte, size)      # negativo, em pt
            baseline = box['y0'] - desc
            if f.get('desloca_sem_bateria') and 'bateria' in ocultar:
                baseline -= f['desloca_sem_bateria']
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
        consumo_mes, resultado['geracao_mensal'], gw, gh)))
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

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with open(caminho_saida, 'wb') as f:
        out.write(f)
    return caminho_saida
