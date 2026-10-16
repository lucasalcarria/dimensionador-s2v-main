# -*- coding: utf-8 -*-
"""
Testes do orçamento de CARREGADOR VEICULAR (wallbox.py, proposta_wallbox.py e
as rotas /api/wallbox/*). Independente da planilha solar.

    py teste_wallbox.py
"""
import copy
import math
import os
import sys
import tempfile

import engine
import wallbox

OK = FALHA = 0


def checa(nome, cond, detalhe=''):
    global OK, FALHA
    if cond:
        OK += 1
        print(f'  ok   {nome}')
    else:
        FALHA += 1
        print(f'  FALHA {nome} {detalhe}')


def perto(a, b, tol=0.005):
    return abs(a - b) <= tol


# preços fixos AQUI: o teste não pode depender do que o usuário edita na tela
CFG = copy.deepcopy(engine.carregar_config())
CFG['wallbox'] = copy.deepcopy(wallbox.parametros(CFG))
CFG['wallbox'].update({
    'aliquota_imposto': 0.08, 'margem_padrao': 0.30, 'mao_de_obra_base': 450.0,
    'mao_de_obra_por_metro': 12.0, 'art_rs': 106.0, 'folga_cabo_pct': 15,
    'queda_max_pct': 4, 'fator_disjuntor': 1.25, 'fator_correcao_iz': 1.0,
    'cabo_rs_m': {'2.5': 3.2, '4': 5.0, '6': 7.5, '10': 12.5, '16': 19.0,
                  '25': 30.0, '35': 42.0, '50': 60.0},
    'eletroduto_rs_m': 9.0, 'aterramento_rs': 190.0, 'miscelanea_rs': 90.0})
for i, m in enumerate(CFG['wallbox']['mobi']):     # preço de teste por modelo
    m['preco'] = 1000.0 + i


def preco_de(modelo_parcial):
    return next(m['preco'] for m in CFG['wallbox']['mobi']
                if m['modelo'] == modelo_parcial)


def calc(cfg=CFG, **kw):
    base = dict(nome='Teste', pot_kw=7.4, corrente_a=32, alimentacao='220_FF',
                distancia_m=15, aliquota=0.08, margem=0.30)
    base.update(kw)
    e = wallbox.EntradaWallbox(**base)
    return e, wallbox.calcular(e, cfg)


print('1. Dimensionamento (NBR 5410)')
_, r = calc()
t = r['tecnico']
checa('32 A → disjuntor 40 A (1º padrão ≥ 1,25 × 32)', t['disjuntor'] == 40)
checa('F+F: 2 condutores carregados → 6 mm² (Iz 41 A ≥ 40 A)', t['secao'] == 6)
checa('PE = fase até 16 mm²', t['secao_pe'] == 6)
checa('queda = 2·L·I·ρ/S/V = 1,64 %',
      perto(t['queda_pct'], 2 * 15 * 32 * 0.0225 / 6 / 220 * 100, 1e-9))
_, r = calc(distancia_m=60)
checa('60 m: a QUEDA manda — 6 mm² daria 6,5 %, sobe para 10 mm² (3,9 %)',
      r['tecnico']['secao'] == 10 and r['tecnico']['queda_pct'] <= 4)
_, r = calc(pot_kw=22, corrente_a=32, alimentacao='380_3FN', distancia_m=25)
t = r['tecnico']
checa('trifásico 32 A: 3 carregados, 6 mm² (36 A) < 40 A → 10 mm²',
      t['secao'] == 10 and t['disjuntor'] == 40 and t['n_fase'] == 4)
checa('queda trifásica usa √3',
      perto(t['queda_pct'], math.sqrt(3) * 25 * 32 * 0.0225 / 10 / 380 * 100, 1e-9))
_, r = calc(corrente_a=None, pot_kw=7.4)
checa('sem corrente de placa: I = P / V = 33,6 A',
      perto(r['tecnico']['ib'], 7400 / 220, 1e-9))
_, r = calc(secao_manual=4)
checa('seção manual menor que o disjuntor gera aviso',
      any('conduz' in a for a in r['avisos']))

_, r = calc(distancia_m=None)
_, r15 = calc(distancia_m=15)
checa('distância vazia: proposta diz A VERIFICAR NA VISITA',
      r['textos']['distancia'] == 'A VERIFICAR NA VISITA'
      and r['distancia_a_verificar'])
checa('distância vazia: custos estimados com a distância padrão (15 m) e aviso',
      perto(r['preco_venda'], r15['preco_venda'])
      and any('a verificar' in a for a in r['avisos']))

