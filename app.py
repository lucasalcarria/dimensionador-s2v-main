# -*- coding: utf-8 -*-
"""
Dimensionador S2V — servidor local.

Execute `python app.py` (ou o atalho iniciar.bat no Windows). O navegador
abre sozinho em http://127.0.0.1:8177. Tudo roda na sua máquina; internet é
usada apenas se você clicar em "buscar irradiação" ou "buscar CEP".
"""
from __future__ import annotations
import os
import re
import threading
import webbrowser
import json

from flask import (Flask, jsonify, redirect, render_template,
                   render_template_string, request, send_file,
                   send_from_directory, session)

import engine
import proposta
import drive

BASE = os.path.dirname(os.path.abspath(__file__))
PROPOSTAS = os.path.join(engine.dir_execucao(), 'propostas')
CLIENTES = os.path.join(engine.dir_execucao(), 'clientes')
PORTA = 8177

app = Flask(__name__)


# ------------------------------------------------------------------ acesso
# Login é OPCIONAL: só é exigido quando existe uma senha. A senha e a chave de
# sessão ficam em `acesso.json` (NÃO versionado), fora do config.json (que é
# versionado) — assim a senha nunca vaza no Git. Também aceita as variáveis de
# ambiente S2V_SENHA / S2V_SECRET (úteis na nuvem). Sem senha, o uso local segue
# sem pedir nada.
def _acesso_path() -> str:
    return os.path.join(engine.dir_execucao(), 'acesso.json')


