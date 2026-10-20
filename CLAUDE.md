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
(Já houve **uma** exceção autorizada: a regra do maior valor, decisão 10/11 —
uma fatura real provou que a planilha cobrava dobrado. Os valores alterados
estão marcados com comentário no próprio teste.)

### Caso de validação (CLIENTE PLANILHA)
UC 00000000, Cidade Exemplo-PR, consumos `[344,384,256,250,300×8]`, ilum. 38,7,
BIFÁSICO, 6× ASTRONERGY N-TYPE 620W, CHINT 3kW 220V, kit R$ 4.974,72,
FIBROCIMENTO, perfil 3.8, margem 16% →
**venda R$ 8.193,08 · fatura_sem R$ 403,32 · fatura_com R$ 92,79 · economia R$ 310,53**
⚠ A planilha dava **R$ 125,70 / R$ 277,62** aqui. Esses dois números foram
**corrigidos** (ver "Regra do maior valor", decisão 10) — o resto do caso segue
batendo com a planilha célula a célula.

### Caso de validação do GRUPO B contra FATURA REAL (FATURA-B — COPEL, 09/2026)
UC 000000000000002, Cidade Exemplo-PR, B1 bifásico, **total R$ 117,53** (travado em
`teste_correcoes.py`, seção 1b). Consumo medido **307 kWh**; a usina que ele já
tem injetou **430 kWh** (registrador GERAC) e os 307 foram compensados
**inteiros** — a TE zera na fatura (128,20 − 128,20 = 0). O custo de
disponibilidade não aparece porque a sobra de Fio B (R$ 78,83) é **maior** que
ele (R$ 51,59). Tarifas s/ tributos: TE 0,310850 · TUSD 0,457170; ICMS 19 %,
PIS 1,4485 %, COFINS 6,6555 %; bandeira AMARELA (cobrada e devolvida se anulam);
COSIP R$ 38,70. **Fio B desta fatura: 0,128739 R$/kWh** (a linha "ENERGIA
INJETADA TUSD" devolve 0,328431 contra 0,457170 da cheia), o que a 60 % implica
um Fio B cheio de **~214,6 R$/MWh** — bem acima dos 159,14 que o `config.json`
trazia. **O Fio B vem SEMPRE das pré-definições**; os testes fixam o seu valor
internamente para não travar a edição do usuário.

### Caso de validação do GRUPO A (ALIMENTOS FATURA-A — A4 Verde, COPEL/PR)
UC 000000000000001, Cidade Exemplo-PR, ref. **09/2026**, **total R$ 17.648,07** (a
fatura fecha centavo a centavo em `teste_grupo_a.py`, seção 10). Consumo 1.039
kWh ponta + 18.434 fora ponta; **5.490 kWh injetados** (usina 135 kW, **GD1**);
demanda contratada 175 kW mas **faturada 167,47 kW** × R$ 25,33/kW; bandeira
AMARELA; COSIP R$ 132,37; reativo excedente R$ 424,24. ICMS 19 %, PIS 1,44 %,
COFINS 6,63 %. Tarifas s/ tributos: TE P 0,475500 · TUSD P **1,463390** (é assim
a modalidade Verde: a ponta é cara no kWh, não na demanda) · TE FP 0,295750 ·
TUSD FP 0,146590. O motor dá R$ 17.648,01 — os 6 centavos são o arredondamento
de cada linha pela COPEL.

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
| `teste_correcoes.py` | suíte das correções pós-planilha (grupo B) |
| `teste_grupo_a.py` | suíte do grupo A (média tensão) |
| `config.json` | parâmetros de negócio (editável pelo usuário) |
| `ferramentas/html_para_fundo.py` | build: converte o HTML do design em `fundo.pdf` + `layout.json` + cartões |
| `MAPA-PROPOSTA.md` | de onde sai cada número impresso na proposta |
| `ferramentas/icones_traco.py` | build: SVG (Lucide/Tabler/marca) → `assets/icones_traco.json` |
| `ferramentas/previa.py` | antes × depois da proposta e conferência das caixas dos ícones |
| `ferramentas/recolorir_titulos.py`, `padronizar_linhas.py` | cirurgias idempotentes no `fundo.pdf` |
| `ferramentas/conferir_aneel.py` | confere tarifas, Fio B e TUSD-G contra a ANEEL (manual, online) |
| `exemplos/` | JSONs anonimizados que reproduzem faturas reais + `BRIEFING-HELENA.md` |
| `wallbox.py` | motor do orçamento de **carregador veicular** (dimensionamento + preço) |
| `proposta_wallbox.py` | PDF de 2 págs. do carregador, sobre `assets/wallbox/fundo.pdf` |
| `templates/wallbox.html` | tela da aba "🔌 Carregador" (`/wallbox`) |
| `teste_wallbox.py` | suíte do carregador (técnica, preço, trava do consultor, PDF) |
| `ferramentas/wallbox_fundo.py` | build: apaga os campos `[...]` do PDF do design → `fundo.pdf` |

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
Só precisa de `pypdfium2`, `fontTools`, `brotli` e (para os ícones) `potracer`
+ `numpy` — **no build, não no programa**.

### ⚠ O build completo NÃO reproduz os assets atuais
Verificado em 06/10/2026: rodar `html_para_fundo.py` sobre o HTML do design
**altera `fundo.pdf` e `layout.json`** — a pág. 5 (layout do pagamento no cartão,
campo `cartao_parcela_txt`, posição do `valor_venda`) foi ajustada **à mão**
depois do último build. Um build completo apaga esses ajustes — e também a
**cor dos títulos de seção** (revisão de design B1: todos VERDES, só o "KIT
GERADOR FOTOVOLTAICO" azul — "ETAPAS DO PROJETO" era azul na arte; tudo azul foi
testado e recusado pelo usuário). Se rebuildar, rode
`py ferramentas/recolorir_titulos.py` (idempotente).
Depois de um build completo rode também `py ferramentas/padronizar_linhas.py`.
Tudo o mais da revisão de design é desenhado por `proposta.py` POR CIMA da
arte e sobrevive ao build — ver "Revisão de design da proposta". Os cartões e as
garantias da pág. 3, esses sim, saem idênticos. Até alguém levar os ajustes da
pág. 5 de volta para o HTML/conversor: **não rode o build completo**; para os
ícones use o modo abaixo.

### Ícones em vetor (`ferramentas/vetor_icones.py`) — hoje só reserva
⚠ Desde a revisão de design, TODOS os ícones são redesenhados em traço por
`proposta.py` (`assets/icones_traco.json`). Os ícones vetorizados descritos
aqui continuam no `fundo.pdf`/`layout_cards.json`, mas ficam APAGADOS por baixo
e só aparecem se o JSON dos ícones de traço faltar. O texto abaixo é histórico.

Os ícones vieram do design como **PNG de 36 a 106 px** mostrados a ~38 pt —
serrilhados. Reamostrar (o que `_suavizar` fazia) não cria nitidez; por isso
modelos anteriores não resolveram. Agora cada ícone é **traçado em curvas**
(potrace) e desenhado em vetor **dentro da mesma caixa** da imagem original:
posição, tamanho, círculos e alinhamentos ficam idênticos por construção.
- **Quem é ícone:** tem transparência **e** uma cor só (`eh_icone`). O logo S2V
  (degradê), as fotos e os logos dos bancos (sem transparência) ficam raster.
- **Traçado:** margem transparente (ícone que encosta na borda não vira
  "corcova") → reamostra a ~1600 px → desfoque de **¼ da espessura do traço**
  (máx. 1 px original — 1 px fixo fechava as junções dos ícones de linha de
  2 px e o painel solar virava manchas) → corte que **preserva a área** (a
  área do vetor = tinta total da imagem; corte fixo em 50 % engrossava traço
  fino). Conferido: o painel de 48 px sai com linhas de 2,26/1,97 px contra
  2,21/2,03 px de tinta no original.
- **Fundo (`vetorizar_fundo`)**: cirurgia no `fundo.pdf` PRONTO — cada
  XObject de imagem-ícone vira um Form XObject vetorial com caixa 0..1, sob o
  MESMO nome; o `Do` e a matriz que posicionam ficam intactos. 15 ícones.
- **Cartões e garantias**: `desenhar_svg(..., icones=[])` não estampa o ícone
  no PNG e o devolve traçado, com a caixa; vai para `layout_cards.json`
  (`cards.<nome>.icones`, `garantias.icones`) e a proposta desenha por cima do
  cartão em `proposta._desenhar_icones` (ReportLab puro, sem potrace). Os ícones
  de bateria/homologação/performance já vinham como desenho vetorial no HTML.
- **Rodar só isto:**
  `py ferramentas/html_para_fundo.py ~/Downloads/proposta_s2v.html --so-icones`
  (idempotente: o que já é vetor fica como está). O build completo também
  vetoriza no final.
- **Prova feita:** proposta inteira antes × depois renderizada a 200 dpi — 23
  regiões alteradas, **todas** sobre ícones; págs. 4 e 5 com zero pixel
  alterado; ícones raster na proposta: 15 → 0. Reagrupamento dos cartões (sem
  bateria/string box) conferido: o ícone acompanha o cartão.
- Ainda raster, por decisão: molduras e rótulos fixos dos cartões e das
  garantias (PNG a 600 dpi, nítidos) e o logo S2V do cabeçalho (degradê).

## Revisão de design da proposta (out/2026) — o que mudou e as regras

Feita com o usuário **uma mudança por vez**, cada uma com antes × depois
(`ferramentas/previa.py`) e aprovação. Ele gosta da proposta como é: nada de
redesenho em bloco. Ideias que ele VIU e RECUSOU (não repropor): todos os títulos
em azul; textos da pág. 2 em minúsculas; ícones dimensionados só pela área
(ficaram pequenos); caixa de ícone quadrada com margens vazias.

Resumo do que ficou:
- **Defeitos corrigidos**: eixo do gráfico SEMPRE em kWh (20/10/2026: números com milhar e "kWh" uma vez no alto do eixo; a regra antiga de MWh virava o eixo quando só o TOPO chegava a 1.000) (o
  rótulo era cortado); separador de milhar ("19.473 kWh/mês"); "05" no cabeçalho
  da pág. 5; "—" quando não há nº de UC; "COBERTURA DO CONSUMO" no grupo A.
- **Padronização**: títulos de seção verdes (só "KIT GERADOR FOTOVOLTAICO"
  azul); capa com cidade logo abaixo do endereço; painel de garantias
  centralizado; ícones, linhas, tamanhos e espaços num sistema único (abaixo).
- **Conteúdo**: nota de irradiação pela cidade; nota do grupo A; aviso de foto
  padrão de outro equipamento; nota da usina existente.
- **Grupo A**: cartões da pág. 5 com "demanda e taxas" e "% a menos na
  energia"; ponta/fora ponta na pág. 3 e no gráfico.

Detalhe de cada item (nomes de função, medidas e o porquê):

Correções desenhadas em `proposta.py` por cima da arte (sobrevivem ao build):
"05" no cabeçalho da pág. 5, "COBERTURA DO CONSUMO" no grupo A e o **painel
de garantias** da pág. 3, redesenhado inteiro em `_garantias_painel`
(`GAR_AJUSTE`: dx 6,1 centra na área divisória→borda; dy 11 desce o grupo sem
bateria — "meio-termo" escolhido pelo usuário; o centro exato, 22, ficou baixo
demais para ele). Escudo e ícone da bateria são relidos do fundo pela posição.
**Ícones e linhas — UMA família, UM sistema (B5)** — pedido do usuário: "mesma
família, mesmas espessuras", da capa à última página. TODOS os ícones são de
traço, desenhados por `proposta.py` sobre o fundo (o antigo é apagado):
`ICONES_TRACO` (posições fixas, págs. 1–5), `ICONE_CARTAO` (cartões da pág. 3,
que se reagrupam) e `_garantias_painel` (garantias). Desenhos em
`assets/icones_traco.json`, gerado por `ferramentas/icones_traco.py` a partir da
**Lucide** (ISC), do **Tabler** (só o WhatsApp) e de desenhos **da marca** na
mesma grade 24 (`MARCA`: painel, inversor, drone, torre, bateria, string box,
degradação). O programa só lê o JSON — sem internet. Sem o JSON, cai nos
ícones antigos. **Sistema de linhas**:
- traço de ícone **1,5 pt** (pequenos, até 15 pt: **1,1 pt**) — `_traco_de`;
- anel de círculo **1,98 pt** (os cinza da arte já eram; os verdes da capa e da
  faixa da pág. 2 passaram a ser) — `TRACO_ARO`;
- bordas de cartão e réguas **0,99 pt**; divisórias e ligações **0,74 pt** — a
  arte já seguia, exceto as 4 linhas da tabela da pág. 3, corrigidas no fundo
  por `ferramentas/padronizar_linhas.py` (idempotente; rodar de novo após um
  build completo, junto com `recolorir_titulos.py`).
**Tamanhos e espaços** — tudo medido no **retângulo de tinta** do ícone (o
"retângulo azul" do usuário: do primeiro ao último ponto visível, com o traço;
`limites` exatos no JSON). Nada de caixas com margens vazias.
- **Escala por GRUPO** (`_dims(nome, lado, grupo)`): todos os ícones de um grupo
  (pilares, faixa da capa, rodapé, diagrama, tabela, cartões, garantias,
  etapas, projetos, retorno) têm o mesmo **TAMANHO PERCEBIDO** = ponto médio
  (média geométrica) entre a área do retângulo de tinta e a área da
  **silhueta** (casco convexo, `silhueta` no JSON) — uma moldura quadrada
  ("UC", 99 % do retângulo) pesa mais que uma "pessoa" (75 %) ou o "sol" (71 %)
  e por isso fica um pouco menor; o maior lado do grupo é o tamanho do grupo
  (nenhum fica mais alto/largo que os outros). Sem distorcer os desenhos.
  Tamanhos: **M 26**, **P 15**, dentro de círculo **0,60 × diâmetro** (22/14/0,52
  ficou pequeno para o usuário).
  (Histórico: "maior lado = tamanho" deixava estreitos × quadrados muito
  diferentes; "área" sem teto deixou tudo pequeno. A regra atual junta os dois.)
  Bateria e drone (desenhos da marca) foram refeitos mais perto do quadrado.
- **Espaços na tinta**: texto a 10 pt (M) / 6 pt (P) da borda da tinta; listas
  no mesmo eixo, com a tinta do mais largo a esse espaço do texto
  (`_cx_coluna`). **Dentro de quadro com borda** (tabela da pág. 3, cartões do
  retorno da pág. 5) o ícone fica CENTRADO entre a borda e o texto — mesmo
  espaço dos dois lados. Na faixa da capa, divisória→tinta = tinta→texto =
  10 pt (`FAIXA_ESPACO` = 2 × GAP_M).
**Rodapé da capa** (`_rodape_capa`) também DISTRIBUÍDO: caixa P + 6 pt + texto,
1º item na margem 37,34, último terminando em 558,84, espaços iguais.
**Faixa da capa dinâmica** (`_faixa_capa`): cliente · UC · local · sistema em
colunas de **largura igual** sempre que possível; espaço fixo entre
colunas (20 pt) com a divisória (0,74) no meio; uma coluna só cresce se o conteúdo não
cabe, e as outras repartem o resto por igual ("encher por igual"); 1ª e última
encostam nas margens 37,45 / 558,84. Se nem o conteúdo cabe, o texto mais
largo quebra em linhas (nunca encolhe a letra). Os valores (campos do
layout.json) recebem o x da coluna pelo `faixa_ovr` no laço de campos.
Cores: azul #004D94 no diagrama da pág. 2, na tabela da pág. 3 e nas etapas;
verde #089C83 no resto. **Ícone novo = da Lucide (ou desenho da marca na grade
24), entrada nessas tabelas, sem espessura própria.**
Prancha de todos os ícones: `previa/prancha_icones.png`.
**Notas de rodapé (C2/C3)** — `_reescrever_nota` em `proposta.py`:
- pág. 3 (*): a arte diz "radiação solar de Maringá", verdade só no perfil 3.8.
  Irradiação buscada na internet → a cidade buscada (`Entradas.irradiacao_local`,
  vem do `/api/irradiacao` pela tela e fica no DADOS.json); outro perfil → "da
  região do projeto". Texto em `engine._textos` (`irrad_local`).
