# -*- coding: utf-8 -*-
"""Pré-visualização da proposta para AJUSTES DE LAYOUT — antes × depois.

Gera a proposta de casos-padrão, renderiza cada página em PNG e compara com uma
REFERÊNCIA aprovada: o que mudou aparece contornado em vermelho, lado a lado.
É o que permite mexer na proposta UMA coisa de cada vez sem estragar o resto.

    py ferramentas/previa.py --base   # congela o estado atual como referência
    py ferramentas/previa.py          # renderiza e compara com a referência

Saída em `previa/` (fora do Git):
    previa/base/<caso>_p<n>.png        a referência aprovada
    previa/atual/<caso>_p<n>.png       como está agora
    previa/comparar/<caso>_p<n>.png    referência | atual, mudanças em vermelho
Os casos usam dados FICTÍCIOS (nada de cliente real).
"""
from __future__ import annotations

import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:                                               # noqa: BLE001
    pass

import engine                                                   # noqa: E402
import proposta                                                 # noqa: E402
from engine import UC, Entradas                                 # noqa: E402

SAIDA = os.path.join(RAIZ, 'previa')
DPI = 110            # leve para comparar; aumente para olhar detalhe


def _residencial(bateria=True, stringbox=True):
    uc = UC(tipo='GERADORA', ilum_publica=38.7, ligacao='BIFASICO',
            consumos=[344, 384, 256, 250] + [300] * 8, te=0.31085, tusd=0.45717,
            icms=0.19, cofins=0.066555, pis=0.014485, pct_noturno=0.65)
    return Entradas(nome='CLIENTE EXEMPLO RESIDENCIAL', endereco='Rua Exemplo',
                    numero='100', cidade='Cidade Exemplo - PR', ucs=[uc],
                    qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=3,
                    tensao_inversor=220, valor_kit=4974.72, conexao='HÍBRIDO',
                    marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
                    estrutura='FIBROCIMENTO', perfil_irradiacao='3.8',
                    margem_desejada=0.16, tem_bateria=bateria, bat_kwh=5, bat_marca='DEYE',
                    tem_stringbox=stringbox)


def _grupo_a():
    import app
    d = json.load(open(os.path.join(RAIZ, 'exemplos', 'fatura_real_grupo_a.json'),
                       encoding='utf-8'))
    d.update(nome='CLIENTE EXEMPLO MEDIA TENSAO', qtd_modulos_kit=200,
             valor_kit=190000, marca_inversor='CHINT', pot_inversor_kw=125,
             tensao_inversor=380,
             inversores=[dict(marca='CHINT', pot_kw=125, tensao=380, qtd=1)])
    with app.app.test_request_context('/'):
        return app._montar_entradas(d)


CASOS = {
    'b_completo': lambda: _residencial(True, True),
    'b_enxuto': lambda: _residencial(False, False),
    'a_ampliacao': _grupo_a,
}


def renderizar(destino: str) -> dict:
    import pypdfium2 as pdfium
    os.makedirs(destino, exist_ok=True)
    cfg = engine.carregar_config()
    paginas = {}
    for nome, fazer in CASOS.items():
        pdf = os.path.join(destino, f'{nome}.pdf')
        proposta.gerar_proposta(engine.calcular(fazer(), cfg), pdf)
        doc = pdfium.PdfDocument(pdf)
        for i in range(len(doc)):
            png = os.path.join(destino, f'{nome}_p{i + 1}.png')
            doc[i].render(scale=DPI / 72).to_pil().convert('RGB').save(png)
            paginas[f'{nome}_p{i + 1}'] = png
        doc.close()
    return paginas


def comparar(base: dict, atual: dict) -> int:
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage
    pasta = os.path.join(SAIDA, 'comparar')
    os.makedirs(pasta, exist_ok=True)       # (OneDrive às vezes trava o rmtree)
    for f in os.listdir(pasta):
        os.remove(os.path.join(pasta, f))
    mudou = 0
    for chave, png in sorted(atual.items()):
        if chave not in base:
            print(f'  {chave}: página nova (sem referência)')
            continue
        a, b = Image.open(base[chave]), Image.open(png)
        if a.size != b.size:
            print(f'  {chave}: tamanho de página mudou!')
            mudou += 1
            continue
        diff = np.abs(np.asarray(a).astype(int) - np.asarray(b).astype(int)).max(axis=2) > 40
        lab, n = ndimage.label(ndimage.binary_dilation(diff, iterations=4))
        if not n:
            continue
        mudou += n
        k = 72 / DPI
        print(f'  {chave}: {n} região(ões) alterada(s)')
        lado = Image.new('RGB', (a.width * 2 + 20, a.height), (90, 90, 90))
        lado.paste(a, (0, 0))
        lado.paste(b, (a.width + 20, 0))
        d = ImageDraw.Draw(lado)
        for s in ndimage.find_objects(lab):
            y0, y1, x0, x1 = s[0].start, s[0].stop, s[1].start, s[1].stop
            print(f'      x {x0 * k:5.0f}–{x1 * k:5.0f}  topo {y0 * k:5.0f}–{y1 * k:5.0f} pt')
            for dx in (0, a.width + 20):
                d.rectangle((x0 + dx - 3, y0 - 3, x1 + dx + 3, y1 + 3),
                            outline=(230, 30, 30), width=3)
        lado.save(os.path.join(pasta, f'{chave}.png'))
    return mudou


