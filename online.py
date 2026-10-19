# -*- coding: utf-8 -*-
"""
Recursos de internet (opcionais — o programa funciona 100% offline sem eles):

  * buscar_irradiacao(cidade): média mensal de irradiação global horizontal
    (Wh/m²/dia) do ponto, via NASA POWER (climatologia 2001-2020), com
    geocodificação pela API aberta do Open-Meteo. Sem chave de API.
  * buscar_cep(cep): endereço pelo ViaCEP.

Todas as chamadas têm timeout curto e devolvem erro amigável quando não há
conexão.
"""
from __future__ import annotations
import gzip
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 25
# Cabeçalhos de navegador: sites gov.br atrás de WAF costumam rejeitar
# user-agents "de script" com 400/403.
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/126.0.0.0 Safari/537.36'),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
}
UA = HEADERS  # compat


def _get_json_urllib(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get('Content-Encoding', '') == 'gzip':
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return json.loads(raw.decode('utf-8'))


def _get_json_curl(url: str) -> dict:
    """Fallback via curl do sistema (Windows 10+ já traz curl.exe).

    O curl do Windows usa a pilha TLS do próprio sistema (Schannel), com
    'impressão digital' TLS diferente da do Python — o que costuma passar por
    WAFs gov.br que derrubam o handshake do OpenSSL (erro SSL: UNEXPECTED_EOF).
    """
    import shutil
    import subprocess
    exe = shutil.which('curl')
    if not exe:
        raise LookupError('curl não disponível no sistema')
    cmd = [exe, '-sS', '--max-time', str(TIMEOUT),
           '-A', HEADERS['User-Agent'],
           '-H', 'Accept: application/json',
           '-H', 'Accept-Language: pt-BR,pt;q=0.9', url]
    p = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 10)
    if p.returncode != 0:
        raise LookupError(f'curl falhou: {p.stderr.decode("utf-8", "replace")[:150]}')
    return json.loads(p.stdout.decode('utf-8'))


def _get_json(url: str) -> dict:
    """GET JSON com retentativa e fallback de pilha TLS (urllib -> curl)."""
    erros = []
    for tentativa in range(2):                 # urllib, 2 tentativas
        try:
            return _get_json_urllib(url)
        except urllib.error.HTTPError as e:
            corpo = ''
            try:
                corpo = e.read()[:300].decode('utf-8', 'replace')
            except Exception:                                  # noqa: BLE001
                pass
            erros.append(f'HTTP {e.code}' + (f' — {corpo[:220]}' if corpo else ''))
            break                              # HTTP definido: não readianta repetir
        except Exception as e:                                 # noqa: BLE001
            erros.append(f'{getattr(e, "reason", e)}')
            time.sleep(0.8)
    try:                                       # fallback: curl (TLS do sistema)
        return _get_json_curl(url)
    except Exception as e:                                     # noqa: BLE001
        erros.append(str(e)[:120])
    raise LookupError('; '.join(str(x) for x in erros[:3]))


# ---------------------------------------------------------------- tarifas ANEEL
# Base pública "Tarifas de aplicação das distribuidoras" (Dados Abertos ANEEL).
# Traz TE e TUSD SEM impostos (R$/MWh) por distribuidora, subgrupo e vigência —
# exatamente o formato que o config guarda. É a fonte única p/ atualizar todas
# as concessionárias com a resolução mais recente.
ANEEL_RID = 'fcf2906c-7c32-4b9b-a637-054e7a5234f4'
# subgrupo -> (classe, subclasse) conforme a base da ANEEL
_ANEEL_CLASSE = {'B1': ('Residencial', 'Residencial'),
                 'B2': ('Rural', 'Não se aplica')}


def _num_aneel(s) -> float:
    """'310,85' (R$/MWh) -> 0.31085 (R$/kWh). Tolera separador de milhar."""
    return float(str(s).strip().replace('.', '').replace(',', '.')) / 1000.0


