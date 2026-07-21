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

from flask import (Flask, jsonify, render_template, request, send_file,
                   send_from_directory)

import engine
import proposta

BASE = os.path.dirname(os.path.abspath(__file__))
PROPOSTAS = os.path.join(engine.dir_execucao(), 'propostas')
CLIENTES = os.path.join(engine.dir_execucao(), 'clientes')
PORTA = 8177

app = Flask(__name__)


def _clientes_dir() -> str:
    os.makedirs(CLIENTES, exist_ok=True)
    return CLIENTES


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
            bandeira=u.get('bandeira') or 'VERDE'))
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
        cidade=(d.get('cidade') or '').strip(),
        uc_numero=str(d.get('uc_numero') or '').strip(),
        ucs=ucs,
        qtd_modulos_kit=int(_f(d.get('qtd_modulos_kit'))),
        marca_inversor=(d.get('marca_inversor') or '').strip(),
        pot_inversor_kw=_f(d.get('pot_inversor_kw')),
        tensao_inversor=int(_f(d.get('tensao_inversor'), 220)),
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


@app.post('/api/salvar-resumo')
def api_salvar_resumo():
    """Salva o resumo dos resultados (e a conferência) na pasta do cliente."""
    try:
        import resumo_texto
        import conferencia_retorno
        cfg = engine.carregar_config()
        d = request.get_json(force=True)
        incluir_conf = bool(d.pop('_incluir_conferencia', True))
        e = _montar_entradas(d)
        nome = re.sub(r'[^\w \-À-ÿ]', '', e.nome).strip() or 'CLIENTE'
        pasta = os.path.join(_clientes_dir(), nome)
        os.makedirs(pasta, exist_ok=True)
        carimbo = datetime.now().strftime('%Y-%m-%d_%H%M')

        arquivos = []
        cam_res = os.path.join(pasta, f'RESUMO {carimbo}.txt')
        with open(cam_res, 'w', encoding='utf-8') as f:
            f.write(resumo_texto.resumo_texto(e, cfg))
        arquivos.append(cam_res)

        if incluir_conf:
            cam_conf = os.path.join(pasta, f'CONFERENCIA {carimbo}.txt')
            with open(cam_conf, 'w', encoding='utf-8') as f:
                f.write(conferencia_retorno.relatorio_conferencia(e, cfg))
            arquivos.append(cam_conf)

        return jsonify(ok=True, pasta=pasta,
                       arquivos=[os.path.basename(a) for a in arquivos])
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/proposta')
def api_proposta():
    try:
        cfg = engine.carregar_config()
        d = request.get_json(force=True)
        e = _montar_entradas(d)
        r = engine.calcular(e, cfg)
        nome = re.sub(r'[^\w \-À-ÿ]', '', e.nome).strip() or 'PROPOSTA'
        # salva na pasta do cliente (e mantém cópia em propostas/)
        pasta = os.path.join(_clientes_dir(), nome)
        os.makedirs(pasta, exist_ok=True)
        os.makedirs(PROPOSTAS, exist_ok=True)
        destino = os.path.join(pasta, f'{nome}.pdf')
        imagens = {'modulo': _img_bytes(d.get('img_modulo')),
                   'inversor': _img_bytes(d.get('img_inversor'))}
        imagens = {k: v for k, v in imagens.items() if v}
        proposta.gerar_proposta(r, destino, imagens=imagens or None)
        try:
            import shutil
            shutil.copy(destino, os.path.join(PROPOSTAS, f'{nome}.pdf'))
        except OSError:
            pass
        return send_file(destino, as_attachment=True,
                         download_name=f'{nome}.pdf')
    except Exception as exc:                                   # noqa: BLE001
        return jsonify(ok=False, erro=str(exc)), 400


@app.post('/api/irradiacao')
def api_irradiacao():
    try:
        import online
        cidade = (request.get_json(force=True).get('cidade') or '').strip()
        if not cidade:
            raise ValueError('Informe a cidade.')
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
