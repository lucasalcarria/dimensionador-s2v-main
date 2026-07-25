# Mapa dos dados da proposta

De onde sai cada número impresso nas 5 páginas. Serve para responder rápido:
*"esse valor da proposta, quem calcula?"*

## Como a proposta é montada

O layout vem do **HTML entregue pelo design** (`proposta_s2v.html`). Uma
ferramenta de build converte esse HTML uma única vez:

```bash
python ferramentas/html_para_fundo.py ~/Downloads/proposta_s2v.html
```

Ela gera três coisas dentro de `assets/`:

| Arquivo | O que é |
|---|---|
| `fundo.pdf` | a arte vetorial + todos os textos **fixos** das 5 páginas |
| `layout.json` | a posição exata de cada valor **calculado** |
| `cards/*.png` + `layout_cards.json` | os 6 cartões da pág. 3, soltos (eles se reagrupam) |

Depois disso o programa do dia a dia (`proposta.py`) só empilha:
**fundo.pdf → cartões → gráfico → valores do cliente**.

Para um dado ser dinâmico ele precisa de duas coisas: existir em
[engine.py:483](engine.py#L483) (`_textos()`, que devolve o texto já formatado,
com "R$", "kWh/mês" e vírgula decimal) e ter uma linha em
[assets/layout.json](assets/layout.json) dizendo em que página e posição
desenhar. Hoje são **34 posições**.

---

## Página 1 — capa

| O que aparece | Chave | De onde vem |
|---|---|---|
| Neuza Zamferrari | `nome_proper` | nome digitado, em Caixa Alta Inicial |
| 12345, 23456, 34567 | `uc_numero` | os nº de UC de **todas** as faturas cadastradas, juntos |
| Rua Manoel Saes, 213 | `endereco` | logradouro **+ número** (campos separados na tela) |
| Mandaguaçu - PR | `cidade` | cidade digitada (ou vinda do CEP) |
| 3,72 kWp | `kwp_txt` | `resultado['kwp']` arredondado p/ cima, 2 casas |

Os quatro campos de dados da capa (nome, UC, local, sistema) ficam em colunas
estreitas entre divisores. Se o texto não couber, ele **quebra em até 2 linhas**
e, só se ainda assim estourar, a fonte diminui — nunca invade a coluna vizinha.

## Página 2 — "Como a energia flui"

**Nada é dinâmico.** É a página institucional inteira.

## Página 3 — dimensionamento

### Os 6 cartões do kit

Cada cartão é uma peça independente. Quando falta string box e/ou bateria, os
presentes **se reagrupam de cima para baixo, sem buracos** — e, se sobrar um
sozinho na última linha, ele fica centralizado.

| O que aparece | Chave | De onde vem |
|---|---|---|
| 6x | `mod_qtd` | quantidade de módulos do kit |
| Astronergy N-Type 620W | `mod_desc` | marca + potência do módulo |
| 2x | `estr_qtd` | módulos ÷ 4 (ou ÷ 8 se for SOLO), arredondado p/ cima |
| P/ 4 Mod. Fibrocimento | `estr_desc` | tipo de telhado escolhido |
| 1x | `inv_qtd` | sempre 1 |
| INVERSOR HÍBRIDO | `inv_titulo` | tipo de conexão (HÍBRIDO / ON GRID …) |
| CHINT 3kW Mono 220V | `inv_desc` | marca, kW, MONO/TRI (≤10 kW = MONO), tensão |
| 1x / Clamper 2E/2S | `sb_qtd` / `sb_desc` | só com string box |
| 2x / Byd 5,12 kWh | `bat_qtd` / `bat_desc` | só com bateria — sem marca/kWh o card fica só com a quantidade |
| HOMOLOGAÇÃO — 1x | *(fixo)* | está desenhado no cartão |

### Números do sistema

| O que aparece | Chave | Conta por trás |
|---|---|---|
| 3,72 kWp | `kwp_txt` | nº de módulos × potência ÷ 1000 |
| 302 kWh/mês | `consumo_txt` | média dos 12 consumos informados |
| 427 kWh/mês | `geracao_txt` | geração estimada pela irradiação do local |
| 26,2 m² | `area_txt` | área ocupada pelos módulos |
| 141% | `compensa_txt` | geração ÷ consumo (trava em 100 % quando ≥ 97 %) |

