# -*- coding: utf-8 -*-
"""Testes das correções pós-planilha (modo do app, compat_planilha=False).

Complementa o `teste_planilha.py` (réplica exata da planilha, compat=True).
Aqui travamos:
  1. Que o APP (compat=False) reproduz a fatura REAL da COPEL — sem nenhuma
     "correção" de ICMS que afaste do valor validado (R$ 125,70 no PLANILHA).
     Na COPEL: TE abatida INCLUI ICMS; TUSD abatida NÃO inclui ICMS.
  2. Lei 14.300 — abatimento limitado à geração real (corrige a superestimativa
     em sistemas subdimensionados; no-op em sistemas 100%+).
  3. Alavancas de ICMS por componente da tarifa consumida (por concessionária).

Rode com:  py -3 teste_correcoes.py
"""
import sys, math

try:
    sys.stdout.reconfigure(encoding='utf-8')   # evita crash no console cp1252
except Exception:
    pass

from engine import Entradas, UC, calcular, carregar_config

VERDE = '\033[92m'; VERM = '\033[91m'; FIM = '\033[0m'
falhas = []


def ok(nome, obtido, esperado, tol=0.01):
    if isinstance(esperado, bool):
        passou = obtido is esperado
    elif isinstance(esperado, str):
        passou = str(obtido) == esperado
    else:
        passou = abs(obtido - esperado) <= tol
    print(f'  {VERDE+"OK " if passou else VERM+"FALHOU"}{FIM} {nome:<54} '
          f'obtido={obtido!r:<22} esperado={esperado!r}')
    if not passou:
        falhas.append(nome)


def secao(t):
    print(f'\n=== {t} ===')


def caso_planilha():
    """Caso de validação (PLANILHA, COPEL, superdimensionado)."""
    uc1 = UC(tipo='GERADORA', ilum_publica=38.7, ligacao='BIFASICO',
             consumos=[344, 384, 256, 250, 300, 300, 300, 300, 300, 300, 300, 300],
             te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
             pct_noturno=0.65, bandeira='VERDE')
    return Entradas(
        nome='PLANILHA', cidade='Cidade Exemplo - PR',
        ucs=[uc1] + [UC() for _ in range(8)],
        qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=3,
        tensao_inversor=220, valor_kit=4974.72, conexao='HÍBRIDO',
        marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
        estrutura='FIBROCIMENTO', perfil_irradiacao='3.8', margem_desejada=0.16)


cfg = carregar_config()
cfg['fio_b_rs_mwh'] = 159.14        # fixo: o config é editado pelo usuário
cfg_real = dict(cfg); cfg_real['compat_planilha'] = False
cfg_plan = dict(cfg); cfg_plan['compat_planilha'] = True

# ------------------ 1) app reproduz a planilha/realidade (guarda de regressão)
secao('1. PLANILHA: regra do MAIOR VALOR (disponibilidade x sobra de Fio B)')
rp = calcular(caso_planilha(), cfg_plan, ano=2026)
rr = calcular(caso_planilha(), cfg_real, ano=2026)
# A planilha dava 125,70 porque cobrava os DOIS: tirava 50 kWh do compensado
# (pela tarifa cheia) e ainda cobrava a sobra de Fio B sobre o resto. A conta
# real escolhe o MAIOR entre custo de disponibilidade e sobra de Fio B.
ok('planilha (compat=True) fatura_com', rp['fatura_com'], 92.79249453384234, 1e-4)
ok('APP (compat=False) fatura_com NÃO diverge', rr['fatura_com'], 92.79249453384234, 1e-4)
dr = rr['detalhes_uc'][0]
ok('superdimensionado: compensa TUDO o que foi faturado',
   dr['compensado'], dr['faturado'], 1e-9)
# e quem garante o mínimo é o max(piso, liquido), não a subtração no crédito
sobra = dr['faturado'] * (dr['tarifa'] - dr['abat_te'] - dr['abat_tusd'])
ok('cobrado = max(disponibilidade, sobra do Fio B)',
   dr['taxa_min'], max(dr['piso'], sobra), 1e-9)
ok('aqui ganha a sobra do Fio B (consumo alto)', sobra > dr['piso'], True)