- pág. 5 (**): no grupo A, "iluminação pública, tipo de conexão" (conceitos do
  grupo B) vira "demanda medida, o consumo na ponta".
**Foto trocada (C1)** — as fotos padrão de módulo/inversor trazem marca e W
impressos. Nas pré-definições o usuário informa de qual equipamento elas são
(`config.foto_padrao_desc` = `{modulo:{marca,pot_w}, inversor:{marca}}`);
`app._conferir_fotos` / `POST /api/conferir-fotos` compara com o kit e a tela
pergunta antes de gerar (a prévia só mostra o aviso). Foto colada ou do pacote
não gera aviso. Sem cadastro, sem aviso.
**Proposta do grupo A (D), pág. 5** — sob o "AO MÊS" dos cartões sem/com sai
"DEMANDA E TAXAS: R$ …" (a parte que o solar não mexe: demanda, COSIP, reativo
e, com sistema, a TUSD-G = `piso`) e no cartão verde "NN % A MENOS NA ENERGIA".
Números em `r['grupo_a_partes']` (engine.calcular), textos `ga_*` em `_textos`;
teste: seção 18 do `teste_grupo_a`. Opção de duas linhas por cartão foi testada
e não cabe (102 pt de largura). Com a 4ª linha, o miolo dos três cartões é
redesenhado `GA_DY` = 6,25 pt mais alto (`_cartoes_grupo_a`) — só o cartão que TEM a 4ª linha (sem redução a mostrar, o de economia fica como na arte) — para ficar
centrado na vertical — pedido do usuário.
**Grupo A, pág. 3** — sob o "CONSUMO MÉDIO" sai a sublinha "ponta 1.039 · fora
ponta 18.434" (`textos['consumo_postos']`; fora ponta = total exibido − ponta,
para a soma bater), Inter 6 pt cinza; o par fica centrado na célula (centro
309 pt no topo, linhas da tabela em 290/328).
**Grupo A, pág. 4** — a barra de consumo do gráfico vira duas: fora ponta no
azul da marca (embaixo) e ponta em `COR_PONTA` #7FA6C9 (o mesmo azul a 50 %),
legenda com 3 itens. Dado: `r['consumo_ponta_mensal']`. No grupo B, idêntico.
**Usina existente (grupos A e B), pág. 5** — com `gds_existentes`, entra a nota
"*** A conta sem S2V já desconta a usina atual (N kWh/mês): a economia é
adicional." (`textos['nota_usina']`). Para as três notas caberem acima do
"ACEITE", a ** é redesenhada mais alto e as folgas ficam iguais (`_notas_p5`).
Sem usina, as notas são as da arte (no grupo A, só o texto da ** muda).
(B4 — textos ao lado das baterias na pág. 2: minúsculas 8,4 pt foram testadas
e recusadas, "pequeno demais"; maiúsculas maiores não cabem. Ficam como na arte.)

## Carregador veicular (wallbox) — aba própria

Orçamento do **SERVIÇO de instalação** de wallbox: o carregador é **do cliente**
(a proposta diz "FORNECIDO PELO CLIENTE"); a S2V vende mão de obra + materiais +
ART. A planilha `S2V_precificacao_wallbox_baterias.xlsx` do usuário é de
**revenda** de equipamento (taxas da Nuvemshop) — **não** é a base desta aba.
Motor separado (`wallbox.py`): nada passa pelo `engine.py`, o `teste_planilha`
não é afetado.

- **Tela**: `/wallbox`, mesma aparência; o cabeçalho das duas telas tem o seletor
  "☀ Solar | 🔌 Carregador" (`.abas-topo`). Rotas: `POST /api/wallbox/calcular`,
  `/api/wallbox/previa`, `/api/wallbox/proposta`.
- **Técnica** (`dimensionar`): corrente de placa (vazia = P ÷ V ou P ÷ √3·V) →
  disjuntor = 1º padrão ≥ `fator_disjuntor` (1,25, recarga é carga contínua) × I
  → menor seção com **Iz × `fator_correcao_iz` ≥ disjuntor E queda ≤
  `queda_max_pct`** (Iz da NBR 5410 Tab. 36, método B1, por nº de condutores
  carregados; ρ = 0,0225 a 70 °C) → PE pela Tab. 58. Alimentações: 220 F+N,
  220 F+F, 380 3F+N, 220 3F (define condutores, polos de disjuntor/DR e nº de
  DPS). Um wallbox de 7,4 kW é de **32 A de placa** — por isso a tela já vem com
  32 A (7,4 kW ÷ 220 V daria 33,6 A e empurraria para disjuntor de 50 A).
  "Dimensionamento manual" (seção/disjuntor digitados) só gera aviso, não trava.
- **Distância vazia = "A VERIFICAR NA VISITA"** (padrão da tela, pedido do
  usuário): é o que sai na proposta, e cabo, Material CA e mão de obra são
  ESTIMADOS com `distancia_padrao_m` (15 m, ⚙ Preços), com aviso na tela e no
  RESUMO. Digitar os metros depois troca tudo pelo valor real. A pasta do
  projeto fica sem o "…M" no nome.
