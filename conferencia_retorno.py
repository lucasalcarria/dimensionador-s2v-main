# -*- coding: utf-8 -*-
"""
Conferência do retorno financeiro — mostra, passo a passo, todas as contas que
entram na fatura sem solar, na fatura com solar e na projeção de 25 anos.

Uso:
    py -3 conferencia_retorno.py            # roda o exemplo do enunciado
    (ou importe `relatorio_conferencia(entradas, cfg)` para gerar o texto)

A lógica de rateio da geração e do % noturno segue a planilha:
  * a geração mensal é rateada entre as UCs na proporção do consumo de cada uma;
  * "maior" = max(consumo da UC, geração rateada da UC);
  * faturado = TRUNC(maior × %noturno):
      - GERADORA usa o %noturno informado (ex.: 0,65);
      - BENEFICIÁRIA usa sempre 1,0 (100 %).
"""
from __future__ import annotations

from engine import Entradas, UC, calcular, carregar_config, moeda, fator_fio_b


def relatorio_conferencia(e: Entradas, cfg: dict, ano: int | None = None) -> str:
    r = calcular(e, cfg, ano)
    br = cfg.get('formato_ptbr', True)
    m = lambda v: moeda(v, br)
    L = []
    add = L.append

    add('=' * 72)
    add('CONFERÊNCIA DO RETORNO FINANCEIRO')
    add('=' * 72)
    add(f"Consumo total médio ...... {r['consumo_medio']:.1f} kWh/mês "
        f"({r['consumo_anual']:.0f} kWh/ano)")
    add(f"Geração média estimada ... {r['geracao_media']:.1f} kWh/mês "
        f"({r['geracao_anual']:.0f} kWh/ano)")
    add(f"Compensação .............. {r['compensacao'] * 100:.1f} %  "
        f"({'sobredimensionado' if r['compensacao'] > 1 else 'atende parcialmente'})")
    fio_b = fator_fio_b(cfg, ano) * cfg['fio_b_rs_mwh'] / 1000.0
    add(f"Fio B no ano ............. R$ {fio_b:.5f}/kWh "
        f"({fator_fio_b(cfg, ano) * 100:.0f}% de R$ {cfg['fio_b_rs_mwh']:.2f}/MWh)")
    add('')

    add('-' * 72)
    add('POR UNIDADE CONSUMIDORA')
    add('-' * 72)
    for i, d in enumerate(r['detalhes_uc']):
        if not d:
            continue
        add(f"UC {i + 1} — {d['tipo']}")
        add(f"  consumo médio .................. {d['consumo']:.1f} kWh/mês")
        add(f"  rateio da geração .............. {d['rateio'] * 100:.1f} %  "
            f"→ geração rateada = {d['geracao_rateada']:.1f} kWh")
        add(f"  maior(consumo, geração) ........ {d['maior']:.1f} kWh")
        add(f"  % noturno aplicado ............. {d['pct_noturno'] * 100:.0f} %  "
            f"{'(beneficiária = 100%)' if d['tipo'] == 'BENEFICIÁRIA' else '(geradora = valor informado)'}")
        add(f"  faturado = TRUNC(maior × %not) . {d['faturado']:.0f} kWh")
        add(f"  disponibilidade (custo mínimo) . {d['disponibilidade']:.0f} kWh")
        add(f"  compensado = faturado − disp ... {d['compensado']:.0f} kWh")
        add(f"  tarifa cheia (com impostos) .... R$ {d['tarifa']:.5f}/kWh")
        add(f"  abatimento TE .................. R$ {d['abat_te']:.5f}/kWh")
        add(f"  abatimento TUSD (líq. Fio B) ... R$ {d['abat_tusd']:.5f}/kWh")
        add(f"  piso = disp × tarifa ........... {m(d['piso'])}")
        add(f"  líquido = fat×tarifa − comp×(abatTE+abatTUSD) = {m(d['liquido'])}")
        add(f"  taxa mínima = max(piso, líquido) {m(d['taxa_min'])}")
        if d['bandeira'] != 'VERDE':
            add(f"  adicional bandeira ({d['bandeira']}) .. {m(d['extra_bandeira'])}")
        if d['ilum_publica']:
            add(f"  iluminação pública ............. {m(d['ilum_publica'])}")
        add(f"  → fatura SEM solar desta UC .... {m(d['fatura_sem_uc'])}")
        add(f"  → fatura COM solar desta UC .... {m(d['total'])}")
        add('')

    add('-' * 72)
    add('TOTAIS MENSAIS')
    add('-' * 72)
    add(f"  Fatura SEM solar ............... {m(r['fatura_sem'])}")
    add(f"  Fatura COM solar .............. {m(r['fatura_com'])}")
    add(f"  Economia mensal ............... {m(r['economia_mensal'])}")
    add(f"  Economia anual ................ {m(r['economia_mensal'] * 12)}")
    add('')

    add('-' * 72)
    add('PROJEÇÃO DE 25 ANOS')
    add('-' * 72)
    modo = ('planilha original' if cfg.get('compat_planilha')
            else 'estimativa realista')
    add(f"  modo ............ {modo}")
    add(f"  reajuste tarifa . {cfg['reajuste_tarifa_aa'] * 100:.1f} % ao ano")
    add(f"  degradação ...... −{cfg['degradacao_ano1'] * 100:.1f}% no 2º ano, "
        f"depois −{cfg['degradacao_demais'] * 100:.1f}%/ano")
    serie = r['retorno_serie']
    add('')
    add('  ano   economia no ano')
    for i in [0, 1, 2, 4, 9, 14, 24]:
        add(f'   {i + 1:>2}    {m(serie[i])}')
    add(f"  ─────────────────────────")
    add(f"  TOTAL 25 anos ... {m(r['retorno_25'])}")
    add('')

    add('-' * 72)
    add('INVESTIMENTO')
    add('-' * 72)
    add(f"  Valor de venda ................ {m(r['preco_venda'])}")
    add(f"  Payback ....................... {r['textos']['payback_txt']}")
    add(f"  Parcela financiada ............ {m(r['parcela_fin'])}")
    add('=' * 72)
    return '\n'.join(L)


def _exemplo_enunciado(cfg):
    """Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),
    geração ~1424 kWh/mês (16 módulos sobredimensionados)."""
    perfil = cfg['perfis_irradiacao']['3.8']
    from engine import DIAS_MES
    media = sum(perfil[m] / 1000 * DIAS_MES[m] for m in range(12)) / 12
    pot_mod = round((1424 / (cfg['performance_ratio'] * media)) * 1000 / 16, 1)
    ucA = UC(tipo='GERADORA', ligacao='BIFASICO', consumos=[600] * 12,
             pct_noturno=0.65)
    ucB = UC(tipo='BENEFICIÁRIA', ligacao='BIFASICO', consumos=[400] * 12,
             pct_noturno=0.65)
    return Entradas(
        nome='Exemplo A600 geradora + B400 beneficiária',
        ucs=[ucA, ucB] + [UC() for _ in range(7)],
        qtd_modulos_kit=16, marca_inversor='CHINT', pot_inversor_kw=10,
        tensao_inversor=220, valor_kit=20000, marca_modulo='GENÉRICO',
        pot_modulo_w=pot_mod, estrutura='FIBROCIMENTO',
        perfil_irradiacao='3.8', margem_desejada=0.16)


if __name__ == '__main__':
    cfg = carregar_config()
    e = _exemplo_enunciado(cfg)
    print(relatorio_conferencia(e, cfg))