# --- consumo BAIXO: aí quem ganha é o custo de disponibilidade ---
uc_pouco = UC(tipo='GERADORA', ilum_publica=0.0, ligacao='BIFASICO',
              consumos=[60.0] * 12, te=0.27575, tusd=0.36667, icms=0.19,
              cofins=0.058, pis=0.0126, pct_noturno=1.0, bandeira='VERDE')
# sistema pequeno de propósito: se a geração passar do consumo, o 'maior' da
# planilha faz o faturado subir junto e o piso deixa de ser o que manda
e_pouco = Entradas(nome='pouco', ucs=[uc_pouco] + [UC() for _ in range(8)],
                   qtd_modulos_kit=2, marca_inversor='CHINT', pot_inversor_kw=3,
                   tensao_inversor=220, valor_kit=5000,
                   marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
                   estrutura='FIBROCIMENTO', perfil_irradiacao='3.8',
                   margem_desejada=0.16)
dp = calcular(e_pouco, cfg_real, ano=2026)['detalhes_uc'][0]
sobra_p = dp['faturado'] * (dp['tarifa'] - dp['abat_te'] - dp['abat_tusd'])
ok('consumo baixo: ganha o custo de disponibilidade', dp['taxa_min'], dp['piso'], 1e-9)
ok('...e a sobra do Fio B fica abaixo do piso', sobra_p < dp['piso'], True)
# assimetria proposital da COPEL: TE abatida COM ICMS, TUSD abatida SEM ICMS
u = caso_planilha().ucs[0]
fio_b = cfg['fio_b_rs_mwh'] / 1000.0 * 0.60          # 2026 = 60 %
ok('COPEL: abat_TE inclui ICMS (= TE com imposto)', u.abat_te(), u.te_com_imposto(), 1e-12)
ok('COPEL: abat_TUSD NÃO inclui ICMS = (TUSD−FioB)/(1−p−c)',
   u.abat_tusd(fio_b), (u.tusd - fio_b) / (1 - (u.pis + u.cofins)), 1e-9)

# ------------ 1b) FATURA REAL do grupo B: FATURA-B (COPEL, 09/2026) ------------
# UC 000000000000002, Cidade Exemplo-PR, B1 bifásico, TOTAL R$ 117,53.
# Consumo medido 307 kWh; a usina que ele já tem injetou 430 kWh (registrador
# GERAC) e os 307 foram compensados INTEIROS — a TE zera na fatura
# (128,20 − 128,20 = 0). O custo de disponibilidade NÃO aparece porque a sobra
# de Fio B (R$ 78,83) é maior que ele (R$ 51,59): é a regra do MAIOR VALOR.
secao('1b. Fatura real do grupo B — FATURA-B (COPEL 09/2026, R$ 117,53)')
cfg_fb = dict(cfg)
cfg_fb['compat_planilha'] = False
# Fio B que ESTA fatura cobra: a linha "ENERGIA INJETADA TUSD" devolve a TUSD
# já líquida (0,328431 contra 0,457170 cheia) -> 0,128739 R$/kWh a 60 % (2026).
cfg_fb['fio_b_rs_mwh'] = (0.457170 - 0.328431) / 0.60 * 1000

uc_fb = UC(tipo='GERADORA', ligacao='BIFASICO', uc_numero='000000000000002',
              consumos=[307.0] * 12, te=0.310850, tusd=0.457170,
              icms=0.19, cofins=0.066555, pis=0.014485,
              pct_noturno=1.0,          # o consumo da fatura já é o medido
              bandeira='AMARELA', ilum_publica=38.70, gd='GD2',
              gds_existentes=[{'nome': 'usina atual', 'injetado_kwh': 430.0}])
e_fb = Entradas(nome='CLIENTE B', cidade='Cidade Exemplo - PR',
                   ucs=[uc_fb] + [UC() for _ in range(8)],
                   qtd_modulos_kit=0, pot_modulo_w=620, valor_kit=0,
                   marca_inversor='GOODWE', pot_inversor_kw=7.5,
                   tensao_inversor=220, estrutura='FIBROCIMENTO',
                   perfil_irradiacao='3.8', margem_desejada=0.16)