def caixas():
    """Conferência dos ícones: desenha, sobre cada página, um quadrado AZUL
    em volta da parte PREENCHIDA de cada ícone — medida na imagem (do 1º ao
    último pixel colorido, sem o anel dos círculos) — e lista as medidas."""
    import numpy as np
    import pypdfium2 as pdfium
    from PIL import ImageDraw
    pasta = os.path.join(SAIDA, 'caixas')
    os.makedirs(pasta, exist_ok=True)
    cfg = engine.carregar_config()
    S = 300 / 72                                      # 300 dpi
    for nome_caso, fazer in CASOS.items():
        proposta._REGISTRO_ICONES = []
        pdf = os.path.join(pasta, f'{nome_caso}.pdf')
        proposta.gerar_proposta(engine.calcular(fazer(), cfg), pdf)
        reg = proposta._REGISTRO_ICONES
        proposta._REGISTRO_ICONES = None
        doc = pdfium.PdfDocument(pdf)
        linhas = []
        for i in range(len(doc)):
            im = doc[i].render(scale=S).to_pil().convert('RGB')
            a = np.asarray(im).astype(int)
            H = doc[i].get_height()
            # tinta de ícone = verde ou azul da marca (saturado)
            cor = (a.max(axis=2) - a.min(axis=2)) > 70
            d = ImageDraw.Draw(im)
            for r in (r for r in reg if r['pag'] == i + 1):
                cx, cy = r['cx'], H - r['cyb']
                m = r['lado'] * 0.58          # janela justa: não pegar divisórias vizinhas
                x0, y0 = int((cx - m) * S), int((cy - m) * S)
                sub = cor[y0:int((cy + m) * S), x0:int((cx + m) * S)].copy()
                if r['aro']:                         # tira o anel do círculo
                    yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
                    dist = np.hypot(xx / S + (cx - m) - cx, yy / S + (cy - m) - cy)
                    sub[dist > r['aro'] - 1.2] = False
                ys, xs = np.where(sub)
                if not len(xs):
                    continue
                bx0, bx1 = (xs.min() + x0) / S, (xs.max() + 1 + x0) / S
                by0, by1 = (ys.min() + y0) / S, (ys.max() + 1 + y0) / S
                d.rectangle((bx0 * S, by0 * S, bx1 * S, by1 * S),
                            outline=(30, 80, 255), width=3)
                linhas.append(f'  p{i + 1} {r["nome"]:12s} alvo {r["lado"]:5.1f}  '
                              f'tinta {bx1 - bx0:5.1f} × {by1 - by0:5.1f}  '
                              f'centro ({(bx0 + bx1) / 2 - cx:+.2f}, {(by0 + by1) / 2 - cy:+.2f})')
            im.save(os.path.join(pasta, f'{nome_caso}_p{i + 1}.png'))
        doc.close()
        print(f'{nome_caso}:', *linhas, sep='\n')
    print('\nimagens em previa/caixas/ (quadrado azul = parte preenchida medida)')


def main():
    if '--caixas' in sys.argv:
        caixas()
        return
    if '--base' in sys.argv:
        shutil.rmtree(os.path.join(SAIDA, 'base'), ignore_errors=True)
        pg = renderizar(os.path.join(SAIDA, 'base'))
        print(f'referência congelada: {len(pg)} páginas em previa/base/')
        return
    atual = renderizar(os.path.join(SAIDA, 'atual'))
    pasta_base = os.path.join(SAIDA, 'base')
    if not os.path.isdir(pasta_base):
        print(f'{len(atual)} páginas em previa/atual/ — sem referência ainda '
              f'(rode com --base para congelar a atual)')
        return
    base = {os.path.splitext(f)[0]: os.path.join(pasta_base, f)
            for f in os.listdir(pasta_base) if f.endswith('.png')}
    n = comparar(base, atual)
    print(f'\n{"nenhuma mudança" if not n else f"{n} região(ões) alterada(s) — veja previa/comparar/"}')


if __name__ == '__main__':
    main()
