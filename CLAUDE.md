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
   `compat_planilha: true` no config reproduz o comportamento antigo. (Modelar
   a subida do Fio B ano a ano na projeção ficou pendente: o Fio B vai a 90% em
   2028 e 2029 depende de nova convenção — não assumir 100%.)
3. **Preço/Wp sempre converge** (o B75 da planilha estava obsoleto).
4. **Fio B escalonado por ano** (2026=60% … 2029=100%).
5. **Tarifas TE/TUSD vêm da ANEEL Dados Abertos** (`online.buscar_tarifa_aneel`,
   endpoint `/api/aneel-tarifa`). A base pública "Tarifas de aplicação das
   distribuidoras" traz TE/TUSD **sem impostos** (R$/MWh → ÷1000), por
   distribuidora (`SigAgente`, cadastrado em `concessionarias.<nome>.aneel_sigla`),
   subgrupo e vigência — pega a linha "Tarifa de Aplicação", modalidade
   Convencional, classe do subgrupo (B1=Residencial/Residencial;
   B2=Rural/"Não se aplica"), demais campos "Não se aplica", vigência mais
   recente. Filtros por `datastore_search?filters=…` (a API **SQL** dá 400 —
   não usar). Nota histórica: a base antiga da ANEEL e o Luz na Tarifa davam
   400/403/409/TLS; o **portal Dados Abertos responde bem** (urllib→curl no
   `online._get_json`). **Cache offline:** cada busca bem-sucedida é gravada em
   `tarifas_cache.json` (data dir, gitignored); se a ANEEL cair, o endpoint
   devolve o **último registro salvo** (`cache:true`). O **padrão de segurança**
   de TE/TUSD (`_montar_entradas`, quando o campo vem vazio) também usa esse
   cache (COPEL-DIS|B1), não mais um número fixo desatualizado.
   **Sem botão:** escolher a concessionária no seletor da UC (`onchange`) já
   atualiza TE/TUSD (ANEEL → cache → tabela local) e o ICMS (da concessionária,
   `config.impostos.<sub>`); **COPEL é aplicada por padrão ao abrir** (via
   `aplicarConcAuto`, só quando a UC está vazia — não sobrescreve import).
   **PIS/COFINS NÃO são tocados** ao trocar de concessionária (ficam como o
   usuário deixou; backup nas pré-definições). Há um cache de sessão no front
   (`window._tarCache`) p/ não rebuscar a mesma conc/subgrupo.
   (O `/api/copel-verificar` ainda existe p/ o ICMS/resolução da COPEL, mas não é
   mais chamado no fluxo automático — o ICMS vem do `config`, offline-safe.)
   **PIS/COFINS não são automatizáveis** (alíquota efetiva mensal por
   distribuidora, sem API — cada uma publica em PDF/Power BI): ficam manuais nas
   pré-definições.
6. **Cartões da pág. 3 se reagrupam** quando falta string box e/ou bateria
   (sem buracos), e a garantia "BATERIA DE LÍTIO" some sem bateria.
7. **Valores medidos são sagrados**: geometrias em `layout.json`/`deco.json`
   (ex.: 7 círculos da timeline, raio 9pt, cy 776,6) foram medidas em pixels do
   PDF original. Se mexer, **remeça** — não chute.
8. **Abatimento limitado à geração (Lei 14.300).** A planilha creditava
   `compensado = faturado − disponibilidade` **sem** olhar a geração, o que
   superestimava a economia de sistemas **subdimensionados** (compensação
   <100%). Agora `compensado = min(faturado − disp, TRUNC(geração×%noturno))`
   (`engine.calcular`). Em sistemas 100%+ isso é um no-op → o `teste_planilha`
   fica idêntico. Isto também faz a regra do "maior valor" (disponibilidade ×
   Fio B) operar de verdade quando falta geração.
9. **Abatimento de ICMS na COPEL é assimétrico — de propósito.** Na **TE**
   abatida o crédito devolve o ICMS (`abat_te = te_com_imposto`) → a TE
   compensada zera. Na **TUSD** abatida o crédito **não** re-embute o ICMS
   (`abat_tusd = (TUSD − FioB)/(1−PIS−COFINS)`) → a TUSD compensada ainda paga
   ICMS. Essa assimetria é o que **reproduz a fatura real** (NEUZA = R$ 125,70).
   **NÃO "corrigir"** (tentamos aplicar o Convênio 16/2015 à TUSD e o valor caiu
   p/ R$ 104,69, divergindo da conta real — revertido). Se um estado tratar a
   **TUSD abatida COM ICMS**, isso vira regra por concessionária (a pesquisar/
   confirmar com fatura real) — ver "Como adicionar outra concessionária".

## Como adicionar outra concessionária / estado

O motor está preparado para outras concessionárias sem cirurgia:
- **Tarifas e impostos** já são por concessionária em
  `config.json → concessionarias.<nome>` (`tarifas.<subgrupo>` + `impostos`).
- **A regra que MAIS varia por estado — `abat_tusd_inclui_icms`:** a isenção da
  energia COMPENSADA (Convênio 16/2015) alcança a TUSD? `false` = COPEL/PR e RS
  (a TUSD abatida ainda paga ICMS; é o caso validado); `true` = SP (Decreto
  67.521/2023, vence 2026) e MG (a TUSD abatida fica 100% isenta). No motor é
  `UC.abat_tusd_inclui_icms`; padrão `false`. **É a alavanca principal ao
  cadastrar um estado.**
