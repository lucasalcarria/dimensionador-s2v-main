# -*- coding: utf-8 -*-
"""Testes das correções pós-planilha (modo do app, compat_planilha=False).

Complementa o `teste_planilha.py` (réplica exata da planilha, compat=True).
Aqui travamos:
  1. Que o APP (compat=False) reproduz a fatura REAL da COPEL — sem nenhuma
     "correção" de ICMS que afaste do valor validado (R$ 125,70 no NEUZA).
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


def neuza():
    """Caso de validação (NEUZA, COPEL, superdimensionado)."""
    uc1 = UC(tipo='GERADORA', ilum_publica=38.7, ligacao='BIFASICO',
             consumos=[344, 384, 256, 250, 300, 300, 300, 300, 300, 300, 300, 300],
             te=0.27575, tusd=0.36667, icms=0.19, cofins=0.058, pis=0.0126,
             pct_noturno=0.65, bandeira='VERDE')
    return Entradas(
        nome='NEUZA', cidade='Mandaguaçu - PR',
        ucs=[uc1] + [UC() for _ in range(8)],
        qtd_modulos_kit=6, marca_inversor='CHINT', pot_inversor_kw=3,
        tensao_inversor=220, valor_kit=4974.72, conexao='HÍBRIDO',
        marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
        estrutura='FIBROCIMENTO', perfil_irradiacao='3.8', margem_desejada=0.16)


cfg = carregar_config()
cfg_real = dict(cfg); cfg_real['compat_planilha'] = False
cfg_plan = dict(cfg); cfg_plan['compat_planilha'] = True

# ------------------ 1) app reproduz a planilha/realidade (guarda de regressão)
secao('1. NEUZA: app (compat=False) == planilha == fatura real (R$ 125,70)')
rp = calcular(neuza(), cfg_plan, ano=2026)
rr = calcular(neuza(), cfg_real, ano=2026)
ok('planilha (compat=True) fatura_com', rp['fatura_com'], 125.69641635251203, 1e-4)
ok('APP (compat=False) fatura_com NÃO diverge', rr['fatura_com'], 125.69641635251203, 1e-4)
dr = rr['detalhes_uc'][0]
ok('cap é no-op em superdim. (compensado = faturado−disp)',
   dr['compensado'], dr['faturado'] - dr['disponibilidade'], 1e-9)
# assimetria proposital da COPEL: TE abatida COM ICMS, TUSD abatida SEM ICMS
u = neuza().ucs[0]
fio_b = cfg['fio_b_rs_mwh'] / 1000.0 * 0.60          # 2026 = 60 %
ok('COPEL: abat_TE inclui ICMS (= TE com imposto)', u.abat_te(), u.te_com_imposto(), 1e-12)
ok('COPEL: abat_TUSD NÃO inclui ICMS = (TUSD−FioB)/(1−p−c)',
   u.abat_tusd(fio_b), (u.tusd - fio_b) / (1 - (u.pis + u.cofins)), 1e-9)

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