### Garantias

| Rótulo na arte | Chave | Regra |
|---|---|---|
| INVERSOR | `gar_inversor` | 15 se MICRO DEYE/HOYMILES, senão 10 |
| MÓDULOS | `gar_instalacao` | 20 AmeriSolar · 15 N-Type · senão 12 |
| PERFORMANCE LINEAR | `gar_modulos` | 30 p/ Sunova/OSDA/AmeriSolar/N-Type, senão 25 |
| BATERIA DE LÍTIO | `gar_bateria` | 10 anos — a linha **inteira some** sem bateria |

Sem bateria, as três primeiras linhas **descem 22 pt** e ficam centradas no
quadro, em vez de encostadas no alto. Elas são estampadas como uma peça só
(`assets/cards/garantias.png`), igual aos cartões.

> Os rótulos "MÓDULOS" e "PERFORMANCE LINEAR" recebem, respectivamente, a
> garantia de *instalação* e a de *módulos*. É assim desde a planilha; foi
> mantido de propósito. Se quiser trocar, é só inverter as duas chaves.

Todas podem ser travadas em `config.json → garantias_fixas`.

## Página 4 — consumo × geração

| O que aparece | De onde vem |
|---|---|
| Barras azuis (Consumo) | `resultado['consumo_mensal']` — reto se o cliente usou o consumo médio; variando se digitou mês a mês |
| Barras verdes (Geração) | `resultado['geracao_mensal']` — 12 valores, um por mês |
| Escala do eixo Y, meses, legenda | calculados a partir do maior valor |

O gráfico é **vetorial** (matplotlib) e cai exatamente sobre a área reservada na
arte (x 130,2–508,7 · y 230,1–350,0 pt). Fixo: o cartão "PROJETOS REALIZADOS"
é portfólio da empresa, não do cliente.

## Página 5 — investimento e retorno

| O que aparece | Chave | Conta por trás |
|---|---|---|
| R$ 8.758,12 (à vista) | `valor_venda` | preço de venda calculado |
| R$ 403,32 (conta sem) | `fatura_sem` | fatura atual do cliente |
| R$ 125,70 (conta com) | `fatura_com` | fatura depois do sistema |
| R$ 277,62 (economia) | `economia_mensal` | diferença das duas |
| 2,6 ANOS (payback) | `payback_txt` | investimento ÷ economia anual |
| R$ 16.651,45 (25 anos) | `retorno_25` | economia projetada em 25 anos |
| 7 DIAS (validade) | `validade_txt` | `config.json → validade_dias` |
| "referentes a jul/2026" | `disclaimer_data` | mês/ano de hoje, automático |
| NEUZA ZAMFERRARI | `nome_upper` | nome em maiúsculas, sobre a linha de aceite |

Fixo: "CARTÃO DE CRÉDITO — EM ATÉ 12X + TAXA DA MAQUININHA", os logos dos
bancos sob "FINANCIAMENTO", o bloco de aceite e o CNPJ.

---

## Ainda calculado e não impresso

O programa calcula estes dois valores, mas **o layout novo não tem lugar para
eles** (o bloco "FINANCIAMENTO" virou uma vitrine de logos de bancos):

| Valor | Onde está |
|---|---|
| `fin_txt` — "EM 60x SOB 1,99% AO MÊS" | [engine.py:561](engine.py#L561) |
| `parcela_fin` — R$ 251,34 | `resultado['parcela_fin']` |

Se um dia o design abrir espaço, basta acrescentar os dois em `CAMPOS` dentro de
[ferramentas/html_para_fundo.py](ferramentas/html_para_fundo.py) e rodar o
conversor de novo.

## Textos fixos que talvez devessem seguir o cliente

| Texto | Página | Por quê |
|---|---|---|
| "Projeto aprovado COPEL" | 3 | a concessionária já é escolhível na tela |
| "radiação solar de Maringá e região" | 3 | a cidade do cliente já é conhecida |
| "EM ATÉ 12X + TAXA DA MAQUININHA" | 5 | condição comercial, pode mudar |

Nenhum é erro — só não acompanha o cliente hoje.
