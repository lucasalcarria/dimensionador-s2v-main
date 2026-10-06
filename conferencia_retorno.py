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
        if d.get('grupo') == 'A':          # média tensão: outra fatura
            _bloco_grupo_a(add, m, i, d)
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
    if r.get('economia_pos_isencao') is not None:
        add(f"  isenção de ICMS . acaba em {r['anos_isencao']:.0f} ano(s) "
            f"(prazo do Convênio 16/2015 neste parecer de acesso)")
        add(f"                    economia hoje {m(r['economia_mensal'])}/mês "
            f"→ depois {m(r['economia_pos_isencao'])}/mês")
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


def _bloco_grupo_a(add, m, i: int, d: dict) -> None:
    """Detalhamento de uma UC do GRUPO A (média tensão).

    A leitura importante para o cliente: a DEMANDA é paga igual com ou sem
    sistema (o solar não abate kW), então a economia vem só da ENERGIA — e a
    energia da ponta ainda custa mais crédito por causa do fator de ajuste.
    """
    add(f"UC {i + 1} — {d['tipo']} · GRUPO A {d['subgrupo']} {d['modalidade']}")
    add(f"  consumo fora ponta ............. {d['consumo_fora']:.1f} kWh/mês")
    add(f"  consumo na ponta ............... {d['consumo_ponta']:.1f} kWh/mês")
    add(f"  rateio da geração .............. {d['rateio'] * 100:.1f} %  "
        f"→ geração rateada = {d['geracao_rateada']:.1f} kWh")
    if d['injecao_existente']:
        add(f"  já injetado por usina existente . {d['injecao_existente']:.0f} kWh  "
            f"→ isto já abate a conta de HOJE")
    add(f"  autoconsumo (não é medido) ..... {d['autoconsumo']:.0f} kWh  "
        f"→ evita a tarifa CHEIA, com ICMS")
    add(f"  injetado (vira crédito) ........ {d['injetado']:.0f} kWh")
    add(f"  consumo fora ponta ainda medido  {d['consumo_fora_medido']:.1f} kWh")
    add(f"  tarifa cheia fora ponta ........ R$ {d['tarifa_fora']:.5f}/kWh")
    add(f"  tarifa cheia na ponta .......... R$ {d['tarifa_ponta']:.5f}/kWh")
    add(f"  fator de correção da ponta ..... {d['fator_ajuste']:.3f}  "
        f"(1 kWh de ponta = {d['fator_ajuste']:.2f} kWh fora ponta"
        f"{' — informado' if d['fator_manual'] else ' — relação das TEs'})")
    add(f"    pela tarifa cheia daria ...... {d['fator_cheia']:.3f}")
    add(f"  compensado fora ponta .......... {d['compensado_fora']:.0f} kWh")
    add(f"  compensado na ponta ............ {d['compensado_ponta']:.0f} kWh")
    add(f"  abatimento fora ponta .......... R$ {d['abat_fora']:.5f}/kWh")
    add(f"  abatimento na ponta ............ R$ {d['abat_ponta']:.5f}/kWh")
    add(f"  (no grupo A NÃO há Fio B: o fio é pago na demanda, então o kWh "
        f"compensado abate TE + TUSD inteiras)")
    if d['abat_fora'] and d['tarifa_fora']:
        perda = (1 - d['abat_fora'] / d['tarifa_fora']) * 100
        add(f"  o crédito vale {100 - perda:.0f} % da tarifa cheia "
            f"(perde {perda:.0f} % — o ICMS da TE não volta)"
            if not d['abat_fora'] >= d['tarifa_fora'] else
            f"  o crédito vale 100 % da tarifa cheia")
    for rot, det in (('fora ponta/única', d['demanda_fp']), ('ponta', d['demanda_p'])):
        if det:
            add(f"  demanda {rot} ......... contratada {det['contratada']:.2f} kW, "
                f"medida {det['medida']:.2f} kW, faturada {det['faturada']:.2f} kW "
                f"× R$ {det['tarifa']:.2f}/kW = {m(det['valor'])}")
            if det['ultrapassagem']:
                add(f"    ultrapassagem (acima de 105 % da contratada) {m(det['ultrapassagem'])}")
    add(f"  DEMANDA total (não abatida) .... {m(d['demanda_rs'])}")
    if d['demanda_g_kw'] or d['custo_g']:
        add(f"  TUSD-G (demanda de geração) .... {d['demanda_g_kw']:.2f} kW × "
            f"R$ {d['tusd_g_cheia']:.2f}/kW = {m(d['custo_g'])}  "
            f"(tarifa R$ {d['tusd_g_rs_kw']:.2f} sem impostos; "
            f"custo que só existe COM o sistema)")
    rot = ('energia HOJE (c/ usina atual)' if d['injecao_existente']
           else 'energia sem o sistema')
    add(f"  {rot:<30} {m(d['consumo_sem_rs'])}")
    add(f"  energia com o novo sistema ..... {m(d['consumo_com_rs'])}")
    if d['bandeira'] != 'VERDE':
        add(f"  adicional bandeira ({d['bandeira']}) .. {m(d['extra_bandeira'])}")
    if d['ilum_publica']:
        add(f"  iluminação pública ............. {m(d['ilum_publica'])}")
    if d['outros_rs']:
        add(f"  outros itens fixos (reativo…) .. {m(d['outros_rs'])}  "
            f"(iguais com e sem sistema)")
    add(f"  piso da conta (demanda + fixos)  {m(d['piso'])}")
    add(f"  → fatura SEM solar desta UC .... {m(d['fatura_sem_uc'])}")
    add(f"  → fatura COM solar desta UC .... {m(d['total'])}")
    add('')


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