- **ICMS no CONSUMO por componente:** chaves `icms_sobre_te`/`icms_sobre_tusd`
  (`UC.icms_te`/`icms_tusd`, padrão `true`). Hoje TE e TUSD levam ICMS no consumo
  em todos os estados (STJ Tema 986); as alavancas existem só para o caso raro de
  liminar/regra diferente — **não** são a variação normal entre estados.
- **Fluxo já ligado ponta a ponta:** `/api/concessionarias` devolve as regras →
  `lerUC()` (index.html) lê a regra da concessionária **selecionada** em cada UC
  e a envia no payload (sem controle visível) → `_montar_entradas` (`_regra_bool`)
  a coloca na `UC`. Adicionar concessionária = **só** um bloco novo no
  `config.json`.
- ⚠ **Terreno em movimento e sem validação local:** STJ Tema 986, decretos
  estaduais com prazo (o de SP vence em 2026) e ações de restituição. Os valores
  cadastrados (SP/MG=`true`, PR/RS=`false`, SC/RJ a confirmar) e as alíquotas
  são aproximados — **confirme com uma fatura real** antes de usar em proposta.

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

### Deploy — CONCLUÍDO (no ar)

**URL de produção:** `https://dimensionador-563167083292.southamerica-east1.run.app`
(302 → `/login`, protegida pela senha do app). Abrir no celular e digitar a senha.

Projeto: ID **dimensionador-s2v** (número **563167083292**), dentro da organização
**s2vengenharia.com** (org ID **750768823445**). Região **southamerica-east1**.
Bucket **s2v-dimensionador-dados** montado em **/data**; contém `config.json`,
`google_oauth.json`, `google_token.json` (e, em uso, `clientes/`, `acesso.json`).

Como foi feito (Cloud Shell, na conta do usuário):
1. **Billing**: vinculada conta de faturamento ao projeto (era o bloqueio antigo).
2. **Serviços + bucket**: `gcloud services enable run/cloudbuild/storage/
   artifactregistry`; `buckets create gs://s2v-dimensionador-dados
   --location=southamerica-east1`; `roles/storage.objectAdmin` no bucket p/ o SA
   `563167083292-compute@developer.gserviceaccount.com`.
3. **Permissão de build**: o deploy por `--source` exigiu dar
   **`roles/cloudbuild.builds.builder`** ao mesmo SA `…-compute@…` (senão dá 403
   `storage.objects.get` no bucket `run-sources-…` durante "Uploading sources").
4. **Dados no bucket**: `gcloud storage cp` dos 3 arquivos p/ `gs://…/`.
5. **Deploy**: `gcloud run deploy dimensionador --source . --region
   southamerica-east1 --allow-unauthenticated --memory 1Gi
   --set-env-vars S2V_SECRET=<frase>,S2V_SENHA=<senha>
   --add-volume name=dados,type=cloud-storage,bucket=s2v-dimensionador-dados
   --add-volume-mount volume=dados,mount-path=/data`. **Usar o ID do projeto**
   (`gcloud config set project dimensionador-s2v`) — com o número dá erro.
6. **Acesso público**: `--allow-unauthenticated` foi barrado pela política de
   organização **Domain Restricted Sharing** (`iam.allowedPolicyMemberDomains`),
   que proíbe `allUsers`. Resolvido abrindo **exceção só neste projeto**: papel
   `roles/orgpolicy.policyAdmin` ao usuário na org, depois `org-policies
   set-policy` com `allowAll: true` em
   `projects/563167083292/policies/iam.allowedPolicyMemberDomains`; então
   `run services add-iam-policy-binding … --member=allUsers
   --role=roles/run.invoker` (esperar 1–2 min a política propagar).

**Reimplantar depois de mudar o código**: `git push`, e no Cloud Shell
`cd dimensionador-s2v-main && git pull && gcloud run deploy dimensionador
--source . --region southamerica-east1 …` repetindo os MESMOS `--set-env-vars`.
**Mantenha o `S2V_SECRET` igual** entre deploys — se mudar, todos os logins caem.
Notas: reconectar o Drive tem de ser no PC (OAuth Desktop só aceita localhost) —
o refresh token existente vale na nuvem.

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
**Fio B (R$/MWh)** e os **impostos federais (PIS/COFINS)**.
`GET/POST /api/config` gravam **só** as chaves em `CONFIG_EDITAVEL` (app.py); o
PIS/COFINS vai para `concessionarias.COPEL (PR).impostos` (B1/B2/padrão) +
`tarifas_padrao` **sem tocar em 'tarifas' nem no ICMS**. O resto do `config.json`
é preservado byte a byte. Importar projeto salvo também aceita um `DADOS.json`.

**O ICMS NÃO fica nas pré-definições** — varia por estado e vive em
`concessionarias.<nome>.impostos` (aplicado pela concessionária). Não existe
"ICMS rural" como alíquota: no PR o rural é a mesma alíquota, porém isento
(diferimento p/ produtor no CAD/PRO) — por isso o campo foi removido.

**PIS/COFINS mudam todo mês e são FEDERAIS** (iguais em todo o país): ficam no
editor, mantidos à mão. O botão "aplicar tarifas e impostos" da UC **não** mexe
em PIS/COFINS (só TE/TUSD da ANEEL e ICMS da concessionária). Ao salvar as
pré-definições, o PIS/COFINS novo é **aplicado a todas as UCs já abertas** na
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

- **Cálculo** → `python3 teste_planilha.py` (réplica exata da planilha) **e**
  `python3 teste_correcoes.py` (correções pós-planilha: abatimento parcial da
  Lei 14.300, Convênio ICMS 16/2015 e alavanca `icms_te`). Ambos DEVEM passar.
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
