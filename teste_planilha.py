# -*- coding: utf-8 -*-
"""
Teste de validação contra a planilha original.

Rode com:  py -3 teste_planilha.py   (Windows)   ou   python3 teste_planilha.py

O que é verificado:
  1. O caso salvo dentro da planilha (cliente NEUZA ZAMFERRARI) — todos os
     valores de fatura, economia, retorno, preço de venda, payback, parcela e
     textos da proposta devem bater centavo a centavo com as células gravadas
     no arquivo .xlsm (modo `compat_planilha`).
  2. A identidade de convergência do preço (a mesma da macro GERAR_KWP):
     venda = custo/(1−margem), com imposto = alíquota×(venda − kit),
     comissão e seguro proporcionais — testada em vários cenários.
  3. As regras unitárias: mão de obra, material por faixa, transformadores,
     tarifa com imposto e sobreposições manuais (MO/material/alíquota).
"""
import sys

from engine import Entradas, UC, calcular, carregar_config, _trafo

VERDE = '\033[92m'
VERM = '\033[91m'
FIM = '\033[0m'
falhas = []


def ok(nome, obtido, esperado, tol=0.01):
    if esperado is None:
        passou = obtido is None
    elif isinstance(esperado, str):
        passou = str(obtido) == esperado
    else:
        passou = abs(obtido - esperado) <= tol
    cor = VERDE + 'OK ' if passou else VERM + 'FALHOU'
    print(f'  {cor}{FIM} {nome:<46} obtido={obtido!r:<24} esperado={esperado!r}')
    if not passou:
        falhas.append(nome)


def caso_planilha():
    """Entradas exatamente como estão salvas na planilha enviada."""
    uc1 = UC(tipo='GERADORA', ilum_publica=38.7, ligacao='BIFASICO',
             consumos=[344, 384, 256, 250, 300, 300, 300, 300, 300, 300, 300, 300],
             te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
             pct_noturno=0.65, bandeira='VERDE')
    return Entradas(
        nome='NEUZA ZAMFERRARI', endereco='RUA MANOEL SAES, 213',
        cidade='Mandaguaçu - PR', uc_numero='16285387',
        ucs=[uc1] + [UC() for _ in range(8)],
        qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=3,
        tensao_inversor=220, valor_kit=4974.72, conexao='HÍBRIDO',
        marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
        estrutura='FIBROCIMENTO', perfil_irradiacao='3.8',
        margem_desejada=0.16)


def secao(t):
    print(f'\n=== {t} ===')


# ---------------------------------------------------------------- 1) caso salvo
cfg = carregar_config()
cfg['compat_planilha'] = True      # replica a planilha à risca
cfg['formato_ptbr'] = False        # a planilha foi salva no formato en-US

secao('1. Caso salvo na planilha (modo compatível)')
e = caso_planilha()
r = calcular(e, cfg, ano=2026)
ok('PR!U9   consumo médio (kWh/mês)', r['consumo_medio'], 302.8333333333333, 1e-6)
ok('PR!X12  potência do sistema (kWp)', r['kwp'], 3.72, 1e-9)
ok('PR!X9   área (m²)', r['area_m2'], 26.2, 1e-9)
ok('PR!I21  geração média (kWh/mês)', r['geracao_media'], 427.27472914173023, 1e-6)
ok('PR!L20  compensação', r['compensacao'], 1.4109237065769848, 1e-9)
ok('DD!B21  kWp p/ compensar 100%', r['kwp_necessario'], 2.64, 1e-9)
ok('PR!U12  módulos sugeridos', r['modulos_sugeridos'], 4, 0)
ok('PR!Q21  mão de obra', r['custo_mo'], 850, 0)
ok('PR!S21  material', r['custo_material'], 800, 0)
ok('PR!T21  transformador', r['custo_trafo'], 0, 0)
ok('PR!L25  fatura SEM sistema', r['fatura_sem'], 403.3183937801772, 1e-6)
ok('PR!M25  fatura COM sistema', r['fatura_com'], 125.69641635251203, 1e-6)
ok('PR!N25  economia mensal', r['economia_mensal'], 277.6219774276652, 1e-6)
ok('PR!O25  retorno 25 anos (fórmula da planilha)',
   r['retorno_25'], 16651.447413837283, 1e-4)