- **Preço = a lógica do solar com kit = 0**: imposto, comissão e seguro são % do
  próprio preço → `preço = custos diretos ÷ (1 − margem − imposto − comissão −
  seguro)` (é o ponto fixo do laço `preco_convergido`; o teste prova). Imposto
  sobre a venda INTEIRA (não há kit em faturamento direto). Valor fixado à mão →
  a margem vira consequência. Cartão igual ao solar (venda ÷ (1 − taxa)).
- **Proteção = SEMPRE uma CLAMPER Mobi** (pedido do usuário). Ela já traz DPS,
  disjuntor e IDR — por isso não há mais quadro/disjuntor/DR/DPS avulsos nem a
  chave "DR tipo B". Catálogo em `config.wallbox.mobi` (24 modelos, do guia
  CLAMPER "Proteção para veículos elétricos e carregadores", 2024): **Box** 8 kW
  220 V bifásico (32 A), 15 kW 220 V tri (40 A), 26 kW 380 V tri (40 A); **Plug**
  220 V bifásico com tomadas — residencial 5 kW (20 A), industrial 8 kW (32 A),
  as duas 8+5 kW; cada um em cinza/preto, com ou sem medidor. A tela escolhe
  linha, cor, medidor e tomadas; `escolher_mobi` filtra pela alimentação e pega
  o menor que atende a corrente do carregador (avisa se não atende). **Preços em
  branco**: o usuário cadastra o custo de cada modelo no ⚙ Preços (ou digita no
  orçamento). **Mobi sem preço não gera PDF** (prévia nem proposta) — o valor
  sairia errado para menos.
- **Foto da Mobi na proposta** (como módulo/inversor no solar) — **pág. 1**,
  na faixa do antigo painel "PROTEÇÃO E ATERRAMENTO" (38–557,28 × 79,89–293,89
  pt). O painel da arte foi APAGADO do fundo (`ferramentas/wallbox_fundo.py`,
  `_PAINEL`, o build avisa se não achar) e é redesenhado por
  `proposta_wallbox._faixa_protecao`: **metade esquerda = foto da Mobi grande**
  (inteira, sem cortar) + legenda verde "PROTEÇÃO CLAMPER MOBI BOX/PLUG";
  **metade direita = painel SIMPLIFICADO** (mesmo estilo: fundo #F3F7F8, ícone de
  terra, título verde, bolinhas ✓) com 6 itens curtos `ITENS_PROTECAO` (negrito +
  1 linha). Sem foto, o painel ocupa a largura toda em 2 colunas. Pedido do
  usuário: a 1ª versão (foto sob o logo da pág. 2, 114 × 72 pt) ficou pequena
  demais. Ordem da foto: colada no orçamento (`img_mobi`) → PADRÃO da linha (Box
  ou Plug, `padrao_mobi_box.txt`/`padrao_mobi_plug.txt` no data dir, gitignored,
  editadas no ⚙ Preços via `/api/wallbox/fotos-padrao`, POST só admin) → sem
  foto. Vai solta na pasta como `MOBI.<ext>` (nunca no DADOS.json) e volta no
  Importar. `_IMG_BASE`/`_IMG_PADRAO` em app.py generalizam os ajudantes de foto
  do solar sem mudar módulo/inversor.
- **Custos resumidos** (como no solar): Mobi · **Material CA** (um campo só, tudo
  o que não é a Mobi; vazio = estimativa por cabos com folga + eletroduto +
  aterramento + miscelânea) · mão de obra (vazio = base + por metro) · ART ·
  deslocamento. Preços e regras em `config.json → wallbox`, editáveis no
  **⚙ Preços** da aba (grava via `POST /api/config {wallbox}`). ⚠ Os valores da
  estimativa do Material CA e da mão de obra são EXEMPLOS (out/2026).
- **SÓ ADMIN** (pedido do usuário, 16/10/2026): `_rota_admin` barra `/wallbox`
  (consultor volta para `/`) e todo `/api/wallbox/*` (403); no solar a aba
  `.abas-topo` tem `so-admin`, então o consultor nem vê o seletor. A blindagem
  antiga (`_WB_CUSTOS` descartado do payload de consultor) continua no código,
  como segunda trava, caso a aba um dia seja liberada.
- **Nuvem**: `wallbox.parametros(cfg)` completa o bloco com o `config.json` que
  vem no programa — o do bucket não tem `wallbox` e a aba funciona assim mesmo.
  Quando o admin salva o ⚙ Preços na nuvem, o bloco passa a existir no bucket.
- **PDF**: arte do design em `assets/wallbox/modelo.pdf`; `fundo.pdf` é ele sem os
  14 campos `[...]` e sem o painel de proteção da pág. 1 (`ferramentas/wallbox_fundo.py`, que lista posição/fonte de
  cada um). `proposta_wallbox.CAMPOS` escreve cada valor no lugar e na fonte do
  colchete (Outfit/Work Sans em `assets/fonts`, OFL); texto longo quebra em
  linhas ou reduz a letra até 70 %. Design novo → rodar o build e reler as
  posições, não chutar.
