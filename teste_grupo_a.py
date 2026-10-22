# -*- coding: utf-8 -*-
"""Testes do GRUPO A (média tensão) — fatura com demanda e ponta/fora ponta.

O grupo A não está na planilha: é uma extensão. Estes testes travam o que foi
decidido, para ninguém "consertar" depois sem perceber o estrago:

  1. Grupo B não muda nada (a UC nasce grupo B; `teste_planilha` continua
     valendo — aqui só conferimos que a ponta vazia é inofensiva).
  2. A DEMANDA é paga igual com e sem sistema — o solar não abate kW.
  3. O crédito abate primeiro o FORA PONTA; a sobra abate a PONTA corrigida
     pelo fator de ajuste da REN 1.059/2023 (relação entre as TEs).
  4. A fatura COM sistema nunca cai abaixo do piso (demanda + iluminação).
  5. Não existe custo de disponibilidade (30/50/100 kWh) no grupo A.
  6. Fio B só na PONTA: fora ponta ele é zero (o fio é pago na demanda) e o
     kWh compensado abate TE + TUSD-energia inteiras; o crédito GD2 que migra
     para a PONTA desconta o Fio B de ponta escalonado (seção 19). Há,
     opcionalmente, TUSD-G (demanda de geração), que só existe COM o sistema.
  7. Ultrapassagem de demanda (acima de 105 % da contratada) é cobrada.
  8. O dimensionamento usa o consumo EQUIVALENTE (a ponta pede mais geração).
  9. Só o ADMIN cria UC do grupo A — o payload de um consultor volta a grupo B.
 10. CASO DE VALIDAÇÃO REAL: fatura CLIENTE A (A4 Verde, COPEL,
     UC 000000000000001, ref. 09/2026) — bate linha a linha com o papel.

### Caso de validação (ALIMENTOS FATURA-A — A4 Verde, COPEL/PR, 09/2026)
Total da fatura **R$ 17.648,07**. Consumo 1.039 kWh ponta + 18.434 kWh fora
ponta; injetados 5.490 kWh (usina 135 kW, **GD1** → sem Fio B); demanda
contratada 175 kW, **faturada 167,47 kW** × R$ 25,33/kW; bandeira AMARELA;
COSIP R$ 132,37; reativo excedente R$ 362,34 + R$ 61,90.
ICMS 19 %, PIS 1,44 %, COFINS 6,63 %.

Esta fatura **já perdeu o prazo do Convênio ICMS 16/2015**: o crédito NÃO
devolve o ICMS da TE (`abat_te_inclui_icms=False`) — dá para ver na própria
fatura, em que a linha "ENERGIA INJETADA FP TE" tem ICMS 0,00 e vale
R$ 0,321710 (= TE ÷ (1−PIS−COFINS)), enquanto a TE consumida sai por
R$ 0,397175 (= TE ÷ ((1−ICMS)(1−PIS−COFINS))).

Rode com:  py -3 teste_grupo_a.py
"""
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')   # evita crash no console cp1252
except Exception:
    pass

from engine import Entradas, UC, calcular, carregar_config, fator_fio_b

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


# Caso-base: comércio A4 Verde, 100 kW contratados, 20.000 kWh fora ponta e
# 2.000 kWh na ponta por mês. Tarifas em ordem de grandeza de A4 no PR.
def uc_a4(**kw):
    base = dict(
        tipo='GERADORA', grupo='A', subgrupo_a='A4', modalidade_a='VERDE',
        ligacao='TRIFASICO', consumos=[20000.0] * 12,
        consumos_ponta=[2000.0] * 12,
        demanda_kw=100.0, tusd_demanda=25.0,
        te_ponta=0.90, te_fora=0.30,
        tusd_kwh_ponta=0.18, tusd_kwh_fora=0.10,
        icms=0.19, cofins=0.0663, pis=0.0144)
    base.update(kw)
    return UC(**base)


def entradas(u: UC, qtd_modulos=0, **kw):
    base = dict(nome='TESTE GRUPO A', ucs=[u] + [UC() for _ in range(8)],
                qtd_modulos_kit=qtd_modulos, marca_inversor='CHINT',
                pot_inversor_kw=75, tensao_inversor=380, valor_kit=100000,
                marca_modulo='ASTRONERGY N-TYPE', pot_modulo_w=620,
                estrutura='SOLO', perfil_irradiacao='3.8',
                margem_desejada=0.16)
    base.update(kw)
    return Entradas(**base)


def engine_fatura(u: UC, ger_uc: float, cfg: dict, ano: int = 2026):
    """Fatura de UMA UC do grupo A para uma geração conhecida (sem passar pelo
    rateio) — é assim que se confere contra o papel."""
    from engine import _fatura_grupo_a
    return _fatura_grupo_a(u, ger_uc, cfg)


cfg = carregar_config()
cfg['performance_ratio'] = 0.75     # fixo: o config é editado pelo usuário
ano = 2026
fator = fator_fio_b(cfg, ano)

secao('1. Grupo B segue intocado (ponta vazia não atrapalha)')
b = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[344.0] * 12,
       te=0.31085, tusd=0.45717, icms=0.19, cofins=0.0663, pis=0.0144)
ok('UC nasce no grupo B', b.grupo, 'B')
ok('grupo B não é grupo A', b.eh_grupo_a, False)
ok('consumo médio ignora ponta zerada', b.consumo_medio, 344.0)

secao('2. Demanda: o solar não abate kW')
u = uc_a4()
sem = calcular(entradas(u, 0), cfg, ano)          # sem sistema nenhum
com = calcular(entradas(uc_a4(), 300), cfg, ano)  # 300 módulos = 186 kWp
d_sem = sem['detalhes_uc'][0]
d_com = com['detalhes_uc'][0]
ok('a parcela de demanda é a mesma com e sem sistema',
   round(d_com['demanda_rs'], 2), round(d_sem['demanda_rs'], 2))
# 100 kW × R$ 25,00 com ICMS 19 % e PIS/COFINS 8,07 %
esperado_dem = 100 * 25.0 / ((1 - 0.19) * (1 - (0.0663 + 0.0144)))
ok('demanda = kW × tarifa, com impostos', d_sem['demanda_rs'], esperado_dem, 0.05)
ok('sem sistema, fatura COM = fatura SEM', round(sem['fatura_com'], 2),
   round(sem['fatura_sem'], 2))