r_l = calcular(e_fb, cfg_fb, ano=2026)
d_l = r_l['detalhes_uc'][0]
pc_l = 1 - (0.066555 + 0.014485)
g_l = (1 - 0.19) * pc_l
ok('TE com impostos', 0.310850 / g_l, 0.417590, 1e-4)
ok('TUSD com impostos', 0.457170 / g_l, 0.614137, 1e-4)
ok('crédito da TE devolve o ICMS (convênio vigente)',
   d_l['abat_te'], 0.417590, 1e-4)
ok('crédito da TUSD não devolve o ICMS', d_l['abat_tusd'], 0.357362, 1e-4)
ok('compensa os 307 kWh INTEIROS', d_l['compensado'], 307.0)
ok('sobra do Fio B', d_l['liquido'], 78.83, 0.02)
ok('custo de disponibilidade (não pega aqui)', d_l['piso'], 51.59, 0.02)
ok('cobrado = o maior dos dois', d_l['taxa_min'], 78.83, 0.02)
ok('bandeira amarela se anula (cobrada = devolvida)', d_l['extra_bandeira'], 0.0, 0.02)
ok('TOTAL DA FATURA (papel: R$ 117,53)', r_l['fatura_sem'], 117.53, 0.02)

# ------------ 1c) Fio B POR CONCESSIONÁRIA ------------
secao('1c. Fio B é o da concessionária da UC, não um valor único')
def _uc_fb(fb):
    return UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[400.0] * 12,
              te=0.31085, tusd=0.45717, icms=0.19, cofins=0.066555,
              pis=0.014485, pct_noturno=1.0, gd='GD2', fio_b_rs_mwh=fb)
def _calc_fb(fb):
    e = Entradas(nome='fb', ucs=[_uc_fb(fb)] + [UC() for _ in range(8)],
                 qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=3,
                 tensao_inversor=220, valor_kit=5000, pot_modulo_w=620,
                 estrutura='FIBROCIMENTO', perfil_irradiacao='3.8',
                 margem_desejada=0.16)
    return calcular(e, cfg_real, ano=2026)['detalhes_uc'][0]
d_cel, d_ems, d_glob = _calc_fb(132.7903), _calc_fb(346.1256), _calc_fb(None)
pc_fb = 1 - (0.066555 + 0.014485)
ok('CELESC: abatimento da TUSD usa o Fio B dela',
   d_cel['abat_tusd'], (0.45717 - 0.6 * 0.1327903) / pc_fb, 1e-9)
ok('ENERGISA: idem, com o dela', d_ems['abat_tusd'],
   (0.45717 - 0.6 * 0.3461256) / pc_fb, 1e-9)
ok('Fio B maior -> conta com sistema maior',
   d_ems['total'] > d_cel['total'], True)
ok('sem concessionária: usa o global do config', d_glob['abat_tusd'],
   (0.45717 - 0.6 * cfg_real['fio_b_rs_mwh'] / 1000) / pc_fb, 1e-9)
import app as _app_fb
ok('o servidor acha o Fio B pela concessionária',
   _app_fb._fio_b_da_conc('CELESC (SC)'), 132.7903, 1e-6)
ok('concessionária desconhecida -> None (cai no global)',
   _app_fb._fio_b_da_conc('NAO EXISTE') is None, True)

# ------------------ 2) abatimento parcial (subdimensionado) — Lei 14.300
secao('2. Subdimensionado: crédito limitado à geração real (Lei 14.300)')
uc = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[1100] * 12,
        te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
        pct_noturno=0.65, bandeira='VERDE')
e = Entradas(nome='subdim', ucs=[uc] + [UC() for _ in range(8)],
             qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=5,
             tensao_inversor=220, valor_kit=15000, marca_modulo='ASTRONERGY N-TYPE',
             pot_modulo_w=620, estrutura='FIBROCIMENTO', perfil_irradiacao='3.8',
             margem_desejada=0.16)
r = calcular(e, cfg_real, ano=2026)
d = r['detalhes_uc'][0]
ger_faturavel = math.trunc(d['geracao_rateada'] * d['pct_noturno'])
ok('compensação < 100 % (é subdimensionado)', r['compensacao'] < 1.0, True)
ok('crédito limitado à geração faturável', d['compensado'], ger_faturavel, 0)
ok('crédito ABAIXO do (faturado−disp) antigo',
   d['compensado'] < d['faturado'] - d['disponibilidade'], True)
