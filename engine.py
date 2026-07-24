# -*- coding: utf-8 -*-
"""
Motor de cálculo do dimensionador S2V — réplica fiel da lógica da planilha
"PLANILHA S2V ENGENHARIA - 1 OPÇÃO", com as referências de célula anotadas.

Convenções:
  PR  = aba 'PLANILHA RESUMO'
  DD  = aba 'DADOS'
  TX  = aba 'TEXTO'
Todas as melhorias em relação à planilha são controladas por `config` e estão
documentadas no LEIA-ME (ex.: preço/Wp sempre convergido, tarifa média do
retorno em 25 anos corrigida, fator Fio B automático pelo ano).
"""
from __future__ import annotations
import json
import math
import os
import shutil
import sys
from dataclasses import dataclass, field, asdict
from datetime import date

DIAS_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
         'jul', 'ago', 'set', 'out', 'nov', 'dez']

BASE = os.path.dirname(os.path.abspath(__file__))


def dir_execucao() -> str:
    """Pasta onde o usuário executa o programa (ao lado do .exe, se congelado)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return BASE


def caminho_config() -> str:
    """Caminho do config.json em uso (a cópia editável ao lado do executável,
    quando existir)."""
    externo = os.path.join(dir_execucao(), 'config.json')
    return externo if os.path.exists(externo) else os.path.join(BASE,
                                                                'config.json')


def carregar_config(path: str | None = None) -> dict:
    if path is None:
        externo = os.path.join(dir_execucao(), 'config.json')
        interno = os.path.join(BASE, 'config.json')
        if externo != interno and not os.path.exists(externo) \
                and os.path.exists(interno):
            try:  # cria uma cópia editável ao lado do executável
                shutil.copy(interno, externo)
            except OSError:
                pass
        path = externo if os.path.exists(externo) else interno
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------- entradas
@dataclass
class UC:
    """Uma unidade consumidora — linha 6..14 de PR + linha 31..39."""
    tipo: str = ''                    # PR!D6: '', 'GERADORA' ou 'BENEFICIÁRIA'
    ilum_publica: float = 0.0         # PR!E6 (R$/mês, COSIP)
    ligacao: str = 'MONOFASICO'       # PR!G6
    consumos: list = field(default_factory=lambda: [0.0] * 12)  # PR!H6:S6 (kWh)
    te: float = 0.27575               # PR!D31 (tarifa TE sem imposto)
    tusd: float = 0.36667             # PR!E31 (tarifa TUSD sem imposto)
    icms: float = 0.19                # PR!F31
    cofins: float = 0.058             # PR!G31
    pis: float = 0.0126               # PR!H31
    pct_noturno: float = 0.65         # PR!M31 (fração faturada/injetada)
    bandeira: str = 'VERDE'           # PR!P31

    # ---- derivados
    @property
    def ativa(self) -> bool:
        return bool(self.tipo)

    @property
    def consumo_medio(self) -> float:          # DD!D48 = AVERAGE(PR!H6:S6)
        return sum(self.consumos) / 12.0

    @property
    def disponibilidade(self) -> float:        # kWh mínimos por ligação
        return {'MONOFASICO': 30, 'BIFASICO': 50}.get(self.ligacao, 100)

    @property
    def pct_noturno_efetivo(self) -> float:
        """% noturno aplicado no faturamento com solar.

        Na planilha (coluna M): a GERADORA usa o % noturno informado (M31,
        ex. 0,65); toda BENEFICIÁRIA usa 1 (100 %) — M32:M39 =
        IF(tipo="BENEFICIÁRIA";1;"PREENCHER"). Ou seja, o crédito da
        beneficiária é sempre integralmente faturável.
        """
        if self.tipo == 'BENEFICIÁRIA':
            return 1.0
        return self.pct_noturno

    # PR!I31 / PR!J31 — tarifa com imposto (gross-up de ICMS, PIS e COFINS)
    def te_com_imposto(self) -> float:
        return self.te / ((1 - self.icms) * (1 - (self.cofins + self.pis)))

    def tusd_com_imposto(self) -> float:
        return self.tusd / ((1 - self.icms) * (1 - (self.cofins + self.pis)))

    # PR!F6 — tarifa cheia usada em todo o resto
    def tarifa_cheia(self) -> float:
        return self.te_com_imposto() + self.tusd_com_imposto() if self.ativa else 0.0

    # PR!K31 — abatimento TE (igual a I31)
    def abat_te(self) -> float:
        return self.te_com_imposto()

    # PR!L31 — abatimento TUSD líquido do Fio B (Lei 14.300)
    def abat_tusd(self, fio_b_rs_kwh: float) -> float:
        return (self.tusd - fio_b_rs_kwh) / (1 - (self.pis + self.cofins))


@dataclass
class Entradas:
    # cabeçalho ------------------------------------------------------ PR!3
    nome: str = ''
    endereco: str = ''
    cidade: str = ''
    uc_numero: str = ''
    # unidades consumidoras (até 9) ---------------------------------- PR!6:14
    ucs: list = field(default_factory=list)
    # kit gerador ----------------------------------------------------- PR!20:21
    qtd_modulos_kit: int = 0          # PR!C21 (nº de módulos do kit)
    marca_inversor: str = 'CHINT'     # PR!D21
    pot_inversor_kw: float = 3.0      # PR!E21
    tensao_inversor: int = 220        # PR!F21
    valor_kit: float = 0.0            # PR!G21
    conexao: str = 'HÍBRIDO'          # PR!H21
    # dimensionamento -------------------------------------------------- PR!U:Y
    marca_modulo: str = 'ASTRONERGY N-TYPE'   # PR!V12
    pot_modulo_w: float = 620.0       # PR!W12
    estrutura: str = 'FIBROCIMENTO'   # PR!W9
    perfil_irradiacao: str = '3.8'    # DD!B8 (seletor da linha de irradiação)
    irradiacao_customizada: list | None = None  # 12 valores Wh/m²/dia (internet)
    # custos ------------------------------------------------------------
    entrada: float = 0.0              # PR!R21 (custo 'ENTRADA')
    desloc: float = 0.0               # PR!V21
    comissao_pct: float = 0.0         # PR!X21 (fração; V33 = preço_total × X21)
    seguro_pct: float = 0.0           # PR!Y21 (fração; DD!R36 = Y21 × preço_total)
    # margem -------------------------------------------------------------
    margem_desejada: float | None = 0.16   # PR!W31 (None => usa faixa automática)
    # financiamento -------------------------------------------------------
    fin_taxa_mes: float = 1.99        # DD!M35 (% a.m.)
    fin_parcelas: int = 60            # DD!M36
    # preço de venda manual (sobrepõe o cálculo, como colar em DD!B75)
    wp_manual: float | None = None
    # sobrepor custos automáticos (None = usa a regra da planilha/config)
    mo_manual: float | None = None            # PR!Q21 editável
    material_manual: float | None = None      # PR!S21 editável
    aliquota_manual: float | None = None      # DD!D26 editável (fração, ex. 0.08)
    # componentes opcionais mostrados na página 3 da proposta
    tem_bateria: bool = False
    bat_qtd: int = 1
    bat_marca: str = ''
    bat_kwh: float | None = None              # capacidade em kWh
    tem_stringbox: bool = True
    sb_qtd: int = 1
    sb_marca: str = ''
    sb_es: str = ''                           # ex.: 2E/2S


# ---------------------------------------------------------------- resultados
def _excel_round(x: float, nd: int = 0) -> float:
    """ROUND do Excel (half away from zero)."""
    p = 10 ** nd
    return math.floor(abs(x) * p + 0.5) / p * (1 if x >= 0 else -1)


def _trunc(x: float, nd: int = 0) -> float:
    p = 10 ** nd
    return math.trunc(round(x * p, 9)) / p


def _roundup(x: float, nd: int = 0) -> float:
    """ROUNDUP do Excel (afasta de zero), seguro contra ruído de float."""
    p = 10 ** nd
    v = math.ceil(round(abs(x) * p, 9)) / p
    return v if x >= 0 else -v


class Resultado(dict):
    """dict com acesso por atributo, para deixar o app legível."""
    __getattr__ = dict.__getitem__


def fator_fio_b(config: dict, ano: int | None = None) -> float:
    """DD!J47:K52 — escalonamento da Lei 14.300. Na planilha o ano estava
    fixado em 2026 (60%); aqui segue o ano corrente, com tabela configurável."""
    ano = ano or date.today().year
    tab = {int(k): v for k, v in config['fio_b_escalonamento'].items()}
    if ano in tab:
        return tab[ano]
    return tab[max(tab)] if ano > max(tab) else tab[min(tab)]


def calcular(e: Entradas, config: dict, ano: int | None = None) -> Resultado:
    r = Resultado()
    ano = ano or date.today().year
    ucs_ativas = [u for u in e.ucs if u.ativa]
    geradora = next((u for u in e.ucs if u.tipo == 'GERADORA'), None)

    # ---------------- consumo -------------------------------------- PR!15
    tot_mes = [sum(u.consumos[m] for u in ucs_ativas) for m in range(12)]
    r['consumo_anual'] = sum(tot_mes)                       # PR!V9
    r['consumo_medio'] = r['consumo_anual'] / 12.0          # PR!U9

    # ---------------- irradiação / geração -------------------------- DD!3:9
    if e.irradiacao_customizada:
        irr = list(e.irradiacao_customizada)                 # Wh/m²/dia
    else:
        irr = config['perfis_irradiacao'][e.perfil_irradiacao]
    kwh_kwp_mes = [irr[m] / 1000.0 * DIAS_MES[m] for m in range(12)]  # DD!C9:N9
    r['kwh_kwp_ano'] = sum(kwh_kwp_mes)                      # DD!O9

    pr_perf = config['performance_ratio']                    # 0.75 na planilha
    # DD!B21 — potência FV necessária p/ compensar o consumo anual
    r['kwp_necessario'] = _excel_round(
        r['consumo_anual'] / (pr_perf * r['kwh_kwp_ano']), 2) if r['kwh_kwp_ano'] else 0.0
    # PR!U12 — sugestão de nº de módulos
    r['modulos_sugeridos'] = int(_excel_round(
        r['kwp_necessario'] * 1000 / e.pot_modulo_w, 0)) if e.pot_modulo_w else 0

    qtd = e.qtd_modulos_kit or 0
    r['kwp'] = qtd * e.pot_modulo_w / 1000.0                 # PR!X12
    # DD!D22:O22 — geração mensal do sistema
    r['geracao_mensal'] = [r['kwp'] * pr_perf * g for g in kwh_kwp_mes]
    r['geracao_anual'] = sum(r['geracao_mensal'])            # PR!J21
    r['geracao_media'] = r['geracao_anual'] / 12.0           # PR!I21
    # PR!L20 — compensação (geração anual / consumo anual)
    r['compensacao'] = (r['geracao_anual'] / r['consumo_anual']
                        if r['consumo_anual'] else 0.0)

    # DD!O28 — área ocupada / PR!X9
    if e.estrutura != 'SOLO':
        r['area_m2'] = qtd * (2.7 if e.pot_modulo_w >= 600 else 2.6) + 10
    else:
        r['area_m2'] = qtd * 8.5

    # ---------------- custos ----------------------------------------- PR!Q20:Y21
    mo_min = config.get('mao_de_obra_minima', 850)
    mo_mod = config.get('mao_de_obra_por_modulo', 85)
    r['custo_mo_auto'] = float(mo_min) if qtd < 10 else qtd * float(mo_mod)  # PR!Q21
    r['custo_mo'] = (e.mo_manual if e.mo_manual is not None
                     else r['custo_mo_auto'])
    r['custo_material_auto'] = _material_extra(r['kwp'], config)  # PR!S21
    r['custo_material'] = (e.material_manual if e.material_manual is not None
                           else r['custo_material_auto'])
    r['custo_trafo'], r['trafo_desc'] = _trafo(e, config)    # PR!T21 = Σ DD!S26:S34
    r['custo_desloc'] = e.desloc                             # PR!V21
    r['custo_entrada'] = e.entrada                           # PR!R21

    # ---------------- preço de venda (CÁLCULO WP) --------------------- DD!74:95
    faixas = config['faixas_margem']                         # DD!B78
    aliq = (e.aliquota_manual if e.aliquota_manual is not None
            else config['aliquota_imposto'])                 # DD!D26 = 8 %
    r['aliquota_usada'] = aliq

    def margem_para(custo_total: float) -> float:
        base = custo_total / 0.8
        for lim, m in faixas:
            if base <= lim:
                return m
        return faixas[-1][1]

    def preco_convergido(margem_fixa: float | None) -> tuple[float, float, float, float]:
        """Itera WP → imposto → custo → WP até convergir (macro GERAR_KWP).
        Retorna (preco_total, wp, imposto, margem_usada)."""
        preco = max(e.valor_kit * 1.3, 1000.0)               # semente
        margem = margem_fixa if margem_fixa is not None else 0.2
        for _ in range(60):
            imposto = aliq * (preco - e.valor_kit)           # DD!E83 ramo normal
            comissao = preco * e.comissao_pct                # PR!V33
            seguro = preco * e.seguro_pct                    # DD!R36
            custo = (r['custo_mo'] + comissao + e.desloc + r['custo_trafo'] +
                     r['custo_material'] + e.entrada + e.valor_kit +
                     seguro + imposto)                       # DD!C83 / PR!X25
            m = margem_fixa if margem_fixa is not None else margem_para(custo)
            novo = custo / (1 - m)                           # DD!B84 ×1000×kWp
            if abs(novo - preco) < 0.005:
                preco = novo
                margem = m
                break
            preco, margem = novo, m
        imposto = aliq * (preco - e.valor_kit)
        wp = preco / 1000.0 / r['kwp'] if r['kwp'] else 0.0
        return preco, wp, imposto, margem

    if e.wp_manual is not None:                              # equivale a DD!B75 manual
        r['preco_wp'] = e.wp_manual
        r['preco_venda'] = r['kwp'] * 1000 * e.wp_manual     # DD!B25 / PR!U35
        r['margem_usada'] = (e.margem_desejada if e.margem_desejada is not None
                             else margem_para(r['preco_venda'] * 0.8))
        r['custo_imposto'] = aliq * (r['preco_venda'] - e.valor_kit)
    else:
        preco, wp, imposto, margem = preco_convergido(e.margem_desejada)
        r['preco_venda'], r['preco_wp'] = preco, wp
        r['custo_imposto'], r['margem_usada'] = imposto, margem

    r['custo_comissao'] = r['preco_venda'] * e.comissao_pct  # PR!V33
    r['custo_seguro'] = r['preco_venda'] * e.seguro_pct      # DD!R36
    # PR!X25 — custo total
    r['custo_total'] = (r['custo_mo'] + r['custo_comissao'] + r['custo_desloc'] +
                        r['custo_imposto'] + r['custo_trafo'] + r['custo_material'] +
                        r['custo_entrada'] + e.valor_kit + r['custo_seguro'])
    # PR!U32 / PR!V32
    r['lucro_pct'] = ((r['preco_venda'] - r['custo_total']) / r['preco_venda']
                      if r['preco_venda'] else 0.0)
    r['lucro_rs'] = r['preco_venda'] * r['lucro_pct']

    # ---------------- fatura SEM sistema ------------------------------ DD!47:57
    fio_b = fator_fio_b(config, ano) * config['fio_b_rs_mwh'] / 1000.0  # DD!K50
    soma_consumo = sum(u.consumo_medio for u in ucs_ativas) or 1.0      # DD!D57
    detalhes_uc = []
    fatura_sem = 0.0                                          # DD!B57 → PR!L25
    for u in e.ucs:
        if not u.ativa:
            detalhes_uc.append(None)
            continue
        rateio = u.consumo_medio / soma_consumo               # DD!E48
        ger_uc = rateio * r['geracao_media']                  # DD!F48
        maior = max(u.consumo_medio, ger_uc)                  # DD!G48
        fatura_sem += u.tarifa_cheia() * maior + u.ilum_publica  # DD!B48

        # ---- fatura COM sistema ------------------------------------- PR!31:39
        pct_not = u.pct_noturno_efetivo                       # M31 / M32:M39
        faturado = _trunc(maior * pct_not, 0)                 # PR!N31
        compensado = faturado - u.disponibilidade             # PR!O31
        piso = u.disponibilidade * u.tarifa_cheia()
        liquido = (faturado * u.tarifa_cheia() -
                   compensado * (u.abat_te() + u.abat_tusd(fio_b)))
        taxa_min = max(piso, liquido)                         # PR!Q31
        band = config['bandeiras'].get(u.bandeira, 0.0)       # DD!J54:J57
        band_gross = band / ((1 - u.icms) * (1 - (u.cofins + u.pis)))  # DD!K55..
        extra_band = 0.0 if u.bandeira == 'VERDE' else (faturado - compensado) * band_gross
        total_uc = taxa_min + extra_band + u.ilum_publica     # PR!R31
        detalhes_uc.append(dict(
            tipo=u.tipo, consumo=u.consumo_medio, rateio=rateio,
            geracao_rateada=ger_uc, maior=maior, pct_noturno=pct_not,
            faturado=faturado, disponibilidade=u.disponibilidade,
            compensado=compensado, tarifa=u.tarifa_cheia(),
            abat_te=u.abat_te(), abat_tusd=u.abat_tusd(fio_b),
            piso=piso, liquido=liquido, taxa_min=taxa_min,
            bandeira=u.bandeira, extra_bandeira=extra_band,
            ilum_publica=u.ilum_publica, total=total_uc,
            fatura_sem_uc=u.tarifa_cheia() * maior + u.ilum_publica))
        r.setdefault('_fatura_com_parcelas', []).append(total_uc)

    r['detalhes_uc'] = detalhes_uc
    r['tarifas_cheias'] = [(u.tarifa_cheia() if u.ativa else None)
                           for u in e.ucs]
    r['fatura_sem'] = fatura_sem                              # PR!L25
    r['fatura_com'] = sum(r.get('_fatura_com_parcelas', []))  # PR!M25
    r['economia_mensal'] = r['fatura_sem'] - r['fatura_com']  # PR!N25
    r.pop('_fatura_com_parcelas', None)

    # ---------------- retorno em 25 anos ------------------------------ DD!39:67
    ger = r['geracao_mensal']
    if len(ucs_ativas) >= 1 and geradora:
        liq = [tot_mes[m] - ger[m] for m in range(12)]        # DD!C39:N39
        fat_kwh = [max(v, 100.0) for v in liq]                # DD!C40 (piso 100)
        econ_scred = [tot_mes[m] - fat_kwh[m] for m in range(12)]   # DD!C41
        cred = [-v if v < 0 else 0.0 for v in liq]            # DD!C42
        econ_total = [cred[m] + econ_scred[m] for m in range(12)]   # DD!C43
        ger2 = 0.0  # geração do "sistema 2" (não usado nesta versão da planilha)
        abativel = [max(tot_mes[m] - ger2 - 100.0, 0.0)
                    for m in range(12)]                       # DD!C44 (usa D23=0)
        desperdicado = max(sum(cred) - sum(abativel), 0.0)    # DD!C45
        kwh_ano1 = sum(econ_total) - desperdicado             # DD!O43
    else:
        kwh_ano1 = 0.0

    reaj = config['reajuste_tarifa_aa']
    serie = []
    if config.get('compat_planilha'):
        # Reprodução exata da planilha (DD!P42 dividia a tarifa média pelas 9
        # linhas de UC, mesmo vazias, e reajustava a tarifa já no 1º ano).
        tarifa_media = sum(u.tarifa_cheia() for u in e.ucs) / 9
        kwh, tar = kwh_ano1, tarifa_media
        for ano_i in range(25):                               # DD!O43:Q67
            tar *= (1 + reaj)
            if ano_i == 1:
                kwh *= (1 - config['degradacao_ano1'])
            elif ano_i > 1:
                kwh *= (1 - config['degradacao_demais'])
            serie.append(kwh * tar)
    else:
        # Estimativa realista: parte da ECONOMIA efetiva de hoje (fatura sem −
        # fatura com, que já considera Fio B, custo de disponibilidade,
        # bandeira e iluminação), reajusta a tarifa em `reajuste_tarifa_aa`
        # ao ano a partir do 2º ano e aplica a degradação dos módulos
        # (−2,5 % no 2º ano, −0,7 % a.a. depois).
        econ_ano = max(r['economia_mensal'], 0.0) * 12.0
        fator_ger = 1.0
        for ano_i in range(25):
            if ano_i == 1:
                fator_ger *= (1 - config['degradacao_ano1'])
            elif ano_i > 1:
                fator_ger *= (1 - config['degradacao_demais'])
            serie.append(econ_ano * (1 + reaj) ** ano_i * fator_ger)
    r['retorno_25'] = sum(serie)                              # PR!O25
    r['retorno_serie'] = serie

    # cartões opcionais da página 3 da proposta
    r['ocultar_cartoes'] = [nome for nome, tem in
                            (('bateria', e.tem_bateria),
                             ('stringbox', e.tem_stringbox)) if not tem]
    r['sb_custom'] = bool(e.tem_stringbox and
                          (e.sb_marca or e.sb_es or (e.sb_qtd or 1) != 1))

    # PR!O20 — payback simples
    r['payback_anos'] = (_trunc(r['preco_venda'] / (r['economia_mensal'] * 12), 1)
                         if r['economia_mensal'] > 0 else 0.0)

    # PR!U37 — financiamento (PMT)
    i = e.fin_taxa_mes / 100.0
    n = e.fin_parcelas
    r['parcela_fin'] = (r['preco_venda'] * i / (1 - (1 + i) ** -n)
                        if i > 0 and n > 0 else 0.0)

    # textos prontos (aba TEXTO) --------------------------------------
    r['textos'] = _textos(e, r, config)
    return r


def _material_extra(kwp: float, config: dict) -> float:
    """DD!G26:G35 — material por faixa de potência (custo base × 1,6)."""
    for lim_inf, lim_sup, base in config['material_extra_faixas']:
        if lim_inf < kwp <= lim_sup or (lim_inf == 0 and kwp <= lim_sup):
            return base * config['material_markup']
    return 0.0


def _trafo(e: Entradas, config: dict) -> tuple[float, str]:
    """DD!R25:S34 — autotrafo 380/220 V p/ inversores ≥12 kW em 380 V."""
    if not (e.pot_inversor_kw >= 12 and e.tensao_inversor == 380):
        return 0.0, ''
    p = e.pot_inversor_kw / 0.8                               # DD!R25
    for lim_inf, lim_sup, kva, preco in config['trafos']:
        if lim_inf == lim_sup:                                # DD!S26 (p = 15)
            hit = abs(p - lim_inf) < 1e-9
        elif lim_sup is None:                                 # DD!S34 (p > 120)
            hit = p > lim_inf
        else:                                                 # DD!S27..S33
            hit = lim_inf < p < lim_sup
        if hit:
            return float(preco), f'TRAFO {kva}KVA'
    return 0.0, ''


# ------------------------------------------------------------------ formato
def fmt_general(v: float) -> str:
    """Formato 'Geral' do Excel: sem zeros à direita."""
    if v == int(v):
        return str(int(v))
    s = f'{v:.10f}'.rstrip('0').rstrip('.')
    return s


def fmt_num(v: float, nd: int, locale_br: bool) -> str:
    s = f'{v:,.{nd}f}'
    if locale_br:
        s = s.replace(',', '§').replace('.', ',').replace('§', '.')
    return s


def moeda(v: float, locale_br: bool = True) -> str:
    return 'R$ ' + fmt_num(v, 2, locale_br)


def _dec(v_str: str, locale_br: bool) -> str:
    return v_str.replace('.', ',') if locale_br else v_str


def _textos(e: Entradas, r: Resultado, config: dict) -> dict:
    """Réplica da aba TEXTO — strings exatamente como na proposta."""
    br = config.get('formato_ptbr', True)
    t = {}
    t['nome_proper'] = e.nome.title()                        # TX!B2
    t['nome_upper'] = e.nome.upper()                         # TX!B4
    t['endereco'] = e.endereco.title()                       # TX!B3
    t['cidade'] = e.cidade                                   # PR!U3
    t['uc_numero'] = str(e.uc_numero)                        # PR!Y3
    kwp_txt = fmt_general(_roundup(r['kwp'], 2))             # TX!D3 (ROUNDUP)
    t['kwp_txt'] = _dec(kwp_txt, br) + ' kWp'
    t['area_txt'] = _dec(fmt_general(round(r['area_m2'], 6)), br) + ' m²'  # TX!D4
    t['consumo_txt'] = f"{int(_trunc(r['consumo_medio']))} kWh/mês"        # TX!E6
    # TX!D7/E7 — geração exibida (limitada ao consumo quando compensa ~100 %)
    if r['compensacao'] >= 0.97 and r['consumo_medio'] > r['geracao_media']:
        ger_show = int(_trunc(r['consumo_medio']))
    else:
        ger_show = int(_trunc(r['geracao_media']))
    t['geracao_txt'] = f'{ger_show} kWh/mês'
    # TX!D8 — % de compensação
    if 0.97 <= r['compensacao'] <= 1.0:
        t['compensa_txt'] = '100%'
    else:
        t['compensa_txt'] = f"{_excel_round(r['compensacao'] * 100):.0f}%"
    t['mod_qtd'] = f'{e.qtd_modulos_kit}x'                   # TX!B8
    t['mod_desc'] = (f'{e.marca_modulo} '
                     f'{fmt_general(e.pot_modulo_w)}').title() + 'W'     # TX!B10
    t['inv_titulo'] = f'INVERSOR {e.conexao}'                # TX!B9
    t['inv_qtd'] = '1x'                                      # TX!C12
    mono_tri = 'MONO' if e.pot_inversor_kw <= 10 else 'TRI'  # DD!B28
    kw_txt = _dec(fmt_general(e.pot_inversor_kw), br)
    t['inv_desc'] = (f'{e.marca_inversor} {kw_txt}kW' +
                     f' {mono_tri} {e.tensao_inversor}V '.title())         # TX!B12
    if e.estrutura != 'SOLO':                                # TX!B13/C13
        t['estr_qtd'] = f'{math.ceil(e.qtd_modulos_kit / 4)}x'
        t['estr_desc'] = f'P/ 4 Mod. {e.estrutura.title()}'
    else:
        t['estr_qtd'] = f'{math.ceil(e.qtd_modulos_kit / 8)}x'
        t['estr_desc'] = 'Solo P/ 8 Mod.'
    g = config.get('garantias_fixas') or {}
    minv = e.marca_inversor.upper()
    mmod = e.marca_modulo.upper()
    gar_inv = g.get('inversor') or (15 if minv in ('MICRO DEYE', 'HOYMILES')
                                    else 10)                 # DD!O30
    gar_inst = g.get('instalacao') or (20 if mmod == 'AMERISOLAR'
                                       else 15 if 'N-TYPE' in mmod
                                       else 12)              # DD!O31
    gar_mod = g.get('modulos') or (30 if (mmod in ('SUNOVA', 'OSDA', 'AMERISOLAR')
                                          or 'N-TYPE' in mmod)
                                   else 25)                  # DD!O32
    t['gar_inversor'] = f'{gar_inv} ANOS'                    # TX!I6
    t['gar_instalacao'] = f'{gar_inst} ANOS'                 # TX!I7
    t['gar_modulos'] = f'{gar_mod} ANOS'                     # TX!I3
    # página 5
    t['fatura_sem'] = moeda(r['fatura_sem'], br)             # PR!L25
    t['fatura_com'] = moeda(r['fatura_com'], br)             # PR!M25
    t['economia_mensal'] = moeda(r['economia_mensal'], br)   # PR!N25
    t['retorno_25'] = moeda(r['retorno_25'], br)             # PR!O25
    t['valor_venda'] = moeda(r['preco_venda'], br)           # PR!U35
    pay = _trunc(r['payback_anos'], 1)
    t['payback_txt'] = _dec(fmt_general(pay), br) + ' ANOS'  # PR!O20
    # cartões opcionais (pág. 3)
    if e.tem_bateria:
        t['bat_qtd'] = f'{int(e.bat_qtd or 1)}x'              # cartão BATERIA
        cap = (f'{_dec(fmt_general(round(e.bat_kwh, 2)), br)} kWh'
               if e.bat_kwh else '')
        desc_bat = ' '.join(x for x in (e.bat_marca.strip().title(), cap) if x)
        t['bat_desc'] = desc_bat or t['inv_desc']             # (a planilha usava
        #                                                        o texto do inversor)
        gb = (config.get('garantias_fixas') or {}).get('bateria')
        t['gar_bateria'] = f'{gb or 10} ANOS'                # garantia da bateria
    if e.tem_stringbox:
        t['sb_qtd'] = f'{int(e.sb_qtd or 1)}x'                # cartão STRING BOX
        t['sb_desc'] = ' '.join(x for x in (e.sb_marca.strip().title(),
                                            e.sb_es.strip().upper()) if x)
    hoje = date.today()
    t['disclaimer_data'] = (f'considerados são referentes a '
                            f'{MESES[hoje.month - 1]}/{hoje.year}.')
    # prazo de validade impresso na pág. 5 (era fixo na arte antiga)
    t['validade_txt'] = f"{int(config.get('validade_dias', 7))} DIAS"
    t['fin_txt'] = (f'EM {e.fin_parcelas}x SOB '
                    f"{_dec(fmt_general(e.fin_taxa_mes), br)}% AO MÊS")     # TX!I2
    return t
