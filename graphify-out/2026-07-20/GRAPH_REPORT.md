# Graph Report - dimensionador-s2v-main  (2026-07-20)

## Corpus Check
- 22 files · ~27,823 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 265 nodes · 403 edges · 20 communities (10 shown, 10 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Motor de Cálculo & Validação (engine.py)
- Documentação do Skill Graphify
- Servidor Flask & API (app.py)
- Geração de PDF da Proposta
- Configuração & Documentação Geral
- Interface do Usuário (JS da index.html)
- Integração com Internet (online.py)
- Unidade Consumidora (UC) — campos
- PWA: pendência vs. implementação
- Script de Inicialização (iniciar.sh)
- Export FalkorDB (ref. graphify)
- Export GraphML (ref. graphify)
- Servidor MCP (ref. graphify)
- Export Neo4j (ref. graphify)
- Export SVG (ref. graphify)
- Benchmark de tokens (ref. graphify)
- Regra: Fio B Escalonado
- Regra: Preço/Wp Convergente
- teste_planilha.py
- Constrained Query Expansion

## God Nodes (most connected - your core abstractions)
1. `calcular()` - 20 edges
2. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
3. `graphify (knowledge graph tool)` - 20 edges
4. `UC` - 16 edges
5. `Entradas` - 12 edges
6. `gerar_proposta()` - 12 edges
7. `carregar_config()` - 11 edges
8. `_textos()` - 11 edges
9. `Dimensionador S2V (project)` - 10 edges
10. `_montar_entradas()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Regra número 1: engine.py réplica validada da planilha` --semantically_similar_to--> `Honesty Rules (never invent an edge)`  [INFERRED] [semantically similar]
  CLAUDE.md → .claude/skills/graphify/SKILL.md
- `Pendência: PWA (manifest.json + service worker)` --semantically_similar_to--> `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS] [semantically similar]
  CLAUDE.md → templates/index.html
- `Caso de validação NEUZA ZAMFERRARI (UC 16285387)` --semantically_similar_to--> `Teste automatizado contra a planilha`  [INFERRED] [semantically similar]
  CLAUDE.md → LEIA-ME.md
- `Teste automatizado contra a planilha` --semantically_similar_to--> `Regra número 1: engine.py réplica validada da planilha`  [INFERRED] [semantically similar]
  LEIA-ME.md → CLAUDE.md
- `Valores medidos são sagrados (layout.json/deco.json)` --semantically_similar_to--> `Node ID Format Rule ({stem}_{entity})`  [INFERRED] [semantically similar]
  CLAUDE.md → .claude/skills/graphify/references/extraction-spec.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Build Pipeline (extract → build → cluster → report)** — _claude_skills_graphify_skill_structural_extraction, _claude_skills_graphify_skill_semantic_extraction, _claude_skills_graphify_skill_community_detection, _claude_skills_graphify_skill_graph_json [EXTRACTED 1.00]
- **Graph Query & Explanation Flows (query/path/explain + save-result)** — _claude_skills_graphify_skill_query_command, _claude_skills_graphify_skill_path_command, _claude_skills_graphify_skill_explain_command, _claude_skills_graphify_references_query_save_result [EXTRACTED 1.00]
- **Dimensionador S2V Core Architecture (engine/proposta/app/UI)** — engine, proposta, app, templates_index [EXTRACTED 1.00]

## Communities (20 total, 10 thin omitted)

### Community 0 - "Motor de Cálculo & Validação (engine.py)"
Cohesion: 0.13
Nodes (28): % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, relatorio_conferencia(), dict, calcular(), _dec(), Entradas (+20 more)

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.06
Nodes (36): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+28 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.06
Nodes (39): api_atualizar_tarifa(), api_calcular(), api_concessionarias(), api_conferencia(), api_copel_verificar(), api_proposta(), api_rede(), api_salvar_resumo() (+31 more)

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.09
Nodes (34): Cartões da pág. 3 se reagrupam (string box/bateria), _carregar_cards(), _carregar_deco(), _carregar_layout(), _desenhar_campo_cartao(), _desenhar_cards_p3(), _desenhar_fotos_p3(), _estender_cover() (+26 more)

### Community 4 - "Configuração & Documentação Geral"
Cohesion: 0.08
Nodes (24): Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Usar no celular via QR code / mesma rede Wi-Fi, Conferência do retorno financeiro, Parâmetros editáveis em config.json, Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME), Estrutura de pastas do projeto (+16 more)

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.09
Nodes (16): Tarifas da concessionária — tabela local sem depender de internet, addUC(), agendar(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT(), calc() (+8 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.13
Nodes (20): ANEEL removida de propósito / tarifas em tabela local, Raspagem HTML do site da COPEL (sem Power BI), NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), geocodificar(), _get_html() (+12 more)

### Community 7 - "Unidade Consumidora (UC) — campos"
Cohesion: 0.21
Nodes (3): Uma unidade consumidora — linha 6..14 de PR + linha 31..39., % noturno aplicado no faturamento com solar.          Na planilha (coluna M): a, UC

### Community 19 - "teste_planilha.py"
Cohesion: 0.20
Nodes (13): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), DD!R25:S34 — autotrafo 380/220 V p/ inversores ≥12 kW em 380 V., _trafo(), Uso no celular via QR code / LAN, Teste automatizado contra a planilha, templates/index.html (UI: HTML+CSS+JS) (+5 more)

### Community 21 - "Constrained Query Expansion"
Cohesion: 0.33
Nodes (6): BFS Traversal Mode, DFS Traversal Mode, graphify reflect / LESSONS.md, save-result Work Memory (useful/dead_end/corrected), Constrained Query Expansion, graphify query

## Ambiguous Edges - Review These
- `Pendência: PWA (manifest.json + service worker)` → `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS]
  CLAUDE.md · relation: semantically_similar_to

## Knowledge Gaps
- **40 isolated node(s):** `iniciar.sh script`, `Instalação Windows com Python`, `Executável único (.exe) via build_windows.bat`, `Instalação Linux/macOS via iniciar.sh`, `Passo a passo na tela (máscaras, UCs, kit gerador)` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pendência: PWA (manifest.json + service worker)` and `PWA Service Worker Registration (sw.js)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `graphify (knowledge graph tool)` connect `Documentação do Skill Graphify` to `Constrained Query Expansion`?**
  _High betweenness centrality (0.226) - this node is a cross-community bridge._
- **Why does `Dimensionador S2V (project)` connect `teste_planilha.py` to `Motor de Cálculo & Validação (engine.py)`, `Servidor Flask & API (app.py)`, `Geração de PDF da Proposta`, `Configuração & Documentação Geral`, `Integração com Internet (online.py)`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `teste_planilha.py` to `Motor de Cálculo & Validação (engine.py)`, `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.216) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Instalação Windows com Python`, `Executável único (.exe) via build_windows.bat` to the rest of the system?**
  _40 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.13118279569892474 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.06031746031746032 - nodes in this community are weakly interconnected._