secao('3. Autoconsumo × injeção (sem %noturno) e fator da ponta)')
ok('fator de correção = TE ponta / TE fora ponta', u.fator_ajuste_ponta(), 3.0)
ok('fator informado à mão prevalece',
   uc_a4(fator_ponta_manual=1.63).fator_ajuste_ponta(), 1.63)
# PADRÃO = PIOR CASO (decisão do usuário): nada de autoconsumo, toda a
# geração do sistema novo é injetada e volta como crédito
pc = calcular(entradas(uc_a4(), 27), cfg, ano)['detalhes_uc'][0]
ok('pior caso (padrão): autoconsumo zero', pc['autoconsumo'], 0.0)
ok('pior caso: toda a geração é injetada', pc['injetado'],
   int(pc['geracao_rateada']), 0)
ok('pior caso: o resultado diz a regra', pc['autoconsumo_regra'], 'pior_caso')
# as outras regras continuam disponíveis (config.autoconsumo_grupo_a)
cfg_ot = dict(cfg, autoconsumo_grupo_a='otimista')
cfg_med = dict(cfg, autoconsumo_grupo_a='medido')
# OTIMISTA — sistema pequeno diante do consumo: tudo usado na hora
peq = calcular(entradas(uc_a4(), 27), cfg_ot, ano)    # ~16,7 kWp
dp = peq['detalhes_uc'][0]
ok('geração pequena vira toda autoconsumo',
   dp['autoconsumo'], dp['geracao_rateada'], 1.0)
ok('nada injetado', dp['injetado'], 0.0)
ok('e nada compensado na ponta', dp['compensado_ponta'], 0.0)
# sistema grande: cobre todo o fora ponta e o excedente vira crédito p/ a ponta
gr = calcular(entradas(uc_a4(), 400), cfg_ot, ano)
dg = gr['detalhes_uc'][0]
ok('autoconsumo limitado ao consumo fora ponta', dg['autoconsumo'], 20000.0, 1.0)
ok('fora ponta zerado: não sobra nada para compensar lá',
   dg['compensado_fora'], 0.0, 1.0)
ok('excedente injetado = geração − fora ponta',
   dg['injetado'], dg['geracao_rateada'] - 20000.0, 1.0)
ok('ponta = min(consumo, injetado / fator)', dg['compensado_ponta'],
   min(2000.0, dg['injetado'] / 3.0), 1.0)

secao('4. Piso da conta: demanda + iluminação pública')
enorme = calcular(entradas(uc_a4(ilum_publica=50.0), 900), cfg, ano)
de = enorme['detalhes_uc'][0]
ok('fatura COM não fica abaixo do piso', de['total'] >= de['piso'] - 0.01, True)
ok('piso = demanda + COSIP', de['piso'], de['demanda_rs'] + 50.0, 0.01)

secao('5. Não existe custo de disponibilidade no grupo A')
ok('disponibilidade zerada', de['disponibilidade'], 0.0)
tri = uc_a4(ligacao='TRIFASICO')
mono = uc_a4(ligacao='MONOFASICO')
r1 = calcular(entradas(tri, 300), cfg, ano)['fatura_com']
r2 = calcular(entradas(mono, 300), cfg, ano)['fatura_com']
ok('a ligação não muda a fatura do grupo A', round(r1, 2), round(r2, 2))

secao('6. Sem Fio B no grupo A + TUSD-G (demanda de geração)')
d2 = calcular(entradas(uc_a4(gd='GD2'), 300), cfg, ano)['detalhes_uc'][0]
d1 = calcular(entradas(uc_a4(gd='GD1'), 300), cfg, ano)['detalhes_uc'][0]
ok('GD1 e GD2 abatem igual (não há Fio B)', d1['abat_fora'], d2['abat_fora'], 1e-9)
# o kWh compensado devolve a TE cheia + a TUSD INTEIRA (só PIS/COFINS)
pc = 1 - (0.0663 + 0.0144)
te_cheia = 0.30 / ((1 - 0.19) * pc)
ok('abatimento fora ponta = TE cheia + TUSD inteira',
   d2['abat_fora'], te_cheia + 0.10 / pc, 1e-9)
ok('abatimento na ponta = TE cheia + TUSD inteira',
   d2['abat_ponta'], 0.90 / ((1 - 0.19) * pc) + 0.18 / pc, 1e-9)

# TUSD-G: contrata-se só o que os inversores passam da demanda de consumo.
# O caso-base tem 100 kW contratados; com 150 kW de inversor sobram 50 kW.
g = calcular(entradas(uc_a4(tusd_g_rs_kw=7.88), 300,
                      pot_inversor_kw=150), cfg, ano)['detalhes_uc'][0]
ok('TUSD-G = inversores − demanda de consumo', g['demanda_g_kw'], 50.0, 0.01)
# a entrada é SEM impostos: R$ 7,88 viram ~R$ 10,58/kW com ICMS e PIS/COFINS
ok('TUSD-G com impostos ~ R$ 10,58/kW', g['tusd_g_cheia'], 10.58, 0.01)
ok('custo da TUSD-G', g['custo_g'], 50 * g['tusd_g_cheia'], 0.01)
sem_g = calcular(entradas(uc_a4(tusd_g_rs_kw=7.88), 300,
                          pot_inversor_kw=80), cfg, ano)['detalhes_uc'][0]
ok('inversor menor que a demanda: nada a contratar', sem_g['demanda_g_kw'], 0.0)
manual = calcular(entradas(uc_a4(tusd_g_rs_kw=7.88, demanda_g_kw=30), 300,
                           pot_inversor_kw=150), cfg, ano)['detalhes_uc'][0]
ok('kW informado à mão prevalece', manual['demanda_g_kw'], 30.0)
ok('a TUSD-G entra só na fatura COM sistema',
   g['fatura_sem_uc'], sem_g['fatura_sem_uc'], 0.01)
ok('e encarece a fatura COM sistema', g['total'] > sem_g['total'], True)

secao('7. Ultrapassagem de demanda (acima de 105 % da contratada)')
dentro = calcular(entradas(uc_a4(demanda_medida_kw=104.0), 0),
                  cfg, ano)['detalhes_uc'][0]
fora = calcular(entradas(uc_a4(demanda_medida_kw=130.0), 0),
                cfg, ano)['detalhes_uc'][0]
ok('104 kW medidos em 100 contratados: sem ultrapassagem',
   dentro['demanda_fp']['ultrapassagem'], 0.0)
ok('130 kW medidos: cobra o excedente de novo',
   fora['demanda_fp']['ultrapassagem'],
   30 * 25.0 / ((1 - 0.19) * (1 - (0.0663 + 0.0144))), 0.05)

