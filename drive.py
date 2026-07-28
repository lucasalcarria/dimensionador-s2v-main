# -*- coding: utf-8 -*-
"""
Integração opcional com o Google Drive (OAuth) — envia as propostas para uma
pasta do Drive, para ficarem acessíveis no celular pelo app do Drive.

Fluxo (sem dependências extras — só urllib, como o online.py):

  1. `google_oauth.json`  — credencial "App para computador" baixada do Google
     Cloud (fica na pasta do programa; NÃO é versionada).
  2. Autorização única no navegador do PC:
        auth_url()  →  usuário aprova  →  /oauth2/callback  →  trocar_codigo()
     guarda o refresh token em `google_token.json`.
  3. Depois disso, `_access_token()` renova sozinho quando expira, e as funções
     `pasta_por_caminho()` / `enviar_arquivo()` gravam no Drive.

Tudo é tolerante a falha: se o Drive estiver fora do ar, quem chama trata o erro
e o programa segue salvando localmente.
"""
from __future__ import annotations
import gzip
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import engine

# escopo: 'drive' (achar a pasta ORÇAMENTOS pelo nome + criar/enviar) e o e-mail
# só para mostrar "conectado como…". Tudo dentro do Drive do próprio usuário.
ESCOPO = ('https://www.googleapis.com/auth/drive '
          'https://www.googleapis.com/auth/userinfo.email openid')
PASTA_MIME = 'application/vnd.google-apps.folder'
TIMEOUT = 30
_UA = {'User-Agent': 'DimensionadorS2V/1.0'}


def _arq(nome: str) -> str:
    return os.path.join(engine.dir_execucao(), nome)


def caminho_credencial() -> str:
    return _arq('google_oauth.json')


def caminho_token() -> str:
    return _arq('google_token.json')


def tem_credencial() -> bool:
    return os.path.exists(caminho_credencial())


def conectado() -> bool:
    try:
        with open(caminho_token(), encoding='utf-8') as f:
            return bool(json.load(f).get('refresh_token'))
    except (OSError, ValueError):
        return False


def _cred() -> dict:
    with open(caminho_credencial(), encoding='utf-8') as f:
        d = json.load(f)
    return d.get('installed') or d.get('web') or {}


# --------------------------------------------------------------- HTTP
def _http(url: str, *, data=None, headers=None, method=None) -> bytes:
    h = dict(_UA)
    h['Accept-Encoding'] = 'gzip'
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            if resp.headers.get('Content-Encoding', '') == 'gzip':
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            return raw
    except urllib.error.HTTPError as e:
        corpo = ''
        try:
            raw = e.read()
            if e.headers.get('Content-Encoding', '') == 'gzip':
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            corpo = raw.decode('utf-8', 'replace')
        except Exception:                                      # noqa: BLE001
            pass
        raise RuntimeError(f'Google {e.code}: {corpo[:400]}') from None


def _post_form(url: str, campos: dict) -> dict:
    dados = urllib.parse.urlencode(campos).encode()
    raw = _http(url, data=dados,
                headers={'Content-Type': 'application/x-www-form-urlencoded'})
    return json.loads(raw.decode('utf-8'))


# --------------------------------------------------------------- OAuth
def auth_url(redirect_uri: str) -> str:
    """URL da tela de consentimento do Google (autorização única)."""
    c = _cred()
    p = {'client_id': c['client_id'], 'redirect_uri': redirect_uri,
         'response_type': 'code', 'scope': ESCOPO,
         'access_type': 'offline', 'prompt': 'consent',
         'include_granted_scopes': 'true'}
    return c.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth') \
        + '?' + urllib.parse.urlencode(p)


def trocar_codigo(code: str, redirect_uri: str) -> dict:
    """Troca o `code` do callback pelos tokens e grava google_token.json."""
    c = _cred()
    tok = _post_form(c['token_uri'], {
        'code': code, 'client_id': c['client_id'],
        'client_secret': c['client_secret'], 'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'})
    if 'refresh_token' not in tok:
        raise RuntimeError('O Google não devolveu refresh_token. Revogue o '
                           'acesso do app na sua conta e conecte de novo.')
    dados = {'refresh_token': tok['refresh_token'],
             'access_token': tok.get('access_token', ''),
             'expira_em': time.time() + int(tok.get('expires_in', 3600)) - 60,
             'email': _buscar_email(tok.get('access_token', ''))}
    _salvar_token(dados)
    return dados


def _salvar_token(dados: dict) -> None:
    with open(caminho_token(), 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def _ler_token() -> dict:
    with open(caminho_token(), encoding='utf-8') as f:
        return json.load(f)


def desconectar() -> None:
    try:
        os.remove(caminho_token())
    except OSError:
        pass


def _buscar_email(access_token: str) -> str:
    if not access_token:
        return ''
    try:
        raw = _http('https://openidconnect.googleapis.com/v1/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'})
        return json.loads(raw.decode('utf-8')).get('email', '')
    except Exception:                                          # noqa: BLE001
        return ''


def email_conectado() -> str:
    try:
        return _ler_token().get('email', '')
    except (OSError, ValueError):
        return ''


def _access_token() -> str:
    """Token de acesso válido; renova pelo refresh token quando expira."""
    t = _ler_token()
    if t.get('access_token') and time.time() < t.get('expira_em', 0):
        return t['access_token']
    c = _cred()
    novo = _post_form(c['token_uri'], {
        'refresh_token': t['refresh_token'], 'client_id': c['client_id'],
        'client_secret': c['client_secret'], 'grant_type': 'refresh_token'})
    t['access_token'] = novo['access_token']
    t['expira_em'] = time.time() + int(novo.get('expires_in', 3600)) - 60
    _salvar_token(t)
    return t['access_token']


