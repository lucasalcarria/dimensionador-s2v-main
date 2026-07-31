# Dimensionador S2V — contexto do projeto

Programa **offline** (Flask local, porta 8177) que substitui a planilha Excel de
dimensionamento fotovoltaico da S2V Engenharia. Gera a proposta comercial em PDF
de 5 páginas sobre o layout original da empresa.

**Responda sempre em português (pt-BR).** O usuário é engenheiro, não programador:
explique o *porquê* das mudanças em linguagem simples e evite jargão.

## Regra número 1

`engine.py` é uma **réplica validada da planilha**. `teste_planilha.py` tem 80+
verificações que batem centavo a centavo com ela.

```bash
python3 teste_planilha.py     # DEVE passar 100% antes de qualquer entrega
```

Se um ajuste quebrar esse teste, **o ajuste está errado** — não o teste. Nunca
"conserte" o teste para acomodar código novo sem antes confirmar com o usuário.

### Caso de validação (NEUZA ZAMFERRARI)
UC 16285387, Mandaguaçu-PR, consumos `[344,384,256,250,300×8]`, ilum. 38,7,
BIFÁSICO, 6× ASTRONERGY N-TYPE 620W, CHINT 3kW 220V, kit R$ 4.974,72,
FIBROCIMENTO, perfil 3.8, margem 16% →
**venda R$ 8.193,08 · fatura_sem R$ 403,32 · fatura_com R$ 125,70 · economia R$ 277,62**

## Arquitetura

| Arquivo | Papel |
|---|---|
| `engine.py` | motor de cálculo (réplica da planilha) — o coração |
| `proposta.py` | PDF: overlay ReportLab sobre `assets/fundo.pdf` |
| `app.py` | servidor Flask + endpoints REST |
| `templates/index.html` | UI inteira (HTML+CSS+JS num arquivo só) |
| `online.py` | internet opcional: CEP, irradiação (NASA), site da COPEL |
| `conferencia_retorno.py` | relatório passo a passo do retorno financeiro |
| `resumo_texto.py` | resumo salvo na pasta do cliente |
| `teste_planilha.py` | suíte de validação contra a planilha |
| `config.json` | parâmetros de negócio (editável pelo usuário) |
| `ferramentas/html_para_fundo.py` | build: converte o HTML do design em `fundo.pdf` + `layout.json` + cartões |
| `MAPA-PROPOSTA.md` | de onde sai cada número impresso na proposta |

`assets/`: `fundo.pdf` (arte + textos fixos), `layout.json` (posição de cada
campo), `cards/` (tiles 600dpi dos cartões da pág. 3 + `layout_cards.json`),
`deco.json` (banda de fotos da pág. 3), `fonts/`, `logo.png`.
`assets/_v1/` guarda o fundo/layout antigos, só como referência.

## O layout vem do HTML do design

`assets/fundo.pdf` e `assets/layout.json` **não são editados à mão**: são
gerados a partir do HTML que o design entrega (`proposta_s2v.html`).

```bash
python ferramentas/html_para_fundo.py ~/Downloads/proposta_s2v.html
```

O HTML traz o SVG da arte em coordenadas de PDF (viewBox 595,32 × 841,92) e cada
texto com `left`/`top` em px. O conversor: redesenha o SVG em vetor com
ReportLab, calcula a linha de base pela regra do CSS `line-height:1`
(`base = topo + k × tamanho`, com k medido nas fontes embutidas), separa os
textos **fixos** (vão para o fundo) dos **calculados** (viram campos do
`layout.json`), e recorta os 6 cartões da pág. 3 como peças soltas.

Quando chegar um HTML novo, é só rodar o conversor de novo. Se aparecer um campo
calculado novo, acrescente a linha correspondente em `CAMPOS` dentro dele.
Só precisa de `pypdfium2`, `fontTools` e `brotli` — **no build, não no programa**.

## Decisões que NÃO devem ser revertidas

1. **% noturno**: a GERADORA usa o valor informado (ex. 0,65); toda
   **BENEFICIÁRIA usa sempre 1,0 (100%)**. Vem da planilha (M32:M39 =
   `SE(tipo="BENEFICIÁRIA";1;…)`). Está em `UC.pct_noturno_efetivo`.
2. **Retorno de 25 anos**: economia mensal × 12 projetada (reajuste 5% a.a. a
   partir do ano 2, degradação 2,5%/0,7%). A planilha original tinha um bug
   (dividia a tarifa por 9 via COUNTA) que dava R$ 16.651 em vez de ~R$ 141 mil.
   `compat_planilha: true` no config reproduz o comportamento antigo.