def buscar_tarifa_aneel(sigla: str, subgrupo: str = 'B1') -> dict:
    """TE/TUSD vigentes (sem impostos, R$/kWh) de uma distribuidora na ANEEL.

    `sigla` é o SigAgente da base (ex.: 'COPEL-DIS', 'EMS', 'ELETROPAULO').
    Pega a linha "Tarifa de Aplicação", modalidade Convencional, da classe do
    subgrupo, posto/detalhe/acessante "Não se aplica", com a vigência mais
    recente. Devolve {te, tusd, reh, vigencia, sigla, subgrupo}.
    """
    classe, subclasse = _ANEEL_CLASSE.get(subgrupo, _ANEEL_CLASSE['B1'])
    filtros = {'SigAgente': sigla, 'DscBaseTarifaria': 'Tarifa de Aplicação',
               'DscSubGrupo': subgrupo, 'DscModalidadeTarifaria': 'Convencional',
               'DscClasse': classe, 'DscSubClasse': subclasse,
               'DscDetalhe': 'Não se aplica', 'NomPostoTarifario': 'Não se aplica'}
    p = urllib.parse.urlencode({
        'resource_id': ANEEL_RID,
        'filters': json.dumps(filtros, ensure_ascii=False),
        'sort': 'DatInicioVigencia desc', 'limit': 1})
    data = _get_json('https://dadosabertos.aneel.gov.br/api/3/action/'
                     'datastore_search?' + p)
    recs = ((data.get('result') or {}).get('records')) or []
    if not recs:
        raise LookupError(f'ANEEL sem tarifa p/ {sigla} {subgrupo} (classe {classe})')
    x = recs[0]
    return {'te': _num_aneel(x['VlrTE']), 'tusd': _num_aneel(x['VlrTUSD']),
            'reh': (x.get('DscREH') or '').strip(),
            'vigencia': x.get('DatInicioVigencia', ''),
            'sigla': sigla, 'subgrupo': subgrupo}


# Base "Bandeiras tarifárias" (Dados Abertos ANEEL), recurso "Acionamento": uma
# linha por mês (DatCompetencia), com a bandeira acionada e o adicional em
# R$/MWh SEM impostos. Vale para o país inteiro (SIN).
ANEEL_BANDEIRA_RID = '0591b8f6-fe54-437b-b72b-1aa2efd46e42'


def buscar_bandeira_aneel(hoje=None) -> dict:
    """Bandeira tarifária acionada no mês de `hoje` (padrão: hoje).

    A ANEEL anuncia a bandeira do mês seguinte no fim do mês, então a linha
    mais recente pode ser a do mês que vem — pegamos a do mês corrente (ou a
    última anterior a ele) e devolvemos a seguinte, se já anunciada, em
    `proxima`. Devolve {bandeira, adicional (R$/kWh), competencia 'AAAA-MM',
    proxima}. `bandeira` vem no rótulo do config ('VERDE', 'VERMELHA P1'…)."""
    from datetime import date
    hoje = hoje or date.today()       # o app passa engine.hoje() (Brasília)
    mes = f'{hoje.year:04d}-{hoje.month:02d}'
    p = urllib.parse.urlencode({'resource_id': ANEEL_BANDEIRA_RID,
                                'sort': 'DatCompetencia desc', 'limit': 3})
    data = _get_json('https://dadosabertos.aneel.gov.br/api/3/action/'
                     'datastore_search?' + p)
    recs = ((data.get('result') or {}).get('records')) or []

    def _linha(x):
        return {'bandeira': ' '.join(str(x.get('NomBandeiraAcionada') or '')
                                     .upper().split()),
                'adicional': round(_num_aneel(x.get('VlrAdicionalBandeira') or '0'), 6),
                'competencia': str(x.get('DatCompetencia') or '')[:7]}
    linhas = [_linha(x) for x in recs if x.get('NomBandeiraAcionada')]
    atuais = [l for l in linhas if l['competencia'] <= mes]
    if not atuais:
        raise LookupError('ANEEL sem bandeira acionada para ' + mes)
    atual = max(atuais, key=lambda l: l['competencia'])
    futuras = [l for l in linhas if l['competencia'] > atual['competencia']]
    atual['proxima'] = min(futuras, key=lambda l: l['competencia']) if futuras else None
    return atual