secao('8. Dimensionamento pelo consumo equivalente')
r = calcular(entradas(uc_a4(), 300), cfg, ano)
ok('consumo anual soma os dois postos', r['consumo_anual'], 22000.0 * 12, 1.0)
ok('equivalente = fora ponta + ponta × fator',
   r['consumo_anual_equiv'], (20000.0 + 2000.0 * 3.0) * 12, 1.0)
ok('kWp necessário é maior que o do consumo bruto',
   r['consumo_anual_equiv'] > r['consumo_anual'], True)
# usina existente já abate parte do consumo: o projeto novo cobre só o resto
com_ex = calcular(entradas(uc_a4(gds_existentes=[
    {'nome': 'antiga', 'injetado_kwh': 5000.0}]), 300), cfg, ano)
ok('a injeção existente é descontada do dimensionamento',
   com_ex['consumo_anual_equiv'], r['consumo_anual_equiv'] - 5000 * 12, 1.0)
ok('e o kWp necessário cai', com_ex['kwp_necessario'] < r['kwp_necessario'], True)

secao('10. Fatura real ALIMENTOS FATURA-A (A4 Verde, COPEL, 09/2026)')
# Tarifas SEM tributos, como impressas na coluna "Tarifa unit. (R$)".
fatura_a = UC(
    tipo='GERADORA', grupo='A', subgrupo_a='A4', modalidade_a='VERDE',
    gd='GD1',                                   # usina GD1: isenta de Fio B
    uc_numero='000000000000001', ligacao='TRIFASICO',
    consumos=[18434.0] * 12,                    # fora ponta (já medido)
    consumos_ponta=[1039.0] * 12,
    demanda_kw=175.0, demanda_faturada_kw=167.47, tusd_demanda=25.33,
    te_ponta=0.475500, tusd_kwh_ponta=1.463390,
    te_fora=0.295750, tusd_kwh_fora=0.146590,
    icms=0.19, cofins=0.0663, pis=0.0144,
    bandeira='AMARELA', ilum_publica=132.37,
    outros_rs=362.34 + 61.90,                   # reativo excedente (não muda)
    abat_te_inclui_icms=False,                  # convênio 16/2015 vencido
    # a usina de 135 kW que o cliente JÁ TEM: injeta 5.490 kWh no mês. O
    # consumo impresso na fatura já está líquido do autoconsumo dela.
    gds_existentes=[{'nome': 'usina atual', 'kwp': 135.0,
                     'injetado_kwh': 5490.0, 'isento_icms': False}])

INJ = 5490.0
e_at = entradas(fatura_a, 0)
r_at = calcular(e_at, cfg, 2026)
# sem projeto NOVO (ger_uc = 0): o que sai é a fatura de hoje, com o crédito
# da usina existente — exatamente o papel.
d_at = engine_fatura(fatura_a, 0.0, cfg)
ok('fator de correção da FATURA-A (~1,63 na prática)',
   fatura_a.fator_ajuste_ponta(), 1.608, 0.01)

# A coluna "Tarifa unit." da fatura vem arredondada em 4 casas: a TE ponta sai
# impressa como 0,475500, mas o valor cobrado (663,53 ÷ 1.039) implica
# 0,475541 — daí a folga de 1e-4 nestas duas linhas. O mesmo na demanda
# (25,330000 impresso). As tarifas de fora ponta, que é onde está 95 % do
# dinheiro, batem na 6ª casa.
ok('preço unit. TE ponta com tributos', fatura_a._cheia(0.475500, 0), 0.638624, 1e-4)
ok('preço unit. TUSD ponta com tributos', fatura_a._cheia(0, 1.463390), 1.965255, 1e-5)
ok('preço unit. TE fora ponta com tributos', fatura_a._cheia(0.295750, 0), 0.397175, 1e-5)
ok('preço unit. TUSD fora ponta com tributos', fatura_a._cheia(0, 0.146590), 0.196862, 1e-5)
ok('preço unit. da DEMANDA com tributos',
   25.33 / ((1 - 0.19) * (1 - (0.0663 + 0.0144))), 34.016719, 1e-4)
# o abatimento por kWh injetado é a soma das duas linhas negativas da fatura:
# TE 0,321710 (sem ICMS, convênio vencido) + TUSD 0,159457 (GD1, sem Fio B)
ok('crédito por kWh injetado (TE + TUSD, sem ICMS)',
   fatura_a.abat_posto(False), 0.321710 + 0.159457, 1e-5)
ok('a TE do crédito não traz o ICMS de volta',
   0.295750 / (1 - (0.0663 + 0.0144)), 0.321710, 1e-5)
ok('adicional bandeira cobrado (com ICMS)', fatura_a.band_cheia(0.01885), 0.025314, 1e-5)
ok('adicional bandeira devolvido (sem ICMS)', fatura_a.band_credito(0.01885), 0.020503, 1e-5)

ok('energia PONTA cobrada', 1039 * d_at['tarifa_ponta'], 663.53 + 2041.90, 0.10)
ok('energia FORA PONTA cobrada', 18434 * d_at['tarifa_fora'], 7321.53 + 3628.96, 0.10)
ok('crédito da energia injetada', INJ * d_at['abat_fora'], 1766.19 + 875.42, 0.10)
ok('parcela de DEMANDA', d_at['demanda_rs'], 5696.78, 0.05)
ok('bandeira cobrada', (1039 + 18434) * fatura_a.band_cheia(0.01885), 26.29 + 466.64, 0.10)
ok('bandeira devolvida', INJ * fatura_a.band_credito(0.01885), 112.56, 0.10)
ok('a usina existente é reconhecida', d_at['injecao_existente'], INJ)
ok('compensado = tudo o que ela injeta', d_at['compensado_fora'], INJ, 1.0)
ok('nenhuma geração nova neste cenário', d_at['injetado'], 0.0)
ok('nada sobrou para a ponta', d_at['compensado_ponta'], 0.0, 0.5)
# 6 centavos de diferença no total: a COPEL arredonda CADA linha em 2 casas.
ok('TOTAL DA FATURA (papel: R$ 17.648,07)', d_at['total'], 17648.07, 0.15)
ok('a fatura de HOJE já vem compensada (sem projeto novo, sem = com)',
   d_at['fatura_sem_uc'], d_at['total'], 0.01)
# tirando a usina existente, a conta volta ao bruto (o que ele pagaria sem GD)
bruto = engine_fatura(
    UC(**{**{k: v for k, v in fatura_a.__dict__.items()
             if k != 'gds_existentes'}, 'gds_existentes': []}), 0.0, cfg)