3. **Preço/Wp sempre converge** (o B75 da planilha estava obsoleto).
4. **Fio B escalonado por ano** (2026=60% … 2029=100%).
5. **ANEEL foi removida de propósito.** Tentamos a base de dados aberta e o
   portal Luz na Tarifa: deram 400, 403, 409 e queda de handshake TLS na máquina
   do usuário. **Não tente reintroduzir.** As tarifas vivem numa **tabela local**
   em `config.json → concessionarias.<nome>.tarifas.<subgrupo>` (TE/TUSD **sem**
   impostos), atualizada pela tela ("atualizar valores…"), que converte de
   "com impostos" usando `sem = com × (1−ICMS) × (1−PIS−COFINS)`.
   Do site da COPEL raspamos só HTML de verdade: resolução/vigência e ICMS
   (a tabela de tarifas de lá é um Power BI embutido — não é raspável).
   **O botão "aplicar tarifas e impostos" de cada UC** aplica a tabela local de
   TE/TUSD *e* busca o ICMS vigente no site da COPEL (`/api/copel-verificar`);
   se o site cair, usa o ICMS da tabela local. O antigo botão "atualizar
   valores…" (modal de colar tarifas) foi removido — TE/TUSD se editam direto
   nos campos da UC ou pelo `config.json`.
6. **Cartões da pág. 3 se reagrupam** quando falta string box e/ou bateria
   (sem buracos), e a garantia "BATERIA DE LÍTIO" some sem bateria.
7. **Valores medidos são sagrados**: geometrias em `layout.json`/`deco.json`
   (ex.: 7 círculos da timeline, raio 9pt, cy 776,6) foram medidas em pixels do
   PDF original. Se mexer, **remeça** — não chute.

## Cliente, UCs e salvamento (app.py + index.html)

- **Endereço** é dividido em dois campos: `endereco` (logradouro) e `numero`.
  Na proposta eles voltam juntos ("Rua X, 123") em `_textos()`.
- O **nº da UC** não fica mais em Cliente: cada Unidade Consumidora tem o seu
  (`UC.uc_numero`). Na capa a proposta lista todos juntos ("12345, 23456, …").
- Cada UC escolhe **consumo médio (rápido) OU mês a mês** — nunca os dois. O
  gráfico da pág. 4 usa `resultado['consumo_mensal']` (reto ou variável conforme
  o que foi digitado).
- **Um único botão** ("Gerar proposta e salvar") faz tudo: calcula, gera o PDF e
  grava o projeto. Cada projeto vai para uma **subpasta nomeada**
  `<base>/<CONSULTOR>/<NOME>/<7,44KWP ONGRID CHINT 5K 220V COLONIAL>/` contendo
  `RESUMO.txt`, `CONFERENCIA.txt`, `DADOS.json` e `<nome>.pdf`. O rótulo do
  projeto sai de `app._nome_projeto()` (kWp + conexão + inversores + estrutura);
  o **consultor** é um campo livre em Cliente (`app._pasta_projeto` insere esse
  nível só quando preenchido). O botão **Importar projeto** varre a base em
  qualquer profundidade (`os.walk`, procura `DADOS.json`) e repovoa via `aplicar()`.
- **Pasta base configurável** (`config.pasta_saida`, editável nas pré-definições):
  vazio = `clientes/` local; pode apontar para uma pasta do Google Drive para
  Desktop (ex.: `G:\Meu Drive\ORÇAMENTOS`). Cai no local se o caminho não existir.

## Acesso remoto / login (app.py)

Para expor na internet (uso via dados móveis). Login é **opcional**: só é exigido
quando há senha. A senha e a chave de sessão ficam em **`acesso.json`**
(gitignored — NUNCA no `config.json`, que é versionado). Também aceita
`S2V_SENHA`/`S2V_SECRET` por variável de ambiente (úteis na nuvem). A senha é
editável na aba **⚙ Pré-definições → Segurança** (o POST `/api/config` grava a
chave `senha_acesso` em `acesso.json`, não no config). Sem senha, o uso local não
pede nada (e `teste_planilha`, que não usa HTTP, fica intacto).
`@app.before_request` protege tudo; `/login`, estáticos e `/icons/` ficam livres;
rotas `/api/*` sem sessão devolvem 401. `_obter_secret()` guarda uma chave de
sessão estável em `acesso.json` (o login não cai a cada reinício).
## Google Drive (OAuth) — `drive.py`

Envia as propostas para uma pasta do Drive (para ver no celular). Sem
dependências novas — só `urllib`, no estilo do `online.py`.
- **Credencial**: `google_oauth.json` (tipo *Desktop*, do Google Cloud) na raiz
  do projeto. Gitignored, junto com `google_token.json` (o refresh token).
- **Conectar** (uma vez, no PC): botão nas pré-definições → `/oauth2/start`
  (redirect ao Google) → `/oauth2/callback` troca o code por tokens
  (`drive.trocar_codigo`). `_access_token()` renova sozinho pelo refresh token.
