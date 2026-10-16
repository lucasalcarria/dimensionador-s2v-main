# -*- coding: utf-8 -*-
"""
Precificação do SERVIÇO de instalação de carregador veicular (wallbox).

O carregador é do cliente. A S2V instala SEMPRE um quadro de proteção
**CLAMPER Mobi** (Mobi Box para carregador de parede, Mobi Plug quando o cliente
quer tomadas) — ele já traz DPS, disjuntor e IDR. Motor separado do `engine.py`
de propósito: nada aqui toca a réplica da planilha solar.

Custos (resumidos, como no solar):
  Mobi (modelo + preço do catálogo) · Material CA (tudo o mais: cabos,
  eletroduto, aterramento, conexões) · mão de obra · ART · deslocamento.
Material CA e mão de obra têm valor automático e aceitam valor digitado.

Preço: a MESMA lógica do solar (`engine.calcular`, `preco_convergido`): o
imposto, a comissão e o seguro são % do próprio preço. Sem kit em faturamento
direto (kit = 0), o ponto fixo tem forma fechada:
    preço = custos diretos ÷ (1 − margem − imposto − comissão − seguro)

Parâmetros, catálogo Mobi e preços: `config.json → wallbox` (⚙ Preços na tela).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import engine

# alimentação → (rótulo, condutores do circuito com o PE, condutores
# carregados, polos do disjuntor, fator da queda: 2 em F+N/F+F, √3 no trifásico)
ALIMENTACOES = {
    '220_FN': ('220 V · MONOFÁSICO (F+N)', 3, 2, 2, 2.0),
    '220_FF': ('220 V · BIFÁSICO (F+F)', 3, 2, 2, 2.0),
    '380_3FN': ('380 V · TRIFÁSICO (3F+N)', 5, 3, 3, math.sqrt(3)),
    '220_3F': ('220 V · TRIFÁSICO (3F)', 4, 3, 3, math.sqrt(3)),
}
RHO_COBRE = 0.0225          # Ω·mm²/m — cobre a 70 °C (temperatura de serviço do PVC)


def parametros(config: dict) -> dict:
    """Bloco `wallbox` do config em uso, completado pelo config.json que vem com
    o programa. Na nuvem o config.json é o do bucket (ver CLAUDE.md, "Cloud
    Run"), que pode não ter este bloco ou alguma chave nova: sem isso a aba
    quebraria até alguém mesclar o arquivo à mão."""
    import json
    import os
    try:
        with open(os.path.join(engine.BASE, 'config.json'), encoding='utf-8') as f:
            padrao = json.load(f).get('wallbox') or {}
    except (OSError, ValueError):
        padrao = {}
    return {**padrao, **(config.get('wallbox') or {})}


@dataclass
class EntradaWallbox:
    # cliente --------------------------------------------------------------
    nome: str = ''
    endereco: str = ''
    numero: str = ''
    cidade: str = ''
    consultor: str = ''
    # carregador (do cliente) ----------------------------------------------
    modelo: str = ''
    pot_kw: float = 7.4
    corrente_a: float | None = None      # vazio = calculada pela potência
    alimentacao: str = '220_FF'
    distancia_m: float | None = None    # vazio = A VERIFICAR NA VISITA
    secao_manual: float | None = None    # mm² — sobrepõe a escolha automática
    disjuntor_manual: float | None = None
    # CLAMPER Mobi ---------------------------------------------------------
    mobi_linha: str = 'BOX'              # 'BOX' | 'PLUG'
    mobi_tomadas: str = 'RESIDENCIAL'    # só no Plug: RESIDENCIAL | INDUSTRIAL | AMBAS
    mobi_cor: str = 'CINZA'              # 'CINZA' | 'PRETO'
    mobi_medidor: bool = False
    mobi_preco_manual: float | None = None
    # custos ---------------------------------------------------------------
    material_ca_manual: float | None = None
    mo_manual: float | None = None
    desloc: float = 0.0
    # margem e pagamento (frações) -----------------------------------------
    aliquota: float = 0.08
    comissao_pct: float = 0.0
    seguro_pct: float = 0.0
    margem: float = 0.30
    preco_venda_manual: float | None = None
    cartao_taxa_pct: float = 12.4
    cartao_parcelas: int = 12
    # textos da proposta ---------------------------------------------------
    garantia: str = '1 ANO'
    prazo_execucao: str = ''


def _num(v) -> float:
    return float(str(v).replace(',', '.'))


def dimensionar(e: EntradaWallbox, cw: dict) -> dict:
    """Corrente, disjuntor e cabo do circuito exclusivo do carregador."""
    if e.alimentacao not in ALIMENTACOES:
        raise ValueError(f'Alimentação desconhecida: {e.alimentacao}')
    rot, n_cond, n_carreg, polos_dj, k_queda = ALIMENTACOES[e.alimentacao]
    tensao = 380.0 if e.alimentacao.startswith('380') else 220.0
    trifasico = n_carreg == 3
    avisos = []

    # corrente nominal: a de placa do carregador, ou P / V (P / √3·V)
    if e.corrente_a:
        ib = float(e.corrente_a)
    elif e.pot_kw:
        ib = e.pot_kw * 1000 / ((math.sqrt(3) if trifasico else 1.0) * tensao)
    else:
        raise ValueError('Informe a potência ou a corrente do carregador.')

    # disjuntor: 1º valor padrão ≥ fator × Ib (recarga é carga contínua)
    padroes = sorted(float(x) for x in cw['disjuntores_a'])
    alvo = ib * float(cw.get('fator_disjuntor', 1.25))
    if e.disjuntor_manual:
        dj = float(e.disjuntor_manual)
    else:
        dj = next((x for x in padroes if x >= alvo - 1e-9), padroes[-1])
        if dj < alvo - 1e-9:
            avisos.append(f'Corrente acima do maior disjuntor da tabela '
                          f'({engine.fmt_general(dj)} A).')

    # seção: menor que atenda Iz × fator ≥ disjuntor E queda ≤ máxima
    iz_tab = {_num(s): float(i) for s, i in cw['iz_b1'][str(n_carreg)].items()}
    fc = float(cw.get('fator_correcao_iz', 1.0))
    qmax = float(cw.get('queda_max_pct', 4))
    L = float(e.distancia_m or 0)

    def queda(s):
        return k_queda * L * ib * RHO_COBRE / s / tensao * 100

    if e.secao_manual:
        secao = float(e.secao_manual)
        iz = iz_tab.get(secao)
        if iz is not None and iz * fc < dj:
            avisos.append(f'Cabo de {_mm2(secao)} mm² conduz '
                          f'{engine.fmt_general(round(iz * fc, 1))} A, menos que o '
                          f'disjuntor de {engine.fmt_general(dj)} A.')
    else:
        ok = [s for s in sorted(iz_tab) if iz_tab[s] * fc >= dj and queda(s) <= qmax]
        if ok:
            secao = ok[0]
        else:
            secao = max(iz_tab)
            avisos.append('Nenhuma seção da tabela atende corrente e queda de '
                          'tensão ao mesmo tempo — confira o circuito.')
    iz = iz_tab.get(secao)
    q = queda(secao)
    if q > qmax:
        avisos.append(f'Queda de tensão {q:.1f} % acima do limite de '
                      f'{engine.fmt_general(qmax)} %.')
    # condutor de proteção (NBR 5410 Tab. 58)
    pe = secao if secao <= 16 else (16.0 if secao <= 35 else secao / 2)
    return dict(alimentacao_txt=rot, tensao=tensao, trifasico=trifasico,
                ib=ib, disjuntor=dj, polos_dj=polos_dj, n_fase=n_cond - 1,
                secao=secao, secao_pe=pe,
                iz=(iz * fc if iz is not None else None), queda_pct=q,
                avisos=avisos)


def _mm2(s: float) -> str:
    return engine.fmt_general(s).replace('.', ',')


def escolher_mobi(e: EntradaWallbox, ib: float, cw: dict) -> tuple[dict | None, list]:
    """Modelo do catálogo pelas escolhas da tela (linha, tomadas, cor,
    medidor) e pela alimentação. Entre os que servem, o MENOR cuja corrente
    atende o carregador. Devolve (modelo ou None, avisos)."""
    linha = (e.mobi_linha or 'BOX').upper()
    cands = [m for m in cw.get('mobi') or []
             if m.get('linha') == linha
             and m.get('cor') == (e.mobi_cor or 'CINZA').upper()
             and bool(m.get('medidor')) == bool(e.mobi_medidor)
             and e.alimentacao in (m.get('alimentacao') or [])
             and (linha != 'PLUG'
                  or m.get('tomadas') == (e.mobi_tomadas or '').upper())]
    if not cands:
        nome = 'Mobi Plug' if linha == 'PLUG' else 'Mobi Box'
        return None, [f'Não há {nome} no catálogo para '
                      f'{ALIMENTACOES[e.alimentacao][0].lower()} com essas '
                      f'opções — confira em ⚙ Preços.']
    cands.sort(key=lambda m: float(m.get('corrente_a') or 0))
    m = next((x for x in cands if float(x.get('corrente_a') or 0) >= ib - 1e-9),
             cands[-1])
    avisos = []
    if float(m.get('corrente_a') or 0) < ib - 1e-9:
        avisos.append(f"{m['modelo']} vai até {engine.fmt_general(m['corrente_a'])} A, "
                      f"menos que os {engine.fmt_general(round(ib, 1))} A do carregador.")
    return m, avisos


def material_ca_auto(e: EntradaWallbox, t: dict, cw: dict) -> float:
    """Estimativa do Material CA (tudo o que não é a Mobi): cabos de fase e PE
    com folga, eletroduto, aterramento e conexões. A tela deixa digitar outro."""
    tab = {_num(s): float(p) for s, p in cw['cabo_rs_m'].items()}

    def rs_m(s):                     # seção fora da tabela: a próxima acima
        acima = [x for x in sorted(tab) if x >= s]
        return tab[acima[0]] if acima else tab[max(tab)]

    L = float(e.distancia_m or 0)
    m_cabo = L * (1 + float(cw.get('folga_cabo_pct', 15)) / 100)
    return (m_cabo * (t['n_fase'] * rs_m(t['secao']) + rs_m(t['secao_pe'])) +
            L * float(cw['eletroduto_rs_m']) + float(cw['aterramento_rs']) +
            float(cw['miscelanea_rs']))


def calcular(e: EntradaWallbox, config: dict) -> dict:
    cw = parametros(config)
    # distância vazia = "a verificar na visita": a proposta diz isso, mas cabo,
    # Material CA e mão de obra precisam de metros — são ESTIMADOS com a
    # distância padrão, e a tela avisa. `e` (original) só vai para os textos.
    a_verificar = not e.distancia_m
    dist_calc = (float(cw.get('distancia_padrao_m', 15)) if a_verificar
                 else float(e.distancia_m))
    textos_e, e = e, replace(e, distancia_m=dist_calc)
    t = dimensionar(e, cw)
    mobi, av_mobi = escolher_mobi(e, t['ib'], cw)
    r = dict(tecnico=t, mobi=mobi, avisos=list(t['avisos']) + av_mobi,
             distancia_a_verificar=a_verificar, distancia_calc=dist_calc)
    if a_verificar:
        r['avisos'].insert(0, f'Distância a verificar na visita: cabo, Material CA '
                              f'e mão de obra estimados com '
                              f'{engine.fmt_general(dist_calc)} m.')

    preco_cat = float((mobi or {}).get('preco') or 0)
    r['custo_mobi_auto'] = preco_cat
    r['custo_mobi'] = (float(e.mobi_preco_manual) if e.mobi_preco_manual is not None
                       else preco_cat)
    r['mobi_sem_preco'] = r['custo_mobi'] <= 0
    if mobi and r['mobi_sem_preco']:
        r['avisos'].append(f"Sem preço para {mobi['modelo']}: cadastre em ⚙ Preços "
                           f"ou digite no orçamento.")
    r['custo_material_auto'] = material_ca_auto(e, t, cw)
    r['custo_material'] = (float(e.material_ca_manual)
                           if e.material_ca_manual is not None
                           else r['custo_material_auto'])
    r['custo_mo_auto'] = (float(cw['mao_de_obra_base']) +
                          float(cw['mao_de_obra_por_metro']) * float(e.distancia_m or 0))
    r['custo_mo'] = float(e.mo_manual) if e.mo_manual is not None else r['custo_mo_auto']
    r['custo_art'] = float(cw['art_rs'])
    r['custo_desloc'] = float(e.desloc or 0)
    diretos = (r['custo_mobi'] + r['custo_material'] + r['custo_mo'] +
               r['custo_art'] + r['custo_desloc'])
    r['custo_direto'] = diretos

    # ---- preço de venda: mesma conta do solar (engine.preco_convergido)
    var = e.aliquota + e.comissao_pct + e.seguro_pct     # % do próprio preço
    if e.preco_venda_manual is not None:
        preco = float(e.preco_venda_manual)
    else:
        den = 1 - e.margem - var
        if den <= 0:
            raise ValueError('Margem + imposto + comissão + seguro passam de 100 %.')
        preco = diretos / den
    r['preco_venda'] = preco
    r['aliquota_usada'] = e.aliquota
    r['margem_usada'] = e.margem
    r['custo_imposto'] = preco * e.aliquota
    r['custo_comissao'] = preco * e.comissao_pct
    r['custo_seguro'] = preco * e.seguro_pct
    r['custo_total'] = (diretos + r['custo_imposto'] + r['custo_comissao'] +
                        r['custo_seguro'])
    r['lucro_rs'] = preco - r['custo_total']
    r['lucro_pct'] = r['lucro_rs'] / preco if preco else 0.0

    # cartão: taxa repassada ao cliente (igual ao solar)
    tx = e.cartao_taxa_pct / 100.0
    nc = int(e.cartao_parcelas or 0)
    r['cartao_parcelas'] = nc
    r['cartao_valor_credito'] = preco / (1 - tx) if 0 <= tx < 1 else preco
    r['parcela_cartao'] = r['cartao_valor_credito'] / nc if nc > 0 else 0.0
    r['textos'] = _textos(textos_e, r, config)
    return r


_MESES = ('JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
          'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO')


def _textos(e: EntradaWallbox, r: dict, config: dict) -> dict:
    from datetime import date
    br = config.get('formato_ptbr', True)
    t = r['tecnico']
    hoje = date.today()
    num = lambda v, nd=1: engine.fmt_num(v, nd, br).rstrip('0').rstrip(',.')
    local = ', '.join(p for p in ((e.endereco or '').strip(),
                                  (e.numero or '').strip()) if p)
    nc = r['cartao_parcelas']
    return dict(
        cliente=(e.nome or '').strip().upper(),
        local=local.upper(),
        cidade=(e.cidade or '').strip().upper(),
        modelo=(e.modelo or '').strip().upper() or 'A DEFINIR',
        potencia=(f'{num(e.pot_kw, 2)} kW' if e.pot_kw else '—'),
        alimentacao=t['alimentacao_txt'],
        corrente=f"{num(t['ib'])} A",
        distancia=(f'{num(e.distancia_m)} m' if e.distancia_m
                   else 'A VERIFICAR NA VISITA'),
        valor=engine.moeda(r['preco_venda'], br),
        parcelamento=(f"OU {nc}x DE {engine.moeda(r['parcela_cartao'], br)} NO CARTÃO"
                      if nc > 1 and r['parcela_cartao'] else ''),
        garantia=(e.garantia or '').strip().upper() or '—',
        prazo=(e.prazo_execucao or '').strip().upper() or '—',
        referencia=f'{_MESES[hoje.month - 1]}/{hoje.year}',
        # legenda da foto da Mobi na pág. 2
        mobi_legenda=({'BOX': 'PROTEÇÃO CLAMPER MOBI BOX',
                       'PLUG': 'PROTEÇÃO CLAMPER MOBI PLUG'}
                      .get((r.get('mobi') or {}).get('linha'), '')),
    )


def composicao(r: dict) -> list:
    """(rótulo, R$, observação) de cada custo — a mesma soma de custo_total."""
    mobi = (r.get('mobi') or {}).get('modelo') or 'Clamper Mobi'
    return [(mobi, r['custo_mobi'], ''),
            ('Material CA', r['custo_material'],
             '' if r['custo_material'] == r['custo_material_auto'] else 'digitado'),
            ('Mão de obra', r['custo_mo'],
             '' if r['custo_mo'] == r['custo_mo_auto'] else 'digitada'),
            ('ART', r['custo_art'], ''),
            ('Deslocamento', r['custo_desloc'], ''),
            ('Comissão', r['custo_comissao'], ''),
            ('Seguro', r['custo_seguro'], ''),
            ('Imposto', r['custo_imposto'], '')]


def resumo_texto(e: EntradaWallbox, r: dict, config: dict) -> str:
    """RESUMO.txt da pasta do projeto: técnica + composição do preço."""
    br = config.get('formato_ptbr', True)
    m = lambda v: engine.moeda(v, br)
    d = lambda v, nd: engine.fmt_num(v, nd, br)
    t, tx = r['tecnico'], r['textos']
    venda = r['preco_venda']
    pct = lambda v: f"{d(v / venda * 100, 1):>5} %" if venda else '   — '
    L = ['INSTALAÇÃO DE CARREGADOR VEICULAR (WALLBOX) — S2V ENGENHARIA', '',
         f"Cliente: {tx['cliente']}",
         f"Local: {' — '.join(p for p in (tx['local'], tx['cidade']) if p) or '—'}",
         f"Consultor: {e.consultor or '—'}", '',
         f"Carregador (do cliente): {tx['modelo']} · {tx['potencia']}",
         f"Alimentação: {t['alimentacao_txt']}",
         f"Corrente nominal: {d(t['ib'], 1)} A · disjuntor "
         f"{engine.fmt_general(t['disjuntor'])} A {t['polos_dj']}P",
         f"Cabo: {_mm2(t['secao'])} mm² + PE {_mm2(t['secao_pe'])} mm² · "
         f"{tx['distancia']} · queda {d(t['queda_pct'], 2)} %"
         + (f" (estimada com {engine.fmt_general(r['distancia_calc'])} m)"
            if r['distancia_a_verificar'] else ''),
         f"Proteção: {(r.get('mobi') or {}).get('modelo') or '—'}"]
    L += [f'AVISO: {a}' for a in r['avisos']]
    L += ['', 'COMPOSIÇÃO DO PREÇO']
    for rot, v, obs in composicao(r):
        L.append(f"  {(rot + (f' ({obs})' if obs else ''))[:56]:56} {pct(v)} {m(v):>13}")
    L += [f"  {'CUSTO TOTAL':56} {pct(r['custo_total'])} {m(r['custo_total']):>13}",
          f"  {'LUCRO':56} {pct(r['lucro_rs'])} {m(r['lucro_rs']):>13}",
          f"  {'VALOR DE VENDA':56} 100,0 % {m(venda):>13}", '',
          f"Cartão: {tx['parcelamento'] or '—'}",
          f"Garantia: {tx['garantia']} · Prazo: {tx['prazo']}"]
    return '\n'.join(L) + '\n'