ok('sem NENHUMA usina, a conta é a bruta',
   bruto['total'], 17648.07 + 1766.19 + 875.42 + 112.56, 0.20)

secao('11. Prazo do Convênio 16/2015 (corre por PARECER DE ACESSO)')
# usina NOVA: 4 anos de isenção e depois a economia cai de patamar
nova = uc_a4(abat_te_inclui_icms=True, isencao_icms_anos=4)
r_nova = calcular(entradas(nova, 300), cfg, ano)
ok('projeção sabe quando a isenção acaba', r_nova['anos_isencao'], 4.0)
ok('economia depois do prazo é menor',
   r_nova['economia_pos_isencao'] < r_nova['economia_mensal'], True)
serie = r_nova['retorno_serie']
# anos 1..4 com isenção, 5º em diante sem: a série cai justo na virada
salto_normal = serie[2] / serie[1]
salto_virada = serie[4] / serie[3]
ok('a série desce de patamar no 5º ano', salto_virada < salto_normal, True)

# sem informar o prazo, nada muda (é o comportamento das propostas de hoje)
sem_prazo = calcular(entradas(uc_a4(abat_te_inclui_icms=True), 300), cfg, ano)
ok('sem o prazo informado, projeção antiga',
   sem_prazo['anos_isencao'] is None, True)
ok('sem o prazo, a série é a de sempre',
   sem_prazo['retorno_serie'][4] / sem_prazo['retorno_serie'][3],
   salto_normal, 1e-9)
# usina já fora do prazo (FATURA-A): 0 ano restante = sem isenção desde já
velha = uc_a4(abat_te_inclui_icms=False, isencao_icms_anos=0)
r_velha = calcular(entradas(velha, 300), cfg, ano)
ok('usina fora do prazo: economia já é a reduzida',
   r_velha['economia_pos_isencao'], r_velha['economia_mensal'], 0.01)
ok('retorno da usina nova supera o da que já perdeu a isenção',
   r_nova['retorno_25'] > r_velha['retorno_25'], True)

secao('12. Usina já existente também no grupo B')
b_sem = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[600.0] * 12,
           te=0.31085, tusd=0.45717, icms=0.19, cofins=0.0663, pis=0.0144,
           pct_noturno=1.0)
b_com = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[600.0] * 12,
           te=0.31085, tusd=0.45717, icms=0.19, cofins=0.0663, pis=0.0144,
           pct_noturno=1.0,
           gds_existentes=[{'nome': 'usina antiga', 'injetado_kwh': 300.0}])
r_b1 = calcular(entradas(b_sem, 20), cfg, ano)
r_b2 = calcular(entradas(b_com, 20), cfg, ano)
ok('sem usina existente, a fatura SEM é a da planilha',
   r_b1['fatura_sem'] > r_b2['fatura_sem'], True)
ok('com usina existente, a conta de HOJE já vem abatida',
   r_b2['fatura_sem'] < r_b1['fatura_sem'], True)
ok('e por isso a economia do NOVO projeto é menor',
   r_b2['economia_mensal'] < r_b1['economia_mensal'], True)
ok('a fatura COM é melhor (mais energia compensada)',
   r_b2['fatura_com'] <= r_b1['fatura_com'] + 0.01, True)

secao('13. Isenção de ICMS corre por PARECER: cada usina tem a sua')
# duas usinas iguais no tamanho, uma dentro do prazo e outra fora
dentro = uc_a4(gds_existentes=[{'nome': 'nova', 'injetado_kwh': 3000.0,
                                'isento_icms': True}])
fora = uc_a4(gds_existentes=[{'nome': 'antiga', 'injetado_kwh': 3000.0,
                              'isento_icms': False}])
d_in = calcular(entradas(dentro, 0), cfg, ano)['detalhes_uc'][0]
d_fo = calcular(entradas(fora, 0), cfg, ano)['detalhes_uc'][0]
ok('usina no prazo abate mais que a vencida',
   d_in['fatura_sem_uc'] < d_fo['fatura_sem_uc'], True)
# a diferença é exatamente o ICMS da TE sobre os 3.000 kWh compensados
pc = 1 - (0.0663 + 0.0144)
dif = 3000 * (0.30 / ((1 - 0.19) * pc) - 0.30 / pc)
ok('e a diferença é o ICMS da TE do crédito',
   d_fo['fatura_sem_uc'] - d_in['fatura_sem_uc'], dif, 0.05)

# as duas juntas na mesma UC: cada uma com seu abatimento
mista = uc_a4(gds_existentes=[{'nome': 'antiga', 'injetado_kwh': 3000.0,
                               'isento_icms': False},
                              {'nome': 'nova', 'injetado_kwh': 3000.0,
                               'isento_icms': True}])
d_mi = calcular(entradas(mista, 0), cfg, ano)['detalhes_uc'][0]
ok('as duas juntas compensam 6.000 kWh', d_mi['compensado_fora'], 6000.0, 1.0)
so_fora = calcular(entradas(uc_a4(gds_existentes=[
    {'nome': 'a', 'injetado_kwh': 3000.0, 'isento_icms': False},
    {'nome': 'b', 'injetado_kwh': 3000.0, 'isento_icms': False}]), 0),
    cfg, ano)['detalhes_uc'][0]
so_dentro = calcular(entradas(uc_a4(gds_existentes=[
    {'nome': 'a', 'injetado_kwh': 3000.0, 'isento_icms': True},
    {'nome': 'b', 'injetado_kwh': 3000.0, 'isento_icms': True}]), 0),
    cfg, ano)['detalhes_uc'][0]
ok('a mista fica no meio do caminho',
   so_dentro['fatura_sem_uc'] < d_mi['fatura_sem_uc'] < so_fora['fatura_sem_uc'],
   True)

# grupo B: mesma regra
b = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[900.0] * 12,
       te=0.31085, tusd=0.45717, icms=0.19, cofins=0.0663, pis=0.0144,
       pct_noturno=1.0,
       gds_existentes=[{'nome': 'antiga', 'injetado_kwh': 400.0,
                        'isento_icms': False}])
b2 = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[900.0] * 12,
        te=0.31085, tusd=0.45717, icms=0.19, cofins=0.0663, pis=0.0144,
        pct_noturno=1.0,
        gds_existentes=[{'nome': 'nova', 'injetado_kwh': 400.0,
                         'isento_icms': True}])