def _num_bruto(s) -> float:
    """'20,45' -> 20.45 (sem dividir por mil — usado nas tarifas de DEMANDA)."""
    try:
        return float(str(s).strip().replace('.', '').replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0


def buscar_tarifa_aneel_a(sigla: str, subgrupo: str = 'A4',
                          modalidade: str = 'VERDE') -> dict:
    """Tarifas do GRUPO A (média tensão) de uma distribuidora, na ANEEL.

    Devolve TE e TUSD-energia por posto (R$/kWh) e a TUSD-demanda (R$/kW),
    todas SEM impostos, da vigência mais recente. A base separa as linhas por
    `NomPostoTarifario` (Ponta / Fora ponta / Não se aplica) e pela unidade
    (MWh = energia, kW = demanda) — então pedimos todas as linhas do subgrupo +
    modalidade e classificamos aqui, que é mais resistente a mudança de rótulo
    do que filtrar campo por campo.

    Nunca levanta para o chamador decidir o que é "não achei": se algum valor
    não vier, ele volta zero e a tela pede o número à mão (é o caminho
    recomendado — o grupo A tem componentes que variam por contrato).
    """
    mod = 'Azul' if (modalidade or '').strip().upper() == 'AZUL' else 'Verde'
    # DscDetalhe separa a tarifa NORMAL ('Não se aplica') das linhas especiais
    # do mesmo subgrupo: 'APE' (autoprodutor equiparado) e 'SCEE' (sistema de
    # compensação, cuja TE é outra — 0,03009 na COPEL contra 0,47555 da normal).
    # Sem este filtro a última linha da resposta vencia e a TE saía errada.
    filtros = {'SigAgente': sigla, 'DscBaseTarifaria': 'Tarifa de Aplicação',
               'DscSubGrupo': subgrupo.upper(),
               'DscModalidadeTarifaria': mod,
               'DscDetalhe': 'Não se aplica'}
    p = urllib.parse.urlencode({
        'resource_id': ANEEL_RID,
        'filters': json.dumps(filtros, ensure_ascii=False),
        'sort': 'DatInicioVigencia desc', 'limit': 200})
    data = _get_json('https://dadosabertos.aneel.gov.br/api/3/action/'
                     'datastore_search?' + p)
    recs = ((data.get('result') or {}).get('records')) or []
    if not recs:
        raise LookupError(f'ANEEL sem tarifa p/ {sigla} {subgrupo} {mod}')
    vig = max((x.get('DatInicioVigencia') or '') for x in recs)
    recs = [x for x in recs if (x.get('DatInicioVigencia') or '') == vig]
    out = {'te_ponta': 0.0, 'te_fora': 0.0, 'tusd_kwh_ponta': 0.0,
           'tusd_kwh_fora': 0.0, 'tusd_demanda': 0.0, 'tusd_demanda_p': 0.0}
    for x in recs:
        posto = (x.get('NomPostoTarifario') or '').strip().lower()
        unid = (x.get('DscUnidadeTerciaria') or '').strip().lower()
        # demanda: unidade em kW (ou, se o rótulo mudar, linha sem TE)
        demanda = unid.startswith('kw') or (unid == '' and
                                            _num_bruto(x.get('VlrTE')) == 0)
        if demanda:
            if posto.startswith('ponta'):
                out['tusd_demanda_p'] = _num_bruto(x.get('VlrTUSD'))
            else:            # 'fora ponta' (Azul) ou 'não se aplica' (Verde)
                out['tusd_demanda'] = _num_bruto(x.get('VlrTUSD'))
            continue
        if posto.startswith('ponta'):
            out['te_ponta'] = _num_aneel(x.get('VlrTE'))
            out['tusd_kwh_ponta'] = _num_aneel(x.get('VlrTUSD'))
        elif posto.startswith('fora'):
            out['te_fora'] = _num_aneel(x.get('VlrTE'))
            out['tusd_kwh_fora'] = _num_aneel(x.get('VlrTUSD'))
    out.update(sigla=sigla, subgrupo=subgrupo.upper(), modalidade=mod,
               vigencia=vig, reh=(recs[0].get('DscREH') or '').strip())
    return out


_UF_NOME = {'AC': 'ACRE', 'AL': 'ALAGOAS', 'AP': 'AMAPA', 'AM': 'AMAZONAS',
            'BA': 'BAHIA', 'CE': 'CEARA', 'DF': 'DISTRITO FEDERAL',
            'ES': 'ESPIRITO SANTO', 'GO': 'GOIAS', 'MA': 'MARANHAO',
            'MT': 'MATO GROSSO', 'MS': 'MATO GROSSO DO SUL',
            'MG': 'MINAS GERAIS', 'PA': 'PARA', 'PB': 'PARAIBA',
            'PR': 'PARANA', 'PE': 'PERNAMBUCO', 'PI': 'PIAUI',
            'RJ': 'RIO DE JANEIRO', 'RN': 'RIO GRANDE DO NORTE',
            'RS': 'RIO GRANDE DO SUL', 'RO': 'RONDONIA', 'RR': 'RORAIMA',
            'SC': 'SANTA CATARINA', 'SP': 'SAO PAULO', 'SE': 'SERGIPE',
            'TO': 'TOCANTINS'}


def geocodificar(cidade: str, uf: str = '') -> dict:
    """Nome da cidade -> {nome, uf, lat, lon}. Prioriza resultados no Brasil
    e, com `uf` (sigla), os do estado."""
    q = urllib.parse.quote(cidade.strip())
    data = _get_json('https://geocoding-api.open-meteo.com/v1/search'
                     f'?name={q}&count=10&language=pt&format=json')
    resultados = data.get('results') or []
    if not resultados:
        raise LookupError(f'Cidade não encontrada: {cidade!r}')
    br = [r for r in resultados if r.get('country_code') == 'BR']
    if uf and br:
        est = _UF_NOME.get(uf.upper(), '')
        br = [r for r in br
              if _sem_acento(r.get('admin1', '')) == est] or br
    r = (br or resultados)[0]
    return dict(nome=r['name'], uf=r.get('admin1', ''),
                lat=r['latitude'], lon=r['longitude'])


_INPE = None                       # tabela do Atlas, carregada uma vez
_INPE_RAIO_KM = 30.0               # sede mais próxima aceita (distritos)


def _sem_acento(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.upper().replace("'", ' ').replace('-', ' ').split())


def _tabela_inpe() -> list:
    global _INPE
    if _INPE is None:
        arq = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'assets', 'irradiacao_inpe.json')
        try:
            with open(arq, encoding='utf-8') as f:
                _INPE = json.load(f)['municipios']
        except (OSError, ValueError, KeyError):
            _INPE = []
    return _INPE


