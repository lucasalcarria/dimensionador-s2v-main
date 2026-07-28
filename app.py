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
from datetime import datetime

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

# caminhos liberados sem login (a própria tela de login e os estáticos)
_LIVRE = {'/login', '/logo.png', '/manifest.webmanifest', '/sw.js', '/qr.png'}


@app.before_request
def _exige_login():
    senha = _senha_acesso()
    if not senha:                                   # sem senha => sem login
        return None
    if session.get('auth') is True:
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
<p>Digite a senha de acesso.</p>
<input type=password name=senha autofocus placeholder="senha">
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
        if hmac.compare_digest(request.form.get('senha', ''), senha):
            session['auth'] = True
            session.permanent = True
            return redirect('/')
        erro = 'Senha incorreta.'
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
    partes = [f'{kwp}KWP', conexao, invs, (e.estrutura or '').upper()]
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


def _montar_entradas(d: dict) -> engine.Entradas:
    ucs = []
    for u in d.get('ucs', []):
        ucs.append(engine.UC(
            tipo=(u.get('tipo') or '').strip(),
            ilum_publica=_f(u.get('ilum_publica')),
            ligacao=u.get('ligacao') or 'MONOFASICO',
            consumos=[_f(x) for x in (u.get('consumos') or [0] * 12)],
            te=_f(u.get('te'), 0.27575),          # R$/kWh SEM impostos
            tusd=_f(u.get('tusd'), 0.36667),      # R$/kWh SEM impostos
            icms=_f(u.get('icms'), 19.0) / 100.0,       # tela usa %
            cofins=_f(u.get('cofins'), 5.8) / 100.0,
            pis=_f(u.get('pis'), 1.26) / 100.0,
            pct_noturno=_f(u.get('pct_noturno'), 65.0) / 100.0,
            bandeira=u.get('bandeira') or 'VERDE',
            uc_numero=str(u.get('uc_numero') or '').strip(),
            gd=(u.get('gd') or 'GD2').strip().upper()))
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
        entrada=_f(d.get('entrada')),
        desloc=_f(d.get('desloc')),
        comissao_pct=_f(d.get('comissao_pct')) / 100.0,
        seguro_pct=_f(d.get('seguro_pct')) / 100.0,
        margem_desejada=margem,
        fin_taxa_mes=_f(d.get('fin_taxa_mes'), 1.99),
        fin_parcelas=int(_f(d.get('fin_parcelas'), 60)),
        wp_manual=(None if d.get('wp_manual') in (None, '')
                   else _f(d.get('wp_manual'))),
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


def _resumo(r: dict, cfg: dict) -> dict:
    br = cfg.get('formato_ptbr', True)
    m = lambda v: engine.moeda(v, br)
    return dict(
        kwp=round(r['kwp'], 2),
        kwp_necessario=r['kwp_necessario'],
        modulos_sugeridos=r['modulos_sugeridos'],
        area_m2=round(r['area_m2'], 1),
        geracao_media=round(r['geracao_media'], 1),
        consumo_medio=round(r['consumo_medio'], 1),
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
        custo_mo_auto=m(r['custo_mo_auto']),
        custo_material_auto=m(r['custo_material_auto']),
        aliquota_usada_pct=round(r['aliquota_usada'] * 100, 2),
        tarifas_cheias=[(round(t, 4) if t is not None else None)
                        for t in r['tarifas_cheias']],
        textos=r['textos'])


# ------------------------------------------------------------------ rotas
@app.get('/')
def index():
    cfg = engine.carregar_config()
    return render_template('index.html', cfg=cfg,
                           perfis=list(cfg['perfis_irradiacao'].keys()))


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


@app.post('/api/calcular')
def api_calcular():
    try:
        cfg = engine.carregar_config()
        e = _montar_entradas(request.get_json(force=True))
        r = engine.calcular(e, cfg)
        return jsonify(ok=True, resumo=_resumo(r, cfg))
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


@app.get('/api/concessionarias')
def api_concessionarias():
    """Concessionárias: tarifas locais por subgrupo + alíquotas + subgrupos."""
    try:
        cfg = engine.carregar_config()
        conc = {}
        for nome, v in (cfg.get('concessionarias') or {}).items():
            imp = {}
            for sub, a in (v.get('impostos') or {}).items():
                imp[sub] = dict(
                    icms_pct=round(a.get('icms', 0) * 100, 2),
                    cofins_pct=round(a.get('cofins', 0) * 100, 2),
                    pis_pct=round(a.get('pis', 0) * 100, 2))
            conc[nome] = dict(impostos=imp,
                              tarifas=v.get('tarifas') or {},
                              site_tarifas=v.get('site_tarifas', ''),
                              site_tributos=v.get('site_tributos', ''),
                              fonte_impostos=v.get('fonte_impostos', ''))
        return jsonify(ok=True, concessionarias=conc,
                       subgrupos=cfg.get('subgrupos') or
                       [{'id': 'B1', 'rotulo': 'B1 – Residencial'}])
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


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
                   obs=f'atualizado pela tela em {datetime.now():%d/%m/%Y %H:%M}')
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
                   'financiamento_padrao', 'performance_ratio',
                   'perda_irradiacao', 'marcas_modulo', 'marcas_inversor',
                   'bandeiras', 'subgrupos', 'pasta_saida', 'pasta_drive')