rb = calcular(entradas(b, 10), cfg, ano)
rb2 = calcular(entradas(b2, 10), cfg, ano)
ok('grupo B: usina vencida deixa a conta de hoje mais cara',
   rb['fatura_sem'] > rb2['fatura_sem'], True)

secao('14. Geração REAL da usina existente (o medidor não vê o autoconsumo)')
# A fatura mostra consumo 307 e injeção 430. O app diz que a usina gerou 600:
# logo 170 kWh foram gerados e consumidos na hora, sem passar pelo medidor.
# Esses 170 faltam NOS DOIS lados: consumo real 477, geração real 600.
b = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[307.0] * 12,
       te=0.310850, tusd=0.457170, icms=0.19, cofins=0.066555, pis=0.014485,
       pct_noturno=1.0, bandeira='AMARELA', ilum_publica=38.70,
       gds_existentes=[{'nome': 'usina atual', 'injetado_kwh': 430.0,
                        'geracao_kwh': 600.0}])
ok('autoconsumo = geração real − injetado', b.autoconsumo_existente(), 170.0)
ok('geração real da usina', b.geracao_existente(), 600.0)
ok('consumo medido (o da fatura)', b.consumo_medio, 307.0)
ok('consumo REAL = medido + autoconsumo', b.consumo_real_medio, 477.0)

def _calc(uc):
    return calcular(entradas(uc, 0), cfg, ano)

r_real = _calc(b)
ok('o consumo mostrado passa a ser o real', r_real['consumo_medio'], 477.0, 0.1)
ok('o medido continua disponível', r_real['consumo_medido_anual'] / 12, 307.0, 0.1)

# sem informar a geração, o programa só conhece o que o medidor viu
b2 = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[307.0] * 12,
        te=0.310850, tusd=0.457170, icms=0.19, cofins=0.066555, pis=0.014485,
        pct_noturno=1.0, bandeira='AMARELA', ilum_publica=38.70,
        gds_existentes=[{'nome': 'usina atual', 'injetado_kwh': 430.0}])
ok('sem a geração do app, autoconsumo é desconhecido (zero)',
   b2.autoconsumo_existente(), 0.0)
ok('e o consumo mostrado volta a ser o medido',
   _calc(b2)['consumo_medio'], 307.0, 0.1)

# a FATURA não muda: a concessionária cobra o que o medidor viu
ok('a fatura é a mesma nos dois casos (cobra-se o medido)',
   round(r_real['fatura_sem'], 2), round(_calc(b2)['fatura_sem'], 2))

# o autoconsumo entra nos dois lados e se cancela no dimensionamento
ok('dimensionamento não muda (o autoconsumo se cancela)',
   r_real['consumo_anual_equiv'], _calc(b2)['consumo_anual_equiv'], 0.1)

secao('15. Autoconsumo: fração MEDIDA na usina atual, não hipótese')
# Regra "medido": sem usina com geração informada, cai no PIOR CASO (nada de
# autoconsumo); a regra "otimista" assume absorção total até o fora ponta.
sem_med = calcular(entradas(uc_a4(), 300), cfg_med, ano)['detalhes_uc'][0]
ok('sem medição, o autoconsumo não é medido', sem_med['autoconsumo_medido'], False)
ok('e cai no pior caso (zero)', sem_med['autoconsumo'], 0.0)
ot = calcular(entradas(uc_a4(), 300), cfg_ot, ano)['detalhes_uc'][0]
ok('otimista: absorção até o consumo fora ponta',
   ot['autoconsumo'], min(20000.0, ot['geracao_rateada']), 1.0)

# Com a usina atual medida (gerou 1.000, injetou 400 -> 60 % fica na casa), o
# motor usa ESSA fração para o sistema novo em vez de arbitrar.
med = uc_a4(gds_existentes=[{'nome': 'atual', 'injetado_kwh': 400.0,
                             'geracao_kwh': 1000.0}])
ok('fração de autoconsumo medida', med.fracao_autoconsumo(), 0.6, 1e-9)
d_med = calcular(entradas(med, 300), cfg_med, ano)['detalhes_uc'][0]
ok('agora o autoconsumo é medido', d_med['autoconsumo_medido'], True)
ok('autoconsumo = geração × fração medida',
   d_med['autoconsumo'], min(20000.0, d_med['geracao_rateada'] * 0.6), 1.0)
ok('e sobra MAIS para injetar que na hipótese otimista',
   d_med['injetado'] > ot['injetado'], True)
ok('e MENOS que no pior caso', d_med['injetado'] < sem_med['injetado'], True)

secao('16. Rateio entre usinas é PROPORCIONAL ao que cada uma injetou')
# Duas usinas iguais, uma no prazo da isenção e outra fora: o crédito devolvido
# tem de ser a média das duas, não o de quem veio primeiro na lista.
def _mista(ordem):
    return uc_a4(gds_existentes=[
        {'nome': 'a', 'injetado_kwh': 3000.0, 'isento_icms': ordem[0]},
        {'nome': 'b', 'injetado_kwh': 3000.0, 'isento_icms': ordem[1]}])
d1 = calcular(entradas(_mista([True, False]), 0), cfg, ano)['detalhes_uc'][0]
d2 = calcular(entradas(_mista([False, True]), 0), cfg, ano)['detalhes_uc'][0]
ok('a ordem das usinas na lista NÃO muda a conta',
   d1['fatura_sem_uc'], d2['fatura_sem_uc'], 1e-9)
so_sim = calcular(entradas(_mista([True, True]), 0), cfg, ano)['detalhes_uc'][0]
so_nao = calcular(entradas(_mista([False, False]), 0), cfg, ano)['detalhes_uc'][0]
ok('a mista é exatamente a média das duas puras',
   d1['fatura_sem_uc'], (so_sim['fatura_sem_uc'] + so_nao['fatura_sem_uc']) / 2, 0.02)

secao('17. ICMS da demanda só sobre a utilizada (Súmula 391 do STJ)')
# Contrata 200 kW mas só usa 120: a diferença de 80 kW é paga sem ICMS.
pc17 = 1 - (0.0663 + 0.0144)
ociosa = uc_a4(demanda_kw=200.0, demanda_medida_kw=120.0)
d17 = calcular(entradas(ociosa, 0), cfg, ano)['detalhes_uc'][0]
esperado = (120 * 25.0 / ((1 - 0.19) * pc17)    # utilizada: com ICMS (uc_a4 usa 25,00)
            + 80 * 25.0 / pc17)                 # ociosa: só PIS/COFINS
