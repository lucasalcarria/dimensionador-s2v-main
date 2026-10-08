# -*- coding: utf-8 -*-
"""Padroniza a COR dos títulos de seção do `assets/fundo.pdf` (build-only).

Decisão do usuário (06/10/2026, item B1 da revisão de design): títulos de
seção em VERDE #089C83 — só o "KIT GERADOR FOTOVOLTAICO" fica azul (ele é
desenhado pela proposta, não está no fundo). O único título fora da regra
da arte era "ETAPAS DO PROJETO", em azul. (Testou-se tudo azul; o usuário
preferiu o verde.)

Cirurgia mínima no fundo PRONTO, como em `vetor_icones.vetorizar_fundo`: cada
título é um bloco `BT … ET` próprio, achado pela posição (Tm) medida; o bloco
é embrulhado em `q <cor> rg … Q`. Nada mais muda — nem posição, nem fonte, nem
a cor herdada pelos textos seguintes (o `Q` devolve o estado anterior).
Idempotente: rodar de novo não faz nada.

    py ferramentas/recolorir_titulos.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNDO = os.path.join(RAIZ, 'assets', 'fundo.pdf')
COR = '.031373 .611765 .513725 rg'                # #089C83, o verde da arte

# título -> página (1-based); a posição é lida do próprio fundo.pdf
TITULOS = {
    'ETAPAS DO PROJETO': 4,
}


def _posicao(pagina: int, texto: str):
    """(x, y) da origem do 1º caractere de `texto`, lida pelo pdfium."""
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    tp = pdfium.PdfDocument(FUNDO)[pagina - 1].get_textpage()
    i = tp.get_text_range().find(texto)
    if i < 0:
        raise SystemExit(f'não achei "{texto}" na pág. {pagina}')
    x, y = ctypes.c_double(), ctypes.c_double()
    R.FPDFText_GetCharOrigin(tp.raw, i, ctypes.byref(x), ctypes.byref(y))
    return x.value, y.value


def main():
    from pypdf import PdfReader, PdfWriter
    alvos = {}                                     # página -> [(x, y, nome)]
    for nome, pg in TITULOS.items():
        x, y = _posicao(pg, nome)
        alvos.setdefault(pg, []).append((x, y, nome))

    w = PdfWriter(clone_from=PdfReader(FUNDO))
    feitos = 0
    for pg, lista in alvos.items():
        page = w.pages[pg - 1]
        co = page.get_contents()
        dados = co.get_data().decode('latin-1')
        for x, y, nome in lista:
            # bloco BT com Tm na posição (tolerância de 0,6 pt). O fim é um ET
            # SOLTO: "PROJETOS" e "RETORNO" têm "ET" dentro da palavra.
            achou = False
            for m in re.finditer(r'BT 1 0 0 1 ([\d.]+) ([\d.]+) Tm.*?\sET(?=\s|$)', dados, re.S):
                if abs(float(m.group(1)) - x) < 0.6 and abs(float(m.group(2)) - y) < 0.6:
                    antes = dados[max(0, m.start() - 40):m.start()]
                    if antes.rstrip().endswith(COR):     # já recolorido
                        achou = True
                        break
                    dados = (dados[:m.start()] + f'q {COR}\n' + m.group(0)
                             + '\nQ' + dados[m.end():])
                    achou = True
                    feitos += 1
                    break
            if not achou:
                raise SystemExit(f'bloco de "{nome}" não encontrado na pág. {pg}')
        co.set_data(dados.encode('latin-1'))
        page.replace_contents(co)
    if feitos:
        with open(FUNDO, 'wb') as f:
            w.write(f)
    print(f'{feitos} título(s) recolorido(s) para verde #089C83'
          + ('' if feitos else ' — já estava tudo verde'))


if __name__ == '__main__':
    main()