- **Salvamento**: SEMPRE `<base>/INSTALAÇÕES WALLBOX/<CLIENTE>/WALLBOX 7,4KW 220V F+F 18M/`
  (`app.PASTA_WALLBOX`, no lugar do consultor — pedido do usuário; é o nome da pasta que JÁ existe no Drive dele, no plural — o singular criava uma pasta nova), com
  `RESUMO.txt`, `DADOS.json` (`tipo: wallbox`) e `<CLIENTE> - WALLBOX.pdf`. `/api/resumos-salvos` separa por tipo pelo nome da pasta
  (`?tipo=wallbox`): o Importar de uma aba não lista projetos da outra.
  A pasta é **EXCLUSIVA do carregador**: o solar não a lista em
  `/api/drive/consultores` e `/api/proposta` recusa salvar nela
  (`_eh_pasta_wallbox`: sem acento/caixa, aceita o singular). Na tela do
  carregador o campo vira "Pasta dos orçamentos", só leitura. Com Mobi sem preço
  a tela mostra o aviso no painel e trava Gerar/Prévia (era o motivo de "nada
  aparece no Drive").
- Verificar: `py teste_wallbox.py` (deve passar 100 %).

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
   **UC adicionada (beneficiária) também busca a tarifa** (`addUC` →
   `aplicarConcAuto`): antes ela nascia em COPEL igual à geradora, o
   `sincronizarConcBeneficiarias` via "nada mudou" e TE/TUSD ficavam vazias.
   **Bandeira vigente (19/10/2026):** `online.buscar_bandeira_aneel` lê a base
   "Bandeiras tarifárias → Acionamento" (`0591b8f6-…`, uma linha por mês, R$/MWh
   sem impostos) → `GET /api/aneel-bandeira`, cache `BANDEIRA` no
   `tarifas_cache.json`. A tela busca ao abrir (`carregarBandeira`): UC nova
   nasce com a bandeira vigente (importada mantém a sua) e a linha de
   conferência da aba Tarifas mostra o adicional com impostos, a "cheia + bandeira"
   e avisa se a escolhida difere da vigente. Na proposta, pág. 5, a linha do
   "RETORNO FINANCEIRO" ganha à direita "BANDEIRA TARIFÁRIA EM OUT/2026 [VERDE]"
   (`proposta._bandeira_p5`; `Entradas.bandeira_vigente/_competencia`, só texto,
   não entra na conta; sem a tela, `app._bandeira_do_payload` usa o cache; sem
   nada, não imprime).
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
   ICMS. Essa assimetria é o que **reproduz a fatura real** (PLANILHA = R$ 125,70).
   **NÃO "corrigir"** (tentamos aplicar o Convênio 16/2015 à TUSD e o valor caiu
   p/ R$ 104,69, divergindo da conta real — revertido). Se um estado tratar a
   **TUSD abatida COM ICMS**, isso vira regra por concessionária (a pesquisar/
   confirmar com fatura real) — ver "Como adicionar outra concessionária".

11. **Regra do MAIOR VALOR: custo de disponibilidade × sobra de Fio B.**
    A energia compensada é **TUDO** o que houver de crédito
    (`compensado = min(faturado, ger_faturavel)`), e o mínimo da conta é
    garantido depois, pelo `taxa_min = max(piso, liquido)`. A planilha
    subtraía a disponibilidade do crédito
    (`faturado − disponibilidade`), o que cobrava **duas vezes**: os 50 kWh
    pela tarifa cheia **mais** a sobra de Fio B sobre o resto.
    Por kWh compensado sobra `Fio B ÷ (1−PIS−COFINS)` **+** o ICMS da TUSD que
    o crédito não devolve — na fatura FATURA-B, R$ 0,2568/kWh. Com ligação
    bifásica e as tarifas de 2026 o **ponto de virada fica em ~201 kWh**:
    abaixo disso manda o custo de disponibilidade, acima manda o Fio B.
    Confirmado pela **fatura real FATURA-B** (R$ 117,53, reproduzida centavo a
    centavo) e pelo raciocínio do usuário. Efeito: a economia declarada no
    grupo B **sobe** (a planilha negava 50 kWh de crédito todo mês) — na PLANILHA,
    de R$ 277,62 para R$ 310,53. **O grupo A não é afetado** (lá não existe
    custo de disponibilidade). **Não reverter para `faturado − disponibilidade`.**
    **Bandeira quando a disponibilidade vence** (08/10/2026, pedido do usuário):
    a bandeira é cobrada no faturado e devolvida no compensado; como agora se
    compensa tudo, sobraria zero — mas no custo de disponibilidade o faturado é
    o mínimo, então a conta COM o sistema leva a bandeira sobre os kWh da
    disponibilidade (bifásico amarela: R$ 1,27; vermelha P2: R$ 5,29). Com o Fio
    B vencendo, continua se anulando (como na FATURA-B). ⚠ Regra da ANEEL, ainda
    sem fatura que a comprove. A "conta SEM" segue a planilha (sem bandeira).

## Grupo A (média tensão) — SÓ o administrador

UC de **grupo A** (A4, A3a…) tem fatura de outra natureza e por isso um bloco
próprio: `UC.grupo='A'` liga os campos de média tensão. **É exclusivo do admin**
— o seletor tem classe `so-admin` na tela e, o que importa de verdade, o
servidor força `grupo='B'` em qualquer payload de consultor (`_montar_entradas`,
via `_pode_admin()`). Endpoint `/api/aneel-tarifa-a` também é rota de admin.

O que muda na conta (`engine._fatura_grupo_a`, testado em `teste_grupo_a.py`):

1. **Demanda (R$/kW) o solar NÃO abate.** É o piso da fatura, paga igual com e
   sem sistema — é por isso que a economia do grupo A é percentualmente menor.
   `faturada = max(contratada, medida)`, **mas o campo "Demanda faturada (kW)"
   ganha da regra** quando preenchido: cada distribuidora tem a sua e o que
   está impresso manda (a FATURA-A cobrou 167,47 kW de 175 contratados).
   **ICMS só sobre a demanda utilizada**
   (Súmula 391 do STJ — a contratada e não usada leva só PIS/COFINS);
   **ultrapassagem** acima de 105 % da contratada cobra o excedente outra vez
   (efeito: dobro da tarifa). Modalidade **VERDE** = uma demanda; **AZUL** =
   demanda de ponta + fora ponta (`tusd_demanda` / `tusd_demanda_p`).
1b. **No grupo A NÃO existe "% noturno"** — o campo é escondido (`.so-grupo-b`).
   O rateio dia/noite já está no próprio ponta/fora ponta: o sol só gera fora
   ponta. **Autoconsumo do sistema NOVO = PIOR CASO por padrão** (decisão do
   usuário, igual à planilha paralela dele): **zero** — toda a geração nova é
   **injetada** e volta como crédito, que vale menos que o kWh evitado (o ICMS da
   TUSD não volta: R$ 0,0374/kWh na FATURA-A). `config.autoconsumo_grupo_a`:
   `pior_caso` (padrão) · `medido` (fração medida na usina existente com a
   geração do app; sem ela, pior caso) · `otimista` (tudo até o consumo fora
   ponta — era o padrão antigo e superestimava a economia; na FATURA-A com
   112,5 kWp novos: R$ 7.642,99 otimista × **R$ 7.159,31** pior caso). O autoconsumo some da conta pela **tarifa CHEIA (com ICMS)**,
   porque nem chega a ser medido; o injetado volta pelo abatimento (sem o ICMS
   da TE onde o convênio venceu). Sem o Convênio 16/2015, **1 kWh autoconsumido
   vale mais que 1 kWh injetado**.
2. **Energia separada em PONTA e FORA PONTA**, cada posto com TE e TUSD-energia
   próprias (`te_ponta/te_fora`, `tusd_kwh_ponta/tusd_kwh_fora`). No grupo A o
   campo "consumo" de sempre passa a ser o **fora ponta**; a ponta tem os seus
   (`consumos_ponta`), no mesmo modo rápido/detalhado.
3. **Não existe custo de disponibilidade** (30/50/100 kWh): o mínimo é a
   demanda. Por isso o campo Ligação fica desabilitado no grupo A.
4. **Ordem da compensação (REN 1.059/2023):** o crédito (gerado fora ponta, onde
   o sol está) abate primeiro o **fora ponta**; a sobra abate a **ponta**
   dividida pelo **fator de correção** = `TE_ponta / TE_fora` (padrão), que na
   prática dá **~1,6** — na fatura FATURA-A, 1,608, e o usuário usa 1,63.
   `UC.fator_ponta_manual` sobrepõe (campo "Fator de correção da ponta").
   ⚠ **A base é a TE, não a tarifa cheia**: pela cheia daria 4,38 em A4 Verde
   (a TUSD da ponta é ~10× a de fora ponta) — a tela mostra as duas contas na
   linha de conferência para a escolha ser consciente. Isso também entra no
   **dimensionamento**:
   `consumo_anual_equiv = fora + ponta × fator` alimenta `kwp_necessario` e a
   `compensacao` (no grupo B é idêntico ao consumo anual, então nada muda).
4b. **A UC tem ABAS e a tela se adapta ao grupo.** Cada UC é
   `Consumo · Tarifas · Demanda · Usinas` (`.uc-abas` + `.uc-pane`, trocadas por
   `setAba`). **A aba Demanda só existe no grupo A.** Os painéis ficam TODOS no
   DOM, apenas escondidos — `lerUC` lê a UC inteira por `querySelector`, então
   trocar de aba não muda o que vai ao servidor. `setGrupo` liga/desliga
   `.so-grupo-b` (modalidade B1/B2, tarifas de kWh único, % noturno) e
   `.so-grupo-a` (tarifas por posto, aba Demanda, isenção do convênio), troca os
   rótulos do consumo e, voltando ao grupo B, tira o usuário da aba Demanda que
   acabou de sumir. `aplicarModo` põe o consumo de **ponta ao lado do fora
   ponta** e respeita o modo rápido/detalhado. Dentro das abas, seções com
   `.sub-rot`. A **bandeira** mora na aba Tarifas nos dois grupos (antes ela era
   movida de container por JS — isso deixou de existir).
5. **NÃO existe Fio B no grupo A** — nem em GD1 nem em GD2. O fio é remunerado
   pela **demanda**, então o escalonamento da Lei 14.300 que corta o crédito no
   grupo B não se aplica: o kWh compensado abate a **TE e a TUSD-energia
   inteiras** (`abat_posto`, sem nenhum desconto). Confirmado pela fatura
   FATURA-A: "ENERGIA INJETADA FP TUSD" devolve R$ 0,159457, que é a TUSD cheia
   (0,146590) apenas dividida por PIS/COFINS. **Não reintroduzir Fio B aqui.**
5b. **TUSD-G — demanda de GERAÇÃO** (`UC.demanda_g_kw`, `UC.tusd_g_rs_kw`).
   Opcional e disponível para **GD1 e GD2**. É bem mais barata que a demanda de
   consumo. **A tarifa entra SEM impostos**, como todas as outras
   (`tusd_g_com_imposto()` faz o gross-up): `config.tusd_g_rs_kw = 7,66` sem
   impostos (oficial, REH 3.592/2026) ≈ **R$ 10,29/kW com impostos** (o usuário
   estimava ~10,58).
   Na prática contrata-se como TUSD-G só o que **falta** para cobrir a potência
   dos inversores: `demanda_g = max(kW de inversores do projeto NOVO + kW de
   inversores das USINAS EXISTENTES − demanda de consumo contratada, 0)`, que é
   o cálculo automático quando o campo fica vazio (o usuário pode digitar
   outro). Cada usina em `gds_existentes` tem `inversor_kw` (campo "Inversor
   (kW)" na aba Usinas); vazio = usa o kWp (dá um pouco MAIS de TUSD-G, lado
   seguro). Exemplo: `exemplos/projeto_novo_grupo_a.json` — 75 kW novos + 135 kW
   existentes − 175 contratados = **35 kW** (seção 18 do `teste_grupo_a`). É um custo que **só existe COM o sistema** —
   entra no `total` e no `piso`, nunca na `fatura_sem`, e por isso derruba a
   economia e o payback. Na FATURA-A dá zero: 135 kW de inversor < 175 kW de
   demanda contratada, nada a contratar (por isso a fatura validada não muda).
6. **Assimetria do ICMS mantida** igual ao grupo B (`abat_posto`): a TE abatida
   volta com ICMS; a TUSD abatida não, salvo estado com
   `abat_tusd_inclui_icms=true`.
7. **Projeção de 25 anos:** com UC do grupo A o `compat_planilha` é ignorado (a
   planilha não conhece média tensão) — usa sempre a estimativa realista, que
   parte da economia efetiva.
8. **Tarifas pela ANEEL (opcional):** botão "buscar tarifas na ANEEL" →
   `online.buscar_tarifa_aneel_a` (subgrupo + modalidade, separa demanda de
   energia por `DscUnidadeTerciaria` kW/MWh e por `NomPostoTarifario`), com o
   mesmo cache offline do grupo B (chave `SIGLA|SUB|MOD`). ⚠ **Não foi testado
   contra a API** (a base não respondia quando foi escrito) e o grupo A tem
   componentes que variam por contrato: **o valor da fatura manda**, a busca é
   só conveniência e falha sem quebrar nada.

9. **Itens que o sistema não muda** (reativo excedente, multas) vão em
   `outros_rs` (R$/mês, já com impostos): entram igual com e sem solar, só para
   a "fatura sem" bater com a de verdade. Na FATURA-A são R$ 424,24.

✅ **Validado** contra a fatura FATURA-A (ver o caso lá em cima): tarifas com
tributos, demanda, crédito injetado, bandeira cobrada/devolvida e o total.
⚠ **O que a FATURA-A NÃO conseguiu validar**, porque ela é GD1 e a injeção coube
inteira no fora ponta:
- a **compensação da ponta com crédito fora ponta** (item 4): o fator de ajuste
  fica 1,608 (TE P/TE FP), mas nenhum crédito chegou a migrar de posto. Em A4
  **Verde** isso é sensível: a TUSD da ponta é 10× a de fora ponta, então
  converter crédito pela relação das **TEs** (como diz a REN) é generoso — se a
  COPEL fizer diferente, é aqui que se mexe;
- a **TUSD-G** (item 5b) está modelada e testada, mas nenhuma fatura a mostrou.

10. **O Convênio ICMS 16/2015 tem prazo — e onde ele venceu a conta muda muito.**
    `UC.abat_te_inclui_icms` (padrão **True**, que é o caso PLANILHA/validado): com
    a isenção valendo, a energia compensada é isenta e o crédito **devolve o
    ICMS da TE** (`abat_te = te_com_imposto`). Onde o prazo caducou (**fatura
    FATURA-A 09/2026**), o ICMS incide sobre o **consumo cheio** e o crédito volta
    só com PIS/COFINS (`abat_te = te / (1−PIS−COFINS)`). Dá para ler isso na
    própria fatura: a linha "ENERGIA INJETADA FP TE" tem **ICMS 0,00** e vale
    R$ 0,321710 (= TE ÷ 0,9193), enquanto a TE consumida sai por R$ 0,397175
    (= TE ÷ (0,81 × 0,9193)); e a base de ICMS (R$ 20.269,79) **não desconta** a
    energia injetada. O adicional de **bandeira** segue a mesma regra
    (`band_credito`). É regra por concessionária (`abat_te_inclui_icms` no
    `config.json`, exposta em `/api/concessionarias`) e a UC do grupo A pode
    sobrepor com a caixinha na tela.
    **O prazo corre por PARECER DE ACESSO, não por estado nem por cliente**
    (no PR, ~4 anos): cada parecer tem o seu relógio, então uma usina NOVA
    começa a contagem do zero ainda que outra usina do mesmo cliente já tenha
    perdido a isenção. Por isso o grupo B **não** deve ser mexido em bloco — a
    PLANILHA continua correta. Na FATURA-A a isenção acabou porque **aquela** usina
    tem mais de 4 anos.
    `UC.isencao_icms_anos` = anos que ainda restam NESTE parecer (campo "anos
    restantes neste parecer" na tela). Preenchido, a **projeção de 25 anos desce
    de patamar** no ano da virada: até lá a economia é a cheia, depois passa a
    ser a de uma conta sem devolução do ICMS (`engine.calcular` recalcula as
    faturas com `abat_te_inclui_icms=False` via `dataclasses.replace`).
    **Vazio = não modela a virada** → projeção idêntica à de antes, que é o
    motivo de nenhuma proposta existente ter mudado de número.

## Usinas que a UC JÁ TEM (`gds_existentes`) — grupos A e B

`UC.gds_existentes` é uma lista `[{nome, kwp, injetado_kwh, isento_icms}]` com
as usinas que o cliente já tinha **antes** do orçamento em questão. O que entra
na conta é o **`injetado_kwh`** (kWh/mês) — número que vem impresso na fatura,
na linha "ENERGIA INJETADA". Na tela é um `<details>` ("usinas que esta UC já
tem") com linhas que se somam, disponível nos dois grupos.

**`isento_icms` por usina, não por UC.** O prazo do Convênio 16/2015 corre por
**parecer de acesso**, então numa mesma UC a usina de 2019 pode já ter perdido a
isenção enquanto a de 2024 ainda a tem — e o crédito de cada uma vale um valor
diferente. `UC.usinas_existentes()` devolve `[(kWh, isenta?)]` e os abatimentos
aceitam o estado: `abat_te(com_icms)`, `abat_posto(ponta, com_icms)`,
`band_credito(band, com_icms)` (sem o argumento, herdam o flag da UC, que é o
que vale para o **projeto novo**). No grupo A a compensação percorre **baldes**
(`_balde`/`_conta`), um por usina, consumindo as **antigas primeiro** — assim o
crédito que eventualmente sobra sem uso é o do projeto novo, que é a leitura
conservadora. No grupo B o mesmo rateio só entra **quando há usina antiga**;
sem elas a linha é a da planilha, intocada.

**Por que importa:** sem isso, a `fatura_sem` seria a conta de um cliente que
não gera nada, e a proposta cobraria de novo uma economia que o cliente **já
tem** — inflando economia, payback e retorno de 25 anos.

### ⚠ A fatura MENTE sobre consumo e geração quando já existe GD

Onde há usina instalada, **nem o consumo nem a injeção impressos são os valores
reais**. O medidor da concessionária não enxerga o que a usina gera e a casa
consome **no mesmo instante** — essa parcela some da fatura, mas não deixou de
existir. E ela falta nos **dois** lados ao mesmo tempo:

```
consumo real = consumo medido + autoconsumo
geração real = injetado       + autoconsumo     ← o MESMO autoconsumo
```

A geração real **só** se obtém no **app de monitoramento** da usina (Goodwe,
Solarman…). Por isso cada usina em `gds_existentes` tem `geracao_kwh` além de
`injetado_kwh`, e o motor deriva:
`autoconsumo_existente() = max(geracao_kwh − injetado_kwh, 0)`;
`geracao_existente() = injetado + autoconsumo`;
`UC.consumo_real_medio = consumo_medio + autoconsumo` (e `consumos_reais()`
para o gráfico). Vale para **grupo A e grupo B**.

Onde cada número manda:
- **Faturamento** (`_faturas_uc`, `_fatura_grupo_a`) usa sempre o **MEDIDO** —
  é o que a concessionária cobra, e é o que reproduz a fatura centavo a centavo.
  `UC.consumo_medio` continua sendo o medido: **não mexer**, o `teste_planilha`
  depende disso.
- **Consumo exibido e gráfico da proposta** (`r['consumo_medio']`,
  `r['consumo_mensal']`) passam a ser o **REAL**, senão a proposta mostra ao
  cliente um consumo menor do que o dele de verdade. `r['consumo_medido_anual']`
  e `r['autoconsumo_existente']` ficam disponíveis para conferência, e a tela
  escreve "451 kWh/mês (medido 281 + 170 autoconsumido)".
- **Dimensionamento**: consumo real − **geração real** das usinas atuais. O
  autoconsumo entra nos dois lados e **se cancela**, então o kWp necessário não
  muda — mas as duas grandezas ficam certas, o que importa quando se quiser
  modelar o autoconsumo do sistema NOVO.

Sem `geracao_kwh` informado, o autoconsumo vale zero e tudo se comporta como
antes (o programa só conhece o que o medidor viu).

**Também entra no DIMENSIONAMENTO** (`calcular`): `consumo_anual_equiv` desconta
`injecao_existente() × 12`, porque o que as usinas antigas já injetam não
precisa ser coberto outra vez. Sem esse desconto o sistema sai superdimensionado
e a proposta, cara demais (na FATURA-A: 175 kWp sugeridos virariam 127 kWp).
`r['injecao_existente_ano']` guarda o total descontado.

- **Grupo A** (`_fatura_grupo_a`): a função `_conta(autoconsumo, injetado)`
  calcula energia+bandeira de um cenário, e é chamada **duas vezes** —
  `hoje = _conta(0, injeção existente)` vira a `fatura_sem`, e
  `depois = _conta(autoconsumo novo, injeção existente + injetado novo)` vira o
  `total`. Foi isto que deixou a validação FATURA-A natural: a usina de 135 kW
  que ela já tem é uma `gds_existentes` injetando 5.490 kWh, e **sem projeto
  novo a conta bate nos R$ 17.648,07 do papel**.
- **Grupo B**: `ger_faturavel` ganha `+ inj_ex` (com lista vazia é o de sempre),
  e a `fatura_sem_uc` só troca de fórmula **quando existe usina** — sem usina
  fica a expressão da planilha, intocada, que é o que mantém o `teste_planilha`
  e o caso PLANILHA idênticos. Não "unifique" essas duas fórmulas.

## ⚠ Pendências de validação — o que AINDA é suposição

Auditoria de 06/10/2026. Tudo o mais no motor fecha centavo a centavo contra duas
faturas reais (FATURA-B R$ 117,53 e FATURA-A R$ 17.648,07). Estes pontos **não**:

### Números sem fatura que os comprove
| Valor | Onde | Como fechar |
|---|---|---|
| **Tolerância de 105 %** | `_demanda_rs` (engine) | **Fonte: REN ANEEL nº 1.000/2021.** Tem teste, mas nenhuma fatura a exercitou. |
| **~4 anos de isenção** | só em placeholder/doc | Informado pelo usuário como aproximado. Não é padrão no código. |

✅ **Fio B e TUSD-G deixaram de ser suposição (06/10/2026).** Ver a seção
"Componentes tarifários" logo abaixo: os dois têm agora valor OFICIAL da ANEEL.
| **Tolerância de 105 %** | `_demanda_rs` (engine) | **Fonte: REN ANEEL nº 1.000/2021.** Tem teste (seção 7 do `teste_grupo_a`), mas nenhuma fatura o exercitou. |
| **~4 anos de isenção** | só em placeholder/doc | Informado pelo usuário como aproximado. Não é padrão no código. |

### Regras com teste, mas sem fatura que as exercite
- **ICMS só sobre a demanda utilizada** (Súmula 391 do STJ) — seção 17 do
  `teste_grupo_a`. Na FATURA-A a faturada (167,47) ficou abaixo da medida, então a
  parcela ociosa deu zero e a regra não rodou.
- **Ultrapassagem** acima de 105 % — seção 7. A FATURA-A não ultrapassou.
- **Compensação da ponta com crédito fora ponta** — a FATURA-A absorveu tudo no
  fora ponta, nenhum crédito migrou de posto.

### ✅ Busca da ANEEL do grupo A — TESTADA e CORRIGIDA (06/10/2026)
`online.buscar_tarifa_aneel_a` foi finalmente rodada contra a API e tinha um
**bug real**: faltava filtrar `DscDetalhe`. Além da tarifa normal
(`'Não se aplica'`), a base traz, no MESMO subgrupo, as linhas **`APE`**
(autoprodutor equiparado) e **`SCEE`** (sistema de compensação) — e a do SCEE
tem outra TE (0,03009 contra 0,47555 da normal, no A4 da COPEL). Sem o filtro,
a última linha da resposta vencia e a TE saía 15× menor. **Corrigido.**
Conferido contra a fatura FATURA-A, agora os cinco valores batem na 5ª casa:
TE ponta 0,47555 · TUSD ponta 1,46339 · TE fora ponta 0,29575 · TUSD fora ponta
0,14659 · demanda 25,33 (REH 3.592/2026, vigência 2026-06-24).
Rode `py ferramentas/conferir_aneel.py` para repetir a conferência.

### Já corrigido nesta auditoria
- **Autoconsumo do grupo A** era `min(consumo fora ponta, geração)` — absorção
  total, o limite otimista. Passou pela fração MEDIDA e, em 08/10/2026, o
  usuário fixou o **PIOR CASO como padrão** (autoconsumo zero, tudo injetado —
  ver item 1b do Grupo A). `medido` e `otimista` seguem disponíveis em
  `config.autoconsumo_grupo_a`; a tela escreve qual regra valeu.
- **Rateio entre usinas** era "as antigas primeiro" (escolha arbitrária). Agora é
  **proporcional** ao kWh que cada uma injetou — a energia entra num pote só e
  nada diz de qual usina veio o kWh que abateu a conta. Travado em teste: a
  ordem na lista não muda a conta, e a mista é a média das puras.
- **`fator_ponta_manual` fixado em 1,63** no exemplo da FATURA-A anulava o cálculo
  pela razão das TEs (0,4755/0,29575 = **1,6077**). Removido do JSON: o campo só
  deve ser preenchido quando a distribuidora aplicar outra regra, comprovada.

## Componentes tarifários da ANEEL — onde achar Fio B e TUSD-G

A base que o programa usa para TE/TUSD (**"Tarifas de aplicação"**,
`fcf2906c-…`) **não** decompõe a tarifa. A decomposição está noutro conjunto:

> **"Componentes Tarifárias"** — um recurso CSV por ano.
> 2026: `resource_id = e8717aa8-2521-453f-bf16-fbb9a16eea39`
> Campos: `NumCPFCNPJ`, `DscSubGrupoTarifario`, `DscModalidadeTarifaria`,
> `DscPostoTarifario`, `DscUnidade`, **`DscComponenteTarifario`**,
> `VlrComponenteTarifario`. CNPJ da COPEL-DIS: `04368898000106`.

Valores oficiais da **REH 3.592/2026** (vigência 24/06/2026), já no `config.json`:

| O quê | Componente | Valor |
|---|---|---|
| **Fio B do grupo B** | `TUSD_FioB`, B1, R$/MWh | **214,5356** na COPEL (eu havia derivado 214,57 da fatura — 0,016 % de erro) |
| **TUSD-G** | `TUSD`, A4, modalidade **`Geração`**, R$/kW | **7,66** (dá ~R$ 10,29/kW com impostos; o usuário estimava ~10,58) |

### Fio B é POR CONCESSIONÁRIA
Varia de **132,79 (CELESC)** a **346,13 (ENERGISA)** R$/MWh em 2026 — um valor
único para todas errava a proposta de outra distribuidora em até ~40 %. Cada
bloco de `config.concessionarias` tem o seu `fio_b_rs_mwh` (+ `_fio_b_fonte`
com a REH e a vigência); `app._fio_b_da_conc` o põe na `UC.fio_b_rs_mwh` pela
concessionária escolhida, e `_faturas_uc` usa o da UC — sem ele, o global
`config.fio_b_rs_mwh` (que a planilha e os testes usam). Teste: seção 1c do
`teste_correcoes`. `ferramentas/conferir_aneel.py` confere as oito.
⚠ Na nuvem, lembre: concessionária/chave nova no `config.json` **não sobe com o
deploy** — mescle no bucket (ver "Cloud Run").

### ⚠ Por que "não há Fio B no grupo A" continua certo — mas por outro motivo

A base mostra que **existe** `TUSD_FioB` no A4, e grande: **1.018,54 R$/MWh na
PONTA**. Mas **na FORA PONTA ele é ZERO**. E no grupo A o Fio B também aparece
como componente da **demanda** (16,08 R$/kW no A4 Verde) — é lá que o fio é
remunerado, exatamente como o usuário descreveu.

Como o sol injeta **fora ponta**, onde o Fio B é zero, o crédito solar não sofre
desconto nenhum — que é o que a fatura FATURA-A mostra e o que `abat_posto`
implementa. **A regra está certa para solar**, mas o enunciado correto não é
"o grupo A não tem Fio B": é **"a TUSD fora ponta do A4 tem Fio B zero, e é fora
ponta que o solar injeta"**.

⚠ **Consequência ainda em aberto:** se um dia um crédito fora ponta for usado na
PONTA, a pergunta "o Fio B da ponta (1.018,54 R$/MWh) incide sobre esse crédito?"
passa a valer dinheiro. O usuário afirma que não incide em nenhum posto; a base
não contradiz (o Fio B pertence ao posto da injeção, que é fora ponta). A fatura
FATURA-A **não resolve** — nela nenhum crédito migrou de posto. Fica como a
principal pendência do grupo A.

### Portais bloqueados (não insista)
`calculostarifarios.aneel.gov.br` e `leis.org` estão atrás do **Cloudflare**:
devolvem 403 "Just a moment…" a qualquer requisição sem navegador, inclusive com
user-agent de Chrome. Use a base Componentes Tarifárias acima, que é a mesma
informação por API.

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
- **ICMS rural (subgrupo B2)** é por estado, em `impostos.B2.icms`: PR/SP/RJ
  isentam (0), MG reduz (12%), RS/SC/MS caem no `padrão` (a confirmar). O
  `aplicarConc` aplica o ICMS do subgrupo escolhido (B1 vs B2) — selecionar
  "B2 – Rural" zera/reduz o ICMS e derruba a tarifa cheia. Convênio ICMS 76/1991.
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
  grava o projeto (o antigo botão "Calcular" foi removido — o valor já recalcula
  sozinho por `agendar()`; erros aparecem ao gerar). Ao final, o PDF **abre
  automaticamente** numa nova aba (`window.open`), com link de download de
  reserva. Cada projeto vai para uma **subpasta nomeada**
  `<base>/<CONSULTOR>/<NOME>/<7,44KWP ONGRID CHINT 5K 220V COLONIAL>/` contendo
  `RESUMO.txt`, `CONFERENCIA.txt`, `DADOS.json`, `<nome>.pdf` e as **fotos que
  foram para o PDF** (`MODULO.<ext>` / `INVERSOR.<ext>` — arquivos soltos, não
  base64 dentro do `DADOS.json`, que ficaria enorme). O rótulo do
  projeto sai de `app._nome_projeto()` (kWp + conexão + inversores + estrutura).
  **Microinversor:** quando `e.tem_micro()`, o rótulo ganha **MICRO** após a
  conexão (ex.: `4,96KWP ONGRID MICRO CHINT 6K 220V FIBROCIMENTO`) e o PDF ganha
  o sufixo **" - MICRO"** (`JOÃO ... - MICRO.pdf`); string fica como está.
  O **consultor** é um campo livre em Cliente (`app._pasta_projeto` insere esse
  nível só quando preenchido). O botão **Importar projeto** varre a base em
  qualquer profundidade (`os.walk`, procura `DADOS.json`) e repovoa via `aplicar()`
  — incluindo o **CEP** e as **fotos** (o `/api/importar-resumo` lê o MODULO/
  INVERSOR da pasta com `_ler_imgs_projeto` e devolve como data URL).
  ⚠ Campo `<input type="number">` **não aceita vírgula**: escrever "6,63" nele
  deixa o campo VAZIO. Por isso `_set`/`preencherUC` usam ponto nesses campos
  (era o que apagava PIS/COFINS ao importar).
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
**Consultor × admin (19/10/2026):** o `/api/calcular` do consultor sai SEM os
campos de custo (`app._RESUMO_CUSTOS`: composição, custos, margem, lucro, preço/Wp)
— antes a tela só os escondia e o JSON chegava inteiro ao navegador. A
solicitação de cotação exige o telhado (a lista abre vazia; antes vinha
FIBROCIMENTO marcado sem ninguém escolher). O telhado da PROPOSTA do consultor
vem do pacote (`_PACOTE_EQUIP`), não de um campo dele.
**Pacote ← solicitação:** no 🔔 do admin, "📦 Criar pacote" abre um pacote com o
telhado do pedido, nome NEUTRO (kWp + telhado — o nome aparece a todos os consultores
e vai ao config.json público) e `origem` = {solicitacao_id, cidade, consumo_medio,
kwp_sugerido} (sem nome de cliente/consultor; o selo lê o nome da solicitação). O
quadro do kit usa a irradiação dessa cidade e mostra cobertura % + "usar N módulos"
para 100 %. Salvar marca a solicitação `atendida` com `pacote {id,nome,kwp}`; o
consultor vê isso em "Suas solicitações" (quadro da potência sugerida) com "usar
este kit". `origem` nunca vai ao consultor (`_pacote_publico` só manda equipamento).
Editor de pacotes: Ctrl+V/arrastar caem na caixa de imagem sob o mouse; micro =
botão Micro/String, string box/bateria = chaves; Custo 380 V só com inversor 380 V
(e vai ZERO sem ele — o motor soma sempre; vale também no formulário do admin).
`/api/sugestao` (potência sugerida do consultor) agora roda o próprio `engine.calcular`
com kit zero (`_montar_entradas(d, com_pacote=False)`): desconta as usinas
existentes igual à proposta (antes era uma conta à parte que não descontava).

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

**URL de produção:** `<URL-PRODUCAO>`
(302 → `/login`, protegida pela senha do app). Abrir no celular e digitar a senha.

Projeto: ID **<PROJETO-ID>** (número **<NUMERO-PROJETO>**), dentro da organização
**<DOMINIO-DA-ORG>** (org ID **<ORG-ID>**). Região **southamerica-east1**.
Bucket **<BUCKET>** montado em **/data**; contém `config.json`,
`google_oauth.json`, `google_token.json` (e, em uso, `clientes/`, `acesso.json`).

Como foi feito (Cloud Shell, na conta do usuário):
1. **Billing**: vinculada conta de faturamento ao projeto (era o bloqueio antigo).
2. **Serviços + bucket**: `gcloud services enable run/cloudbuild/storage/
   artifactregistry`; `buckets create gs://<BUCKET>
   --location=southamerica-east1`; `roles/storage.objectAdmin` no bucket p/ o SA
   `<NUMERO-PROJETO>-compute@developer.gserviceaccount.com`.
3. **Permissão de build**: o deploy por `--source` exigiu dar
   **`roles/cloudbuild.builds.builder`** ao mesmo SA `…-compute@…` (senão dá 403
   `storage.objects.get` no bucket `run-sources-…` durante "Uploading sources").
4. **Dados no bucket**: `gcloud storage cp` dos 3 arquivos p/ `gs://…/`.
5. **Deploy**: `gcloud run deploy dimensionador --source . --region
   southamerica-east1 --allow-unauthenticated --memory 1Gi
   --set-env-vars S2V_SECRET=<frase>,S2V_SENHA=<senha>
   --add-volume name=dados,type=cloud-storage,bucket=<BUCKET>
   --add-volume-mount volume=dados,mount-path=/data`. **Usar o ID do projeto**
   (`gcloud config set project <PROJETO-ID>`) — com o número dá erro.
6. **Acesso público**: `--allow-unauthenticated` foi barrado pela política de
   organização **Domain Restricted Sharing** (`iam.allowedPolicyMemberDomains`),
   que proíbe `allUsers`. Resolvido abrindo **exceção só neste projeto**: papel
   `roles/orgpolicy.policyAdmin` ao usuário na org, depois `org-policies
   set-policy` com `allowAll: true` em
   `projects/<NUMERO-PROJETO>/policies/iam.allowedPolicyMemberDomains`; então
   `run services add-iam-policy-binding … --member=allUsers
   --role=roles/run.invoker` (esperar 1–2 min a política propagar).

**Reimplantar depois de mudar o código**: `git push`, e no Cloud Shell
`cd ~/dimensionador-s2v-main && git pull && gcloud config set project
<PROJETO-ID> && gcloud run deploy dimensionador --source . --region
southamerica-east1 --quiet`. **NÃO repita `--set-env-vars`**: num serviço que já
existe o Cloud Run herda as variáveis (`S2V_SECRET`, `S2V_SENHA`) e o volume da
revisão anterior; `--set-env-vars` SUBSTITUI todas (para trocar só a senha use
`--update-env-vars S2V_SENHA=…`). Se o `S2V_SECRET` mudar, todos os logins caem.
Conferir depois: `gcloud run services describe dimensionador --region
southamerica-east1 --format="value(spec.template.spec.containers[0].env[].name,
spec.template.spec.volumes[].name, status.url)"` → `S2V_SECRET;S2V_SENHA`,
`dados` e a URL. Erro "You do not currently have an active account selected" =
rodar `gcloud auth login` (ou clicar em Autorizar ao abrir o Cloud Shell).
Notas: reconectar o Drive tem de ser no PC (OAuth Desktop só aceita localhost) —
o refresh token existente vale na nuvem.

⚠ **Reimplantar NÃO atualiza o `config.json` do bucket.** Na nuvem o programa lê
o `config.json` do **bucket** (`S2V_DATA_DIR=/data`), não o do código. Então
mudanças feitas direto no `config.json` versionado (concessionária nova, novo
subgrupo, chaves que a tela de pré-definições não grava) **não aparecem na nuvem**
só com `git pull` + `gcloud run deploy` — é preciso mandar o config ao bucket.
**Nunca sobrescreva o do bucket com o do repo** (o bucket pode ter edições feitas
pelo celular — tarifas da COPEL, PIS/COFINS). **Mescle**: adicione só o que falta.
Ex.: para propagar concessionárias novas, no Cloud Shell:
```bash
cd ~/dimensionador-s2v-main && git pull
gcloud storage cp gs://<BUCKET>/config.json /tmp/bucket.json
python3 - <<'PY'
import json
repo   = json.load(open('config.json', encoding='utf-8'))
bucket = json.load(open('/tmp/bucket.json', encoding='utf-8'))
bc = bucket.setdefault('concessionarias', {})
add = [n for n, v in (repo.get('concessionarias') or {}).items()
       if n not in bc and not bc.update({n: v})]   # só adiciona o que falta
json.dump(bucket, open('/tmp/merged.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=2)
print('Adicionadas ao cofre:', add or '(nenhuma)')
PY
gcloud storage cp /tmp/merged.json gs://<BUCKET>/config.json
```
`carregar_config` relê o arquivo a cada requisição → basta recarregar a página no
celular, sem reimplantar. (Sintoma clássico do esquecimento: no celular só aparece
a COPEL no seletor de concessionária, embora o repo tenha todas.)

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

## Composição do preço (painel da direita)

O bloco "Composição do preço" mostra **todos** os itens que somam o custo, em
**% do valor de venda e em R$**: kit, mão de obra, material extra, padrão de
entrada, transformador (com o **adicional 380 V somado dentro**), deslocamento,
comissão, seguro e imposto — seguidos de custo total, lucro e venda (100%). Itens zerados
continuam visíveis (esmaecidos) para a soma poder ser conferida. A lista é
montada **no servidor** (`app._composicao`), a partir das mesmas chaves que
`engine.calcular` usa em `custo_total` — assim não existe uma segunda versão da
conta no JavaScript. `engine` expõe `custo_kit` e `custo_380v` só para isso (já
entravam na conta antes, não apareciam no resultado).

## Texto auxiliar nos campos — a regra

A tela tinha cinza demais competindo com o que importa. A regra agora:
1. **Rótulo** = nome + unidade, e nada mais. Suficixo cinza (`<small class=auto>`)
   só quando é **dinâmico** (preenchido em tempo de uso: `u-not-obs`,
   `u-a-dem-rot`). Detalhe que cabia no cinza foi **dobrado no próprio rótulo**
   ("Preço do kW de TUSD-G, **sem impostos** (R$/kW)", "Injeta na rede",
   "Gerou no total") — texto normal lê melhor que cinza.
2. **Placeholder** só quando o campo **vazio significa algo**, em no máximo duas
   palavras: `automático`, `= a contratada`, `pela regra`, `não modelar`.
   **Nunca** valor de exemplo ("ex.: 25,33") nem repetir a unidade do rótulo
   ("kWh/mês") — isso era puro ruído.
3. **Todo o resto vai para o `title`** (dica ao passar o mouse), que não ocupa
   espaço nem disputa atenção.
4. **Um `.sub-rot` por seção** continua valendo — é o único lugar que explica o
   bloco (ex.: de qual coluna da fatura sair).

Resultado: cinza ao lado de rótulo caiu de 9 para 2 (os dois dinâmicos) e
placeholders de 15 para 6. **Ao acrescentar campo, siga esta regra.**

## Chaves deslizantes (`sw-wrap`) — tela menos densa

Seletor de **duas opções** virou chave deslizante, não `<select>`. `swHTML(cls,
valOff, valOn, rotOff, rotOn, acao, ligado, titulo)` monta um `<label
class=sw-wrap>` com o checkbox visível **mais um `<input type=hidden>` irmão com
a classe `cls`** — é o hidden que guarda o valor, então `lerUC`/`preencherUC`
continuam lendo `.u-gd`, `.u-grupo` e `.u-a-mod` por `.value` exatamente como
liam do `<select>`. `swSync()` grava o valor, troca o rótulo e chama a função
nomeada em `data-acao` (ex.: `setGrupo`), passando **o hidden** — por isso as
funções que recebem `sel` e usam `sel.value`/`sel.closest('.uc')` não mudaram.
`swSet(el, v)` posiciona a chave ao importar um projeto e devolve `false` quando
o campo não é chave (aí o chamador segue pelo caminho antigo).
Booleanos que já eram checkbox (`u-a-conv`, `tem_stringbox`, `tem_bateria`) só
ganharam a roupa: são `.sw-in` + `.sw` + `.sw-rot`, sem hidden.
**Ao acrescentar uma opção nova de duas vias, use `swHTML` em vez de `<select>`.**

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

## Irradiação e performance ratio — UMA perda só (16/10/2026)

**Perda = 1 − PR.** O `config.performance_ratio` (0,75, DADOS!D22, editável nas
pré-definições) é a ÚNICA perda do sistema: entra na geração
(`kWp × PR × irradiação × dias`) e no kWp necessário. Os perfis guardam a
irradiação **bruta** (o "3.8" guarda ~5,04 kWh/m²/dia; o nome já é × 0,75).
`online.buscar_irradiacao(cidade)` devolve a global **horizontal bruta**, na
mesma convenção, nesta ordem: (1) **INPE — Atlas Brasileiro de Energia Solar
2017**, sede municipal, em `assets/irradiacao_inpe.json` (5.569 cidades, SEM
internet; gerado por `ferramentas/irradiacao_inpe.py` a partir do CSV
"sedes-munic" do LABREN) — é a base do SunData/CRESESB e bate com ele
(Maringá 4,89; jan 5,888; jun 3,333); aceita "Cidade - UF", "Cidade/UF",
sem acento; nome repetido sem UF pede a UF; (2) nome fora da tabela
(distrito) → localiza pela internet e usa a sede do INPE mais próxima, até
30 km (`obs` diz qual); (3) só então NASA POWER (`ALLSKY_SFC_SW_DWN`, grade
~50 km, Maringá 5,02 = 2,7 % mais otimista). Resposta traz `fonte` e `obs`. Até out/2026 a busca descontava
também uma `perda_irradiacao` de 25 % — somada ao PR, contava as perdas em
dobro (Maringá: 1.030 em vez de ~1.375 kWh/kWp/ano). Removida da tela, do
`config.json` e do `/api/irradiacao`. (O `config.json` do bucket ainda pode ter a
chave; é ignorada.)
Projeto salvo agora leva `irradiacao_bruta: true`. Ao **importar** um projeto
antigo com irradiação da internet sem essa marca, a tela divide os valores por
0,75 e avisa (a perda antiga era 25 % por padrão).
**Plano HORIZONTAL de propósito** (decisão do usuário, 16/10/2026: "o mais
confiável e conservador, sem fugir do que já é feito"): telhado real raramente
está no ângulo/orientação ideais, e é a convenção dos perfis. Inclinar na
latitude em Maringá ganha só +4,7 % no ano (CRESESB 4,89 → 5,12: sol quase a
pino no verão, muita difusa) e achata a curva mensal. O LABREN também publica
`TILTED_LATITUDE` por município, se um dia quiser oferecer a opção.
Resultado em Maringá, kWh/kWp/ano com PR 0,75: perfil "3.8" 1.378 · INPE 1.337.

**Tela sem lista de perfis (16/10/2026).** A seção "Irradiação & geração"
(só admin) tem: cidade da irradiação (vazio = cidade do cliente; busca sozinha
ao digitar a cidade ou pelo CEP), botão buscar, campo **Performance ratio** do
projeto e o quadro `mostrarIrr()` com fonte, global × PR = **perfil
equivalente** (só a média). O PR é **por projeto e SÓ do admin**
(`Entradas.performance_ratio`, `app._pr_do_payload`: consultor/vazio → None =
o PR das pré-definições, que vira o "padrão"; aceita 0,40–1,00 ou em %; vai no
DADOS.json). Os perfis continuam no `config.json` e no motor (teste_planilha,
Helena, projetos antigos): sem cidade buscada vale o "3.8" com aviso no quadro;
projeto importado mantém a irradiação/perfil salvos (não rebusca sozinho).

**PR padrão = 0,77** (decisão do usuário, 16/10/2026): com a irradiação
HORIZONTAL do INPE, é o PR que reproduz o perfil "3.8" (3,78 efetivos) em
Maringá — 4,89 × 0,77 = 3,77; 1.373 × 1.378 kWh/kWp/ano. Conferido contra o
CRESESB nos 104 municípios a até 100 km de Maringá (diferença máx. 0,005
kWh/m²/dia num mês). Opções recusadas: inclinado+0,75 (+1,6 %, telhado ideal)
e horizontal+0,80 (+3,5 %). Os testes FIXAM `performance_ratio = 0,75` (o da
planilha, DADOS!D22), como já fixavam o Fio B. Projeto importado sem PR salvo
abre com 0,75 (foi feito assim). ⚠ Sem cidade buscada, o perfil "3.8" de
reserva com 0,77 fica ~2,7 % acima do de antes; o JSON da Helena com
`perfil_irradiacao` também (sem `performance_ratio` no JSON = o padrão 0,77).

## GD1 × GD2 por UC

`UC.gd` ('GD1' ou 'GD2', padrão **GD2**). GD2 paga o Fio B escalonado (Lei
14.300, comportamento validado). GD1 é isenta de Fio B até 2045 → compensa a TUSD
integral (`fio_b_uc = 0` na fatura daquela UC). Cada UC escolhe na tela; a de
validação usa o default GD2, então `teste_planilha` segue idêntico.

## Próximo passo: integração com a HELENA (bot da S2V)

**Estado em 09/10/2026.** Tudo abaixo já está no GitHub (commit `985aa86`, branch
`main`). O deploy no Cloud Run dessa versão **ainda não foi confirmado**: o
usuário rodou o comando único no Cloud Shell e parou em "You do not currently
have an active account selected" — falta `gcloud auth login` e rodar de novo
(comando em "Cloud Run"; sem `--set-env-vars`, o serviço herda senha e chave).

### Quem é a Helena e a divisão de trabalho
Assistente da S2V (o usuário a montou no Claude Desktop) que conversa com o
cliente e **lê a fatura**. Regra de ouro, já no `exemplos/BRIEFING-HELENA.md`:
**a Helena monta o JSON; o Dimensionador faz TODAS as contas.** Ela nunca
calcula economia, payback, kWp ou valor de conta por conta própria (num teste
ela errou a lógica de usina existente e dimensionou uma ampliação desnecessária
— está na seção 7 do briefing).

### O contrato que já existe (rotas reais do `app.py`)
Todas as rotas `/api/*` exigem **sessão** (cookie) quando há senha; sem sessão
devolvem `401 {"ok": false, "erro": "sessão expirada — faça login"}`.
- **Login**: `POST /login` com formulário `usuario` + `senha`. `usuario` vazio =
  **administrador**; preenchido = consultor (nome + senha cadastrados nas
  pré-definições). O cookie de sessão vale nas chamadas seguintes.
- **Grupo A exige ADMIN**: com sessão de consultor o servidor força `grupo='B'`
  e descarta a demanda **sem avisar**. Consultor também não manda preço: escolhe
  um `pacote_id` e o servidor injeta equipamento e custos (`_aplicar_pacote`).
- `POST /api/sugestao` → `{kwp_necessario, consumo_medio, consumo_anual}` — só
  consumo + irradiação, não precisa de kit. Bom para a primeira resposta.
- `POST /api/calcular` → `{ok, resumo}`. No `resumo`: `kwp`, `kwp_necessario`,
  `modulos_sugeridos`, `geracao_media`, `consumo_medio`, `compensacao_pct`,
  `preco_venda` / `preco_venda_num`, `fatura_sem`, `fatura_com`,
  `economia_mensal`, `payback`, `retorno_25`, `parcela_fin`, `parcela_cartao`,
  `composicao` (custos — **não mostrar ao cliente**), `tem_grupo_a`, `grupo_a`
  (lista por UC: demanda, energia sem/com, autoconsumo, injetado, TUSD-G,
  `autoconsumo_regra`…) e `textos` (as strings que vão para a proposta).
- `POST /api/conferencia` → `{texto}`: o passo a passo do retorno (auditoria).
- `POST /api/conferir-fotos` → `{avisos: [...]}`: foto padrão de outro equipamento.
- `POST /api/previa` → **PDF** da proposta, sem salvar nada nem enviar ao Drive.
- `POST /api/proposta` → **PDF** + grava a pasta do projeto (RESUMO, CONFERENCIA,
  DADOS.json, fotos) e envia ao Drive se configurado. É a ação "de verdade".
- Apoio: `GET /api/concessionarias`, `GET /api/aneel-tarifa`,
  `GET /api/aneel-tarifa-a` (admin), `POST /api/irradiacao`, `GET /api/cep/<cep>`,
  `GET /api/pacotes`.
O mesmo JSON serve para `calcular`, `previa` e `proposta` (e é o `DADOS.json`
que a tela importa).

### O formato do JSON (armadilhas — detalhe no briefing)
- **Percentuais em %**, não em fração: `icms: 19`, `pct_noturno: 65`,
  `margem_desejada: 16`.
- `consumos` = **12 posições** (jan–dez). No grupo A, `consumos` é o **fora
  ponta** e `consumos_ponta` a ponta; não existe `pct_noturno`.
- Tarifas **sem tributos** (coluna "Tarifa unit." da fatura). O **Fio B não vai
  no JSON** — vem das pré-definições, por concessionária.
- Cliente que já gera: `gds_existentes: [{nome, kwp, inversor_kw, injetado_kwh,
  geracao_kwh, isento_icms}]` e, no grupo B, `pct_noturno: 100`. `injetado_kwh`
  vem da fatura; `geracao_kwh` só do app de monitoramento (0 se não souber);
  `inversor_kw` entra na TUSD-G do grupo A.
- Projeto novo tem parecer novo: `abat_te_inclui_icms: true` e
  `isencao_icms_anos` (~4). Usina antiga com mais de ~4 anos: `isento_icms: false`.
- `irradiacao_customizada` (12 valores) + `irradiacao_local` (cidade) quando a
  irradiação vier da internet; senão `perfil_irradiacao` ("3.8" = Maringá).
- **Teste de sanidade antes de orçar**: mandar com `qtd_modulos_kit: 0` — o
  `fatura_sem` tem de bater com o total da fatura do cliente. Não bateu = erro
  de leitura; não prosseguir.
Moldes prontos e conferidos (anonimizados): `exemplos/fatura_real_grupo_b.json`
(R$ 117,53), `exemplos/fatura_real_grupo_a.json` (R$ 17.648,01) e
`exemplos/projeto_novo_grupo_a.json` (projeto novo de 112,5 kWp sobre a usina
existente: conta R$ 17.648,01 → R$ 10.488,70, 35 kW de TUSD-G, pior caso).

### Critérios da S2V que a Helena tem de respeitar
- **Pior caso sempre** no autoconsumo do grupo A (o programa já faz).
- Nunca prometer "zerar a conta" em média tensão: a demanda não é abatida.
- Não estimar potência de usina existente pelo injetado, nem dimensionar
  ampliação por "carga ÷ produtividade" — mandar o consumo com a carga nova +
  `gds_existentes` e usar o kWp que o programa devolver.
- Na dúvida, perguntar (geração real, idade da usina/parecer, módulos já
  instalados, padrão de entrada) em vez de estimar.

### O que FALTA decidir/construir para ligar a Helena (ainda não começou)
1. **Como ela chama o programa**: hoje só existe a API HTTP com cookie de
   sessão. Opções: (a) um servidor MCP fino que faz login e expõe `sugestao` /
   `calcular` / `previa` / `proposta` como ferramentas; (b) um token fixo por
   cabeçalho (ex.: `Authorization: Bearer`, guardado em `acesso.json`/variável de
   ambiente) para não depender de cookie. Nenhum dos dois existe.
2. **Com que papel ela entra**: consultor (só pacotes, sem grupo A, sem ver
   custos) ou admin (tudo). Para grupo A hoje só serve admin — talvez um papel
   próprio "helena" (grupo A sim, custos não).
3. **Local ou nuvem**: `localhost:8177` (PC ligado) ou a URL do Cloud Run.
4. **O que volta para o cliente**: só números, ou o PDF (`/api/previa` não
   salva; `/api/proposta` salva e manda ao Drive — a Helena não deveria salvar
   orçamentos em nome de consultor sem critério).
5. **Leitura da fatura**: a Helena lê e monta o JSON (briefing, seções 3 e 4);
   o "anexar fatura" dentro do próprio programa continua não implementado.

### Decisões de cálculo em aberto (aguardando o usuário)
Surgiram ao auditar um orçamento do grupo B em 08/10/2026 e mexem em valores do
`teste_planilha` — **não fazer sem confirmação**:
- **A "conta sem S2V" não inclui a bandeira** (fórmula da planilha:
  tarifa × kWh + iluminação). Erro para o lado conservador (~R$ 16/mês numa
  amarela com 640 kWh).
- **A "conta sem" usa o MAIOR entre consumo e geração** (`maior`, DD!G48). Em
  sistema sobredimensionado (176 % no caso auditado) a conta sem vira a de quem
  consumiria toda a geração: R$ 709 contra ~R$ 424 da conta de hoje, e a economia
  anunciada R$ 554 contra ~R$ 315 com o consumo atual. É réplica fiel da
  planilha — e o caso de validação (141 %) depende disso.
- Falta uma **fatura com custo de disponibilidade + bandeira** não verde para
  travar a regra nova da bandeira (decisão 11).

## Dados do usuário (nunca versionar / nunca sobrescrever)

`clientes/`, `propostas/` e caches estão no `.gitignore`. **Não** os apague nem
sobrescreva. `config.json` **é versionado** mas o usuário edita as tarifas por
lá — ao mexer nele, prefira acrescentar chaves a reescrever o arquivo.

## Como verificar mudanças

- **Cálculo** → `python3 teste_planilha.py` (réplica exata da planilha),
  `python3 teste_correcoes.py` (correções pós-planilha: abatimento parcial da
  Lei 14.300, Convênio ICMS 16/2015 e alavanca `icms_te`) **e**
  `python3 teste_grupo_a.py` (média tensão: demanda não abatida, ordem da
  compensação, fator de ajuste da ponta, trava do consultor). Todos DEVEM passar.
  Carregador veicular → `python3 teste_wallbox.py`.
  (No Windows: `py`, e `PYTHONIOENCODING=utf-8` para o console não engasgar.)
- **PDF** → gere e confira por pixels/OCR (`pdftoppm -r 150` + PIL/pytesseract).
  Não confie em "parece certo": meça.
  **Ajuste de layout = antes × depois:** `py ferramentas/previa.py --base`
  congela a proposta atual (3 casos fictícios: B completo, B sem bateria/string
  box, A ampliação) em `previa/base/`; depois de mexer, `py ferramentas/previa.py`
  aponta cada região que mudou (em pt) e salva o lado a lado em
  `previa/comparar/`. Mudança fora do lugar pretendido = efeito colateral.
  `py ferramentas/previa.py --caixas` desenha um quadrado AZUL em volta da
  parte PREENCHIDA de cada ícone — MEDIDA na imagem a 300 dpi, sem o anel dos
  círculos — e lista largura × altura e o desvio do centro (`previa/caixas/`).
  É a prova de que tamanhos e centros seguem a regra (`proposta._REGISTRO_ICONES`
  anota cada ícone desenhado só nesse modo).
  O usuário quer padronizar a proposta **UMA mudança aprovada por vez** — nunca
  em bloco. Na tela, o botão **👁 Pré-visualizar** (`/api/previa`) gera o mesmo
  PDF sem salvar pasta nem enviar ao Drive.
- **UI** → o JS é validado com `node --check` (remova as tags Jinja antes).
  ⚠ **Não há Node nesta máquina.** Use o motor JS que vem dentro do VS Code:
  ```bash
  py -c "import io,re,os;s=io.open('templates/index.html',encoding='utf-8').read();  js=re.search(r'<script>(.*)</script>',s,re.S).group(1);  js=re.sub(r'\{\{.*?\}\}','null',js,flags=re.S);js=re.sub(r'\{%.*?%\}','',js,flags=re.S);  io.open(os.environ['TEMP']+'/s2v_check.js','w',encoding='utf-8').write(js)"
  ELECTRON_RUN_AS_NODE=1 "$LOCALAPPDATA/Programs/Microsoft VS Code/Code.exe"     --check "$TEMP/s2v_check.js"
  ```
  Sem saída = sem erro de sintaxe. **Faça isso sempre que mexer no `index.html`** —
  um erro de sintaxe no JS deixa a tela carregada porém morta, e nenhum teste de
  Python pega isso.
- **Servidor** → suba numa porta de teste e chame os endpoints; não deixe
  processos pendurados.

## Data e hora = Brasília

O Cloud Run roda em UTC. Toda data/hora do programa sai de `engine.agora()` /
`engine.hoje()` (UTC−3 fixo, `FUSO_BR`) — nunca do relógio do servidor. Sem isso a
solicitação das 17:37 saía às 20:37 e, depois das 21h, o mês do orçamento virava.

## Estilo

Código e comentários em português, com referência à célula da planilha quando
aplicável (ex.: `# PR!N31`). Sem dependências novas sem necessidade real
(hoje: flask, reportlab, pypdf, matplotlib, qrcode).

## Pendências combinadas

- **Integração com a Helena** — ver "Próximo passo".
- **Anexar fatura dentro do programa** (PDF/foto → dados da UC): não implementado.
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