- **Escopo**: `auth/drive` (achar ORÇAMENTOS pelo nome + criar/enviar) + email.
- **Salvamento**: `/api/proposta` grava local (backup) **e**, se `pasta_drive`
  (nome da pasta base no Drive, ex. "ORÇAMENTOS") estiver definido e o Drive
  conectado, envia para `pasta_drive/<consultor>/<cliente>/<projeto>/` via
  `drive.enviar_projeto`. Falha no Drive **não** quebra a geração (vai num
  header `X-Drive-Aviso`). `/api/drive/status` e `/api/drive/desconectar`
  cuidam do estado. Import ainda lê da pasta LOCAL.
- **Nuvem**: a autorização única precisa de navegador (feita no PC); o refresh
  token resultante vale no Cloud Run também.

## Cloud Run (rodar sem depender do PC)

`engine.dir_execucao()` obedece a **`S2V_DATA_DIR`**: é a alavanca única — TODOS
os arquivos mutáveis (config.json editável, `clientes/`, `google_oauth.json`,
`google_token.json`, `acesso.json`) saem dela. No Cloud Run monta-se um **bucket
do Cloud Storage** em `/data` e `S2V_DATA_DIR=/data`, então tudo persiste (o
disco do Cloud Run é efêmero). Localmente a variável fica vazia → pasta do
programa, comportamento igual ao de sempre.
- **Dockerfile** + **.dockerignore** na raiz; `requirements.txt` inclui
  `gunicorn` (só no container Linux — `sys_platform != win32`). CMD roda
  `gunicorn … app:app` ligado a `$PORT`. O `python app.py` local (Flask dev +
  browser) não é usado no container (gunicorn importa `app:app`, não roda
  `__main__`).
- **Segredos na nuvem**: `S2V_SENHA` + `S2V_SECRET` como variáveis de ambiente;
  Drive lê `google_oauth.json`/`google_token.json` do bucket (data dir).
- **Deploy**: `gcloud run deploy --source .` (Cloud Build) com o bucket montado.

### Deploy — EM ANDAMENTO (retomar daqui)

Código já **commitado e no GitHub** (`github.com/lucasalcarria/dimensionador-s2v-main`,
branch `main`, commit `1d624e3` "Prepara para Cloud Run"). Falta só o deploy, que
roda na conta Google do usuário via **Cloud Shell** (nada instalado no PC).
Projeto do Google Cloud: número **563167083292** (o mesmo do OAuth do Drive).
Região escolhida: **southamerica-east1**. Bucket: **s2v-dimensionador-dados**
(montar em **/data**).

**BLOQUEIO ATUAL:** o projeto **não tem faturamento (billing) ativado** — o
`gcloud services enable` e o `buckets create` deram `billing-enabled / 
UREQ_PROJECT_BILLING_NOT_FOUND`. O usuário precisa **vincular uma conta de
faturamento** (cartão) ao projeto no Console (Faturamento → Vincular conta).
Cloud Run é grátis no volume dele, mas o Google exige cartão cadastrado.

Passos que faltam (depois do billing):
1. **Etapa 1** (refazer): no Cloud Shell, `git clone` do repo, `cd` nele,
   `gcloud services enable run/cloudbuild/storage/artifactregistry`,
   `gcloud storage buckets create gs://s2v-dimensionador-dados --location=southamerica-east1`,
   e dar `roles/storage.objectAdmin` no bucket para o SA
   `${PROJNUM}-compute@developer.gserviceaccount.com`.
2. **Etapa 2**: subir ao bucket os 3 arquivos do PC — `config.json`,
   `google_oauth.json`, `google_token.json` (os dois últimos são segredos,
   gitignored; sobem pelo botão de upload do Cloud Shell + `gcloud storage cp … gs://…/`).
3. **Etapa 3** (deploy):
   `gcloud run deploy dimensionador --source . --region southamerica-east1
   --allow-unauthenticated --memory 1Gi
   --set-env-vars S2V_SECRET=<frase>,S2V_SENHA=<senha>
   --add-volume name=dados,type=cloud-storage,bucket=s2v-dimensionador-dados
   --add-volume-mount volume=dados,mount-path=/data`.
   Dá um URL `https://…run.app` fixo → abre no celular, pede a senha.
Notas: `--allow-unauthenticated` (protegido pela senha do app); reconectar o
Drive tem de ser no PC (OAuth Desktop só aceita localhost) — o refresh token já
existente vale na nuvem. Não consigo testar o deploy (conta do usuário): ir por
etapas e ler os erros.

## Inversores (1 ou vários)

