# -*- coding: utf-8 -*-
"""
Build do fundo da proposta de CARREGADOR VEICULAR (wallbox).

O design entrega a proposta pronta, com os campos variáveis escritos entre
colchetes ("[CLIENTE]", "[R$ VALOR]"…). Este script apaga do PDF:
  1. esses textos "[...]" — os valores são escritos por cima, depois, por
     `proposta_wallbox.py`, na posição de cada colchete;
  2. o painel "PROTEÇÃO E ATERRAMENTO" da pág. 1 (fundo cinza, ícone, título e
     as 8 frases) — `proposta_wallbox` redesenha uma versão SIMPLIFICADA na
     metade direita, com a foto da CLAMPER Mobi na esquerda (pedido do usuário).
Arte, fotos e o resto dos textos fixos ficam byte a byte. Grava
`assets/wallbox/fundo.pdf`.

    py ferramentas/wallbox_fundo.py                 # usa assets/wallbox/modelo.pdf
    py ferramentas/wallbox_fundo.py novo_modelo.pdf # PDF novo do design

Quando o design mudar, rode de novo e confira as posições em
`proposta_wallbox.CAMPOS` (o script lista cada campo apagado com x/y/fonte)
e o `PAINEL` — se o painel não for achado, o script avisa.
"""
import os
import re
import shutil
import sys

from pypdf import PdfWriter
from pypdf.generic import ContentStream

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(BASE, 'assets', 'wallbox')

# um bloco de texto do ReportLab: BT 1 0 0 1 x y Tm /Fonte tam Tf … (TEXTO) Tj T* ET
_BLOCO = re.compile(rb'BT 1 0 0 1 ([\d.]+) ([\d.]+) Tm /(\S+) ([\d.]+) Tf [\d.]+ TL '
                    rb'\((\[.*?\])\) Tj T\* ET\n?')
# painel "PROTEÇÃO E ATERRAMENTO" (pág. 1): do preenchimento cinza #F3F7F8 do
# retângulo (38–557 × 79,9–293,9 pt) até o texto "NORMAS:", que fica
_PAINEL = re.compile(rb'\.952941 \.968627 \.972549 rg\nn\n52 79\.88976 m\n.*?'
                     rb'(?=\.031373 \.611765 \.513725 rg\nBT 1 0 0 1 38 58\.88976 Tm)',
                     re.S)


def construir(origem: str) -> None:
    modelo = os.path.join(PASTA, 'modelo.pdf')
    if os.path.abspath(origem) != os.path.abspath(modelo):
        shutil.copyfile(origem, modelo)          # guarda a fonte do build
    escritor = PdfWriter(clone_from=modelo)
    for n, pag in enumerate(escritor.pages, 1):
        dados = pag.get_contents().get_data()
        for m in _BLOCO.finditer(dados):
            x, y, fonte, tam, txt = m.groups()
            print(f'  pag. {n}: x={x.decode():>9} y={y.decode():>9} '
                  f'{fonte.decode():6} {tam.decode():>5}  {txt.decode("latin1")}')
        dados = _BLOCO.sub(b'', dados)
        if n == 1:
            dados, achou = _PAINEL.subn(b'', dados)
            print(f'  pag. 1: painel PROTECAO E ATERRAMENTO apagado: {achou}')
            if achou != 1:
                print('  ATENCAO: painel nao encontrado - confira _PAINEL')
        cs = ContentStream(None, escritor)
        cs.set_data(dados)
        pag.replace_contents(cs)
    destino = os.path.join(PASTA, 'fundo.pdf')
    with open(destino, 'wb') as f:
        escritor.write(f)
    print('gravado:', destino)


if __name__ == '__main__':
    construir(sys.argv[1] if len(sys.argv) > 1
              else os.path.join(PASTA, 'modelo.pdf'))