print('2. Escolha da CLAMPER Mobi')
_, r = calc()
checa('220 bifásico → Mobi Box 8 kW cinza sem medidor',
      r['mobi']['modelo'] == 'CLAMPER Mobi Box 220V 8kW Cinza')
_, r = calc(mobi_cor='PRETO', mobi_medidor=True)
checa('cor e medidor escolhem o modelo',
      r['mobi']['modelo'] == 'CLAMPER Mobi Box 220V 8kW Preto c/ Medidor'
      and r['custo_mobi'] == preco_de('CLAMPER Mobi Box 220V 8kW Preto c/ Medidor'))
_, r = calc(alimentacao='380_3FN', pot_kw=22)
checa('380 V trifásico → Mobi Box 26 kW', r['mobi']['pot_kw'] == 26)
_, r = calc(alimentacao='220_3F', pot_kw=11, corrente_a=None)
checa('220 V trifásico → Mobi Box 15 kW', r['mobi']['pot_kw'] == 15)
_, r = calc(mobi_linha='PLUG', mobi_tomadas='RESIDENCIAL + INDUSTRIAL')
checa('Mobi Plug com as duas tomadas → 8+5 kW', r['mobi']['pot_kw'] == 13
      and r['mobi']['tomadas'] == 'RESIDENCIAL + INDUSTRIAL')
_, r = calc(mobi_linha='PLUG', mobi_tomadas='RESIDENCIAL')
checa('Plug residencial (20 A) num carregador de 32 A → aviso',
      any('vai até 20 A' in a for a in r['avisos']))
_, r = calc(mobi_linha='PLUG', alimentacao='380_3FN', pot_kw=22)
checa('Mobi Plug não existe em 380 V → sem modelo e com aviso',
      r['mobi'] is None and any('Não há Mobi Plug' in a for a in r['avisos']))
_, r = calc(mobi_preco_manual=1500.0)
checa('preço da Mobi digitado no orçamento vale', r['custo_mobi'] == 1500)
sem = copy.deepcopy(CFG)
for m in sem['wallbox']['mobi']:
    m['preco'] = None
_, r = calc(cfg=sem)
checa('Mobi sem preço cadastrado → marcada e com aviso',
      r['mobi_sem_preco'] and any('Sem preço' in a for a in r['avisos']))

print('3. Custos resumidos')
_, r = calc()
cabo = 15 * 1.15 * (2 * 7.5 + 7.5)
checa('Material CA automático = cabos (2 fases + PE, folga 15 %) + eletroduto '
      '+ aterramento + miscelânea',
      perto(r['custo_material'], cabo + 15 * 9 + 190 + 90))
checa('mão de obra automática = 450 + 12 × 15 m', perto(r['custo_mo'], 630))
checa('custo direto = Mobi + Material CA + mão de obra + ART + deslocamento',
      perto(r['custo_direto'], r['custo_mobi'] + r['custo_material'] + 630 + 106))
_, r = calc(material_ca_manual=800.0, mo_manual=500.0, desloc=60.0)
checa('Material CA e mão de obra digitados valem',
      r['custo_material'] == 800 and r['custo_mo'] == 500)
checa('composição tem só os itens resumidos',
      [x[0] for x in wallbox.composicao(r)][1:] ==
      ['Material CA', 'Mão de obra', 'ART', 'Deslocamento', 'Comissão',
       'Seguro', 'Imposto'])
checa('composição soma o custo total',
      perto(sum(x[1] for x in wallbox.composicao(r)), r['custo_total']))
r2 = wallbox.calcular(wallbox.EntradaWallbox(pot_kw=7.4, corrente_a=32),
                      {'formato_ptbr': True})
checa('config SEM bloco wallbox (bucket da nuvem) usa o padrão do programa',
      r2['mobi'] is not None)

print('4. Preço — mesma lógica do solar')
_, r = calc(desloc=120, comissao_pct=0.03, seguro_pct=0.01)
preco = 1000.0                               # o laço do engine.preco_convergido
for _ in range(200):                         # com kit = 0
    preco = (r['custo_direto'] + preco * (0.08 + 0.03 + 0.01)) / (1 - 0.30)
checa('forma fechada = ponto fixo do laço do solar', perto(r['preco_venda'], preco))
checa('lucro líquido = margem pedida (30 %)', perto(r['lucro_pct'], 0.30, 1e-9))
checa('custo total + lucro = venda',
      perto(r['custo_total'] + r['lucro_rs'], r['preco_venda']))
