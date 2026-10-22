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
        if 0 < d.get('frac_gd2', 1) < 1:
            add(f"    GD1 + GD2 na UC (REN 655-R): parcela GD2 {d['frac_gd2'] * 100:.1f} % "
                f"→ Fio B efetivo R$ {d['fio_b_efetivo']:.5f}/kWh")
        add(f"  piso = disp × tarifa ........... {m(d['piso'])}")
        add(f"  líquido = fat×tarifa − comp×(abatTE+abatTUSD) = {m(d['liquido'])}")
        add(f"  taxa mínima = max(piso, líquido) {m(d['taxa_min'])}")
        if d['bandeira'] != 'VERDE':
            add(f"  adicional bandeira ({d['bandeira']}) .. {m(d['extra_bandeira'])}")
        if d['ilum_publica']:
            add(f"  iluminação pública ............. {m(d['ilum_publica'])}")
        if d.get('band_sem'):
            add(f"  bandeira na conta SEM .......... {m(d['band_sem'])}  (REN art. 307)")
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
    if not cfg.get('compat_planilha'):
        esc = cfg['fio_b_escalonamento']
        add("  Fio B do GD2 .... sobe ano a ano (Lei 14.300): "
            + ' · '.join(f"{k} {v * 100:.0f}%" for k, v in sorted(esc.items())
                         if int(k) >= (ano or __import__('engine').hoje().year)))
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
    """Detalhamento de uma UC do GRUPO A (média tensão), em SEÇÕES — cada uma
    responde uma pergunta, e as duas situações (HOJE, só com as usinas que já
    existem, e COM o sistema novo) ficam lado a lado para comparar.

    A leitura importante para o cliente: a DEMANDA é paga igual com ou sem
    sistema (o solar não abate kW), então a economia vem só da ENERGIA — e a
    energia da ponta ainda custa mais crédito por causa do fator de correção.
    """
    t = d.get('tar_sem') or {}
    hoje, dep = d.get('gd_hoje') or {}, d.get('gd_depois') or {}
    pc = 1 - (t.get('pis', 0) + t.get('cofins', 0))
    ic = t.get('icms', 0)
    kwh = lambda v: f"{v:,.0f}".replace(',', '.') + ' kWh'
    rs5 = lambda v: f"R$ {v:.6f}".replace('.', ',')
    pct = lambda v: f"{v * 100:.1f} %".replace('.', ',')
    col = lambda rot, a, b: add(f"     {rot:<34}{a:>17}{b:>17}")
    br = lambda v, n=5: f"{v:.{n}f}".replace('.', ',')     # número pt-BR

    def tit(n, texto):
        add('')
        add(f"  {n}. {texto}")
        add('  ' + '·' * 68)

    add('═' * 72)
    add(f"UC {i + 1} — {d['tipo']} · GRUPO A {d['subgrupo']} {d['modalidade']}")
    add('═' * 72)

    # 1 ------------------------------------------------------------ consumo
    tit(1, 'CONSUMO DA FATURA (kWh/mês)')
    add(f"     fora ponta ........ {kwh(d['consumo_fora'])}")
    add(f"     ponta ............. {kwh(d['consumo_ponta'])}")
    add(f"     geração do projeto novo nesta UC: {kwh(d['geracao_rateada'])} "
        f"({pct(d['rateio'])} da geração)")
    reg = {'beneficiaria': 'beneficiária: a usina não fica aqui, tudo chega como crédito',
           'informado': 'informado na tela', 'pior_caso': 'pior caso — padrão',
           'medido': 'medido na usina atual', 'otimista': 'otimista'}.get(
               d['autoconsumo_regra'], d['autoconsumo_regra'])
    add(f"     autoconsumo do novo: {pct(d.get('autoconsumo_pct', 0))} = "
        f"{kwh(d['autoconsumo'])} ({reg})")
    add(f"       → some da conta pela tarifa CHEIA; o resto, {kwh(d['injetado'])}, é injetado")

    # 2 ------------------------------------------------------------ tarifas
    tit(2, 'TARIFAS POR kWh (R$)')
    add(f"     {'posto':<12}{'TE s/ imp.':>12}{'TUSD s/ imp.':>14}{'cheia c/ imp.':>15}")
    add(f"     {'fora ponta':<12}{br(t.get('te_f', 0)):>12}{br(t.get('tusd_f', 0)):>14}"
        f"{br(d['tarifa_fora']):>15}")
    add(f"     {'ponta':<12}{br(t.get('te_p', 0)):>12}{br(t.get('tusd_p', 0)):>14}"
        f"{br(d['tarifa_ponta']):>15}")
    p2 = lambda v: br(v * 100, 2) + ' %'
    add(f"     ICMS {p2(ic)} · PIS {p2(t.get('pis', 0))} · COFINS {p2(t.get('cofins', 0))}")
    add(f"     fator de correção da ponta: {br(d['fator_ajuste'], 4)} "
        f"({'informado' if d['fator_manual'] else 'TE ponta ÷ TE fora ponta'})")
    add(f"       pela tarifa cheia daria {br(d['fator_cheia'], 3)} — não é o que a REN manda")
    add(f"       → 1 kWh de ponta consome {br(d['fator_ajuste'], 4)} kWh de crédito")

    # 3 ------------------------------------------------- usinas e classes
    us = dep.get('usinas') or hoje.get('usinas') or []
    if us:
        tit(3, 'USINAS E CLASSES (REN 1.000/2021, art. 655-R)')
        add(f"     {'usina':<20}{'classe':>7}{'potência CA':>14}{'injeta/mês':>13}{'ICMS do crédito':>17}")
        for x in us:
            potxt = (f"{br(x['pot_kw'], 1)} kW" if x['pot_kw'] else '—')
            if x['pot_fonte'] == 'kWp':
                potxt += '*'
            add(f"     {x['nome'][:20]:<20}{'GD2' if x['gd2'] else 'GD1':>7}{potxt:>14}"
                f"{kwh(x['kwh']):>13}{'isento' if x['isento'] else 'paga ICMS':>17}")
        if any(x['pot_fonte'] == 'kWp' for x in us):
            add("     * sem o inversor informado: usado o kWp da usina")
        for nome, c in (('HOJE (só as atuais)', hoje), ('COM o sistema novo', dep)):
            if not c.get('usinas'):
                continue
            base = ('pela potência dos inversores' if c['base_prop'] == 'potencia'
                    else '⚠ pela ENERGIA INJETADA (falta potência de usina)')
            add(f"     parcela GD2 {nome:<24} {pct(c['frac_gd2']):>7}  {base}")
        if d.get('fio_b_ponta') or t.get('fio_b_cheio'):
            fb = t.get('fio_b_cheio', 0) / 1000
            add(f"     Fio B de ponta: {rs5(fb)} cheio × {t.get('fator_ano', 0) * 100:.0f} % "
                f"(Lei 14.300) = {rs5(d.get('fio_b_ponta', 0))}")
            for nome, c in (('hoje', hoje), ('com o sistema', dep)):
                if c.get('usinas'):
                    add(f"       × parcela GD2 {nome:<14} = {rs5(c['fio_b_efetivo'])} "
                        f"descontado por kWh de ponta")
            add("     A UC tem um medidor só: nenhuma usina \"abate primeiro\" — todo kWh")
            add("     compensado leva a mistura GD1/GD2 na proporção da potência.")
        elif t.get('azul'):
            add("     modalidade AZUL: Fio B de ponta não levantado — sem desconto")

    # 4 ----------------------------------------------- uso do crédito (kWh)
    tit(4, 'COMO O CRÉDITO FOI USADO (kWh/mês)')
    col('', 'HOJE', 'COM O SISTEMA')
    col('crédito disponível (injetado)', kwh(hoje.get('credito_total_kwh', 0)),
        kwh(dep.get('credito_total_kwh', 0)))
    col('fora ponta a abater', kwh(hoje.get('cf_fat', d['consumo_fora'])),
        kwh(dep.get('cf_fat', 0)))
    col('→ abatido no fora ponta', kwh(hoje.get('comp_f', 0)), kwh(dep.get('comp_f', 0)))
    col('→ crédito levado à ponta', kwh(hoje.get('credito_ponta_kwh', 0)),
        kwh(dep.get('credito_ponta_kwh', 0)))
    col(f'   ÷ {br(d["fator_ajuste"], 4)} = ponta abatida', kwh(hoje.get('comp_p', 0)),
        kwh(dep.get('comp_p', 0)))
    col('→ crédito sem uso no mês', kwh(hoje.get('sobra_kwh', 0)), kwh(dep.get('sobra_kwh', 0)))
    add("     ordem (REN 1.000, art. 655 § 3º e § 5º): primeiro o fora ponta,")
    add("     depois a sobra vai à ponta corrigida pela relação das TEs.")

    # 5 ---------------------------------------- quanto volta por kWh (R$)
    tit(5, 'QUANTO VOLTA POR kWh COMPENSADO (com o sistema)')
    x = (dep.get('usinas') or [None])[0]
    if t and x is not None:
        fr = dep.get('frac_gd2', 0)
        fb = d.get('fio_b_ponta', 0)                  # Fio B escalonado (cheio × %)
        uf = t['tusd_f'] / pc                         # TUSD fora ponta: sem Fio B
        u1 = t['tusd_p'] / pc                         # TUSD ponta, regra GD1
        u2 = (t['tusd_p'] - fb) / pc                  # TUSD ponta, regra GD2
        isos = sorted({u['isento'] for u in dep['usinas']}, reverse=True)
        grupos = []
        for iso in isos:
            nomes = ', '.join(u['nome'] for u in dep['usinas'] if u['isento'] == iso)
            te_div = (1 - ic) * pc if iso else pc
            te_txt = f"÷ ({br(1 - ic, 2)} × {br(pc, 4)})" if iso else f"÷ {br(pc, 4)}"
            grupos.append(dict(iso=iso, nomes=nomes, te_txt=te_txt,
                               tf=t['te_f'] / te_div, tp=t['te_p'] / te_div))
        classes = ([('GD1', u1)] if fr < 1 else []) + ([('GD2', u2)] if fr > 0 else [])

        # a) cada classe SOZINHA — é o valor "de tabela" de um kWh de ponta
        add("     a) PONTA — valor de 1 kWh abatido em cada classe, sozinha")
        for g in grupos:
            rot = 'crédito com isenção de ICMS' if g['iso'] else 'crédito sem isenção de ICMS'
            add(f"        {rot} ({g['nomes']}):")
            add(f"          TE   {br(t['te_p'])} {g['te_txt']} = {br(g['tp'], 6)}")
            for cl, uu in classes:
                if cl == 'GD1':
                    add(f"          GD1  TUSD {br(t['tusd_p'])} ÷ {br(pc, 4)} = {br(uu, 6)}  (sem Fio B)")
                else:
                    add(f"          GD2  TUSD ({br(t['tusd_p'])} − Fio B {br(fb, 6)}) ÷ {br(pc, 4)} = {br(uu, 6)}")
                add(f"               TE + TUSD = {br(g['tp'], 6)} + {br(uu, 6)} = {br(g['tp'] + uu, 6)}"
                    f"  ← 1 kWh de ponta {cl}")
        # b) a mistura da REN 655-R
        if 0 < fr < 1:
            add(f"     b) PONTA — mistura pela potência dos inversores (REN 1.000, art. 655-R)")
            add(f"        GD1 {pct(1 - fr)} · GD2 {pct(fr)} — a COPEL mede tudo junto e aplica")
            add("        a proporção a TODO kWh: nenhuma usina paga ou deixa de pagar sozinha.")
            for g in grupos:
                v1, v2 = g['tp'] + u1, g['tp'] + u2
                mix = (1 - fr) * v1 + fr * v2
                g['vp'] = mix
                add(f"        {'com' if g['iso'] else 'sem'} isenção: {pct(1 - fr)} × {br(v1, 6)}"
                    f" + {pct(fr)} × {br(v2, 6)} = {br(mix, 6)}")
            # c) o Fio B que ficou na mistura
            add("     c) Fio B efetivo — quanto da mistura é Fio B")
            add(f"        {br(fb, 6)} (Fio B escalonado) × {pct(fr)} = "
                f"{br(fb * fr, 6)} por kWh sem impostos")
            add(f"        ÷ {br(pc, 4)} (PIS/COFINS) = {br(fb * fr / pc, 6)} a menos que o GD1 puro")
        else:
            for g in grupos:
                g['vp'] = g['tp'] + (u2 if fr >= 1 else u1)
        # d) fora ponta
        add(f"     {'d' if 0 < fr < 1 else 'b'}) FORA PONTA — Fio B zero: GD1 e GD2 valem igual")
        for g in grupos:
            add(f"        {'com' if g['iso'] else 'sem'} isenção: TE {br(t['te_f'])} {g['te_txt']}"
                f" = {br(g['tf'], 6)}")
            add(f"          + TUSD {br(t['tusd_f'])} ÷ {br(pc, 4)} = {br(uf, 6)} → {br(g['tf'] + uf, 6)}")
        # resumo
        add(f"     {'e' if 0 < fr < 1 else 'c'}) RESUMO — o que volta por kWh compensado")
        add(f"        {'crédito (ICMS do parecer)':<34}{'fora ponta':>12}{'ponta':>12}")
        for g in grupos:
            rot = ('com isenção' if g['iso'] else 'sem isenção') + f" ({g['nomes']})"
            add(f"        {rot[:34]:<34}{br(g['tf'] + uf, 6):>12}{br(g['vp'], 6):>12}")
        add(f"        {'tarifa cheia (referência)':<34}{br(d['tarifa_fora'], 6):>12}"
            f"{br(d['tarifa_ponta'], 6):>12}")
        add("        (a TUSD abatida nunca devolve o ICMS na COPEL; o PIS/COFINS sempre volta)")
    col('', 'HOJE', 'COM O SISTEMA')
    col('R$ devolvidos no fora ponta', m(hoje.get('cred_f_rs', 0)), m(dep.get('cred_f_rs', 0)))
    col('R$ devolvidos na ponta', m(hoje.get('cred_p_rs', 0)), m(dep.get('cred_p_rs', 0)))

    # 6 ---------------------------------------------- demanda e fixos
    tit(6, 'DEMANDA E ITENS FIXOS (o solar não abate)')
    for rot, det in (('fora ponta/única', d['demanda_fp']), ('ponta', d['demanda_p'])):
        if det:
            add(f"     demanda {rot}: contratada {br(det['contratada'], 2)} kW · "
                f"medida {br(det['medida'], 2)} kW")
            add(f"       faturada {br(det['faturada'], 2)} kW × R$ {br(det['tarifa'], 2)}/kW "
                f"sem impostos → {m(det['valor'])} com impostos")
            if det['ultrapassagem']:
                add(f"       ultrapassagem (acima de 105 % da contratada): {m(det['ultrapassagem'])}")
    if d['demanda_g_kw'] or d['custo_g']:
        add(f"     TUSD-G (só COM o sistema): {br(d['demanda_g_kw'], 2)} kW × "
            f"R$ {br(d['tusd_g_cheia'], 2)}/kW = {m(d['custo_g'])}")
        add(f"       (tarifa R$ {br(d['tusd_g_rs_kw'], 2)}/kW sem impostos; inversores "
            f"ligados nesta UC − demanda faturada {br(d.get('demanda_usada_kw', 0), 2)} kW)")
        if d.get('custo_g_hoje'):
            add(f"       HOJE já paga {br(d['demanda_g_hoje_kw'], 2)} kW pelas usinas atuais "
                f"= {m(d['custo_g_hoje'])} (está na conta SEM também)")

    # 7 ---------------------------------------------------- resultado
    tit(7, 'RESULTADO DA FATURA (R$/mês)')
    col('', 'SEM S2V', 'COM S2V')
    col('demanda', m(d['demanda_rs']), m(d['demanda_rs']))
    col('energia (medida − crédito)', m(d['consumo_sem_rs']), m(d['consumo_com_rs']))
    if d['bandeira'] != 'VERDE':
        col(f"bandeira {d['bandeira']}", m(d.get('band_sem_rs', 0)), m(d['extra_bandeira']))
    if d['custo_g'] or d.get('custo_g_hoje'):
        col('TUSD-G', m(d.get('custo_g_hoje', 0)), m(d['custo_g']))
    if d['ilum_publica']:
        col('iluminação pública', m(d['ilum_publica']), m(d['ilum_publica']))
    if d['outros_rs']:
        col('outros fixos (reativo…)', m(d['outros_rs']), m(d['outros_rs']))
    add('     ' + '─' * 68)
    col('TOTAL DESTA UC', m(d['fatura_sem_uc']), m(d['total']))
    if abs(d['total'] - d['piso']) < 0.005:
        add(f"     (com o sistema a conta parou no piso: demanda + fixos = {m(d['piso'])})")
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