comp_antigo = d['faturado'] - d['disponibilidade']
liq_antigo = d['faturado'] * d['tarifa'] - comp_antigo * (d['abat_te'] + d['abat_tusd'])
fatura_antiga = max(d['piso'], liq_antigo) + d['ilum_publica']
ok('fatura corrigida > fatura "otimista" antiga', r['fatura_com'] > fatura_antiga + 1, True)

# ------------------ 3) ICMS por componente da tarifa CONSUMIDA (concessionária)
secao('3. Alavancas de ICMS por componente da tarifa consumida')
base = dict(te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
            tipo='GERADORA', ligacao='BIFASICO')
u_full = UC(**base, icms_te=True, icms_tusd=True)      # COPEL/PR
u_sem_te = UC(**base, icms_te=False, icms_tusd=True)
u_sem_tusd = UC(**base, icms_te=True, icms_tusd=False)
ok('COPEL: TE com ICMS', u_full.te_com_imposto(), 0.36629233781518405, 1e-9)
ok('sem ICMS na TE: TE menor', u_sem_te.te_com_imposto(),
   0.27575 / (1 - (0.058 + 0.0126)), 1e-9)
ok('sem ICMS na TUSD: TUSD menor', u_sem_tusd.tusd_com_imposto(),
   0.36667 / (1 - (0.058 + 0.0126)), 1e-9)
ok('componentes independentes', u_sem_te.tusd_com_imposto(),
   u_full.tusd_com_imposto(), 1e-12)

# ------------------ 4) fiação: regra da concessionária → engine pelo payload
secao('4. Fiação: regra da concessionária chega ao engine pelo payload')
import app
with app.app.test_request_context():       # _montar_entradas lê session
    ent = app._montar_entradas({'ucs': [{
        'tipo': 'GERADORA', 'ligacao': 'BIFASICO', 'consumos': [300] * 12,
        'te': 0.27575, 'tusd': 0.36667, 'icms': 19, 'cofins': 5.8, 'pis': 1.26,
        'icms_te': False, 'icms_tusd': True}]})
    u0 = ent.ucs[0]
    padrao = app._montar_entradas({'ucs': [{'tipo': 'GERADORA'}]}).ucs[0].icms_te
ok('payload icms_te=False chega na UC', u0.icms_te, False)
ok('payload icms_tusd=True chega na UC', u0.icms_tusd, True)
ok('sem info, padrão é COPEL (icms_te=True)', padrao, True)

# ------------------ 5) isenção alcança a TUSD? (regra por estado)
secao('5. TUSD abatida COM ICMS (SP/MG) vs SEM (COPEL/RS)')
fio_b = cfg['fio_b_rs_mwh'] / 1000.0 * 0.60
pc = 1 - (0.0126 + 0.058)
u_pr = UC(te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
          tipo='GERADORA', ligacao='BIFASICO', abat_tusd_inclui_icms=False)
u_sp = UC(te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
          tipo='GERADORA', ligacao='BIFASICO', abat_tusd_inclui_icms=True)
ok('COPEL/RS: TUSD abatida SEM ICMS', u_pr.abat_tusd(fio_b), (0.36667 - fio_b) / pc, 1e-9)
ok('SP/MG: TUSD abatida COM ICMS', u_sp.abat_tusd(fio_b),
   (0.36667 / (1 - 0.19) - fio_b) / pc, 1e-9)
liq_sp = u_sp.tarifa_cheia() - (u_sp.abat_te() + u_sp.abat_tusd(fio_b))
ok('SP: kWh compensado paga só o Fio B', liq_sp, fio_b / pc, 1e-9)
ok('SP abate mais que COPEL na TUSD', u_sp.abat_tusd(fio_b) > u_pr.abat_tusd(fio_b), True)
# a regra viaja pelo payload
with app.app.test_request_context():
    usp = app._montar_entradas({'ucs': [{'tipo': 'GERADORA',
        'abat_tusd_inclui_icms': True}]}).ucs[0]
ok('payload abat_tusd_inclui_icms=True chega na UC', usp.abat_tusd_inclui_icms, True)

print()
if falhas:
    print(f'{VERM}✗ {len(falhas)} verificação(ões) falharam:{FIM}', *falhas, sep='\n  - ')
    sys.exit(1)
print(f'{VERDE}✓ TODAS as correções conferidas — comportamento correto travado.{FIM}')