secao('2. Preço de venda — como a macro GERAR_KWP faria hoje')
# 2a. margem digitada (PR!W31 = 16 %): iteração até convergir
ok('convergido c/ margem 16 %  (R$)', r['preco_venda'], 8193.081578947368, 0.01)
# 2b. margem em branco → faixa automática (DD!B78 = 20 % p/ este porte) = DD!B95
e.margem_desejada = None
rb = calcular(e, cfg, ano=2026)
ok('DD!B95  preço/Wp faixa automática', rb['preco_wp'], 2.324799286107587, 1e-6)
ok('        preço de venda faixa (R$)', rb['preco_venda'], 8648.253344320224, 0.01)
# 2c. preço/Wp manual = valor que estava colado em DD!B75 → reproduz a planilha salva
e.margem_desejada = 0.16
e.wp_manual = 2.354333938294011
rm = calcular(e, cfg, ano=2026)
ok('PR!U35  valor de venda (planilha salva)', rm['preco_venda'], 8758.12225045372, 1e-6)
ok('PR!X25  custo total', rm['custo_total'], 6927.392180036298, 1e-6)
ok('PR!U32  lucro %', rm['lucro_pct'], 0.20903225806451606, 1e-9)
ok('PR!O20  payback (anos)', rm['payback_anos'], 2.6, 1e-9)
ok('PR!U37  parcela financiamento (R$)', rm['parcela_fin'], 251.34370541051413, 1e-6)

secao('3. Textos da proposta (aba TEXTO, formato da planilha)')
t = rm['textos']
ok("TX!D3  '3.72 kWp'", t['kwp_txt'], '3.72 kWp')
ok("TX!D4  '26.2 m²'", t['area_txt'], '26.2 m²')
ok("TX!E6  '302 kWh/mês'", t['consumo_txt'], '302 kWh/mês')
ok("TX!E7  '427 kWh/mês'", t['geracao_txt'], '427 kWh/mês')
ok("TX!D8  '141%'", t['compensa_txt'], '141%')
ok("TX!B8  '6x'", t['mod_qtd'], '6x')
ok("TX!B10 'Astronergy N-Type 620W'", t['mod_desc'], 'Astronergy N-Type 620W')
ok("TX!B12 'CHINT 3kW Mono 220V '", t['inv_desc'], 'CHINT 3kW Mono 220V ')
ok("TX!B13 'P/ 4 Mod. Fibrocimento'", t['estr_desc'], 'P/ 4 Mod. Fibrocimento')
ok("TX!C13 '2x'", t['estr_qtd'], '2x')
ok("TX!I6  '10 ANOS' (garantia inversor)", t['gar_inversor'], '10 ANOS')
ok("TX!I7  '15 ANOS'", t['gar_instalacao'], '15 ANOS')
ok("TX!I3  '30 ANOS' (garantia módulos)", t['gar_modulos'], '30 ANOS')
ok("PR!O20 '2.6 ANOS'", t['payback_txt'], '2.6 ANOS')
ok("PR!U35 'R$ 8,758.12'", t['valor_venda'], 'R$ 8,758.12')

secao('4. Identidade de convergência (venda = custo ÷ (1 − margem))')


def identidade(nome, **kw):
    ent = caso_planilha()
    for k, val in kw.items():
        setattr(ent, k, val)
    res = calcular(ent, cfg, ano=2026)
    alq = res['aliquota_usada']
    custo = (res['custo_mo'] + res['custo_material'] + res['custo_trafo'] +
             ent.desloc + ent.entrada + ent.valor_kit +
             res['preco_venda'] * ent.comissao_pct +
             res['preco_venda'] * ent.seguro_pct +
             alq * (res['preco_venda'] - ent.valor_kit))
    m = res['margem_usada']
    ok(nome, res['preco_venda'], custo / (1 - m), 0.02)


identidade('margem 16 %')
identidade('margem 20 %', margem_desejada=0.20)
identidade('margem 12 % + comissão 3 % + seguro 1 %',
           margem_desejada=0.12, comissao_pct=0.03, seguro_pct=0.01)
identidade('margem automática (faixa)', margem_desejada=None)
identidade('c/ deslocamento e entrada',
           desloc=350.0, entrada=200.0)
identidade('kit 45 mód. 620 W / inversor 25 kW 380 V (c/ trafo)',
           qtd_modulos_kit=45, pot_inversor_kw=25, tensao_inversor=380,
           valor_kit=38000.0)
identidade('MO/material/alíquota manuais',
           mo_manual=1500.0, material_manual=650.0, aliquota_manual=0.10)

secao('5. Regras unitárias')
base = caso_planilha()
res9 = calcular((lambda x: (setattr(x, 'qtd_modulos_kit', 9), x)[1])(caso_planilha()), cfg)
ok('MO: 9 módulos → R$ 850', res9['custo_mo'], 850, 0)
res10 = calcular((lambda x: (setattr(x, 'qtd_modulos_kit', 10), x)[1])(caso_planilha()), cfg)
ok('MO: 10 módulos → R$ 850 (10×85)', res10['custo_mo'], 850, 0)
res12 = calcular((lambda x: (setattr(x, 'qtd_modulos_kit', 12), x)[1])(caso_planilha()), cfg)
ok('MO: 12 módulos → R$ 1.020', res12['custo_mo'], 1020, 0)
ok('Material: 3,72 kWp → faixa (3;6] = 500×1,6', res12['custo_material_auto']
   if False else r['custo_material_auto'], 800, 0)
e_m = caso_planilha(); e_m.qtd_modulos_kit = 10   # 6,2 kWp → faixa (6;10]
ok('Material: 6,20 kWp → 800×1,6 = 1.280',
   calcular(e_m, cfg)['custo_material_auto'], 1280, 0)


