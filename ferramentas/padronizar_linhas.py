# -*- coding: utf-8 -*-
"""Padroniza a ESPESSURA das linhas do `assets/fundo.pdf` (build-only).

Sistema de linhas da proposta (revisão de design B5, pedido do usuário):
  * bordas de cartões/quadros e réguas de cabeçalho ... 0,99 pt
  * divisórias internas e linhas de ligação .......... 0,74 pt
  * anéis dos círculos ................................ 1,98 pt
A arte já seguia isso, com UMA exceção: na tabela da pág. 3 (potência,
consumo…) as 4 linhas entre as fileiras eram 0,99 e a coluna do meio 0,74.
Aqui as 4 viram 0,74 — divisórias, como a coluna. Idempotente.

    py ferramentas/padronizar_linhas.py
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNDO = os.path.join(RAIZ, 'assets', 'fundo.pdf')

# (página 1-based, regex do trecho "<largura> w … n x y m x2 y l")
ALVOS = [
    # linhas horizontais da tabela da pág. 3: de x ~37,4 a ~321,5
    (3, r'\.99 w(\s+1 J\s+1 j\s+n 37\.\d+ (?:551\.01|513\.58|476\.05|438\.62) m '
        r'321\.\d+ [\d.]+ l)'),
]


def main():
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(FUNDO))
    feitos = 0
    for pg, padrao in ALVOS:
        page = w.pages[pg - 1]
        co = page.get_contents()
        dados = co.get_data().decode('latin-1')
        novo, n = re.subn(padrao, r'.74 w\1', dados)
        if n:
            feitos += n
            co.set_data(novo.encode('latin-1'))
            page.replace_contents(co)
    if feitos:
        with open(FUNDO, 'wb') as f:
            w.write(f)
    print(f'{feitos} linha(s) ajustada(s) para 0,74 pt'
          + ('' if feitos else ' — já estava padronizado'))


if __name__ == '__main__':
    main()