def _separar_uf(cidade: str) -> tuple:
    """'Maringá - PR' / 'Maringá/PR' / 'Maringá, PR' -> ('Maringá', 'PR')."""
    s = str(cidade or '').strip()
    for sep in (' - ', '/', ',', '-'):
        if sep in s:
            nome, uf = s.rsplit(sep, 1)
            if len(uf.strip()) == 2 and uf.strip().isalpha():
                return nome.strip(), uf.strip().upper()
    return s, ''


def _resposta_inpe(m: list, obs: str = '') -> dict:
    nome, uf, lat, lon, mensal = m
    media = round(sum(mensal) / 12.0 / 1000.0, 2)
    return dict(cidade=nome, uf=uf, lat=lat, lon=lon,
                mensal=[float(v) for v in mensal],
                media_dia_kwh=media, ghi_dia_kwh=media,
                fonte='INPE — Atlas Brasileiro de Energia Solar 2017 (CRESESB)',
                obs=obs)


def _irradiacao_inpe(cidade: str) -> dict | None:
    """Procura a cidade na tabela do INPE (sem internet). None = não achou
    pelo nome. Nome repetido em vários estados sem UF -> pede a UF."""
    tab = _tabela_inpe()
    if not tab:
        return None
    nome, uf = _separar_uf(cidade)
    alvo = _sem_acento(nome)
    achados = [m for m in tab if _sem_acento(m[0]) == alvo
               and (not uf or m[1] == uf)]
    if len(achados) == 1:
        return _resposta_inpe(achados[0])
    if len(achados) > 1:
        ufs = ', '.join(sorted(m[1] for m in achados))
        raise LookupError(f'Há {len(achados)} cidades "{nome}" ({ufs}) — '
                          f'informe a UF, ex.: "{nome} - {achados[0][1]}".')
    return None


