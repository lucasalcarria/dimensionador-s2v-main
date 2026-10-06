# -*- coding: utf-8 -*-
"""Confere contra a ANEEL tudo o que o programa guarda de tarifa.

Dois conjuntos de dados da ANEEL Dados Abertos:
  * "Tarifas de aplicação"  -> TE e TUSD (o que o programa busca em uso normal)
  * "Componentes Tarifárias" -> a DECOMPOSIÇÃO: Fio B, TUSD-G etc.

Precisa de internet. NÃO entra nas suítes (`teste_planilha`, `teste_correcoes`,
`teste_grupo_a`), que rodam offline — este é um conferidor manual, para rodar a
cada revisão tarifária (a da COPEL vira todo 24 de junho).

    py ferramentas/conferir_aneel.py
"""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import engine                                                   # noqa: E402
import online                                                   # noqa: E402

VERDE = '\033[92m'; VERM = '\033[91m'; FIM = '\033[0m'

# Componentes Tarifárias — um recurso por ano
RID_COMPONENTES = 'e8717aa8-2521-453f-bf16-fbb9a16eea39'         # 2026
CNPJ_COPEL = '04368898000106'

# o que cada fatura validada mostra, para o confronto
CASOS = [
    ('FATURA-A — A4 Verde (fatura 09/2026)', 'A', ('COPEL-DIS', 'A4', 'VERDE'), {
        'te_ponta': 0.47555, 'tusd_kwh_ponta': 1.46339,
        'te_fora': 0.29575, 'tusd_kwh_fora': 0.14659,
        'tusd_demanda': 25.33}),
    ('FATURA-B — B1 Residencial (fatura 09/2026)', 'B', ('COPEL-DIS', 'B1'), {
        'te': 0.31085, 'tusd': 0.45717}),
]

falhas = 0


def _num(v) -> float:
    """'214,5356' -> 214.5356"""
    try:
        return float(str(v).strip().replace('.', '').replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0


def componente(**filtros) -> float | None:
    """Um valor da base Componentes Tarifárias, ou None se não achar."""
    p = urllib.parse.urlencode({'resource_id': RID_COMPONENTES,
                                'filters': json.dumps(filtros, ensure_ascii=False),
                                'limit': 5})
    try:
        recs = online._get_json('https://dadosabertos.aneel.gov.br/api/3/action/'
                                'datastore_search?' + p)['result']['records']
    except Exception:                                           # noqa: BLE001
        return None
    return _num(recs[0]['VlrComponenteTarifario']) if recs else None


def confere(rotulo, obtido, esperado, tol, unidade=''):
    global falhas
    if obtido is None:
        print(f'  {VERM}não achei{FIM} {rotulo}')
        falhas += 1
        return
    bate = abs(obtido - esperado) <= tol
    if not bate:
        falhas += 1
    cor = VERDE if bate else VERM
    print(f'  {cor}{"OK " if bate else "DIVERGE"}{FIM} {rotulo:<34} '
          f'ANEEL {obtido:<14.5f} nosso {esperado} {unidade}')


def main() -> int:
    # ---- 1. TE/TUSD contra as faturas validadas ----
    for rotulo, tipo, args, papel in CASOS:
        print(f'\n=== {rotulo} ===')
        try:
            r = (online.buscar_tarifa_aneel_a(*args) if tipo == 'A'
                 else online.buscar_tarifa_aneel(*args))
        except Exception as exc:                                # noqa: BLE001
            print(f'  {VERM}não consegui buscar:{FIM} {exc}')
            globals()['falhas'] += 1
            continue
        print(f"  vigência {r.get('vigencia','?')} · {str(r.get('reh',''))[:48]}")
        for campo, impresso in papel.items():
            confere(campo, r.get(campo), impresso, 0.002)

    # ---- 2. Fio B e TUSD-G contra o config ----
    cfg = engine.carregar_config()
    print('\n=== componentes tarifários (decomposição) ===')
    base = dict(NumCPFCNPJ=CNPJ_COPEL, DscBaseTarifaria='Tarifa de Aplicação',
                DatInicioVigencia='2026-06-24')
    confere('Fio B B1 (config.fio_b_rs_mwh)',
            componente(**base, DscSubGrupoTarifario='B1',
                       DscDetalheConsumidor='Não se aplica',
                       DscPostoTarifario='Não se aplica',
                       DscComponenteTarifario='TUSD_FioB'),
            float(cfg['fio_b_rs_mwh']), 0.01, 'R$/MWh')
    confere('TUSD-G A4 (config.tusd_g_rs_kw)',
            componente(**base, DscSubGrupoTarifario='A4',
                       DscModalidadeTarifaria='Geração',
                       DscComponenteTarifario='TUSD'),
            float(cfg['tusd_g_rs_kw']), 0.01, 'R$/kW')
    # Fio B de CADA concessionária cadastrada (vigência mais recente de cada uma)
    print()
    print('=== Fio B por concessionária (B1, mais recente) ===')
    for nome, v in (cfg.get('concessionarias') or {}).items():
        if not isinstance(v, dict) or not v.get('fio_b_rs_mwh'):
            continue
        filtros = dict(SigNomeAgente=v['aneel_sigla'],
                       DscBaseTarifaria='Tarifa de Aplicação',
                       DscSubGrupoTarifario='B1', DscModalidadeTarifaria='Convencional',
                       DscDetalheConsumidor='Não se aplica',
                       DscPostoTarifario='Não se aplica',
                       DscComponenteTarifario='TUSD_FioB')
        p = urllib.parse.urlencode({'resource_id': RID_COMPONENTES,
                                    'filters': json.dumps(filtros, ensure_ascii=False),
                                    'sort': 'DatInicioVigencia desc', 'limit': 1})
        try:
            r = online._get_json('https://dadosabertos.aneel.gov.br/api/3/action/'
                                 'datastore_search?' + p)['result']['records']
            atual = _num(r[0]['VlrComponenteTarifario']) if r else None
        except Exception:                                       # noqa: BLE001
            atual = None
        confere(f'{nome}', atual, float(v['fio_b_rs_mwh']), 0.01, 'R$/MWh')

    # a razão de o crédito solar não sofrer Fio B no grupo A
    fb_fp = componente(**base, DscSubGrupoTarifario='A4',
                       DscModalidadeTarifaria='Verde', DscUnidade='R$/MWh',
                       DscPostoTarifario='Fora ponta',
                       DscDetalheConsumidor='Não se aplica',
                       DscComponenteTarifario='TUSD_FioB')
    confere('Fio B A4 FORA PONTA (tem de ser 0)', fb_fp, 0.0, 0.001, 'R$/MWh')

    print()
    if falhas:
        print(f'{VERM}✗ {falhas} divergência(s).{FIM} Se houve revisão tarifária, '
              f'atualize o config (e os casos daqui); se mudou o FORMATO da base, '
              f'conserte online.buscar_tarifa_aneel_a.')
        return 1
    print(f'{VERDE}✓ tudo bate com a ANEEL e com as faturas validadas.{FIM}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