ok('demanda faturada = a contratada', d17['demanda_fp']['faturada'], 200.0)
ok('ICMS só sobre os 120 kW usados', d17['demanda_rs'], esperado, 0.02)
# se usar tudo o que contratou, não há parcela ociosa
cheio = uc_a4(demanda_kw=200.0, demanda_medida_kw=200.0)
d17b = calcular(entradas(cheio, 0), cfg, ano)['detalhes_uc'][0]
ok('usando tudo, a conta é a cheia com ICMS',
   d17b['demanda_rs'], 200 * 25.0 / ((1 - 0.19) * pc17), 0.02)
ok('e a demanda ociosa sai mais barata que a usada',
   d17['demanda_rs'] < d17b['demanda_rs'], True)

secao('9. Grupo A é só do administrador')
import app as _app
payload = dict(ucs=[dict(tipo='GERADORA', grupo='A', demanda_kw=100,
                         te_fora=0.3, tusd_demanda=25, consumos=[20000] * 12,
                         consumos_ponta=[2000] * 12)],
               qtd_modulos_kit=10, pot_modulo_w=620, valor_kit=10000)
with _app.app.test_request_context('/api/calcular'):
    e_admin = _app._montar_entradas(payload)          # sem sessão = admin local
ok('admin: a UC chega como grupo A', e_admin.ucs[0].grupo, 'A')
with _app.app.test_request_context('/api/calcular'):
    from flask import session
    session['auth'] = True
    session['papel'] = 'consultor'
    _orig, _pac = _app._senha_acesso, _app._aplicar_pacote
    _app._senha_acesso = lambda: 'x'                  # força o modo com login
    _app._aplicar_pacote = lambda d: d                # aqui só interessa a trava
    try:
        e_cons = _app._montar_entradas(payload)
    finally:
        _app._senha_acesso, _app._aplicar_pacote = _orig, _pac
ok('consultor: a UC volta a ser grupo B', e_cons.ucs[0].grupo, 'B')
ok('consultor: a demanda é descartada', e_cons.ucs[0].demanda_kw, 0.0)

secao('18. Cartões da pág. 5: "demanda e taxas" + energia fecham o total')
import json as _json
import os
_d18 = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'exemplos', 'fatura_real_grupo_a.json'),
                       encoding='utf-8'))
_d18.update(qtd_modulos_kit=200, valor_kit=190000, inversores=[
    dict(marca='CHINT', pot_kw=125, tensao=380, qtd=1)])
with _app.app.test_request_context('/'):
    _r18 = calcular(_app._montar_entradas(_d18),
                   dict(carregar_config(), performance_ratio=0.75))
_ga = _r18['grupo_a_partes']
ok('sem: demanda e taxas + energia = conta', _ga['fixo_sem'] + _ga['energia_sem'],
   _r18['fatura_sem'], 1e-6)
ok('com: demanda e taxas + energia = conta', _ga['fixo_com'] + _ga['energia_com'],
   _r18['fatura_com'], 1e-6)
ok('demanda e taxas da FATURA-A (167,47 kW × 25,33 + COSIP + reativo)',
   _ga['fixo_sem'], 5696.79 + 132.37 + 424.24, 0.02)
# 125 kW novos + 135 kW da usina existente passam dos 175 kW contratados:
# a parte fixa COM o sistema = a de hoje + a TUSD-G (que só existe com ele)
ok('parte fixa com o sistema = a de hoje + TUSD-G', _ga['fixo_com'],
   _ga['fixo_sem'] + _r18['detalhes_uc'][0]['custo_g'], 1e-6)
ok('texto do cartão verde', _r18['textos']['ga_reducao'].endswith('% A MENOS NA ENERGIA'), True)
# TUSD-G automática soma os inversores das usinas que a UC JÁ TEM
_u18 = dict(_d18['ucs'][0])
_u18['gds_existentes'] = [dict(g, inversor_kw=135) for g in _u18['gds_existentes']]
_d18b = dict(_d18, ucs=[_u18], qtd_modulos_kit=180, pot_modulo_w=625,
             inversores=[dict(marca='CHINT', pot_kw=75, tensao=380, qtd=1)])
with _app.app.test_request_context('/'):
    _r18b = calcular(_app._montar_entradas(_d18b),
                    dict(carregar_config(), performance_ratio=0.75))
# ALTERADO com autorização do usuário (auditoria de 20/10/2026, correção 2):
# REN 1.000 art. 294 §1º II b desconta a demanda FATURADA (167,47 kW na
# FATURA-A), não a contratada (175) — antes o esperado era 35 kW.
ok('TUSD-G = 75 (novo) + 135 (existente) − 167,47 faturados = 42,53 kW',
   _r18b['detalhes_uc'][0]['demanda_g_kw'], 42.53, 1e-6)
ok('nota *** da usina existente (5.490 kWh/mês injetados)',
   '(5.490 kWh/mês)' in _r18['textos'].get('nota_usina', ''), True)

# ---------------------------------------------------------------------------
secao('19. Fio B de PONTA no crédito GD2 (A4 Verde) — regra do usuário, 20/10/2026')
# A TUSD fora ponta do A4 tem Fio B ZERO; a de PONTA tem 1.018,54 R$/MWh (REH
# 3.592/2026). O crédito GD2 que migra para a ponta devolve a TUSD SEM o Fio B
# escalonado, só com PIS/COFINS — igual ao `abat_tusd` do grupo B:
#   TUSD P abatida = (TUSD P s/ imp. − Fio B escalonado) ÷ (1 − PIS − COFINS)
# Planilha do usuário: ICMS 19 %, COFINS 6,66 %, PIS 1,45 %, Fio B 60 % (2026)
# → TE P 0,638914752 + TUSD P 0,927485036 = 1,566399788 por kWh de ponta.
FIOB_P = 1018.5350622                       # R$/MWh, A4 Verde COPEL (oficial)
_cfg19 = carregar_config()
# a planilha do usuário usa o Fio B arredondado (1.018,54): é ele que reproduz
# os números dela; a diferença para o oficial é R$ 0,000003/kWh
_fb26 = fator_fio_b(_cfg19, 2026) * 1018.54 / 1000.0
_u19 = UC(tipo='GERADORA', grupo='A', subgrupo_a='A4', modalidade_a='VERDE',
          te_ponta=0.47555, tusd_kwh_ponta=1.46339, te_fora=0.29575,
          tusd_kwh_fora=0.14659, icms=0.19, cofins=0.0666, pis=0.0145,
          abat_te_inclui_icms=True)