def _inpe_mais_proxima(lat: float, lon: float) -> tuple:
    """Sede municipal mais próxima do ponto -> (município, distância km)."""
    import math
    melhor, dmin = None, float('inf')
    for m in _tabela_inpe():
        dy = (m[2] - lat) * 111.2
        dx = (m[3] - lon) * 111.2 * math.cos(math.radians(lat))
        d = math.hypot(dx, dy)
        if d < dmin:
            melhor, dmin = m, d
    return melhor, dmin


def buscar_irradiacao(cidade: str) -> dict:
    """Irradiação global HORIZONTAL média mensal (Wh/m²/dia) da cidade.

    Ordem (a mais confiável primeiro):
      1. **INPE** — Atlas Brasileiro de Energia Solar 2017, sede municipal
         (`assets/irradiacao_inpe.json`, gerado por ferramentas/
         irradiacao_inpe.py). É a base do SunData/CRESESB e funciona SEM
         internet. Maringá: 4,89 kWh/m²/dia, igual ao CRESESB.
      2. Nome não achado (distrito, grafia) → localiza pela internet e usa a
         sede do INPE mais próxima, até `_INPE_RAIO_KM`.
      3. Só então a **NASA POWER** (ALLSKY_SFC_SW_DWN), grade de ~50 km —
         em Maringá dá 5,02, 2,7 % acima do INPE (menos conservadora).

    Plano HORIZONTAL de propósito: é o lado conservador (telhado real raramente
    está no ângulo e na orientação ideais) e é a convenção dos perfis da
    planilha. A irradiação vem BRUTA: as perdas entram UMA vez só, pelo
    `performance_ratio` na geração (perda = 1 − PR). Até out/2026 aqui se
    descontava também uma "perda" de 25 %, que somada ao PR contava as perdas
    em dobro.

    Retorna {cidade, uf, lat, lon, mensal:[12], media_dia_kwh, ghi_dia_kwh,
    fonte, obs} (`media_dia_kwh` = `ghi_dia_kwh`, por compatibilidade).
    """
    r = _irradiacao_inpe(cidade)
    if r:
        return r
    nome, uf = _separar_uf(cidade)
    loc = geocodificar(nome, uf)
    if _tabela_inpe():
        m, d = _inpe_mais_proxima(loc['lat'], loc['lon'])
        if m and d <= _INPE_RAIO_KM:
            return _resposta_inpe(
                m, f'"{cidade}" não está na tabela; usada a sede mais '
                   f'próxima, {m[0]}/{m[1]} ({d:.0f} km)')
    url = ('https://power.larc.nasa.gov/api/temporal/climatology/point'
           '?parameters=ALLSKY_SFC_SW_DWN&community=RE'
           f"&longitude={loc['lon']}&latitude={loc['lat']}&format=JSON")
    url = ('https://power.larc.nasa.gov/api/temporal/climatology/point'
           '?parameters=ALLSKY_SFC_SW_DWN&community=RE'
           f"&longitude={loc['lon']}&latitude={loc['lat']}&format=JSON")
    data = _get_json(url)
    par = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
    ordem = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
             'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    ghi_kwh = [float(par[m]) for m in ordem]             # kWh/m²/dia (bruto)
    mensal = [round(v * 1000.0, 1) for v in ghi_kwh]     # Wh/m²/dia
    media = round(sum(ghi_kwh) / 12.0, 2)
    return dict(cidade=loc['nome'], uf=loc['uf'], lat=loc['lat'],
                lon=loc['lon'], mensal=mensal,
                media_dia_kwh=media, ghi_dia_kwh=media,
                fonte='NASA POWER', obs='fora da tabela do INPE')


