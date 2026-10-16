"""Build: tabela de irradiação por município (INPE, Atlas Brasileiro 2017).

Gera `assets/irradiacao_inpe.json` a partir do CSV "sedes municipais" da
irradiação GLOBAL HORIZONTAL do LABREN/INPE — a mesma base do SunData do
CRESESB (Maringá: 4.890 Wh/m²/dia no ano, jan 5.888, jun 3.333, igual ao
"Plano Horizontal" do CRESESB). O programa só lê o JSON: sem internet.

    py ferramentas/irradiacao_inpe.py              # baixa do LABREN
    py ferramentas/irradiacao_inpe.py arquivo.zip  # usa um zip já baixado

Fonte: http://labren.ccst.inpe.br/atlas_2017.html
       (GLOBAL_HORIZONTAL_sedes-munic_(csv).zip)
"""
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile

URL = ('http://labren.ccst.inpe.br/projetos/atlas_2017/'
       'GLOBAL_HORIZONTAL_sedes-munic_(csv).zip')
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'assets', 'irradiacao_inpe.json')

# o CSV traz o estado por extenso, em maiúsculas
UF = {'ACRE': 'AC', 'ALAGOAS': 'AL', 'AMAPÁ': 'AP', 'AMAZONAS': 'AM',
      'BAHIA': 'BA', 'CEARÁ': 'CE', 'DISTRITO FEDERAL': 'DF',
      'ESPÍRITO SANTO': 'ES', 'GOIÁS': 'GO', 'MARANHÃO': 'MA',
      'MATO GROSSO': 'MT', 'MATO GROSSO DO SUL': 'MS', 'MINAS GERAIS': 'MG',
      'PARÁ': 'PA', 'PARAÍBA': 'PB', 'PARANÁ': 'PR', 'PERNAMBUCO': 'PE',
      'PIAUÍ': 'PI', 'RIO DE JANEIRO': 'RJ', 'RIO GRANDE DO NORTE': 'RN',
      'RIO GRANDE DO SUL': 'RS', 'RONDÔNIA': 'RO', 'RORAIMA': 'RR',
      'SANTA CATARINA': 'SC', 'SÃO PAULO': 'SP', 'SERGIPE': 'SE',
      'TOCANTINS': 'TO'}
MESES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
         'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']


def main():
    if len(sys.argv) > 1:
        dados = open(sys.argv[1], 'rb').read()
    else:
        print('baixando', URL)
        dados = urllib.request.urlopen(URL, timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(dados))
    nome_csv = next(n for n in z.namelist() if n.endswith('.csv'))
    texto = z.read(nome_csv).decode('utf-8')
    municipios = []
    for li in csv.DictReader(io.StringIO(texto), delimiter=';'):
        uf = UF[li['STATE'].strip().upper()]
        municipios.append([li['NAME'].strip(), uf,
                           round(float(li['LAT']), 4), round(float(li['LON']), 4),
                           [int(li[m]) for m in MESES]])
    assert len(municipios) > 5500, len(municipios)
    out = {'_fonte': 'INPE/LABREN — Atlas Brasileiro de Energia Solar, 2ª ed. '
                     '(2017), irradiação GLOBAL HORIZONTAL média diária por mês '
                     '(Wh/m²/dia) nas sedes municipais. Mesma base do SunData '
                     '(CRESESB). Gerado por ferramentas/irradiacao_inpe.py.',
           '_campos': ['nome', 'uf', 'lat', 'lon', 'mensal_jan_dez'],
           'municipios': municipios}
    with open(SAIDA, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(municipios)} municípios → {SAIDA} '
          f'({os.path.getsize(SAIDA) // 1024} KB)')


if __name__ == '__main__':
    main()
