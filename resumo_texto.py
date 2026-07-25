# -*- coding: utf-8 -*-
"""
Resumo dos resultados em texto, para salvar na pasta do cliente.

`resumo_texto(entradas, cfg)` devolve um relatório enxuto com os dados do
cliente, o dimensionamento, a composição do preço e o retorno financeiro.
"""
from __future__ import annotations
from datetime import datetime

from engine import Entradas, calcular, moeda


def resumo_texto(e: Entradas, cfg: dict, ano: int | None = None) -> str:
    r = calcular(e, cfg, ano)
    br = cfg.get('formato_ptbr', True)
    m = lambda v: moeda(v, br)
    t = r['textos']
    L = []
    add = L.append

    add('=' * 60)
    add('RESUMO DA PROPOSTA — S2V ENGENHARIA')
    add('=' * 60)
    add(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    add('')
    logradouro = ', '.join(x for x in (e.endereco, e.numero) if x) or '—'
    ucs_num = ', '.join(str(u.uc_numero) for u in e.ucs
                        if u.ativa and str(u.uc_numero).strip()) or '—'
    add('CLIENTE')
    add(f"  Nome ......... {e.nome or '—'}")
    add(f"  UCs .......... {ucs_num}")
    add(f"  Endereço ..... {logradouro}")
    add(f"  Cidade ....... {e.cidade or '—'}")
    add('')
    add('UNIDADES CONSUMIDORAS')
    for i, u in enumerate(e.ucs):
        if not u.ativa:
            continue
        rotulo = f"UC {i + 1}" + (f" (nº {u.uc_numero})" if u.uc_numero else "")
        add(f"  {rotulo} ({u.tipo} · {u.gd}): consumo médio {u.consumo_medio:.0f} "
            f"kWh/mês, ligação {u.ligacao}, bandeira {u.bandeira}")
        add(f"      TE R$ {u.te:.5f} · TUSD R$ {u.tusd:.5f} (sem impostos) · "
            f"ICMS {u.icms * 100:.1f}% · PIS {u.pis * 100:.2f}% · COFINS {u.cofins * 100:.2f}%")
        add(f"      tarifa cheia (c/ impostos) R$ {u.tarifa_cheia():.5f}/kWh")
    add('')
    add('DIMENSIONAMENTO')
    add(f"  Potência do sistema ...... {r['kwp']:.2f} kWp ({e.qtd_modulos_kit} módulos "
        f"{e.marca_modulo} {int(e.pot_modulo_w)}W)")
    add(f"  Inversor ................. {t.get('inv_desc', '').strip()}")
    add(f"  Estrutura ................ {e.estrutura}")
    add(f"  Geração média estimada ... {r['geracao_media']:.0f} kWh/mês")
    add(f"  Consumo médio total ...... {r['consumo_medio']:.0f} kWh/mês")
    add(f"  Compensação .............. {r['compensacao'] * 100:.0f}%")
    add(f"  Área ocupada ............. {r['area_m2']:.1f} m²")
    if e.tem_stringbox:
        add(f"  String box CC ............ {int(e.sb_qtd or 1)}x "
            f"{e.sb_marca} {e.sb_es}".rstrip())
    if e.tem_bateria:
        add(f"  Bateria de lítio ......... {int(e.bat_qtd or 1)}x "
            f"{e.bat_marca} {e.bat_kwh} kWh".rstrip())
    add('')
    add('COMPOSIÇÃO DO PREÇO')
    add(f"  Kit gerador .............. {m(e.valor_kit)}")
    add(f"  Mão de obra .............. {m(r['custo_mo'])}")
    add(f"  Material extra ........... {m(r['custo_material'])}")
    if r['custo_trafo']:
        add(f"  Transformador ............ {m(r['custo_trafo'])} ({r['trafo_desc']})")
    if e.custo_380v:
        add(f"  Custo 380 V .............. {m(e.custo_380v)}")
    add(f"  Imposto ({r['aliquota_usada'] * 100:.0f}% s/ venda−kit) {m(r['custo_imposto'])}")
    if r['custo_comissao']:
        add(f"  Comissão ................. {m(r['custo_comissao'])}")
    if r['custo_seguro']:
        add(f"  Seguro ................... {m(r['custo_seguro'])}")
    add(f"  Custo total .............. {m(r['custo_total'])}")
    add(f"  Margem usada ............. {r['margem_usada'] * 100:.1f}%")
    add(f"  Preço por Wp ............. R$ {r['preco_wp']:.4f}")
    add(f"  Lucro .................... {r['lucro_pct'] * 100:.1f}% ({m(r['lucro_rs'])})")
    add('')
    add('RETORNO FINANCEIRO')
    add(f"  Fatura SEM solar ......... {m(r['fatura_sem'])}")
    add(f"  Fatura COM solar ......... {m(r['fatura_com'])}")
    add(f"  Economia mensal .......... {m(r['economia_mensal'])}")
    add(f"  Economia anual ........... {m(r['economia_mensal'] * 12)}")
    add(f"  Payback .................. {t['payback_txt']}")
    add(f"  Retorno em 25 anos ....... {m(r['retorno_25'])}")
    add('')
    add('INVESTIMENTO')
    add(f"  VALOR À VISTA ............ {m(r['preco_venda'])}")
    add(f"  Financiamento ............ {t.get('fin_txt', '')}")
    add(f"  Parcela estimada ......... {m(r['parcela_fin'])}")
    add('=' * 60)
    return '\n'.join(L)