# --------------------------------------------------------------- Drive API
def _api(url: str, *, data=None, method=None, content_type=None) -> dict:
    h = {'Authorization': f'Bearer {_access_token()}'}
    if content_type:
        h['Content-Type'] = content_type
    raw = _http(url, data=data, headers=h, method=method)
    return json.loads(raw.decode('utf-8')) if raw else {}


def _q_escape(s: str) -> str:
    return s.replace('\\', '\\\\').replace("'", "\\'")


def _achar_pasta(nome: str, parent_id: str) -> str | None:
    q = (f"name = '{_q_escape(nome)}' and '{parent_id}' in parents "
         f"and mimeType = '{PASTA_MIME}' and trashed = false")
    url = ('https://www.googleapis.com/drive/v3/files?'
           + urllib.parse.urlencode({'q': q, 'fields': 'files(id,name)',
                                     'spaces': 'drive', 'pageSize': 1}))
    fs = _api(url).get('files') or []
    return fs[0]['id'] if fs else None


def _criar_pasta(nome: str, parent_id: str) -> str:
    corpo = json.dumps({'name': nome, 'mimeType': PASTA_MIME,
                        'parents': [parent_id]}).encode()
    return _api('https://www.googleapis.com/drive/v3/files?fields=id',
                data=corpo, method='POST',
                content_type='application/json; charset=UTF-8')['id']


def _partes(caminho: str) -> list[str]:
    """Quebra um caminho tipo 'S2V ENGENHARIA/ORÇAMENTOS' em ['S2V …','ORÇ…']."""
    return [p for p in re.split(r'[\\/]+', caminho or '') if p.strip()]


def pasta_por_caminho(partes: list[str], parent_id: str = 'root') -> str:
    """Garante que exista a cadeia de pastas e devolve o id da última (cria o
    que faltar). Ex.: ['S2V ENGENHARIA','ORÇAMENTOS','João','Cliente','7,44 …']."""
    atual = parent_id
    for nome in partes:
        nome = (nome or '').strip()
        if not nome:
            continue
        achado = _achar_pasta(nome, atual)
        atual = achado or _criar_pasta(nome, atual)
    return atual


def _achar_por_caminho(partes: list[str], parent_id: str = 'root') -> str | None:
    """Como pasta_por_caminho, mas NÃO cria nada — devolve None se faltar."""
    atual = parent_id
    for nome in partes:
        nome = (nome or '').strip()
        if not nome:
            continue
        atual = _achar_pasta(nome, atual)
        if not atual:
            return None
    return atual


def _achar_arquivo(nome: str, parent_id: str) -> str | None:
    q = (f"name = '{_q_escape(nome)}' and '{parent_id}' in parents "
         f"and trashed = false")
    url = ('https://www.googleapis.com/drive/v3/files?'
           + urllib.parse.urlencode({'q': q, 'fields': 'files(id)',
                                     'spaces': 'drive', 'pageSize': 1}))
    fs = _api(url).get('files') or []
    return fs[0]['id'] if fs else None


def enviar_arquivo(parent_id: str, nome: str, dados: bytes,
                   mimetype: str) -> str:
    """Cria (ou atualiza, se já existir com o mesmo nome) um arquivo na pasta."""
    fid = _achar_arquivo(nome, parent_id)
    bound = '===s2v_boundary==='
    meta = {'name': nome}
    if not fid:
        meta['parents'] = [parent_id]
    corpo = (f'--{bound}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'
             + json.dumps(meta) + f'\r\n--{bound}\r\n'
             + f'Content-Type: {mimetype}\r\n\r\n').encode() \
        + dados + f'\r\n--{bound}--\r\n'.encode()
    if fid:
        url = (f'https://www.googleapis.com/upload/drive/v3/files/{fid}'
               '?uploadType=multipart&fields=id')
        metodo = 'PATCH'
    else:
        url = ('https://www.googleapis.com/upload/drive/v3/files'
               '?uploadType=multipart&fields=id')
        metodo = 'POST'
    return _api(url, data=corpo, method=metodo,
                content_type=f'multipart/related; boundary={bound}')['id']


def listar_subpastas(base_caminho: str) -> list[str]:
    """Nomes das pastas dentro da pasta base (ex.: os consultores em ORÇAMENTOS).
    Aceita caminho com barras ('S2V ENGENHARIA/ORÇAMENTOS'). [] se não existir."""
    base_id = _achar_por_caminho(_partes(base_caminho))
    if not base_id:
        return []
    q = (f"'{base_id}' in parents and mimeType = '{PASTA_MIME}' "
         f"and trashed = false")
    url = ('https://www.googleapis.com/drive/v3/files?'
           + urllib.parse.urlencode({'q': q, 'fields': 'files(name)',
                                     'spaces': 'drive', 'pageSize': 200,
                                     'orderBy': 'name'}))
    return [f['name'] for f in (_api(url).get('files') or [])]


def enviar_projeto(base: str, consultor: str, cliente: str, projeto: str,
                   arquivos: list[tuple[str, bytes, str]]) -> str:
    """Grava os arquivos de um projeto em base/<consultor>/<cliente>/<projeto>/.
    `base` pode ser um caminho ('S2V ENGENHARIA/ORÇAMENTOS'). Devolve o id da
    pasta do projeto. `arquivos` = [(nome, bytes, mimetype)]."""
    pid = pasta_por_caminho(_partes(base) + [consultor, cliente, projeto])
    for nome, dados, mime in arquivos:
        enviar_arquivo(pid, nome, dados, mime)
    return pid