def _impostos_copel(cfg: dict) -> dict:
    """Alíquotas atuais da COPEL (% já convertido) para o editor."""
    imp = ((cfg.get('concessionarias') or {}).get('COPEL (PR)') or {}) \
        .get('impostos') or {}
    base = imp.get('B1') or imp.get('padrao') or {}
    rural = imp.get('B2') or base
    return {'pis': round(base.get('pis', 0) * 100, 4),
            'cofins': round(base.get('cofins', 0) * 100, 4),
            'icms': round(base.get('icms', 0) * 100, 2),
            'icms_rural': round(rural.get('icms', 0) * 100, 2)}


@app.get('/api/config')
def api_config():
    """Devolve só os parâmetros de negócio que a tela pode editar."""
    try:
        cfg = engine.carregar_config()
        dados = {k: cfg.get(k) for k in CONFIG_EDITAVEL}
        dados['impostos_copel'] = _impostos_copel(cfg)
        dados['tem_senha'] = bool(_senha_acesso())
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
        if 'senha_acesso' in novos:
            ac = _ler_acesso()
            nova = (novos.get('senha_acesso') or '').strip()
            if nova:
                ac['senha'] = nova
            else:
                ac.pop('senha', None)
            _salvar_acesso(ac)
        caminho = engine.caminho_config()
        with open(caminho, encoding='utf-8') as f:
            cfg = json.load(f)                      # mantém ordem e comentários
        for k in CONFIG_EDITAVEL:
            if k in novos:
                cfg[k] = novos[k]
        # impostos vigentes da COPEL: PIS/COFINS/ICMS não são raspáveis (Power
        # BI), então são mantidos aqui à mão. Atualiza os impostos por subgrupo
        # e o padrão das novas UCs — SEM tocar em 'tarifas'.
        ic = novos.get('impostos_copel')
        if ic:
            pis = _f(ic.get('pis')) / 100.0
            cofins = _f(ic.get('cofins')) / 100.0
            icms = _f(ic.get('icms')) / 100.0
            icms_rural = _f(ic.get('icms_rural'), ic.get('icms')) / 100.0
            conc = cfg.setdefault('concessionarias', {}) \
                      .setdefault('COPEL (PR)', {})
            imp = conc.setdefault('impostos', {})
            for sub in ('B1', 'padrao'):
                imp.setdefault(sub, {}).update(
                    {'icms': icms, 'cofins': cofins, 'pis': pis})
            imp.setdefault('B2', {}).update(
                {'icms': icms_rural, 'cofins': cofins, 'pis': pis})
            tp = cfg.setdefault('tarifas_padrao', {})
            tp['pis'], tp['cofins'], tp['icms'] = pis, cofins, icms
        with open(caminho, 'w', encoding='utf-8') as f:      # 2 espaços: mesmo
            json.dump(cfg, f, ensure_ascii=False, indent=2)  # formato do arquivo
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
        return jsonify(ok=True, consultores=drive.listar_subpastas(base))
    except Exception as exc:                                    # noqa: BLE001
        return jsonify(ok=False, erro=str(exc), consultores=[])


@app.get('/api/resumos-salvos')
def api_resumos_salvos():
    """Lista os projetos que podem ser reabertos — qualquer pasta que tenha um
    DADOS.json, em qualquer profundidade (com ou sem o nível do consultor)."""
    base = _clientes_dir()
    itens = []
    for raiz, _dirs, arqs in os.walk(base):
        if 'DADOS.json' not in arqs:
            continue
        rel = os.path.relpath(raiz, base)
        partes = rel.split(os.sep)
        projeto = partes[-1]
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
            return jsonify(ok=True, dados=json.load(f))
    except Exception as exc:                                    # noqa: BLE001
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

        consultor = (d.get('consultor') or '').strip()
        pasta = _pasta_projeto(e, r, consultor)  # <base>/<consultor>/<cliente>/…
        nome_pdf = _limpar_nome(e.nome, 'PROPOSTA')
        imagens = {'modulo': _img_bytes(d.get('img_modulo')),
                   'inversor': _img_bytes(d.get('img_inversor'))}
        imagens = {k: v for k, v in imagens.items() if v}

        txt_resumo = resumo_texto.resumo_texto(e, cfg)
        txt_conf = conferencia_retorno.relatorio_conferencia(e, cfg)
        # DADOS.json repovoa a tela depois; as fotos (base64 grande) ficam fora
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
                     (f'{nome_pdf}.pdf', pdf_bytes, 'application/pdf')])
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
        # perda: a enviada pela tela ou a padrão do config (25 %)
        cfg = engine.carregar_config()
        perda = d.get('perda')
        if perda in (None, ''):
            perda = cfg.get('perda_irradiacao', 0.25)
        else:
            perda = _f(perda) / 100.0
        return jsonify(ok=True, **online.buscar_irradiacao(cidade, perda))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=f'Não foi possível buscar agora: {exc}'), 400


@app.get('/api/cep/<cep>')
def api_cep(cep):
    try:
        import online
        return jsonify(ok=True, **online.buscar_cep(cep))
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=f'Não foi possível buscar agora: {exc}'), 400


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