def _ler_acesso() -> dict:
    try:
        with open(_acesso_path(), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _salvar_acesso(dados: dict) -> None:
    with open(_acesso_path(), 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def _senha_acesso() -> str:
    return (os.environ.get('S2V_SENHA')
            or _ler_acesso().get('senha') or '').strip()


def _obter_secret() -> str:
    """Chave de sessão estável: env, senão acesso.json; cria e guarda se faltar
    (para o login não cair a cada reinício do programa)."""
    s = os.environ.get('S2V_SECRET')
    if s:
        return s
    ac = _ler_acesso()
    if not ac.get('secret'):
        ac['secret'] = os.urandom(24).hex()
        try:
            _salvar_acesso(ac)
        except OSError:
            pass
    return ac['secret']


app.secret_key = _obter_secret()


# ------------------------------------------------------------------ papéis
# Dois níveis de acesso: ADMIN (a senha de sempre, vê tudo) e CONSULTOR (entra
# com nome + senha próprios, guardados em acesso.json → 'consultores'). O
# consultor não vê custos/margem nem edita pré-definições; só monta a proposta a
# partir dos PACOTES prontos do admin. Sem senha de admin (uso local), não há
# login e todo mundo age como admin.
def _consultores() -> list:
    """Lista [{nome, senha}] cadastrada pelo admin (acesso.json)."""
    return _ler_acesso().get('consultores') or []


def _achar_consultor(nome: str, senha: str):
    """Devolve o nome oficial do consultor se nome+senha baterem, senão None."""
    import hmac
    nome = (nome or '').strip()
    for c in _consultores():
        if (c.get('nome') or '').strip().lower() == nome.lower() and \
           hmac.compare_digest(str(c.get('senha') or ''), senha or ''):
            return (c.get('nome') or '').strip()
    return None


def _papel() -> str:
    """'admin' ou 'consultor'. Sem senha de admin (local), tudo é admin."""
    if not _senha_acesso():
        return 'admin'
    return session.get('papel') or 'admin'


def _eh_consultor() -> bool:
    return _papel() == 'consultor'


def _rota_admin(req) -> bool:
    """Rotas que só o ADMIN pode acessar (o consultor recebe 403/redirect)."""
    p, m = req.path, req.method
    if p == '/api/config':                      # ler ou gravar pré-definições
        return True
    if p in ('/api/imagens-padrao', '/api/atualizar-tarifa',
             '/api/wallbox/fotos-padrao',
             '/api/drive/desconectar') and m == 'POST':
        return True
    if p == '/api/aneel-tarifa-a':              # tarifas do grupo A: só admin
        return True
    # carregador veicular (/wallbox): aba inteira só do admin — pedido do usuário
    if p == '/wallbox' or p.startswith('/api/wallbox/'):
        return True
    if p in ('/api/resumos-salvos', '/api/importar-resumo'):
        return True                             # importar projeto: só admin
    if p.startswith('/oauth2/'):                # conectar Google Drive
        return True
    return False


# caminhos liberados sem login (a própria tela de login e os estáticos)
_LIVRE = {'/login', '/logo.png', '/manifest.webmanifest', '/sw.js', '/qr.png',
          '/favicon.ico'}


@app.before_request
def _exige_login():
    senha = _senha_acesso()
    if not senha:                                   # sem senha => sem login
        return None
    if session.get('auth') is True:
        # logado: o consultor ainda é barrado nas rotas de administração
        if _eh_consultor() and _rota_admin(request):
            if request.path.startswith('/api/') or \
               request.path.startswith('/oauth2/'):
                return jsonify(ok=False,
                               erro='Sem permissão (acesso de consultor).'), 403
            return redirect('/')
        return None
    p = request.path
    if p in _LIVRE or p.startswith('/icons/'):
        return None
    if p.startswith('/api/'):
        return jsonify(ok=False, erro='sessão expirada — faça login'), 401
    return redirect('/login')


_LOGIN_HTML = """<!doctype html><meta charset=utf-8>
<title>Entrar — Dimensionador S2V</title>
<meta name=viewport content="width=device-width, initial-scale=1">
<link rel="icon" href="/icons/icon-192.png?v=2">
<link rel="apple-touch-icon" href="/icons/icon-192.png?v=2">
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;
justify-content:center;background:#0b1220;font-family:system-ui,Arial}
form{background:#101b28;border:1px solid #22303f;border-radius:14px;
padding:26px;width:300px;max-width:90vw;color:#e6edf3}
h1{font-size:16px;margin:0 0 4px}p{color:#8aa0b4;font-size:13px;margin:0 0 16px}
input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;
border:1px solid #22303f;background:#0b1220;color:#e6edf3;font-size:15px}
button{width:100%;margin-top:12px;padding:10px;border:0;border-radius:8px;
background:#1462ae;color:#fff;font-weight:600;font-size:15px;cursor:pointer}
.erro{color:#e57373;font-size:13px;margin-top:10px}</style>
<form method=post><h1>Dimensionador S2V</h1>
<p>Consultor: digite seu nome e senha. Administrador: deixe o nome em branco.</p>
<input name=usuario autofocus placeholder="nome do consultor (admin: em branco)"
 autocomplete="username" style="margin-bottom:10px">
<input type=password name=senha placeholder="senha" autocomplete="current-password">
<button>Entrar</button>
{% if erro %}<div class=erro>{{ erro }}</div>{% endif %}</form>"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    import hmac
    senha = _senha_acesso()
    if not senha:                                   # login desativado
        return redirect('/')
    erro = ''
    if request.method == 'POST':
        usuario = (request.form.get('usuario') or '').strip()
        digitada = request.form.get('senha', '')
        if not usuario:                             # ADMIN: só senha
            if hmac.compare_digest(digitada, senha):
                session['auth'] = True
                session['papel'] = 'admin'
                session.pop('consultor', None)
                session.permanent = True
                return redirect('/')
            erro = 'Senha incorreta.'
        else:                                       # CONSULTOR: nome + senha
            nome = _achar_consultor(usuario, digitada)
            if nome:
                session['auth'] = True
                session['papel'] = 'consultor'
                session['consultor'] = nome
                session.permanent = True
                return redirect('/')
            erro = 'Nome ou senha incorretos.'
    return render_template_string(_LOGIN_HTML, erro=erro)


@app.get('/logout')
def logout():
    session.clear()
    return redirect('/login')


def _pasta_base() -> str:
    """Pasta raiz onde os projetos são salvos. Por padrão a 'clientes/' local;
    se 'pasta_saida' estiver definido no config (ex.: uma pasta do Google Drive
    para Desktop), usa ela. Cai no local se o caminho configurado não existir."""
    destino = (engine.carregar_config().get('pasta_saida') or '').strip()
    if destino and os.path.isdir(os.path.dirname(destino) or destino):
        os.makedirs(destino, exist_ok=True)
        return destino
    os.makedirs(CLIENTES, exist_ok=True)
    return CLIENTES


def _clientes_dir() -> str:
    return _pasta_base()


# Pasta "de consultor" EXCLUSIVA dos orçamentos de carregador veicular: todo
# orçamento da aba /wallbox vai para ela, e o solar NUNCA usa (some da lista de
# consultores e o servidor recusa) — pedido do usuário. É o nome da pasta que já
# existe no Drive, no plural.
PASTA_WALLBOX = 'INSTALAÇÕES WALLBOX'


def _eh_pasta_wallbox(nome: str) -> bool:
    """Compara sem acento/caixa/espaços extras e aceita o singular — 'Instalacao
    wallbox' digitado no solar também é barrado."""
    import unicodedata
    n = unicodedata.normalize('NFKD', str(nome or ''))
    n = ' '.join(''.join(c for c in n if not unicodedata.combining(c)).upper().split())
    return n in ('INSTALACOES WALLBOX', 'INSTALACAO WALLBOX')


def _limpar_nome(txt: str, padrao: str) -> str:
    """Deixa um texto seguro para virar nome de pasta no Windows."""
    txt = re.sub(r'[\\/:*?"<>|]', ' ', str(txt or ''))
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt or padrao


def _nome_projeto(e: 'engine.Entradas', r: dict) -> str:
    """Rótulo da pasta do projeto, ex.: '7,44KWP ONGRID CHINT 5K 220V COLONIAL'."""
    kwp = engine.fmt_general(round(r['kwp'], 2)).replace('.', ',')
    conexao = re.sub(r'[\s-]+', '', (e.conexao or '').upper())
    invs = ' + '.join(
        f"{iv['marca'].upper()} {engine.fmt_general(iv['pot_kw'])}K "
        f"{iv['tensao']}V" for iv in e.lista_inversores())
    micro = ['MICRO'] if e.tem_micro() else []   # diferencia microinversor
    partes = [f'{kwp}KWP', conexao] + micro + [invs, (e.estrutura or '').upper()]
    return _limpar_nome(' '.join(p for p in partes if p), 'PROJETO')


def _pasta_projeto(e: 'engine.Entradas', r: dict, consultor: str = '') -> str:
    """<base>/<consultor>/<NOME>/<7,44KWP ONGRID …>/ — cria e devolve o caminho.
    O nível do consultor só entra quando informado (senão vai direto no cliente).
    """
    partes = [_pasta_base()]
    cons = _limpar_nome(consultor, '').strip()
    if cons:
        partes.append(cons)
    partes.append(_limpar_nome(e.nome, 'CLIENTE'))
    partes.append(_nome_projeto(e, r))
    pasta = os.path.join(*partes)
    os.makedirs(pasta, exist_ok=True)
    return pasta


# ------------------------------------------------------------------ helpers
def _f(v, padrao=0.0):
    """Converte número vindo da tela (aceita vírgula) — vazio vira `padrao`."""
    if v is None or v == '':
        return padrao
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace('.', '').replace(',', '.')
                 if re.match(r'^-?\d{1,3}(\.\d{3})+(,\d+)?$', str(v).strip())
                 else str(v).replace(',', '.'))


def _img_bytes(dataurl):
    """Converte um data URL ('data:image/png;base64,XXXX') vindo da tela em
    bytes. Devolve None se vazio ou inválido (o PDF só cobre o espaço)."""
    if not dataurl or not isinstance(dataurl, str):
        return None
    try:
        import base64
        if ',' in dataurl:
            dataurl = dataurl.split(',', 1)[1]
        return base64.b64decode(dataurl)
    except Exception:                                          # noqa: BLE001
        return None


# ---- fotos gravadas JUNTO da proposta (pasta do projeto) -----------------
# As imagens que foram para o PDF ficam na pasta do projeto como arquivos soltos
# (MODULO.png / INVERSOR.jpg …), NÃO dentro do DADOS.json — base64 no JSON
# incharia o arquivo. Ao importar o projeto elas voltam para a tela.
_IMG_MIME_EXT = {'image/png': '.png', 'image/jpeg': '.jpg',
                 'image/jpg': '.jpg', 'image/webp': '.webp',
                 'image/gif': '.gif'}
_IMG_EXT_MIME = {'.png': 'image/png', '.jpg': 'image/jpeg',
                 '.jpeg': 'image/jpeg', '.webp': 'image/webp',
                 '.gif': 'image/gif'}


def _img_ext(dataurl) -> str:
    """Extensão do arquivo a partir do cabeçalho do data URL (padrão .png)."""
    m = re.match(r'data:([\w/+.-]+)[;,]', str(dataurl or ''))
    return _IMG_MIME_EXT.get((m.group(1) if m else '').lower(), '.png')


# foto → nome do arquivo na pasta do projeto ('mobi' = a CLAMPER Mobi do
# orçamento de carregador veicular)
_IMG_BASE = {'modulo': 'MODULO', 'inversor': 'INVERSOR', 'mobi': 'MOBI'}


def _gravar_img_projeto(pasta: str, qual: str, dataurl):
    """Grava a foto usada no PDF na pasta do projeto. Devolve
    (nome, bytes, mime) — ou None quando não há imagem."""
    base = _IMG_BASE.get(qual, 'INVERSOR')
    for ext in _IMG_EXT_MIME:                    # limpa versões antigas
        velho = os.path.join(pasta, base + ext)
        if os.path.exists(velho):
            try:
                os.remove(velho)
            except OSError:
                pass
    dados = _img_bytes(dataurl)
    if not dados:
        return None
    nome = base + _img_ext(dataurl)
    with open(os.path.join(pasta, nome), 'wb') as f:
        f.write(dados)
    return nome, dados, _IMG_EXT_MIME.get(_img_ext(dataurl), 'image/png')


def _ler_imgs_projeto(pasta: str) -> dict:
    """Data URLs das fotos salvas na pasta do projeto, no mesmo formato que a
    tela usa ({'img_modulo': 'data:image/png;base64,…'})."""
    import base64
    out = {}
    for qual, base in _IMG_BASE.items():
        for ext, mime in _IMG_EXT_MIME.items():
            caminho = os.path.join(pasta, base + ext)
            if not os.path.isfile(caminho):
                continue
            try:
                with open(caminho, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('ascii')
            except OSError:
                break
            out['img_' + qual] = 'data:%s;base64,%s' % (mime, b64)
            break
    return out


# ---- imagens PADRÃO de módulo/inversor (fallback global) -----------------
# Ficam num arquivo de texto (o data URL inteiro) na pasta de dados
# (dir_execucao → bucket no Cloud Run), NUNCA no config.json versionado: são
# base64 grande e mudariam o arquivo a cada troca. Servem quando a UC não colar
# a foto no fluxo normal de geração.
_IMG_PADRAO = {'modulo': 'padrao_modulo.txt', 'inversor': 'padrao_inversor.txt',
               # carregador veicular: uma foto padrão por linha da CLAMPER Mobi
               'mobi_box': 'padrao_mobi_box.txt',
               'mobi_plug': 'padrao_mobi_plug.txt'}


def _caminho_img_padrao(qual: str) -> str:
    nome = _IMG_PADRAO.get(qual, 'padrao_inversor.txt')
    return os.path.join(engine.dir_execucao(), nome)


def _ler_img_padrao(qual: str):
    """Data URL salvo da imagem padrão do módulo/inversor, ou None."""
    try:
        with open(_caminho_img_padrao(qual), encoding='utf-8') as f:
            return f.read().strip() or None
    except OSError:
        return None


def _gravar_img_padrao(qual: str, dataurl) -> None:
    """Grava (ou apaga, se vazio) o data URL da imagem padrão."""
    caminho = _caminho_img_padrao(qual)
    if dataurl:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(str(dataurl))
    elif os.path.exists(caminho):
        os.remove(caminho)


# ----- imagens OPCIONAIS por pacote (num único arquivo, fora do config.json) -----
# Um pacote pode ter foto própria do módulo/inversor; se não tiver, a proposta
# usa a imagem PADRÃO. Guardadas por id estável em pacotes_imagens.json (data dir,
# gitignored) para não inchar o config.json versionado.
def _caminho_pac_imgs() -> str:
    return os.path.join(engine.dir_execucao(), 'pacotes_imagens.json')


def _ler_pac_imgs() -> dict:
    try:
        with open(_caminho_pac_imgs(), encoding='utf-8') as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def _salvar_pac_imgs(d: dict) -> None:
    with open(_caminho_pac_imgs(), 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)


def _ler_img_pacote(pid, qual: str):
    """Data URL da imagem do pacote (qual='modulo'|'inversor'), ou None."""
    if pid in (None, ''):
        return None
    return (_ler_pac_imgs().get(str(pid)) or {}).get(qual) or None


def _gravar_img_pacote(pid, qual: str, dataurl) -> None:
    """Grava/apaga a imagem de um pacote no arquivo único."""
    if pid in (None, ''):
        return
    d = _ler_pac_imgs()
    reg = d.setdefault(str(pid), {})
    if dataurl:
        reg[qual] = str(dataurl)
    else:
        reg.pop(qual, None)
    if not reg:                              # sem imagens: remove o registro
        d.pop(str(pid), None)
    _salvar_pac_imgs(d)


def _pode_admin() -> bool:
    """True quando quem está na sessão tem poderes de administrador.

    Usado para blindar recursos exclusivos do admin no SERVIDOR (esconder o
    campo na tela não é trava). Fora de uma requisição (testes, scripts) vale
    como admin, igual ao uso local sem senha.
    """
    try:
        return not _eh_consultor()
    except Exception:                                          # noqa: BLE001
        return True


def _regra_bool(valor, padrao: bool = True) -> bool:
    """Lê uma regra booleana vinda do front/JSON (True/'false'/0/…)."""
    if valor is None:
        return padrao
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() not in ('false', '0', 'nao', 'não', 'no', '')


def _fio_b_da_conc(nome) -> float | None:
    """Fio B (R$/MWh) cadastrado na concessionária, ou None."""
    try:
        v = (engine.carregar_config().get('concessionarias') or {}).get(
            (nome or '').strip()) or {}
        x = v.get('fio_b_rs_mwh')
        return float(x) if x else None
    except (ValueError, TypeError, AttributeError):
        return None


def _cfg_num(chave: str, padrao: float) -> float:
    """Número do config.json, com padrão quando a chave ainda não existe."""
    try:
        return float(engine.carregar_config().get(chave, padrao))
    except (ValueError, TypeError):
        return padrao


def _pr_do_payload(d: dict) -> float | None:
    """PR do projeto — SÓ o admin define (pedido do usuário). Consultor, vazio
    ou fora de 0,40–1,00 → None (= o PR das pré-definições)."""
    if not _pode_admin():
        return None
    v = d.get('performance_ratio')
    if v in (None, ''):
        return None
    v = _f(v)
    if v > 1.0:                     # digitado em % (75 → 0,75)
        v /= 100.0
    if not 0.40 <= v <= 1.0:
        raise ValueError(f'Performance ratio fora da faixa (0,40 a 1,00): {v}')
    return v


def _montar_entradas(d: dict, com_pacote: bool = True) -> engine.Entradas:
    if com_pacote:
        d = _aplicar_pacote(d)      # consultor: injeta equipamento+custos do pacote
    # padrão de segurança para TE/TUSD quando o campo vem vazio: o ÚLTIMO valor
    # da COPEL vindo da ANEEL (cache), em vez de um número fixo desatualizado.
    _cache = _ler_cache_tarifas().get('COPEL-DIS|B1') or {}
    _pte, _ptusd = _cache.get('te', 0.27575), _cache.get('tusd', 0.36667)
    # GRUPO A é exclusivo do ADMIN: para o consultor toda UC volta a ser grupo B
    # (a tela dele não mostra o campo, mas a trava de verdade é esta).
    _admin = _pode_admin()
    ucs = []
    for u in d.get('ucs', []):
        grupo = ((u.get('grupo') or 'B').strip().upper()
                 if _admin else 'B')
        grupo = 'A' if grupo == 'A' else 'B'
        ga = {}
        if grupo == 'A':                     # campos da fatura de média tensão
            ga = dict(
                subgrupo_a=(u.get('subgrupo_a') or 'A4').strip().upper(),
                modalidade_a=(u.get('modalidade_a') or 'VERDE').strip().upper(),
                consumos_ponta=[_f(x) for x in (u.get('consumos_ponta')
                                                or [0] * 12)],
                demanda_kw=_f(u.get('demanda_kw')),
                demanda_kw_p=_f(u.get('demanda_kw_p')),
                demanda_medida_kw=_f(u.get('demanda_medida_kw')),
                demanda_medida_kw_p=_f(u.get('demanda_medida_kw_p')),
                demanda_faturada_kw=_f(u.get('demanda_faturada_kw')),
                demanda_faturada_kw_p=_f(u.get('demanda_faturada_kw_p')),
                outros_rs=_f(u.get('outros_rs')),
                te_ponta=_f(u.get('te_ponta')),
                te_fora=_f(u.get('te_fora')),
                tusd_kwh_ponta=_f(u.get('tusd_kwh_ponta')),
                tusd_kwh_fora=_f(u.get('tusd_kwh_fora')),
                tusd_demanda=_f(u.get('tusd_demanda')),
                tusd_demanda_p=_f(u.get('tusd_demanda_p')),
                # TUSD-G: demanda de geração (GD1 e GD2). Vazia = calculada
                # pelo motor a partir da potência dos inversores.
                demanda_g_kw=_f(u.get('demanda_g_kw')),
                tusd_g_rs_kw=_f(u.get('tusd_g_rs_kw'),
                                _cfg_num('tusd_g_rs_kw', 7.88)),
                # fator de correção da ponta (vazio = relação das TEs)
                fator_ponta_manual=(None if u.get('fator_ponta_manual')
                                    in (None, '', 0)
                                    else _f(u.get('fator_ponta_manual'))))
        # usinas de GD que a UC já tinha ANTES deste orçamento (A e B).
        # Só o que é número interessa ao cálculo: os kWh injetados por mês.
        gds = []
        for g in (u.get('gds_existentes') or []):
            inj = _f(g.get('injetado_kwh'))
            if inj <= 0 and not (g.get('nome') or '').strip():
                continue
            # cada usina tem o SEU parecer de acesso, logo o seu prazo de
            # isenção de ICMS. Ausente = herda o estado declarado na UC.
            iso = g.get('isento_icms')
            gds.append({'nome': (g.get('nome') or '').strip(),
                        'kwp': _f(g.get('kwp')),
                        # kW de inversor desta usina (entra na TUSD-G)
                        'inversor_kw': _f(g.get('inversor_kw')),
                        'injetado_kwh': inj,
                        # geração REAL do mês (app de monitoramento). O medidor
                        # não vê o que foi gerado e consumido no mesmo instante.
                        'geracao_kwh': _f(g.get('geracao_kwh')),
                        'isento_icms': (None if iso is None
                                        else _regra_bool(iso, True))})
        ucs.append(engine.UC(
            grupo=grupo, gds_existentes=gds, **ga,
            tipo=(u.get('tipo') or '').strip(),
            ilum_publica=_f(u.get('ilum_publica')),
            ligacao=u.get('ligacao') or 'MONOFASICO',
            consumos=[_f(x) for x in (u.get('consumos') or [0] * 12)],
            te=_f(u.get('te'), _pte),             # R$/kWh SEM impostos
            tusd=_f(u.get('tusd'), _ptusd),       # R$/kWh SEM impostos
            icms=_f(u.get('icms'), 19.0) / 100.0,       # tela usa %
            cofins=_f(u.get('cofins'), 5.8) / 100.0,
            pis=_f(u.get('pis'), 1.26) / 100.0,
            pct_noturno=_f(u.get('pct_noturno'), 65.0) / 100.0,
            bandeira=u.get('bandeira') or 'VERDE',
            uc_numero=str(u.get('uc_numero') or '').strip(),
            gd=(u.get('gd') or 'GD2').strip().upper(),
            icms_te=_regra_bool(u.get('icms_te'), True),
            icms_tusd=_regra_bool(u.get('icms_tusd'), True),
            abat_tusd_inclui_icms=_regra_bool(u.get('abat_tusd_inclui_icms'), False),
            # Convênio ICMS 16/2015 (crédito devolve o ICMS da TE): vem da
            # concessionária, e a UC do grupo A pode sobrepor na tela.
            abat_te_inclui_icms=_regra_bool(u.get('abat_te_inclui_icms'), True),
            # Fio B da concessionária escolhida na UC (config). Sem
            # concessionária ou sem valor cadastrado, o motor usa o global.
            fio_b_rs_mwh=_fio_b_da_conc(u.get('conc')),
            # anos que ainda restam de isenção NESTE parecer de acesso
            isencao_icms_anos=(None if u.get('isencao_icms_anos') in (None, '')
                               else _f(u.get('isencao_icms_anos')))))
    while len(ucs) < 9:
        ucs.append(engine.UC())

    margem = d.get('margem_desejada')
    margem = None if margem in (None, '',) else _f(margem) / 100.0

    irr = d.get('irradiacao_customizada') or None
    if irr:
        irr = [_f(x) for x in irr]

    return engine.Entradas(
        nome=(d.get('nome') or '').strip(),
        endereco=(d.get('endereco') or '').strip(),
        numero=str(d.get('numero') or '').strip(),
        cidade=(d.get('cidade') or '').strip(),
        uc_numero=str(d.get('uc_numero') or '').strip(),
        ucs=ucs,
        qtd_modulos_kit=int(_f(d.get('qtd_modulos_kit'))),
        marca_inversor=(d.get('marca_inversor') or '').strip(),
        pot_inversor_kw=_f(d.get('pot_inversor_kw')),
        tensao_inversor=int(_f(d.get('tensao_inversor'), 220)),
        inversores=[{'marca': (iv.get('marca') or '').strip(),
                     'pot_kw': _f(iv.get('pot_kw')),
                     'tensao': int(_f(iv.get('tensao'), 220)),
                     'qtd': int(_f(iv.get('qtd'), 1)),
                     'micro': bool(iv.get('micro'))}
                    for iv in (d.get('inversores') or [])],
        custo_380v=_f(d.get('custo_380v')),
        valor_kit=_f(d.get('valor_kit')),
        conexao=(d.get('conexao') or 'HÍBRIDO').strip(),
        marca_modulo=(d.get('marca_modulo') or '').strip(),
        pot_modulo_w=_f(d.get('pot_modulo_w'), 620),
        estrutura=(d.get('estrutura') or 'FIBROCIMENTO').strip(),
        perfil_irradiacao=str(d.get('perfil_irradiacao') or '3.8'),
        irradiacao_customizada=irr,
        irradiacao_local=str(d.get('irradiacao_local') or '').strip() if irr else '',
        performance_ratio=_pr_do_payload(d),
        **_bandeira_do_payload(d),
        entrada=_f(d.get('entrada')),
        desloc=_f(d.get('desloc')),
        comissao_pct=_f(d.get('comissao_pct')) / 100.0,
        seguro_pct=_f(d.get('seguro_pct')) / 100.0,
        margem_desejada=margem,
        fin_taxa_mes=_f(d.get('fin_taxa_mes'), 1.99),
        fin_parcelas=int(_f(d.get('fin_parcelas'), 60)),
        cartao_taxa_pct=_f(d.get('cartao_taxa_pct'), 12.4),
        cartao_parcelas=int(_f(d.get('cartao_parcelas'), 12)),
        forma_parcela=(d.get('forma_parcela') or 'cartao').strip(),
        wp_manual=(None if d.get('wp_manual') in (None, '')
                   else _f(d.get('wp_manual'))),
        # VALOR FINAL fixo: para o consultor já foi blindado no _aplicar_pacote
        # (vem só do pacote); para o admin, é o que ele digitou na tela ou no kit.
        preco_venda_manual=(None if d.get('preco_venda_manual') in (None, '')
                            else _f(d.get('preco_venda_manual'))),
        mo_manual=(None if d.get('mo_manual') in (None, '')
                   else _f(d.get('mo_manual'))),
        material_manual=(None if d.get('material_manual') in (None, '')
                         else _f(d.get('material_manual'))),
        aliquota_manual=(None if d.get('aliquota_pct') in (None, '')
                         else _f(d.get('aliquota_pct')) / 100.0),
        tem_bateria=bool(d.get('tem_bateria')),
        bat_qtd=int(_f(d.get('bat_qtd'), 1)),
        bat_marca=(d.get('bat_marca') or '').strip(),
        bat_kwh=(None if d.get('bat_kwh') in (None, '')
                 else _f(d.get('bat_kwh'))),
        tem_stringbox=bool(d.get('tem_stringbox', True)),
        sb_qtd=int(_f(d.get('sb_qtd'), 1)),
        sb_marca=(d.get('sb_marca') or '').strip(),
        sb_es=(d.get('sb_es') or '').strip())


def _composicao(r: dict, m) -> list:
    """TODOS os itens que somam o custo, na ordem em que aparecem na planilha
    (PR!Q21:Y21 + PR!X25), cada um em R$ e em % do valor de venda. É a mesma
    soma de `r['custo_total']` — nada fica de fora, nem quando vale R$ 0,00."""
    venda = r['preco_venda'] or 0.0
    pct = lambda v: round(v / venda * 100, 1) if venda else 0.0
    auto = lambda v, a: ('auto: ' + m(a)) if abs(v - a) > 0.005 else ''
    itens = [
        ('Kit (módulos + inversores)', r['custo_kit'], ''),
        ('Mão de obra', r['custo_mo'], auto(r['custo_mo'], r['custo_mo_auto'])),
        ('Material extra', r['custo_material'],
         auto(r['custo_material'], r['custo_material_auto'])),
        ('Padrão de entrada', r['custo_entrada'], ''),
        ('Deslocamento', r['custo_desloc'], ''),
        # o adicional 380 V entra JUNTO do transformador (é o mesmo item de
        # custo para o cliente); a descrição do trafo continua na observação
        ('Transformador', r['custo_trafo'] + r['custo_380v'],
         r['trafo_desc'] or ''),
        ('Comissão', r['custo_comissao'], ''),
        ('Seguro', r['custo_seguro'], ''),
        ('Imposto', r['custo_imposto'],
         '%s%% s/ venda − kit' % engine.fmt_general(
             round(r['aliquota_usada'] * 100, 2)).replace('.', ',')),
    ]
    return [{'rotulo': rot, 'rs': m(v), 'pct': pct(v), 'obs': obs}
            for rot, v, obs in itens]


def _resumo(r: dict, cfg: dict) -> dict:
    br = cfg.get('formato_ptbr', True)
    m = lambda v: engine.moeda(v, br)
    venda = r['preco_venda'] or 0.0
    return dict(
        composicao=_composicao(r, m),
        custo_kit=m(r['custo_kit']), custo_desloc=m(r['custo_desloc']),
        custo_entrada=m(r['custo_entrada']), custo_380v=m(r['custo_380v']),
        custo_total_pct=(round(r['custo_total'] / venda * 100, 1)
                         if venda else 0.0),
        kwp=round(r['kwp'], 2),
        kwp_necessario=r['kwp_necessario'],
        modulos_sugeridos=r['modulos_sugeridos'],
        area_m2=round(r['area_m2'], 1),
        geracao_media=round(r['geracao_media'], 1),
        consumo_medio=round(r['consumo_medio'], 1),
        consumo_medido=round(r['consumo_medido_anual'] / 12.0, 1),
        autoconsumo_existente=round(r['autoconsumo_existente'], 1),
        compensacao_pct=round(r['compensacao'] * 100, 1),
        geracao_mensal=[round(v, 1) for v in r['geracao_mensal']],
        custo_mo=m(r['custo_mo']), custo_material=m(r['custo_material']),
        custo_trafo=m(r['custo_trafo']), trafo_desc=r['trafo_desc'],
        custo_imposto=m(r['custo_imposto']),
        custo_comissao=m(r['custo_comissao']), custo_seguro=m(r['custo_seguro']),
        custo_total=m(r['custo_total']),
        margem_usada_pct=round(r['margem_usada'] * 100, 2),
        preco_wp=round(r['preco_wp'], 4),
        preco_venda=m(r['preco_venda']), preco_venda_num=round(r['preco_venda'], 2),
        lucro_pct=round(r['lucro_pct'] * 100, 2), lucro_rs=m(r['lucro_rs']),
        fatura_sem=m(r['fatura_sem']), fatura_com=m(r['fatura_com']),
        economia_mensal=m(r['economia_mensal']),
        payback=r['textos']['payback_txt'],
        retorno_25=m(r['retorno_25']),
        parcela_fin=m(r['parcela_fin']),
        parcela_cartao=m(r['parcela_cartao']),
        cartao_parcelas=r['cartao_parcelas'],
        cartao_valor_credito=m(r['cartao_valor_credito']),
        custo_mo_auto=m(r['custo_mo_auto']),
        custo_material_auto=m(r['custo_material_auto']),
        aliquota_usada_pct=round(r['aliquota_usada'] * 100, 2),
        tarifas_cheias=[(round(t, 4) if t is not None else None)
                        for t in r['tarifas_cheias']],
        tem_grupo_a=bool(r.get('tem_grupo_a')),
        anos_isencao=r.get('anos_isencao'),
        economia_pos_isencao=(m(r['economia_pos_isencao'])
                              if r.get('economia_pos_isencao') is not None
                              else None),
        grupo_a=_resumo_grupo_a(r, m),
        textos=r['textos'])


def _resumo_grupo_a(r: dict, m) -> list:
    """Resumo por UC de média tensão (grupo A) para o painel da tela: o que é
    demanda (não abate), o que é energia e quanto foi compensado em cada posto."""
    out = []
    for i, d in enumerate(r.get('detalhes_uc') or []):
        if not d or d.get('grupo') != 'A':
            continue
        out.append(dict(
            uc=i + 1, modalidade=d['modalidade'], subgrupo=d['subgrupo'],
            consumo_ponta=round(d['consumo_ponta'], 1),
            consumo_fora=round(d['consumo_fora'], 1),
            demanda=m(d['demanda_rs']),
            energia_sem=m(d['consumo_sem_rs']), energia_com=m(d['consumo_com_rs']),
            compensado_ponta=round(d['compensado_ponta'], 0),
            compensado_fora=round(d['compensado_fora'], 0),
            autoconsumo=round(d['autoconsumo'], 0),
            autoconsumo_medido=bool(d['autoconsumo_medido']),
            autoconsumo_regra=d.get('autoconsumo_regra', 'pior_caso'),
            injetado=round(d['injetado'], 0),
            outros=m(d['outros_rs']),
            fator_ajuste=round(d['fator_ajuste'], 3),
            fator_cheia=round(d['fator_cheia'], 3),
            demanda_g_kw=round(d['demanda_g_kw'], 2),
            custo_g=m(d['custo_g']),
            tusd_g_cheia=round(d['tusd_g_cheia'], 4),
            injecao_existente=round(d['injecao_existente'], 0),
            tarifa_ponta=round(d['tarifa_ponta'], 5),
            tarifa_fora=round(d['tarifa_fora'], 5),
            fatura_sem=m(d['fatura_sem_uc']), fatura_com=m(d['total'])))
    return out


# ------------------------------------------------------------------ rotas
@app.get('/')
def index():
    cfg = engine.carregar_config()
    papel = _papel()
    pacotes = [_pacote_publico(p, i) for i, p in enumerate(_pacotes(cfg))]
    return render_template('index.html', cfg=cfg,
                           perfis=list(cfg['perfis_irradiacao'].keys()),
                           papel=papel,
                           consultor_nome=session.get('consultor', ''),
                           pacotes_pub=pacotes)


@app.get('/api/pacotes')
def api_pacotes():
    """Lista pública de pacotes (sem custos) — para o seletor do consultor."""
    try:
        cfg = engine.carregar_config()
        pacs = [_pacote_publico(p, i) for i, p in enumerate(_pacotes(cfg))]
        return jsonify(ok=True, pacotes=pacs)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


# ----------------------------------------------------------- solicitações
# O consultor pede uma cotação de kit ao admin (cliente + kWp desejado +
# telhado). Fica guardado em solicitacoes.json (data dir, gitignored) e o admin
# vê a lista/contador na tela (um "inbox", não push por e-mail).
def _caminho_solic() -> str:
    return os.path.join(engine.dir_execucao(), 'solicitacoes.json')


def _ler_solic() -> list:
    try:
        with open(_caminho_solic(), encoding='utf-8') as f:
            return json.load(f) or []
    except (OSError, ValueError):
        return []


def _salvar_solic(lst: list) -> None:
    with open(_caminho_solic(), 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False, indent=1)


@app.post('/api/solicitacoes')
def api_criar_solic():
    """O consultor (ou admin) registra um pedido de cotação de kit."""
    try:
        import secrets as _s
        d = request.get_json(force=True) or {}
        consultor = (session.get('consultor') if _eh_consultor()
                     else (d.get('consultor') or '')).strip() or '—'
        if not (d.get('telhado') or '').strip():
            raise ValueError('Selecione o telhado do cliente.')
        reg = {'id': 's' + _s.token_hex(4),
               'criada_em': engine.agora().strftime('%d/%m/%Y %H:%M'),
               'consultor': consultor,
               'cliente': (d.get('cliente') or '').strip(),
               'cidade': (d.get('cidade') or '').strip(),
               'telhado': (d.get('telhado') or '').strip(),
               'kwp': _f(d.get('kwp')),
               'consumo_medio': _f(d.get('consumo_medio')),
               'obs': (d.get('obs') or '').strip(),
               'status': 'pendente'}
        lst = _ler_solic()
        lst.append(reg)
        _salvar_solic(lst)
        return jsonify(ok=True, id=reg['id'])
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.get('/api/solicitacoes')
def api_listar_solic():
    """Admin vê todas; consultor vê só as suas. Devolve o total de pendentes."""
    try:
        lst = _ler_solic()
        if _eh_consultor():
            nome = (session.get('consultor') or '')
            lst = [s for s in lst if s.get('consultor') == nome]
        lst = list(reversed(lst))               # mais recentes primeiro
        pend = sum(1 for s in lst if s.get('status') != 'atendida')
        return jsonify(ok=True, solicitacoes=lst, pendentes=pend)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/solicitacoes/atender')
def api_atender_solic():
    """Admin marca como atendida ou remove uma solicitação."""
    if _eh_consultor():
        return jsonify(ok=False, erro='Sem permissão.'), 403
    try:
        d = request.get_json(force=True) or {}
        sid = d.get('id')
        acao = (d.get('acao') or 'atender').strip()
        lst = _ler_solic()
        if acao == 'remover':
            lst = [s for s in lst if s.get('id') != sid]
        else:
            for s in lst:
                if s.get('id') == sid:
                    s['status'] = 'atendida'
                    s.setdefault('atendida_em', engine.agora().strftime('%d/%m/%Y %H:%M'))
                    # pacote criado a partir desta solicitação (o consultor vê
                    # qual kit o atendeu e o escolhe com um clique)
                    if d.get('pacote_id'):
                        s['pacote'] = {'id': str(d['pacote_id']),
                                       'nome': str(d.get('pacote_nome') or ''),
                                       'kwp': _f(d.get('pacote_kwp'))}
        _salvar_solic(lst)
        return jsonify(ok=True)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.get('/logo.png')
def logo():
    return send_file(os.path.join(BASE, 'assets', 'logo.png'),
                     mimetype='image/png')


# ------------------------------------------------------ PWA (ícone no celular)
@app.get('/manifest.webmanifest')
def manifest():
    """Descreve o app para o celular (nome, ícones, cor) — vira ícone na tela."""
    return send_file(os.path.join(BASE, 'assets', 'manifest.webmanifest'),
                     mimetype='application/manifest+json')


@app.get('/sw.js')
def service_worker():
    """Service worker. Servido da raiz (/sw.js) de propósito: só assim ele
    controla o app inteiro. 'no-cache' faz o navegador notar versões novas."""
    resp = send_file(os.path.join(BASE, 'assets', 'sw.js'),
                     mimetype='application/javascript')
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.get('/icons/<path:nome>')
def icones(nome):
    """Ícones do app. send_from_directory impede acesso fora da pasta icons/."""
    return send_from_directory(os.path.join(BASE, 'assets', 'icons'), nome)


@app.get('/favicon.ico')
def favicon():
    """Navegadores pedem /favicon.ico sozinhos (ex.: na tela de login, que não
    tem <link rel=icon>). Serve o ícone do app em vez de devolver 404/redirect."""
    return send_from_directory(os.path.join(BASE, 'assets', 'icons'),
                               'icon-192.png')


# Campos do resumo que revelam CUSTO/MARGEM. A tela do consultor já os
# escondia (.so-admin), mas o JSON chegava inteiro ao navegador dele — bastava
# abrir o F12 para ler kit, mão de obra, imposto e lucro. Agora o servidor nem
# manda (mesma ideia do _WB_CUSTOS do carregador).
_RESUMO_CUSTOS = ('composicao', 'custo_kit', 'custo_desloc', 'custo_entrada',
                  'custo_380v', 'custo_total_pct', 'custo_mo', 'custo_material',
                  'custo_trafo', 'custo_imposto', 'custo_comissao',
                  'custo_seguro', 'custo_total', 'margem_usada_pct', 'preco_wp',
                  'lucro_pct', 'lucro_rs', 'custo_mo_auto',
                  'custo_material_auto', 'aliquota_usada_pct')


@app.post('/api/calcular')
def api_calcular():
    try:
        cfg = engine.carregar_config()
        e = _montar_entradas(request.get_json(force=True))
        r = engine.calcular(e, cfg)
        res = _resumo(r, cfg)
        if _eh_consultor():
            for k in _RESUMO_CUSTOS:
                res.pop(k, None)
        return jsonify(ok=True, resumo=res)
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/pacote-preco')
def api_pacote_preco():
    """Prévia (SÓ admin) do preço e da margem de UM pacote enquanto o kit é
    editado. Não depende do consumo do cliente: os custos saem do próprio kit
    (módulos × potência, inversores, mão de obra, material, imposto…). Devolve o
    valor de venda (o FIXO se o kit tem 'preco_venda_manual', senão o convergido),
    o preço/Wp e a margem líquida REAL — o mesmo cálculo do fluxo normal."""
    try:
        if _eh_consultor():
            return jsonify(ok=False, erro='sem permissão'), 403
        cfg = engine.carregar_config()
        p = request.get_json(force=True) or {}
        d = dict(p)
        d['qtd_modulos_kit'] = p.get('qtd_modulos', p.get('qtd_modulos_kit'))
        d['ucs'] = []                       # preço/margem não dependem do consumo
        e = _montar_entradas(d)
        r = engine.calcular(e, cfg)
        br = cfg.get('formato_ptbr', True)
        return jsonify(ok=True,
                       preco_venda=engine.moeda(r['preco_venda'], br),
                       preco_venda_num=round(r['preco_venda'], 2),
                       preco_wp=round(r['preco_wp'], 4),
                       lucro_pct=round(r['lucro_pct'] * 100, 2),
                       margem_usada_pct=round(r['margem_usada'] * 100, 2),
                       custo_total=engine.moeda(r['custo_total'], br))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/conferencia')
def api_conferencia():
    """Devolve o detalhamento passo a passo do retorno financeiro."""
    try:
        import conferencia_retorno
        cfg = engine.carregar_config()
        e = _montar_entradas(request.get_json(force=True))
        texto = conferencia_retorno.relatorio_conferencia(e, cfg)
        return jsonify(ok=True, texto=texto)
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/sugestao')
def api_sugestao():
    """Potência FV necessária p/ abater 100% do consumo (DD!B21). NÃO precisa de
    pacote — depende só do consumo + irradiação. O consultor usa para pedir uma
    cotação ao administrador antes de existir um kit."""
    try:
        d = dict(request.get_json(force=True) or {})
        cfg = engine.carregar_config()
        # É a MESMA conta da proposta (engine.calcular → DD!B21), com o kit
        # zerado e sem pacote: consumo real − geração das usinas que a UC já
        # tem, fator da ponta no grupo A, irradiação e PR. Antes havia aqui uma
        # conta à parte que NÃO descontava as usinas existentes — a sugestão
        # do consultor saía maior que o kWp da proposta para quem já gera.
        d.update(qtd_modulos_kit=0, valor_kit=0, pacote_id=None)
        e = _montar_entradas(d, com_pacote=False)
        r = engine.calcular(e, cfg)
        return jsonify(ok=True, kwp_necessario=r['kwp_necessario'],
                       consumo_medio=round(r['consumo_medio'], 1),
                       consumo_anual=round(r['consumo_anual_equiv'], 1),
                       geracao_existente=round(r['geracao_existente_ano'] / 12.0, 1))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.get('/api/concessionarias')
def api_concessionarias():
    """Concessionárias: tarifas locais por subgrupo + alíquotas + subgrupos."""
    try:
        cfg = engine.carregar_config()
        conc = {}
        for nome, v in (cfg.get('concessionarias') or {}).items():
            if nome.startswith('_') or not isinstance(v, dict):
                continue                       # pula chaves-comentário (_nota…)
            imp = {}
            for sub, a in (v.get('impostos') or {}).items():
                imp[sub] = dict(
                    icms_pct=round(a.get('icms', 0) * 100, 2),
                    cofins_pct=round(a.get('cofins', 0) * 100, 2),
                    pis_pct=round(a.get('pis', 0) * 100, 2))
            conc[nome] = dict(impostos=imp,
                              tarifas=v.get('tarifas') or {},
                              # regras tributárias por componente (aplicadas
                              # invisivelmente ao selecionar a concessionária).
                              icms_sobre_te=bool(v.get('icms_sobre_te', True)),
                              icms_sobre_tusd=bool(v.get('icms_sobre_tusd', True)),
                              # isenção do ICMS na compensada alcança a TUSD?
                              abat_tusd_inclui_icms=bool(v.get('abat_tusd_inclui_icms', False)),
                              # o Convênio ICMS 16/2015 ainda vale aqui? (o
                              # crédito devolve o ICMS da TE). Onde o prazo
                              # caducou, isto vira false.
                              abat_te_inclui_icms=bool(v.get('abat_te_inclui_icms', True)),
                              aneel_sigla=v.get('aneel_sigla', ''),
                              site_tarifas=v.get('site_tarifas', ''),
                              site_tributos=v.get('site_tributos', ''),
                              fonte_impostos=v.get('fonte_impostos', ''))
        return jsonify(ok=True, concessionarias=conc,
                       subgrupos=cfg.get('subgrupos') or
                       [{'id': 'B1', 'rotulo': 'B1 – Residencial'}])
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


def _caminho_tarifa_cache() -> str:
    # cache do último TE/TUSD da ANEEL por distribuidora (dado de runtime, no
    # data dir → bucket no Cloud Run; gitignored). Sobrevive a quedas de internet.
    return os.path.join(engine.dir_execucao(), 'tarifas_cache.json')


def _ler_cache_tarifas() -> dict:
    try:
        with open(_caminho_tarifa_cache(), encoding='utf-8') as f:
            return json.load(f)
    except Exception:                                          # noqa: BLE001
        return {}


def _salvar_cache_tarifa(chave: str, dados: dict) -> None:
    cache = _ler_cache_tarifas()
    cache[chave] = dados
    try:
        with open(_caminho_tarifa_cache(), 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:                                          # noqa: BLE001
        pass


@app.get('/api/aneel-tarifa')
def api_aneel_tarifa():
    """TE/TUSD vigentes (SEM impostos) de uma concessionária, da ANEEL Dados
    Abertos. Params: `conc` (nome no config) ou `sigla` (SigAgente) + `sub`.
    Online: busca e ATUALIZA o cache. Offline: devolve o ÚLTIMO registro salvo."""
    cfg = engine.carregar_config()
    nome = (request.args.get('conc') or '').strip()
    sub = (request.args.get('sub') or 'B1').strip().upper()
    v = (cfg.get('concessionarias') or {}).get(nome) or {}
    sigla = (request.args.get('sigla') or v.get('aneel_sigla') or '').strip()
    if not sigla:
        return jsonify(ok=False, erro=f'sem sigla ANEEL para {nome!r}'), 400
    chave = f'{sigla}|{sub}'
    import online
    try:
        t = online.buscar_tarifa_aneel(sigla, sub)
        _salvar_cache_tarifa(chave, t)                # guarda o último registro
        return jsonify(ok=True, cache=False, **t)
    except Exception as exc:                                   # noqa: BLE001
        cached = _ler_cache_tarifas().get(chave)
        if cached:                                    # sem internet: último salvo
            return jsonify(ok=True, cache=True,
                           aviso=f'ANEEL indisponível ({exc}) — usei o último registro',
                           **cached)
        return jsonify(ok=False, erro=str(exc)), 502


def _bandeira_do_payload(d: dict) -> dict:
    """Bandeira vigente para a pág. 5: a que a tela buscou na ANEEL
    (`bandeira_vigente` + `bandeira_competencia`); sem ela, o último registro
    salvo no cache. Nunca vai à internet aqui (a geração do PDF não pode
    esperar a ANEEL). Sem nada, a proposta sai sem a indicação."""
    nome = str(d.get('bandeira_vigente') or '').strip().upper()
    comp = str(d.get('bandeira_competencia') or '').strip()
    if not nome:
        c = _ler_cache_tarifas().get('BANDEIRA') or {}
        nome, comp = str(c.get('bandeira') or '').upper(), str(c.get('competencia') or '')
    return {'bandeira_vigente': nome, 'bandeira_competencia': comp}


@app.get('/api/aneel-bandeira')
def api_aneel_bandeira():
    """Bandeira tarifária acionada no mês corrente (ANEEL Dados Abertos), com
    o adicional em R$/kWh SEM impostos. Online: busca e grava no cache;
    offline: devolve o último registro salvo (`cache: true`)."""
    import online
    try:
        b = online.buscar_bandeira_aneel(engine.hoje())
        _salvar_cache_tarifa('BANDEIRA', b)
        return jsonify(ok=True, cache=False, **b)
    except Exception as exc:                                   # noqa: BLE001
        cached = _ler_cache_tarifas().get('BANDEIRA')
        if cached:
            return jsonify(ok=True, cache=True,
                           aviso=f'ANEEL indisponível ({exc}) — usei o último registro',
                           **cached)
        return jsonify(ok=False, erro=str(exc)), 502


@app.get('/api/aneel-tarifa-a')
def api_aneel_tarifa_a():
    """Tarifas do GRUPO A (TE/TUSD por posto + TUSD-demanda) na ANEEL.

    Params: `conc` (nome no config) ou `sigla`, `sub` (A4, A3a…) e `mod`
    (VERDE/AZUL). Mesmo esquema do grupo B: online busca e grava no cache;
    offline devolve o último registro salvo. Exclusivo do administrador.
    """
    if _eh_consultor():
        return jsonify(ok=False, erro='sem permissão'), 403
    cfg = engine.carregar_config()
    nome = (request.args.get('conc') or '').strip()
    sub = (request.args.get('sub') or 'A4').strip().upper()
    mod = (request.args.get('mod') or 'VERDE').strip().upper()
    v = (cfg.get('concessionarias') or {}).get(nome) or {}
    sigla = (request.args.get('sigla') or v.get('aneel_sigla') or '').strip()
    if not sigla:
        return jsonify(ok=False, erro=f'sem sigla ANEEL para {nome!r}'), 400
    chave = f'{sigla}|{sub}|{mod}'
    import online
    try:
        t = online.buscar_tarifa_aneel_a(sigla, sub, mod)
        if not (t.get('te_fora') and t.get('tusd_demanda')):
            raise LookupError('a ANEEL respondeu, mas sem TE fora ponta / '
                              'TUSD-demanda p/ este subgrupo')
        _salvar_cache_tarifa(chave, t)
        return jsonify(ok=True, cache=False, **t)
    except Exception as exc:                                   # noqa: BLE001
        cached = _ler_cache_tarifas().get(chave)
        if cached:
            return jsonify(ok=True, cache=True,
                           aviso=f'ANEEL indisponível ({exc}) — último registro',
                           **cached)
        return jsonify(ok=False, erro=str(exc)), 502


@app.post('/api/atualizar-tarifa')
def api_atualizar_tarifa():
    """Grava TE/TUSD de uma concessionária+subgrupo na tabela local.

    Aceita valores SEM impostos ou COM impostos (converte usando as alíquotas
    informadas: sem = com × (1−ICMS) × (1−PIS−COFINS)).
    """
    try:
        d = request.get_json(force=True)
        nome = (d.get('concessionaria') or '').strip()
        sub = (d.get('subgrupo') or 'B1').strip().upper()
        te = float(d.get('te') or 0)
        tusd = float(d.get('tusd') or 0)
        if te <= 0 or tusd <= 0:
            raise ValueError('Informe TE e TUSD maiores que zero.')
        if bool(d.get('com_impostos')):
            icms = float(d.get('icms') or 0) / 100.0
            pis = float(d.get('pis') or 0) / 100.0
            cofins = float(d.get('cofins') or 0) / 100.0
            fator = (1 - icms) * (1 - (pis + cofins))
            if not 0 < fator <= 1:
                raise ValueError('Alíquotas inválidas para a conversão.')
            te, tusd = te * fator, tusd * fator
        caminho = engine.caminho_config()
        with open(caminho, encoding='utf-8') as f:
            cfg = json.load(f)
        conc = cfg.setdefault('concessionarias', {}).setdefault(nome, {})
        tab = conc.setdefault('tarifas', {}).setdefault(sub, {})
        tab.update(te=round(te, 5), tusd=round(tusd, 5),
                   resolucao=(d.get('resolucao') or '').strip(),
                   vigencia=(d.get('vigencia') or '').strip(),
                   obs=f'atualizado pela tela em {engine.agora():%d/%m/%Y %H:%M}')
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return jsonify(ok=True, te=tab['te'], tusd=tab['tusd'])
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


# pré-definições herdadas da planilha que a tela pode editar (as demais chaves
# do config.json — comentários, concessionárias/tarifas — nunca são tocadas)
CONFIG_EDITAVEL = ('aliquota_imposto', 'mao_de_obra_minima',
                   'mao_de_obra_por_modulo', 'material_markup',
                   'material_extra_faixas', 'trafos', 'garantias_fixas',
                   'faixas_margem', 'fio_b_rs_mwh', 'validade_dias',
                   'financiamento_padrao', 'cartao_infinitetap', 'performance_ratio',
                   'marcas_modulo', 'marcas_inversor',
                   'bandeiras', 'subgrupos', 'pasta_saida', 'pasta_drive',
                   'pacotes', 'foto_padrao_desc', 'wallbox')


# ----------------------------------------------------------------- pacotes
# Pacotes = "kits geradores" prontos que o admin monta (equipamento + números
# internos: valor do kit, margem, comissão, seguro, deslocamento, custo 380 V,
# mão de obra e material manuais, alíquota). O CONSULTOR só escolhe o pacote pelo
# nome; os números internos NUNCA vão ao navegador dele — ficam no servidor e são
# injetados no cálculo por 'pacote_id'. Guardados em config.json → 'pacotes'.
# (Futuro: preencher valor_kit a partir de API das distribuidoras.)

# campos internos do pacote (o que o consultor não pode ver)
# 'preco_venda_manual' = valor FINAL fixo do kit (R$), já com custos+margem
# aplicados; quando preenchido, o pacote vende por esse valor (o convergido é
# ignorado). É poder do admin — o consultor herda o valor, mas não o edita.
_PACOTE_CUSTOS = ('valor_kit', 'margem_desejada', 'comissao_pct', 'seguro_pct',
                  'desloc', 'custo_380v', 'mo_manual', 'material_manual',
                  'aliquota_pct', 'preco_venda_manual')
# campos "públicos" do pacote (equipamento — já aparece impresso na proposta).
# String box e bateria fazem parte do kit (já precificados no valor_kit), então
# entram junto com o pacote e o consultor não os edita separadamente. A ESTRUTURA
# (telhado) também vem do pacote, porque o kit é cotado conforme o tipo de
# telhado — o consultor informa o telhado do cliente escolhendo o pacote certo.
_PACOTE_EQUIP = ('conexao', 'estrutura', 'qtd_modulos', 'marca_modulo',
                 'pot_modulo_w', 'inversores', 'tem_stringbox', 'sb_qtd',
                 'sb_marca', 'sb_es', 'tem_bateria', 'bat_qtd', 'bat_marca',
                 'bat_kwh')


def _pacotes(cfg: dict) -> list:
    return cfg.get('pacotes') or []


def _pacote_id(p: dict, i: int):
    """Id estável do pacote (string). Cai no índice se o pacote ainda não tiver
    um id gravado (pacotes antigos ou editados à mão)."""
    return str(p.get('id') or i)


def _achar_pacote(cfg: dict, pid):
    """Pacote pelo id estável; cai no índice por retrocompatibilidade. None se
    não achar."""
    if pid in (None, ''):
        return None
    pacs = _pacotes(cfg)
    for i, p in enumerate(pacs):
        if _pacote_id(p, i) == str(pid):
            return p
    try:                                    # ainda aceita índice puro
        i = int(pid)
        return pacs[i] if 0 <= i < len(pacs) else None
    except (TypeError, ValueError):
        return None


def _pacote_publico(p: dict, i: int) -> dict:
    """Só o que pode chegar ao navegador do consultor (sem custos nem imagens)."""
    pub = {'id': _pacote_id(p, i), 'nome': p.get('nome') or f'Pacote {i + 1}'}
    for k in _PACOTE_EQUIP:
        pub[k] = p.get(k)
    return pub


def _aplicar_pacote(d: dict) -> dict:
    """Para o CONSULTOR: sobrescreve equipamento + custos com os do pacote
    escolhido, ignorando o que o navegador mandou (blindagem do preço)."""
    if not _eh_consultor():
        return d
    cfg = engine.carregar_config()
    pac = _achar_pacote(cfg, d.get('pacote_id'))
    if pac is None:
        raise ValueError('Escolha um pacote gerador.')
    d = dict(d)
    for k in _PACOTE_CUSTOS + _PACOTE_EQUIP:
        if k in pac:
            d[k] = pac[k]
    # blindagem do VALOR FINAL: para o consultor ele vem SÓ do pacote (ou fica
    # vazio se o kit não fixa nenhum) — nunca do navegador. Assim o consultor não
    # consegue redigitar o valor final por fora, mesmo forçando o payload.
    d['preco_venda_manual'] = pac.get('preco_venda_manual')
    # nomes usados pelo montador de entradas (a tela usa 'qtd_modulos_kit')
    d['qtd_modulos_kit'] = pac.get('qtd_modulos', d.get('qtd_modulos_kit'))
    return d


def _impostos_copel(cfg: dict) -> dict:
    """PIS/COFINS (federais) para o editor. O ICMS NÃO fica aqui — varia por
    estado e vem da concessionária (concessionarias.<nome>.impostos)."""
    imp = ((cfg.get('concessionarias') or {}).get('COPEL (PR)') or {}) \
        .get('impostos') or {}
    base = imp.get('B1') or imp.get('padrao') or {}
    return {'pis': round(base.get('pis', 0) * 100, 4),
            'cofins': round(base.get('cofins', 0) * 100, 4)}


@app.get('/api/config')
def api_config():
    """Devolve só os parâmetros de negócio que a tela pode editar."""
    try:
        cfg = engine.carregar_config()
        dados = {k: cfg.get(k) for k in CONFIG_EDITAVEL}
        import wallbox                  # completa com o padrão do programa
        dados['wallbox'] = wallbox.parametros(cfg)
        # pacotes: acrescenta id estável e as imagens próprias (para o editor)
        pacs = []
        for i, p in enumerate(_pacotes(cfg)):
            pid = _pacote_id(p, i)
            pacs.append({**p, 'id': pid,
                         'img_modulo': _ler_img_pacote(pid, 'modulo'),
                         'img_inversor': _ler_img_pacote(pid, 'inversor')})
        dados['pacotes'] = pacs
        dados['impostos_copel'] = _impostos_copel(cfg)
        dados['tem_senha'] = bool(_senha_acesso())
        dados['consultores'] = _consultores()      # [{nome, senha}] (só admin)
        return jsonify(ok=True, config=dados)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/config')
def api_salvar_config():
    """Grava as pré-definições editadas, preservando o resto do config.json
    (comentários e a TABELA DE TARIFAS das concessionárias ficam intactos)."""
    try:
        novos = request.get_json(force=True) or {}
        # senha de acesso: vai para acesso.json (NÃO versionado), nunca para o
        # config.json. String vazia remove a senha (volta a não exigir login).
        if 'senha_acesso' in novos or 'consultores' in novos:
            ac = _ler_acesso()
            if 'senha_acesso' in novos:
                nova = (novos.get('senha_acesso') or '').strip()
                if nova:
                    ac['senha'] = nova
                else:
                    ac.pop('senha', None)
            # lista de consultores [{nome, senha}] — vive em acesso.json (fora do
            # Git). Entradas sem nome ou sem senha são descartadas.
            if 'consultores' in novos:
                lst = []
                for c in (novos.get('consultores') or []):
                    nome = (c.get('nome') or '').strip()
                    sen = (c.get('senha') or '').strip()
                    if nome and sen:
                        lst.append({'nome': nome, 'senha': sen})
                ac['consultores'] = lst
            _salvar_acesso(ac)
        caminho = engine.caminho_config()
        with open(caminho, encoding='utf-8') as f:
            cfg = json.load(f)                      # mantém ordem e comentários
        for k in CONFIG_EDITAVEL:
            if k in novos:
                cfg[k] = novos[k]
        # pacotes: garante um id estável e MOVE as imagens para o arquivo próprio
        # (nunca grava base64 no config.json versionado).
        if 'pacotes' in novos:
            import secrets as _secrets
            limpos = []
            for i, p in enumerate(novos.get('pacotes') or []):
                p = dict(p)
                pid = str(p.get('id') or '').strip() or ('p' + _secrets.token_hex(4))
                p['id'] = pid
                for qual in ('modulo', 'inversor'):
                    chave = 'img_' + qual
                    if chave in p:                  # ausente = mantém a atual
                        _gravar_img_pacote(pid, qual, p.get(chave))
                        p.pop(chave, None)
                limpos.append(p)
            cfg['pacotes'] = limpos
        # PIS/COFINS são federais (mudam todo mês) e ficam aqui à mão. O ICMS
        # NÃO é editado aqui — varia por estado (concessionarias.<nome>.impostos)
        # e é preservado byte a byte. Atualiza só PIS/COFINS — SEM tocar em
        # 'tarifas' nem no ICMS de cada subgrupo.
        ic = novos.get('impostos_copel')
        if ic:
            pis = _f(ic.get('pis')) / 100.0
            cofins = _f(ic.get('cofins')) / 100.0
            conc = cfg.setdefault('concessionarias', {}) \
                      .setdefault('COPEL (PR)', {})
            imp = conc.setdefault('impostos', {})
            for sub in ('B1', 'B2', 'padrao'):
                imp.setdefault(sub, {}).update({'cofins': cofins, 'pis': pis})
            tp = cfg.setdefault('tarifas_padrao', {})
            tp['pis'], tp['cofins'] = pis, cofins
        with open(caminho, 'w', encoding='utf-8') as f:      # 2 espaços: mesmo
            json.dump(cfg, f, ensure_ascii=False, indent=2)  # formato do arquivo
        return jsonify(ok=True)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.get('/api/imagens-padrao')
def api_imagens_padrao():
    """Data URLs das imagens PADRÃO de módulo/inversor (para preencher o editor)."""
    return jsonify(ok=True,
                   modulo=_ler_img_padrao('modulo'),
                   inversor=_ler_img_padrao('inversor'))


@app.post('/api/imagens-padrao')
def api_salvar_imagens_padrao():
    """Salva/apaga as imagens padrão. Body: {modulo: dataURL|null, inversor: …}.
    Uma chave ausente é ignorada; valor vazio remove aquela imagem."""
    try:
        d = request.get_json(force=True) or {}
        for qual in ('modulo', 'inversor'):
            if qual in d:
                _gravar_img_padrao(qual, d.get(qual))
        return jsonify(ok=True)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.get('/api/copel-verificar')
def api_copel_verificar():
    """Raspagem leve do site da COPEL: resolução/vigência atual + ICMS."""
    try:
        import online
        cfg = engine.carregar_config()
        v = (cfg.get('concessionarias') or {}).get('COPEL (PR)') or {}
        out = {}
        try:
            out['vigencia_site'] = online.vigencia_copel(
                v.get('site_tarifas') or
                'https://www.copel.com/site/copel-distribuicao/'
                'tarifas-de-energia-eletrica/')
        except Exception as e:                                 # noqa: BLE001
            out['vigencia_erro'] = str(e)
        try:
            out['icms_site'] = online.icms_copel(
                v.get('site_tributos') or
                'https://www.copel.com/site/copel-distribuicao/tributos/')
        except Exception as e:                                 # noqa: BLE001
            out['icms_erro'] = str(e)
        return jsonify(ok=True, **out)
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


def _ip_local() -> str:
    """IP desta máquina na rede local (para acesso pelo celular)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))          # não envia nada; só resolve a rota
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


@app.get('/api/rede')
def api_rede():
    """URL para acessar o programa pelo celular (mesma rede Wi-Fi)."""
    ip = _ip_local()
    return jsonify(ok=True, ip=ip, porta=PORTA,
                   url=f'http://{ip}:{PORTA}', local=(ip == '127.0.0.1'))


@app.get('/qr.png')
def qr_png():
    """QR code da URL de rede (requer o pacote opcional 'qrcode')."""
    try:
        import qrcode
        import io as _io
        img = qrcode.make(f'http://{_ip_local()}:{PORTA}')
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception:                                          # noqa: BLE001
        return ('', 404)


# --------------------------------------------------------------- Google Drive
def _redirect_uri() -> str:
    return request.host_url.rstrip('/') + '/oauth2/callback'


@app.get('/oauth2/start')
def oauth2_start():
    """Abre a autorização do Google (deve ser feita LOCALMENTE, no PC)."""
    try:
        if not drive.tem_credencial():
            return ('Falta o arquivo google_oauth.json na pasta do programa.',
                    400)
        import secrets
        session['oauth_state'] = secrets.token_urlsafe(16)
        return redirect(drive.auth_url(_redirect_uri()))
    except Exception as exc:                                    # noqa: BLE001
        return (f'Erro ao iniciar: {exc}', 400)


@app.get('/oauth2/callback')
def oauth2_callback():
    """Recebe o código do Google e guarda o token."""
    erro = request.args.get('error')
    code = request.args.get('code')
    if erro:
        return redirect('/?drive=erro')
    try:
        drive.trocar_codigo(code, _redirect_uri())
        return redirect('/?drive=ok')
    except Exception as exc:                                    # noqa: BLE001
        return (f'Falha ao conectar o Drive: {exc}', 400)


@app.get('/api/drive/status')
def api_drive_status():
    cfg = engine.carregar_config()
    return jsonify(ok=True, tem_credencial=drive.tem_credencial(),
                   conectado=drive.conectado(),
                   email=drive.email_conectado(),
                   pasta=cfg.get('pasta_drive', ''))


@app.post('/api/drive/desconectar')
def api_drive_desconectar():
    drive.desconectar()
    return jsonify(ok=True)


@app.get('/api/drive/consultores')
def api_drive_consultores():
    """Pastas de consultor já existentes na pasta base do Drive (p/ o menu)."""
    cfg = engine.carregar_config()
    base = (cfg.get('pasta_drive') or '').strip()
    if not (base and drive.conectado()):
        return jsonify(ok=True, consultores=[])
    try:
        return jsonify(ok=True, consultores=[
            c for c in drive.listar_subpastas(base) if not _eh_pasta_wallbox(c)])
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc), consultores=[])


@app.get('/api/resumos-salvos')
def api_resumos_salvos():
    """Lista os projetos que podem ser reabertos — qualquer pasta que tenha um
    DADOS.json, em qualquer profundidade (com ou sem o nível do consultor).
    `?tipo=wallbox` lista só os de carregador veicular (pasta 'WALLBOX …'); sem
    o parâmetro, só os solares — a tela de um não importa projeto do outro."""
    base = _clientes_dir()
    so_wallbox = request.args.get('tipo') == 'wallbox'
    itens = []
    for raiz, _dirs, arqs in os.walk(base):
        if 'DADOS.json' not in arqs:
            continue
        rel = os.path.relpath(raiz, base)
        partes = rel.split(os.sep)
        projeto = partes[-1]
        if projeto.upper().startswith('WALLBOX') != so_wallbox:
            continue
        cliente = partes[-2] if len(partes) >= 2 else projeto
        itens.append({'cliente': cliente, 'projeto': projeto,
                      'rel': rel.replace(os.sep, '/'),
                      'caminho': rel.replace(os.sep, ' / ')})
    itens.sort(key=lambda x: x['rel'], reverse=True)
    return jsonify(ok=True, itens=itens)


@app.post('/api/importar-resumo')
def api_importar_resumo():
    """Devolve o payload de um projeto salvo, para repovoar a tela."""
    try:
        d = request.get_json(force=True)
        rel = str(d.get('rel') or '')
        caminho = os.path.abspath(os.path.join(_clientes_dir(), rel,
                                               'DADOS.json'))
        if not caminho.startswith(os.path.abspath(_clientes_dir())):
            raise ValueError('caminho inválido')
        if not os.path.isfile(caminho):
            raise ValueError('projeto não encontrado')
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
        # fotos do módulo/inversor guardadas ao lado do DADOS.json
        dados.update(_ler_imgs_projeto(os.path.dirname(caminho)))
        return jsonify(ok=True, dados=dados)
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


def _imagens_da_proposta(d: dict):
    """Fotos do módulo/inversor que vão para a pág. 3.
    Prioridade: foto colada na tela (admin) > imagem própria do pacote > padrão
    das pré-definições. Devolve (bytes p/ o PDF, data URL módulo, data URL inv.)."""
    pid = d.get('pacote_id')
    img_mod = (d.get('img_modulo') or _ler_img_pacote(pid, 'modulo')
               or _ler_img_padrao('modulo'))
    img_inv = (d.get('img_inversor') or _ler_img_pacote(pid, 'inversor')
               or _ler_img_padrao('inversor'))
    imagens = {'modulo': _img_bytes(img_mod), 'inversor': _img_bytes(img_inv)}
    return {k: v for k, v in imagens.items() if v}, img_mod, img_inv


def _norm_marca(s) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore')
    return s.decode().upper().strip()


def _conferir_fotos(d: dict, e) -> list:
    """Avisos quando a foto que vai para a pág. 3 é a PADRÃO e é de outro
    equipamento. A foto traz marca e potência impressas, e o programa não lê a
    imagem: compara com o que foi cadastrado nas pré-definições
    (`config.foto_padrao_desc`). Foto colada na tela ou do pacote = escolhida
    para o kit, sem aviso. Sem cadastro, nada a comparar, sem aviso."""
    desc = engine.carregar_config().get('foto_padrao_desc') or {}
    pid = d.get('pacote_id')
    avisos = []
    dm = desc.get('modulo') or {}
    if (not d.get('img_modulo') and not _ler_img_pacote(pid, 'modulo')
            and _ler_img_padrao('modulo') and dm.get('marca')):
        marca_f, marca_k = _norm_marca(dm['marca']), _norm_marca(e.marca_modulo)
        pot_f = int(float(dm.get('pot_w') or 0))
        pot_k = int(round(float(e.pot_modulo_w or 0)))
        outra = marca_f.split()[0] not in marca_k if marca_f else False
        if outra or (pot_f and pot_f != pot_k):
            avisos.append(f'A foto do MÓDULO na proposta é a padrão '
                          f'({dm["marca"]} {pot_f or ""}W), mas o kit é '
                          f'{e.marca_modulo} {pot_k}W.')
    di = desc.get('inversor') or {}
    if (not d.get('img_inversor') and not _ler_img_pacote(pid, 'inversor')
            and _ler_img_padrao('inversor') and di.get('marca')):
        marca_f = _norm_marca(di['marca']).split()[0]
        marcas_k = [_norm_marca(iv['marca']) for iv in e.lista_inversores()]
        if marcas_k and not any(marca_f in m for m in marcas_k):
            avisos.append(f'A foto do INVERSOR na proposta é a padrão '
                          f'({di["marca"]}), mas o kit é '
                          f'{" + ".join(iv["marca"] for iv in e.lista_inversores())}.')
    return avisos


@app.post('/api/conferir-fotos')
def api_conferir_fotos():
    """Chamado pela tela antes de gerar: devolve os avisos de foto trocada."""
    try:
        d = request.get_json(force=True) or {}
        return jsonify(ok=True, avisos=_conferir_fotos(d, _montar_entradas(d)))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc), avisos=[]), 400


@app.post('/api/previa')
def api_previa():
    """PRÉ-VISUALIZA a proposta: mesmo cálculo e mesmo PDF da ação principal,
    mas sem gravar pasta, resumo, conferência nem enviar ao Drive. Serve para
    olhar a proposta enquanto se ajusta os números (e para ajustes de layout)."""
    import tempfile
    try:
        cfg = engine.carregar_config()
        d = request.get_json(force=True)
        e = _montar_entradas(d)
        r = engine.calcular(e, cfg)
        imagens, _, _ = _imagens_da_proposta(d)
        fd, caminho = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        try:
            proposta.gerar_proposta(r, caminho, imagens=imagens or None)
            with open(caminho, 'rb') as f:
                pdf = f.read()
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
        resp = app.response_class(pdf, mimetype='application/pdf')
        resp.headers['Content-Disposition'] = 'inline; filename="PREVIA.pdf"'
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/proposta')
def api_proposta():
    """Ação única: calcula, salva o projeto inteiro (resumo, conferência, dados
    e proposta) na pasta do cliente e devolve o PDF para download."""
    try:
        import resumo_texto
        import conferencia_retorno
        cfg = engine.carregar_config()
        d = request.get_json(force=True)
        d.pop('_incluir_conferencia', None)
        e = _montar_entradas(d)
        r = engine.calcular(e, cfg)

        # consultor logado manda no nome da pasta (não confia no que veio da tela)
        consultor = (session.get('consultor') if _eh_consultor()
                     else (d.get('consultor') or '')).strip()
        if _eh_pasta_wallbox(consultor):
            raise ValueError(f'A pasta "{PASTA_WALLBOX}" é exclusiva dos orçamentos '
                             f'de carregador veicular — escolha outro consultor.')
        pasta = _pasta_projeto(e, r, consultor)  # <base>/<consultor>/<cliente>/…
        nome_pdf = _limpar_nome(e.nome, 'PROPOSTA')
        if e.tem_micro():                    # proposta de microinversor: sufixo MICRO
            nome_pdf += ' - MICRO'
        imagens, img_mod, img_inv = _imagens_da_proposta(d)
        # as MESMAS fotos que foram para o PDF ficam soltas na pasta do projeto
        # (MODULO.png / INVERSOR.jpg) — o import as devolve para a tela
        arq_imgs = [it for it in (_gravar_img_projeto(pasta, 'modulo', img_mod),
                                  _gravar_img_projeto(pasta, 'inversor', img_inv))
                    if it]

        txt_resumo = resumo_texto.resumo_texto(e, cfg)
        txt_conf = conferencia_retorno.relatorio_conferencia(e, cfg)
        # DADOS.json repovoa a tela depois; as fotos (base64 grande) ficam fora
        # dele — vão como arquivos MODULO/INVERSOR na mesma pasta (acima)
        d_salvar = {k: v for k, v in d.items()
                    if k not in ('img_modulo', 'img_inversor')}
        txt_dados = json.dumps(d_salvar, ensure_ascii=False, indent=1)

        with open(os.path.join(pasta, 'RESUMO.txt'), 'w', encoding='utf-8') as f:
            f.write(txt_resumo)
        with open(os.path.join(pasta, 'CONFERENCIA.txt'), 'w',
                  encoding='utf-8') as f:
            f.write(txt_conf)
        with open(os.path.join(pasta, 'DADOS.json'), 'w', encoding='utf-8') as f:
            f.write(txt_dados)

        destino = os.path.join(pasta, f'{nome_pdf}.pdf')
        proposta.gerar_proposta(r, destino, imagens=imagens or None)

        # envia ao Google Drive (se conectado e com pasta configurada). Falha no
        # Drive não quebra a geração — o arquivo local + download continuam.
        aviso_drive = None
        enviado_drive = False
        base_drive = (cfg.get('pasta_drive') or '').strip()
        if base_drive and drive.conectado():
            try:
                with open(destino, 'rb') as f:
                    pdf_bytes = f.read()
                drive.enviar_projeto(
                    base_drive, consultor, _limpar_nome(e.nome, 'CLIENTE'),
                    _nome_projeto(e, r),
                    [('RESUMO.txt', txt_resumo.encode('utf-8'), 'text/plain'),
                     ('CONFERENCIA.txt', txt_conf.encode('utf-8'), 'text/plain'),
                     ('DADOS.json', txt_dados.encode('utf-8'),
                      'application/json'),
                     (f'{nome_pdf}.pdf', pdf_bytes, 'application/pdf')]
                    + arq_imgs)
                enviado_drive = True
            except Exception as exc:                           # noqa: BLE001
                aviso_drive = str(exc)[:300]

        resp = send_file(destino, as_attachment=True,
                         download_name=f'{nome_pdf}.pdf')
        if enviado_drive:
            resp.headers['X-Drive-Enviado'] = '1'
        if aviso_drive:                       # cabeçalho HTTP só aceita ASCII
            resp.headers['X-Drive-Aviso'] = \
                aviso_drive.encode('ascii', 'replace').decode('ascii')
        return resp
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/irradiacao')
def api_irradiacao():
    try:
        import online
        d = request.get_json(force=True)
        cidade = (d.get('cidade') or '').strip()
        if not cidade:
            raise ValueError('Informe a cidade.')
        # irradiação BRUTA: as perdas entram só pelo performance_ratio
        return jsonify(ok=True, **online.buscar_irradiacao(cidade))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=f'Não foi possível buscar agora: {exc}'), 400


@app.get('/api/cep/<cep>')
def api_cep(cep):
    try:
        import online
        return jsonify(ok=True, **online.buscar_cep(cep))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=f'Não foi possível buscar agora: {exc}'), 400


# ------------------------------------------------------- carregador veicular
# Aba própria (/wallbox): SERVIÇO de instalação de wallbox — o carregador é do
# cliente; a proteção é sempre um CLAMPER Mobi. Motor em wallbox.py, PDF em
# proposta_wallbox.py, preços em config.json → 'wallbox'. Nada passa pelo engine.
# Campos de CUSTO que o consultor não controla: para ele, o servidor descarta o
# que veio da tela e usa os padrões das pré-definições (mesma blindagem dos
# pacotes do solar). Os dados técnicos e as opções da Mobi seguem livres.
_WB_CUSTOS = ('mobi_preco_manual', 'material_ca_manual', 'mo_manual', 'desloc',
              'aliquota_pct', 'comissao_pct', 'seguro_pct', 'margem_pct',
              'preco_venda_manual', 'cartao_taxa_pct', 'cartao_parcelas')


def _montar_wallbox(d: dict):
    import wallbox
    cw = wallbox.parametros(engine.carregar_config())
    d = dict(d or {})
    if _eh_consultor():
        for k in _WB_CUSTOS:
            d.pop(k, None)
    vazio = lambda k: d.get(k) in (None, '')
    pct = lambda k, padrao: padrao if vazio(k) else _f(d[k]) / 100.0
    rs = lambda k: None if vazio(k) else _f(d[k])
    cartao = cw.get('cartao') or {}
    return wallbox.EntradaWallbox(
        nome=(d.get('nome') or '').strip(),
        endereco=(d.get('endereco') or '').strip(),
        numero=(d.get('numero') or '').strip(),
        cidade=(d.get('cidade') or '').strip(),
        consultor=(session.get('consultor') if _eh_consultor()
                   else (d.get('consultor') or '')).strip(),
        modelo=(d.get('modelo') or '').strip(),
        pot_kw=_f(d.get('pot_kw')),
        corrente_a=rs('corrente_a'),
        alimentacao=d.get('alimentacao') or '220_FF',
        distancia_m=rs('distancia_m'),        # vazio = a verificar
        secao_manual=rs('secao_manual'),
        disjuntor_manual=rs('disjuntor_manual'),
        mobi_linha=(d.get('mobi_linha') or 'BOX').upper(),
        mobi_tomadas=(d.get('mobi_tomadas') or 'RESIDENCIAL').upper(),
        mobi_cor=(d.get('mobi_cor') or 'CINZA').upper(),
        mobi_medidor=_regra_bool(d.get('mobi_medidor'), False),
        mobi_preco_manual=rs('mobi_preco_manual'),
        material_ca_manual=rs('material_ca_manual'),
        mo_manual=rs('mo_manual'),
        desloc=_f(d.get('desloc')),
        aliquota=pct('aliquota_pct', float(cw.get('aliquota_imposto', 0.08))),
        comissao_pct=pct('comissao_pct', float(cw.get('comissao_pct', 0))),
        seguro_pct=pct('seguro_pct', float(cw.get('seguro_pct', 0))),
        margem=pct('margem_pct', float(cw.get('margem_padrao', 0.30))),
        preco_venda_manual=rs('preco_venda_manual'),
        cartao_taxa_pct=(_f(cartao.get('taxa_pct'), 12.4) if vazio('cartao_taxa_pct')
                         else _f(d['cartao_taxa_pct'])),
        cartao_parcelas=int(_f(cartao.get('parcelas'), 12) if vazio('cartao_parcelas')
                            else _f(d['cartao_parcelas'])),
        garantia=(d.get('garantia') or cw.get('garantia') or '').strip(),
        prazo_execucao=(d.get('prazo_execucao') or cw.get('prazo_execucao')
                        or '').strip())


def _resumo_wallbox(r: dict, cfg: dict) -> dict:
    """O que a tela mostra. Para o consultor, sai só o valor, a técnica e o
    modelo da Mobi — nunca custos."""
    import wallbox
    br = cfg.get('formato_ptbr', True)
    m = lambda v: engine.moeda(v, br)
    t = r['tecnico']
    venda = r['preco_venda'] or 0.0
    pct = lambda v: round(v / venda * 100, 1) if venda else 0.0
    res = dict(
        preco_venda=m(venda), preco_venda_num=round(venda, 2),
        parcela_cartao=m(r['parcela_cartao']), cartao_parcelas=r['cartao_parcelas'],
        textos=r['textos'], avisos=r['avisos'],
        tem_foto_padrao=bool(_ler_img_padrao(
            'mobi_plug' if (r.get('mobi') or {}).get('linha') == 'PLUG' else 'mobi_box')),
        mobi_modelo=(r.get('mobi') or {}).get('modelo') or '',
        mobi_sem_preco=r['mobi_sem_preco'],
        tecnico=dict(alimentacao=t['alimentacao_txt'], ib=round(t['ib'], 1),
                     disjuntor=t['disjuntor'], polos_dj=t['polos_dj'],
                     secao=t['secao'], secao_pe=t['secao_pe'],
                     queda_pct=round(t['queda_pct'], 2)))
    if _eh_consultor():
        return res
    res['composicao'] = [{'rotulo': a, 'rs': m(v), 'pct': pct(v), 'obs': obs}
                         for a, v, obs in wallbox.composicao(r)]
    res.update(custo_mobi_auto=round(r['custo_mobi_auto'], 2),
               custo_material_auto=round(r['custo_material_auto'], 2),
               custo_mo_auto=round(r['custo_mo_auto'], 2),
               custo_total=m(r['custo_total']), custo_total_pct=pct(r['custo_total']),
               lucro_rs=m(r['lucro_rs']), lucro_pct=round(r['lucro_pct'] * 100, 2))
    return res


def _nome_projeto_wallbox(e, r: dict) -> str:
    """Rótulo da pasta, ex.: 'WALLBOX 7,4KW 220V F+F 18M'."""
    t = r['tecnico']
    ali = t['alimentacao_txt'].split('(')[-1].rstrip(')') if '(' in \
        t['alimentacao_txt'] else ''
    kw = engine.fmt_general(round(e.pot_kw, 2)).replace('.', ',')
    dist = (engine.fmt_general(round(e.distancia_m, 1)).replace('.', ',') + 'M'
            if e.distancia_m else '')               # a verificar: sem metros
    return _limpar_nome(f"WALLBOX {kw}KW {int(t['tensao'])}V {ali} {dist}",
                        'WALLBOX')


def _foto_mobi(d: dict, e) -> str | None:
    """Foto da Mobi para a pág. 2: a colada no orçamento, senão a padrão da
    linha escolhida (Box ou Plug, ⚙ Preços). Data URL ou None (sem foto o
    espaço fica como na arte)."""
    return (d.get('img_mobi')
            or _ler_img_padrao('mobi_plug' if e.mobi_linha == 'PLUG' else 'mobi_box'))


def _calcular_wallbox_para_pdf(d: dict):
    """Cálculo de quem vai virar PDF: Mobi sem preço não sai (o valor estaria
    errado para menos)."""
    import wallbox
    cfg = engine.carregar_config()
    e = _montar_wallbox(d)
    r = wallbox.calcular(e, cfg)
    if r['mobi'] is None:
        raise ValueError('Nenhum modelo Mobi serve para essas opções: ' +
                         ' '.join(r['avisos']))
    if r['mobi_sem_preco']:
        raise ValueError(f"A {r['mobi']['modelo']} está sem preço: cadastre em "
                         f"⚙ Preços (ou digite o preço da Mobi no orçamento).")
    return cfg, e, r


@app.get('/wallbox')
def pagina_wallbox():
    import wallbox
    cfg = engine.carregar_config()
    return render_template('wallbox.html', cfg=cfg, cw=wallbox.parametros(cfg),
                           papel=_papel(), pasta_wallbox=PASTA_WALLBOX,
                           consultor_nome=session.get('consultor', ''))


@app.get('/api/wallbox/fotos-padrao')
def api_wallbox_fotos_padrao():
    """Fotos padrão da Mobi Box e da Mobi Plug (data URLs ou null)."""
    return jsonify(ok=True, box=_ler_img_padrao('mobi_box'),
                   plug=_ler_img_padrao('mobi_plug'))


@app.post('/api/wallbox/fotos-padrao')
def api_wallbox_salvar_fotos_padrao():
    """Só admin (_rota_admin). Body {box, plug}: chave ausente = mantém;
    vazia = remove."""
    try:
        d = request.get_json(force=True) or {}
        for k in ('box', 'plug'):
            if k in d:
                _gravar_img_padrao('mobi_' + k, d.get(k))
        return jsonify(ok=True)
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/wallbox/calcular')
def api_wallbox_calcular():
    import wallbox
    try:
        cfg = engine.carregar_config()
        r = wallbox.calcular(_montar_wallbox(request.get_json(force=True)), cfg)
        return jsonify(ok=True, resumo=_resumo_wallbox(r, cfg))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/wallbox/previa')
def api_wallbox_previa():
    """PDF da proposta sem gravar pasta nem enviar ao Drive."""
    import tempfile
    import proposta_wallbox
    try:
        d = request.get_json(force=True) or {}
        _, e, r = _calcular_wallbox_para_pdf(d)
        fd, caminho = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        try:
            proposta_wallbox.gerar(r['textos'], caminho,
                                   foto=_img_bytes(_foto_mobi(d, e)))
            with open(caminho, 'rb') as f:
                pdf = f.read()
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
        resp = app.response_class(pdf, mimetype='application/pdf')
        resp.headers['Content-Disposition'] = 'inline; filename="PREVIA.pdf"'
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/wallbox/proposta')
def api_wallbox_proposta():
    """Calcula, grava a pasta do projeto (RESUMO, DADOS.json, PDF) em
    <orçamentos>/INSTALAÇÕES WALLBOX/<CLIENTE>/<WALLBOX …>/, envia ao Drive se
    configurado e devolve o PDF — igual à ação principal do solar."""
    import wallbox
    import proposta_wallbox
    try:
        d = request.get_json(force=True) or {}
        cfg, e, r = _calcular_wallbox_para_pdf(d)
        projeto = _nome_projeto_wallbox(e, r)
        cliente = _limpar_nome(e.nome, 'CLIENTE')
        pasta = os.path.join(_pasta_base(), PASTA_WALLBOX, cliente, projeto)
        os.makedirs(pasta, exist_ok=True)
        nome_pdf = _limpar_nome(e.nome, 'PROPOSTA') + ' - WALLBOX'

        txt_resumo = wallbox.resumo_texto(e, r, cfg)
        foto = _foto_mobi(d, e)
        # a MESMA foto do PDF fica solta na pasta (MOBI.jpg…); o import a devolve
        arq_foto = _gravar_img_projeto(pasta, 'mobi', foto)
        d_salvar = {k: v for k, v in d.items() if k != 'img_mobi'}
        d_salvar['tipo'] = 'wallbox'
        if _eh_consultor():                    # o que valeu de verdade
            d_salvar['consultor'] = e.consultor
        txt_dados = json.dumps(d_salvar, ensure_ascii=False, indent=1)
        with open(os.path.join(pasta, 'RESUMO.txt'), 'w', encoding='utf-8') as f:
            f.write(txt_resumo)
        with open(os.path.join(pasta, 'DADOS.json'), 'w', encoding='utf-8') as f:
            f.write(txt_dados)
        destino = os.path.join(pasta, f'{nome_pdf}.pdf')
        proposta_wallbox.gerar(r['textos'], destino, foto=_img_bytes(foto))

        aviso_drive, enviado_drive = None, False
        base_drive = (cfg.get('pasta_drive') or '').strip()
        if base_drive and drive.conectado():
            try:
                with open(destino, 'rb') as f:
                    pdf_bytes = f.read()
                drive.enviar_projeto(
                    base_drive, PASTA_WALLBOX, cliente, projeto,
                    [('RESUMO.txt', txt_resumo.encode('utf-8'), 'text/plain'),
                     ('DADOS.json', txt_dados.encode('utf-8'), 'application/json'),
                     (f'{nome_pdf}.pdf', pdf_bytes, 'application/pdf')]
                    + ([arq_foto] if arq_foto else []))
                enviado_drive = True
            except Exception as exc:                           # noqa: BLE001
                aviso_drive = str(exc)[:300]
        resp = send_file(destino, as_attachment=True,
                         download_name=f'{nome_pdf}.pdf')
        if enviado_drive:
            resp.headers['X-Drive-Enviado'] = '1'
        if aviso_drive:
            resp.headers['X-Drive-Aviso'] = \
                aviso_drive.encode('ascii', 'replace').decode('ascii')
        return resp
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


def _abrir_navegador():
    webbrowser.open(f'http://127.0.0.1:{PORTA}')


if __name__ == '__main__':
    threading.Timer(1.0, _abrir_navegador).start()
    ip = _ip_local()
    print(f'\n  Dimensionador S2V rodando em http://127.0.0.1:{PORTA}')
    if ip != '127.0.0.1':
        print(f'  📱 No celular (mesmo Wi-Fi): http://{ip}:{PORTA}')
    print('  (deixe esta janela aberta enquanto usa o programa)\n')
    app.run(host='0.0.0.0', port=PORTA, debug=False)