def buscar_cep(cep: str) -> dict:
    """CEP -> {logradouro, bairro, cidade, uf} via ViaCEP."""
    dig = ''.join(ch for ch in cep if ch.isdigit())
    if len(dig) != 8:
        raise ValueError('CEP deve ter 8 dígitos.')
    data = _get_json(f'https://viacep.com.br/ws/{dig}/json/')
    if data.get('erro'):
        raise LookupError('CEP não encontrado.')
    return dict(logradouro=data.get('logradouro', ''),
                bairro=data.get('bairro', ''),
                cidade=data.get('localidade', ''), uf=data.get('uf', ''))


# --------------------------------------------------------------- site COPEL
# O painel de tarifas do site da COPEL é um Power BI embutido (não raspável de
# forma confiável), então as TARIFAS ficam numa tabela local editável no
# config.json. Do site raspamos só o que é HTML de verdade:
#   * a RESOLUÇÃO/VIGÊNCIA atual (página de tarifas) — para avisar quando a
#     tabela local ficar desatualizada;
#   * o ICMS vigente (página de tributos) — para conferir as alíquotas.

def _get_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get('Content-Encoding', '') == 'gzip':
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return raw.decode('utf-8', 'replace')


def vigencia_copel(url: str) -> dict:
    """Lê da página de tarifas da COPEL a resolução vigente e o período.

    Ex.: 'Resolução Homologatória 3.592/2026 ... em vigor no período de
    24 de junho de 2026 a 23 de junho de 2027'.
    """
    import re
    html = _get_html(url)
    texto = re.sub(r'<[^>]+>', ' ', html)
    texto = re.sub(r'\s+', ' ', texto)
    m_res = re.search(r'Resolu[çc][ãa]o Homologat[óo]ria\s*([\d\.]+/\d{4})',
                      texto, re.I)
    m_vig = re.search(
        r'per[íi]odo de\s*(\d{1,2} de \w+ de \d{4})\s*a\s*'
        r'(\d{1,2} de \w+ de \d{4})', texto, re.I)
    m_ef = re.search(r'efeito m[ée]dio de\s*([\d,]+%)', texto, re.I)
    if not m_res:
        raise LookupError('não achei a resolução na página da COPEL')
    return dict(resolucao='REH ' + m_res.group(1),
                vigencia=(f'{m_vig.group(1)} a {m_vig.group(2)}'
                          if m_vig else ''),
                efeito_medio=(m_ef.group(1) if m_ef else ''))


def icms_copel(url: str) -> dict:
    """Lê da página de tributos da COPEL as alíquotas de ICMS vigentes.

    Heurística robusta a mudanças de redação: coleta os percentuais citados
    perto de menções a ICMS/energia (faixa plausível 10–30%); havendo dois
    valores distintos, o menor é o rural (que sempre tem desconto no PR).
    """
    import re
    html = _get_html(url)
    texto = re.sub(r'<[^>]+>', ' ', html)
    texto = re.sub(r'\s+', ' ', texto)
    pcts = []
    for m in re.finditer(r'(\d{1,2})\s*%', texto):
        p = int(m.group(1))
        ctx = texto[max(0, m.start() - 160):m.end() + 160].lower()
        if 10 <= p <= 30 and ('icms' in ctx or 'energia el' in ctx
                              or 'rural' in ctx):
            pcts.append(p / 100.0)
    if not pcts:
        raise LookupError('não achei alíquotas de ICMS na página da COPEL')
    unicos = sorted(set(pcts))
    if len(unicos) == 1:
        return {'icms': unicos[0]}
    return {'icms': unicos[-1], 'icms_rural': unicos[0]}