def trafo_de(kw, v):
    ent = caso_planilha()
    ent.pot_inversor_kw, ent.tensao_inversor = kw, v
    return _trafo(ent, cfg)


ok('Trafo: 12 kW/380 V → 15 kVA R$ 3.540', trafo_de(12, 380)[0], 3540, 0)
ok('Trafo: 16 kW/380 V → 20 kVA R$ 4.526', trafo_de(16, 380)[0], 4526, 0)
ok('Trafo: 20 kW/380 V → 25 kVA R$ 4.526', trafo_de(20, 380)[0], 4526, 0)
ok('Trafo: 24 kW/380 V → 30 kVA R$ 4.817', trafo_de(24, 380)[0], 4817, 0)
ok('Trafo: 32 kW/380 V → 40 kVA R$ 6.320', trafo_de(32, 380)[0], 6320, 0)
ok('Trafo: 100 kW/380 V → 150 kVA R$ 18.280', trafo_de(100, 380)[0], 18280, 0)
ok('Trafo: 13 kW/380 V → lacuna da tabela = 0', trafo_de(13, 380)[0], 0, 0)
ok('Trafo: 12 kW/220 V → não usa = 0', trafo_de(12, 220)[0], 0, 0)

u = caso_planilha().ucs[0]
ok('Tarifa TE com imposto (PR!I31)', u.te_com_imposto(), 0.36629233781518405, 1e-9)
ok('Tarifa cheia com imposto (PR!F6)', u.tarifa_cheia(), 0.8533582000334743, 1e-9)

secao('6. Sobreposições manuais no cálculo completo')
e_o = caso_planilha()
e_o.mo_manual, e_o.material_manual, e_o.aliquota_manual = 1200.0, 500.0, 0.10
ro = calcular(e_o, cfg)
ok('MO manual entra no custo', ro['custo_mo'], 1200, 0)
ok('Material manual entra no custo', ro['custo_material'], 500, 0)
ok('Alíquota manual usada (10 %)', ro['aliquota_usada'], 0.10, 1e-12)
ok('Imposto = 10 % × (venda − kit)',
   ro['custo_imposto'], 0.10 * (ro['preco_venda'] - e_o.valor_kit), 1e-6)

secao('7. % noturno: geradora usa valor informado, beneficiária usa 100 %')
# Caso do enunciado: A=600 (geradora, 65%), B=400 (beneficiária), ger≈1424.
_perfil = cfg['perfis_irradiacao']['3.8']
from engine import DIAS_MES as _DM
_media = sum(_perfil[m] / 1000 * _DM[m] for m in range(12)) / 12
_pot = round((1424 / (cfg['performance_ratio'] * _media)) * 1000 / 16, 4)
_A = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[600] * 12, pct_noturno=0.65)
_B = UC(tipo='BENEFICIÁRIA', ligacao='BIFASICO', consumos=[400] * 12, pct_noturno=0.65)
_e = Entradas(nome='enunciado', ucs=[_A, _B] + [UC() for _ in range(7)],
              qtd_modulos_kit=16, marca_inversor='CHINT', pot_inversor_kw=10,
              tensao_inversor=220, valor_kit=20000, marca_modulo='X',
              pot_modulo_w=_pot, estrutura='FIBROCIMENTO',
              perfil_irradiacao='3.8', margem_desejada=0.16)
_r = calcular(_e, cfg)
dA, dB = _r['detalhes_uc'][0], _r['detalhes_uc'][1]
ok('geração média ≈ 1424 kWh/mês', _r['geracao_media'], 1424.0, 1.0)
ok('A rateio 60 %', dA['rateio'], 0.60, 1e-9)
ok('B rateio 40 %', dB['rateio'], 0.40, 1e-9)
ok('A geração rateada = 60 % × 1424', dA['geracao_rateada'], 0.60 * _r['geracao_media'], 1e-6)
ok('B geração rateada = 40 % × 1424', dB['geracao_rateada'], 0.40 * _r['geracao_media'], 1e-6)
ok('A % noturno = 0,65 (informado)', dA['pct_noturno'], 0.65, 1e-12)
ok('B % noturno = 1,0 (beneficiária)', dB['pct_noturno'], 1.0, 1e-12)
import math as _m
ok('A faturado = TRUNC(60%×1424 × 0,65)', dA['faturado'],
   _m.trunc(0.60 * _r['geracao_media'] * 0.65), 0)
ok('B faturado = TRUNC(40%×1424 × 1,0)', dB['faturado'],
   _m.trunc(0.40 * _r['geracao_media'] * 1.0), 0)

print()
if falhas:
    print(f'{VERM}✗ {len(falhas)} verificação(ões) falharam:{FIM}', *falhas, sep='\n  - ')
    sys.exit(1)
print(f'{VERDE}✓ TODAS as verificações passaram — os valores batem com a planilha.{FIM}')