_pc19 = 1 - (0.0666 + 0.0145)
ok('Fio B de ponta escalonado 2026 (60 %)', _fb26, 0.611124, 1e-6)
ok('TE ponta abatida (com ICMS, convênio valendo)',
   0.47555 / (0.81 * _pc19), 0.638914752, 1e-8)
ok('TUSD ponta abatida = (TUSD − Fio B esc.) ÷ (1 − PIS − COFINS)',
   (1.46339 - _fb26) / _pc19, 0.927485036, 1e-6)
ok('total por kWh de ponta = 1,566400 (planilha do usuário)',
   _u19.abat_posto(True, True, _fb26), 1.566399788, 1e-6)
ok('fora ponta NÃO desconta (Fio B fora ponta = 0)',
   _u19.abat_posto(False, True, _fb26), _u19.abat_posto(False, True), 1e-12)

# na fatura: geração grande o bastante para o crédito chegar à PONTA
def _fat19(gd, ano=2026, **kw):
    u = uc_a4(gd=gd, fio_b_ponta_rs_mwh=FIOB_P, **kw)
    from engine import _fatura_grupo_a
    return _fatura_grupo_a(u, 30000.0, _cfg19, 0.0, ano), u
_g2, _uu = _fat19('GD2')
_g1, _ = _fat19('GD1')
ok('crédito chegou à ponta (sobra do fora ponta)', _g2['compensado_ponta'] > 0, True)
ok('GD1 e GD2 compensam os mesmos kWh', _g1['compensado_ponta'], _g2['compensado_ponta'], 1e-9)
_pc = 1 - (_uu.pis + _uu.cofins)
ok('GD2 paga a mais exatamente ponta compensada × Fio B esc. ÷ PIS/COFINS',
   _g2['total'] - _g1['total'],
   _g2['compensado_ponta'] * fator_fio_b(_cfg19, 2026) * FIOB_P / 1000 / _pc, 0.01)
ok('GD1: abatimento da ponta sem desconto', _g1['abat_ponta'], _uu.abat_posto(True), 1e-12)
ok('conta SEM sistema não muda (GD1 × GD2)', _g2['fatura_sem_uc'], _g1['fatura_sem_uc'], 1e-9)
_g27, _ = _fat19('GD2', 2027)
ok('escalonamento: 2027 desconta 75 % (ano a ano, como o grupo B)',
   _g27['fio_b_ponta'], fator_fio_b(_cfg19, 2027) * FIOB_P / 1000, 1e-12)
_gaz, _ = _fat19('GD2', modalidade_a='AZUL', tusd_demanda_p=60.0, demanda_kw_p=100.0)
ok('modalidade AZUL: sem desconto (ainda não levantada)', _gaz['fio_b_ponta'], 0.0, 1e-12)
# usina antiga GD1 + projeto novo GD2 na mesma UC: só a parte GD2 desconta
_umix = uc_a4(gd='GD2', fio_b_ponta_rs_mwh=FIOB_P,
              gds_existentes=[{'injetado_kwh': 10000, 'gd': 'GD1'}])
from engine import _fatura_grupo_a as _fga
_gmix = _fga(_umix, 20000.0, _cfg19, 0.0, 2026)
_uall = uc_a4(gd='GD2', fio_b_ponta_rs_mwh=FIOB_P,
              gds_existentes=[{'injetado_kwh': 10000, 'gd': 'GD2'}])
_gall = _fga(_uall, 20000.0, _cfg19, 0.0, 2026)
_u1 = uc_a4(gd='GD1', fio_b_ponta_rs_mwh=FIOB_P,
            gds_existentes=[{'injetado_kwh': 10000, 'gd': 'GD1'}])
_gnone = _fga(_u1, 20000.0, _cfg19, 0.0, 2026)
ok('mista (antiga GD1 + nova GD2) fica entre só-GD1 e só-GD2',
   _gnone['total'] < _gmix['total'] <= _gall['total'] + 1e-9, True)
# REN 1.000/2021, art. 655-R §1º II b (REN 1.059/2023): no aumento de
# potência de UC GD I, os descontos são PROPORCIONALIZADOS pela potência
# instalada (CA = inversores) GD I × GD II — nenhuma usina "abate primeiro".
# GD1 existente 135 kW + projeto novo GD2 75 kW → 75/210 = 35,7 % GD2.
_ur = uc_a4(gd='GD2', fio_b_ponta_rs_mwh=FIOB_P, te_ponta=0.47555,
            tusd_kwh_ponta=1.46339, icms=0.19, cofins=0.0666, pis=0.0145,
            gds_existentes=[{'injetado_kwh': 10000, 'gd': 'GD1', 'inversor_kw': 135}])
_gr = _fga(_ur, 20000.0, _cfg19, 75.0, 2026)
_fr = fator_fio_b(_cfg19, 2026) * FIOB_P / 1000.0
ok('fração GD2 pela potência dos inversores (75 ÷ 210)',
   _gr['gd_depois']['frac_gd2'], 75 / 210, 1e-12)
ok('Fio B efetivo na ponta = Fio B escalonado × 75/210',
   _gr['gd_depois']['fio_b_efetivo'], _fr * 75 / 210, 1e-12)
_pcr = 1 - (0.0666 + 0.0145)
ok('kWh de ponta abatido = TE com ICMS + (TUSD − Fio B ef.) ÷ (1 − PIS − COFINS)',
   _gr['abat_ponta'], 0.47555 / (0.81 * _pcr) + (1.46339 - _fr * 75 / 210) / _pcr, 1e-9)
ok('mesmo valor para os dois créditos (mistura única, sem ordem)',
   _gr['gd_depois']['usinas'][0]['ap'], _gr['gd_depois']['usinas'][1]['ap'], 1e-12)
ok('conta SEM: só a usina GD1 → sem desconto',
   _gr['gd_hoje']['frac_gd2'], 0.0, 1e-12)
# sem a potência de alguma usina: proporção pela energia injetada (e avisa)
ok('sem potência informada: proporção pela injeção',
   _gmix['gd_depois']['base_prop'], 'injecao')
# a ordem da lista não muda nada
_uinv = uc_a4(gd='GD1', fio_b_ponta_rs_mwh=FIOB_P,
              gds_existentes=[{'injetado_kwh': 5000, 'gd': 'GD2'},
                              {'injetado_kwh': 17000, 'gd': 'GD1'}])
_uinv2 = uc_a4(gd='GD1', fio_b_ponta_rs_mwh=FIOB_P,
               gds_existentes=[{'injetado_kwh': 17000, 'gd': 'GD1'},
                               {'injetado_kwh': 5000, 'gd': 'GD2'}])
