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


def geocodificar(cidade: str) -> dict:
    """Nome da cidade -> {nome, uf, lat, lon}. Prioriza resultados no Brasil."""
    q = urllib.parse.quote(cidade.strip())
    data = _get_json('https://geocoding-api.open-meteo.com/v1/search'
                     f'?name={q}&count=5&language=pt&format=json')
    resultados = data.get('results') or []
    if not resultados:
        raise LookupError(f'Cidade não encontrada: {cidade!r}')
    br = [r for r in resultados if r.get('country_code') == 'BR']
    r = (br or resultados)[0]
    return dict(nome=r['name'], uf=r.get('admin1', ''),
                lat=r['latitude'], lon=r['longitude'])


def buscar_irradiacao(cidade: str) -> dict:
    """Irradiação média mensal (Wh/m²/dia) para a cidade, via NASA POWER.

    Retorna {cidade, uf, lat, lon, mensal:[12 valores], media_dia_kwh}.
    Os valores ficam na mesma unidade dos perfis da planilha (Wh/m²/dia),
    prontos para usar como 'irradiação customizada'.
    """
    loc = geocodificar(cidade)
    url = ('https://power.larc.nasa.gov/api/temporal/climatology/point'
           '?parameters=ALLSKY_SFC_SW_DWN&community=RE'
           f"&longitude={loc['lon']}&latitude={loc['lat']}&format=JSON")
    data = _get_json(url)
    par = data['properties']['parameter']['ALLSKY_SFC_SW_DWN']
    ordem = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
             'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    mensal_kwh = [float(par[m]) for m in ordem]          # kWh/m²/dia
    mensal = [round(v * 1000.0, 1) for v in mensal_kwh]  # Wh/m²/dia
    media = sum(mensal_kwh) / 12.0
    return dict(cidade=loc['nome'], uf=loc['uf'], lat=loc['lat'],
                lon=loc['lon'], mensal=mensal,
                media_dia_kwh=round(media, 2))


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