_, r = calc(preco_venda_manual=5000.0)
checa('valor fixado: margem vira consequência',
      perto(r['lucro_rs'], 5000 - r['custo_direto'] - 5000 * 0.08))
_, r = calc(cartao_taxa_pct=12.4, cartao_parcelas=12)
checa('cartão: 12 × parcela = venda ÷ (1 − 12,4 %)',
      perto(r['parcela_cartao'] * 12, r['preco_venda'] / (1 - 0.124)))

print('5. Servidor (rotas, trava do consultor, pasta)')
os.environ['S2V_SENHA'] = 'teste-wallbox'
import app as appmod                                       # noqa: E402
tmp = tempfile.mkdtemp()
appmod.engine.carregar_config = lambda: copy.deepcopy(CFG)
appmod._pasta_base = lambda: tmp
appmod.drive.conectado = lambda: False
cli = appmod.app.test_client()
payload = dict(nome='Fulano', consultor='Ana', pot_kw=7.4, corrente_a=32,
               alimentacao='220_FF', distancia_m=15, margem_pct=30, aliquota_pct=8)
with cli.session_transaction() as s:
    s.update(auth=True, papel='admin')
j = cli.post('/api/wallbox/calcular', json=payload).get_json()
checa('admin calcula e vê a composição', j['ok'] and 'composicao' in j['resumo'])
venda_admin = j['resumo']['preco_venda_num']
j2 = cli.post('/api/wallbox/calcular', json=dict(payload, margem_pct=1)).get_json()
checa('admin muda a margem', j2['resumo']['preco_venda_num'] < venda_admin)
rv = cli.post('/api/wallbox/proposta', json=payload)
pasta = os.path.join(tmp, 'INSTALAÇÕES WALLBOX', 'Fulano', 'WALLBOX 7,4KW 220V F+F 15M')
checa('salva em <orçamentos>/INSTALAÇÕES WALLBOX/<cliente>/ (ignora o consultor)',
      rv.status_code == 200 and os.path.isfile(os.path.join(pasta, 'DADOS.json'))
      and not os.path.exists(os.path.join(tmp, 'Ana')))
lst = cli.get('/api/resumos-salvos?tipo=wallbox').get_json()['itens']
checa('Importar do carregador acha o orçamento; o do solar não',
      len(lst) == 1 and not cli.get('/api/resumos-salvos').get_json()['itens'])
enviados = []                                # Drive "conectado", sem rede
appmod.drive.conectado = lambda: True
appmod.drive.enviar_projeto = lambda *a, **k: enviados.append(a[:4])
CFG['pasta_drive'] = 'S2V ENGENHARIA/ORÇAMENTOS'
cli.post('/api/wallbox/proposta', json=payload)
checa('Drive recebe em ORÇAMENTOS/INSTALAÇÕES WALLBOX/<cliente>/<projeto>',
      enviados and enviados[-1] == ('S2V ENGENHARIA/ORÇAMENTOS', 'INSTALAÇÕES WALLBOX',
                                    'Fulano', 'WALLBOX 7,4KW 220V F+F 15M'))
appmod.drive.listar_subpastas = lambda base: ['ANDRÉ TAVARES', 'INSTALAÇÕES WALLBOX']
lst = cli.get('/api/drive/consultores').get_json()['consultores']
checa('solar: a pasta do carregador some da lista de consultores',
      lst == ['ANDRÉ TAVARES'])
checa('solar: "Instalacao wallbox" (sem acento, singular) também é barrado',
      appmod._eh_pasta_wallbox('Instalacao  wallbox')
      and not appmod._eh_pasta_wallbox('ANDRÉ TAVARES'))
import json as _json                                       # noqa: E402
solar = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'exemplos', 'fatura_real_grupo_b.json'),
                        encoding='utf-8'))
rv = cli.post('/api/proposta', json=dict(solar, consultor='INSTALAÇÕES WALLBOX'))
checa('solar: o servidor recusa salvar na pasta do carregador',
      rv.status_code == 400 and 'exclusiva' in rv.get_json()['erro'])
appmod.drive.conectado = lambda: False
appmod.engine.carregar_config = lambda: copy.deepcopy(sem)
rv = cli.post('/api/wallbox/previa', json=payload)
checa('Mobi sem preço NÃO gera PDF', rv.status_code == 400
      and 'sem preço' in rv.get_json()['erro'])
appmod.engine.carregar_config = lambda: copy.deepcopy(CFG)

print('5b. Foto da CLAMPER Mobi (pág. 1, ao lado do painel de proteção)')
import base64                                              # noqa: E402
import io                                                  # noqa: E402
from PIL import Image                                      # noqa: E402
from pypdf import PdfReader                                # noqa: E402