ok('ordem das usinas na lista não muda a conta',
   _fga(_uinv, 0.0, _cfg19, 0.0, 2026)['total'],
   _fga(_uinv2, 0.0, _cfg19, 0.0, 2026)['total'], 1e-6)
# o valor chega pelo cadastro da concessionária (config → app → UC)
import app as _app19
with _app19.app.test_request_context('/'):
    _e19 = _app19._montar_entradas({'ucs': [{'tipo': 'GERADORA', 'grupo': 'A',
        'subgrupo_a': 'A4', 'conc': 'COPEL (PR)', 'consumos': [1000] * 12,
        'gds_existentes': [{'nome': 'antiga', 'injetado_kwh': 100, 'gd': 'GD1'}]}]})
ok('COPEL A4: Fio B de ponta vem do config', _e19.ucs[0].fio_b_ponta_rs_mwh, FIOB_P, 1e-9)
ok('a classe da usina existente chega ao motor', _e19.ucs[0].gds_existentes[0]['gd'], 'GD1')

# ---------------------------------------------------------------------------
secao('20. Autoconsumo do sistema novo informado na tela (padrão 0 % = pior caso)')
_cfg20 = dict(carregar_config(), autoconsumo_grupo_a='pior_caso')
_g0 = _fga(uc_a4(), 15000.0, _cfg20, 0.0, 2026)
ok('vazio: autoconsumo zero (pior caso)', _g0['autoconsumo'], 0.0, 1e-12)
ok('vazio: a regra é o pior caso', _g0['autoconsumo_regra'], 'pior_caso')
_g30 = _fga(uc_a4(autoconsumo_pct=0.30), 15000.0, _cfg20, 0.0, 2026)
ok('30 %: autoconsumo = 30 % da geração', _g30['autoconsumo'], 4500.0, 1e-9)
ok('30 %: injeta o resto', _g30['injetado'], 10500.0, 1e-9)
ok('30 %: regra "informado"', _g30['autoconsumo_regra'], 'informado')
ok('autoconsumo economiza mais que injetar (conta COM menor)',
   _g30['total'] < _g0['total'], True)
ok('conta SEM não muda com o autoconsumo', _g30['fatura_sem_uc'], _g0['fatura_sem_uc'], 1e-9)
_g100 = _fga(uc_a4(autoconsumo_pct=1.0), 30000.0, _cfg20, 0.0, 2026)
ok('100 %: limitado ao consumo fora ponta (20.000)', _g100['autoconsumo'], 20000.0, 1e-9)
_ginf = _fga(uc_a4(autoconsumo_pct=0.0), 15000.0,
             dict(_cfg20, autoconsumo_grupo_a='otimista'), 0.0, 2026)
ok('0 % digitado vale mesmo com a regra "otimista" no config', _ginf['autoconsumo'], 0.0, 1e-12)
with _app19.app.test_request_context('/'):
    _e20 = _app19._montar_entradas({'ucs': [{'tipo': 'GERADORA', 'grupo': 'A',
        'subgrupo_a': 'A4', 'consumos': [1000] * 12, 'autoconsumo_pct': 35}]})
    _e20v = _app19._montar_entradas({'ucs': [{'tipo': 'GERADORA', 'grupo': 'A',
        'subgrupo_a': 'A4', 'consumos': [1000] * 12, 'autoconsumo_pct': ''}]})
ok('tela manda % → motor recebe fração', _e20.ucs[0].autoconsumo_pct, 0.35, 1e-12)
ok('campo vazio → None (regra do config)', _e20v.ucs[0].autoconsumo_pct is None, True)

# ---------------------------------------------------------------------------
secao('21. Várias UCs: usina só na GERADORA (TUSD-G, autoconsumo) — 21/10/2026')
_cfg21 = dict(carregar_config(), autoconsumo_grupo_a='pior_caso', performance_ratio=0.75)
_ua21 = lambda tipo, **k: uc_a4(tipo=tipo, consumos=[8000.0] * 12,
                                consumos_ponta=[800.0] * 12, demanda_kw=60.0,
                                tusd_g_rs_kw=7.66, autoconsumo_pct=0.3, **k)
_r21 = calcular(entradas(_ua21('GERADORA'), 120, pot_inversor_kw=75,
                         ucs=[_ua21('GERADORA'), _ua21('BENEFICIÁRIA')] + [UC() for _ in range(7)]),
                _cfg21, 2026)
_g21, _b21 = _r21['detalhes_uc'][0], _r21['detalhes_uc'][1]
ok('geradora: TUSD-G = 75 kW de inversor − 60 kW faturados', _g21['demanda_g_kw'], 15.0, 1e-9)
ok('beneficiária: sem TUSD-G (a usina não está ligada nela)', _b21['demanda_g_kw'], 0.0, 1e-12)
ok('geradora: autoconsumo de 30 % vale', _g21['autoconsumo'] > 0, True)
ok('beneficiária: autoconsumo zero mesmo com o campo em 30 %', _b21['autoconsumo'], 0.0, 1e-12)
ok('beneficiária: regra "beneficiaria"', _b21['autoconsumo_regra'], 'beneficiaria')
_ger = _r21['geracao_media']
_usada = sum(d['autoconsumo'] + d['compensado_fora'] + d['compensado_ponta'] * d['fator_ajuste']
             for d in (_g21, _b21))
ok('energia usada nas duas UCs ≤ gerada', _usada <= _ger + 2, True)
# TUSD-G que a usina ATUAL já paga entra na conta SEM (não é custo do projeto)
_ux = uc_a4(demanda_kw=60.0, tusd_g_rs_kw=7.66,
            gds_existentes=[{'injetado_kwh': 5000, 'inversor_kw': 100, 'gd': 'GD1'}])
_gx = _fga(_ux, 6000.0, _cfg21, 25.0, 2026)
ok('TUSD-G de hoje = 100 kW atuais − 60 faturados', _gx['demanda_g_hoje_kw'], 40.0, 1e-9)
ok('TUSD-G com o projeto = 125 − 60', _gx['demanda_g_kw'], 65.0, 1e-9)
ok('a TUSD-G de hoje está na conta SEM', _gx['custo_g_hoje'] > 0, True)

print()
if falhas:
    print(f'{VERM}✗ {len(falhas)} verificação(ões) falharam: {falhas}{FIM}')
    sys.exit(1)
print(f'{VERDE}✓ GRUPO A conferido — regras travadas.{FIM}')