`Entradas.inversores` é uma lista `[{marca,pot_kw,tensao,qtd}]`. Quando vazia,
cai nos campos legados `marca_inversor/pot_inversor_kw/tensao_inversor` — é o que
a planilha de validação usa, então `teste_planilha` continua idêntico. Use
`e.lista_inversores()`, `e.qtd_inversores`, `e.tem_380v()` e `e.tem_micro()`.
Cada inversor tem um **toggle micro/string** na tela (`iv.micro`); micro dá
garantia padrão de 12 anos (`_marca_micro()` também detecta pela marca). O único
ponto do cálculo que depende do inversor é `_trafo()` (autotrafo por inversor ≥12 kW/380 V,
somado). Há ainda `Entradas.custo_380v`: custo manual em reais que entra na
composição quando há inversor 380 V (campo condicional na tela, entre Entrada e
Deslocamento). A UI manda os inversores como lista e repete o 1º nos campos
legados por segurança.

## Editor de pré-definições (⚙ no cabeçalho)

O botão **⚙ Pré-definições** abre um editor das constantes herdadas da planilha:
imposto, mão de obra (mínima/por módulo), tabela de material (markup + faixas),
garantias fixas, autotrafo 380 V, bandeiras, listas de marcas, financiamento,
**Fio B (R$/MWh)** e os **impostos vigentes da COPEL (PIS/COFINS/ICMS)**.
`GET/POST /api/config` gravam **só** as chaves em `CONFIG_EDITAVEL` (app.py); os
impostos vão para `concessionarias.COPEL (PR).impostos` + `tarifas_padrao` **sem
tocar em 'tarifas'**. O resto do `config.json` (comentários, tabela de tarifas) é
preservado byte a byte. Importar projeto salvo também aceita um `DADOS.json` do
computador.

**PIS/COFINS mudam todo mês e NÃO são raspáveis** (a página de tributos da COPEL
também é Power BI). Por isso ficam no editor de pré-definições, mantidos à mão; o
botão "aplicar tarifas e impostos" da UC passa a usar esses valores. Ao salvar as
pré-definições, os impostos novos são **aplicados a todas as UCs já abertas** na
tela e a tabela de concessionárias é relida (antes o usuário precisava reabrir).
Deixe os campos de **garantia vazios** para usar as regras automáticas da
planilha — preencher fixa o valor. O `/api/config` grava com **indent=2** (mesmo
formato do arquivo do usuário) para não gerar ruído de diff.

## Irradiação da internet (perda editável)

`online.buscar_irradiacao(cidade, perda)` busca a global horizontal (NASA POWER)
e aplica a **perda** (`config.perda_irradiacao`, padrão 0,25 = 25 %), trazendo o
valor para a mesma convenção dos perfis pré-definidos (Maringá GHI 5,02 × 0,75 ≈
3,8). A perda é editável nas pré-definições e por busca (campo "Perda %" ao lado
de "buscar"). Retorna também `ghi_dia_kwh` (bruto) e `perda`.

## GD1 × GD2 por UC

`UC.gd` ('GD1' ou 'GD2', padrão **GD2**). GD2 paga o Fio B escalonado (Lei
14.300, comportamento validado). GD1 é isenta de Fio B até 2045 → compensa a TUSD
integral (`fio_b_uc = 0` na fatura daquela UC). Cada UC escolhe na tela; a de
validação usa o default GD2, então `teste_planilha` segue idêntico.

## Próximo passo combinado

Anexar **faturas de energia** (PDF da 2ª via ou foto) para extrair os dados da UC
automaticamente (consumo, tarifas, nº da UC, ligação). Ainda não implementado.

## Dados do usuário (nunca versionar / nunca sobrescrever)

`clientes/`, `propostas/` e caches estão no `.gitignore`. **Não** os apague nem
sobrescreva. `config.json` **é versionado** mas o usuário edita as tarifas por
lá — ao mexer nele, prefira acrescentar chaves a reescrever o arquivo.

## Como verificar mudanças

- **Cálculo** → `python3 teste_planilha.py`
- **PDF** → gere e confira por pixels/OCR (`pdftoppm -r 150` + PIL/pytesseract).
  Não confie em "parece certo": meça.
- **UI** → o JS é validado com `node --check` (remova as tags Jinja antes).
- **Servidor** → suba numa porta de teste e chame os endpoints; não deixe
  processos pendurados.

## Estilo

Código e comentários em português, com referência à célula da planilha quando
aplicável (ex.: `# PR!N31`). Sem dependências novas sem necessidade real
(hoje: flask, reportlab, pypdf, matplotlib, qrcode).

## Pendências combinadas

- **PWA**: adicionar `manifest.json` + service worker para virar ícone na tela
  do celular (o acesso via rede local e o QR code já funcionam).
- Se `config.json` der conflito no Git, separar as tarifas do usuário num
  arquivo próprio fora do versionamento.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
