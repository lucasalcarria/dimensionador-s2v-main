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

`assets/`: `fundo.pdf` (layout original), `layout.json` (posição de cada campo),
`cards/` (tiles 600dpi dos cartões da pág. 3 + `layout_cards.json`),
`deco.json` (timeline vetorial e sangria da capa), `fonts/`, `logo.png`.

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
6. **Cartões da pág. 3 se reagrupam** quando falta string box e/ou bateria
   (sem buracos), e a garantia "BATERIA DE LÍTIO" some sem bateria.
7. **Valores medidos são sagrados**: geometrias em `layout.json`/`deco.json`
   (ex.: 7 círculos da timeline, raio 9pt, cy 776,6) foram medidas em pixels do
   PDF original. Se mexer, **remeça** — não chute.

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