def _png(cor):
    b = io.BytesIO()
    Image.new('RGB', (40, 30), cor).save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def _imagens_pag1(pdf_bytes):
    rec = PdfReader(io.BytesIO(pdf_bytes)).pages[0]['/Resources'].get('/XObject', {})
    return sum(1 for v in rec.values() if v.get_object().get('/Subtype') == '/Image')


# as fotos PADRÃO vão para uma pasta temporária, nunca para as do usuário
appmod._caminho_img_padrao = (lambda qual, _d=tempfile.mkdtemp():
                              os.path.join(_d, appmod._IMG_PADRAO[qual]))
base_imgs = _imagens_pag1(cli.post('/api/wallbox/previa', json=payload).data)
rv = cli.post('/api/wallbox/previa', json=dict(payload, img_mobi=_png('red')))
checa('foto colada no orçamento vai para a pág. 1',
      _imagens_pag1(rv.data) == base_imgs + 1)
cli.post('/api/wallbox/fotos-padrao', json={'box': _png('blue'), 'plug': None})
fp = cli.get('/api/wallbox/fotos-padrao').get_json()
checa('foto padrão da Mobi Box grava; a da Plug fica vazia',
      fp['box'] and not fp['plug'])
rv = cli.post('/api/wallbox/previa', json=payload)
checa('sem foto no orçamento: vai a padrão da linha (Box)',
      _imagens_pag1(rv.data) == base_imgs + 1)
rv = cli.post('/api/wallbox/previa',
              json=dict(payload, mobi_linha='PLUG', mobi_tomadas='INDUSTRIAL'))
checa('Plug sem foto padrão: nenhuma foto (painel na largura toda)',
      _imagens_pag1(rv.data) == base_imgs)
rv = cli.post('/api/wallbox/proposta', json=dict(payload, img_mobi=_png('red')))
dados = open(os.path.join(pasta, 'DADOS.json'), encoding='utf-8').read()
checa('proposta salva MOBI.png na pasta e não põe a foto no DADOS.json',
      os.path.isfile(os.path.join(pasta, 'MOBI.png')) and 'img_mobi' not in dados)
imp = cli.post('/api/importar-resumo',
               json={'rel': os.path.relpath(pasta, tmp)}).get_json()
checa('importar devolve a foto da Mobi', bool(imp['dados'].get('img_mobi')))

with cli.session_transaction() as s:
    s.update(auth=True, papel='consultor', consultor='Ana')
rv = cli.post('/api/wallbox/fotos-padrao', json={'box': None})
checa('consultor NÃO troca as fotos padrão', rv.status_code == 403)
# a aba do carregador é SÓ do admin (pedido do usuário)
rv = cli.get('/wallbox')
checa('consultor: a página /wallbox volta para o solar',
      rv.status_code == 302 and rv.headers['Location'].endswith('/'))
barrado = all(cli.post(u, json=payload).status_code == 403 for u in
              ('/api/wallbox/calcular', '/api/wallbox/previa',
               '/api/wallbox/proposta'))
checa('consultor: calcular, prévia e proposta do carregador dão 403', barrado)
checa('consultor: Importar do carregador também é barrado',
      cli.get('/api/resumos-salvos?tipo=wallbox').status_code == 403)
checa('consultor: a aba some do cabeçalho do solar (so-admin)',
      'class="abas-topo so-admin"' in cli.get('/').data.decode())
with cli.session_transaction() as s:
    s.update(auth=True, papel='admin')
rv = cli.post('/api/wallbox/previa', json=payload)
checa('admin: prévia devolve PDF', rv.status_code == 200 and rv.data[:4] == b'%PDF')

print('6. PDF')
import proposta_wallbox                                    # noqa: E402
from pypdf import PdfReader                                # noqa: E402
_, r = calc(nome='Maria Teste', modelo='Intelbras EVE', cidade='Maringá - PR')
fd, arq = tempfile.mkstemp(suffix='.pdf')
os.close(fd)
proposta_wallbox.gerar(r['textos'], arq)
pdf = PdfReader(arq)
texto = ''.join(p.extract_text() for p in pdf.pages)
os.remove(arq)
checa('2 páginas', len(pdf.pages) == 2)
checa('nenhum campo "[...]" sobrando', '[' not in texto)
checa('nome e valor impressos', 'MARIA TESTE' in texto
      and r['textos']['valor'] in texto)

print(f'\n{OK} ok, {FALHA} falha(s)')
sys.exit(1 if FALHA else 0)
