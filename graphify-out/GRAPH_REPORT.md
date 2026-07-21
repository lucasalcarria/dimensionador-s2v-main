# Graph Report - dimensionador-s2v-main  (2026-07-21)

## Corpus Check
- 22 files · ~27,693 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 263 nodes · 399 edges · 22 communities (11 shown, 11 thin omitted)
- Extraction: 94% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
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
- agendar
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
- caminho_config
- Constrained Query Expansion

## God Nodes (most connected - your core abstractions)
1. `calcular()` - 20 edges
2. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
3. `graphify (knowledge graph tool)` - 20 edges
4. `UC` - 16 edges
5. `Entradas` - 12 edges
6. `carregar_config()` - 11 edges
7. `_textos()` - 11 edges
8. `gerar_proposta()` - 11 edges
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

## Communities (22 total, 11 thin omitted)

### Community 0 - "Motor de Cálculo & Validação (engine.py)"
Cohesion: 0.12
Nodes (30): % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, relatorio_conferencia(), dict, calcular(), _dec(), Entradas (+22 more)

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.06
Nodes (36): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+28 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.08
Nodes (33): api_calcular(), api_concessionarias(), api_conferencia(), api_copel_verificar(), api_proposta(), api_rede(), api_salvar_resumo(), _clientes_dir() (+25 more)

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.09
Nodes (33): Cartões da pág. 3 se reagrupam (string box/bateria), Melhorias gráficas da proposta impressa, _carregar_cards(), _carregar_deco(), _carregar_layout(), _desenhar_campo_cartao(), _desenhar_cards_p3(), _desenhar_fotos_p3() (+25 more)

### Community 4 - "Configuração & Documentação Geral"
Cohesion: 0.10
Nodes (22): ANEEL removida de propósito / tarifas em tabela local, Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Usar no celular via QR code / mesma rede Wi-Fi, Conferência do retorno financeiro, Parâmetros editáveis em config.json, Raspagem HTML do site da COPEL (sem Power BI) (+14 more)

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.10
Nodes (17): Salvar resumo na pasta do cliente, Tarifas da concessionária — tabela local sem depender de internet, addUC(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT(), carregarConcessionarias() (+9 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.15
Nodes (18): NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), geocodificar(), _get_html(), _get_json(), _get_json_curl() (+10 more)

### Community 7 - "Unidade Consumidora (UC) — campos"
Cohesion: 0.21
Nodes (3): Uma unidade consumidora — linha 6..14 de PR + linha 31..39., % noturno aplicado no faturamento com solar.          Na planilha (coluna M): a, UC

### Community 19 - "teste_planilha.py"
Cohesion: 0.23
Nodes (11): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), Uso no celular via QR code / LAN, Teste automatizado contra a planilha, templates/index.html (UI: HTML+CSS+JS), caso_planilha(), identidade() (+3 more)

### Community 20 - "caminho_config"
Cohesion: 0.33
Nodes (6): api_atualizar_tarifa(), Grava TE/TUSD de uma concessionária+subgrupo na tabela local.      Aceita valore, caminho_config(), dir_execucao(), Pasta onde o usuário executa o programa (ao lado do .exe, se congelado)., Caminho do config.json em uso (a cópia editável ao lado do executável,     quand

### Community 21 - "Constrained Query Expansion"
Cohesion: 0.33
Nodes (6): BFS Traversal Mode, DFS Traversal Mode, graphify reflect / LESSONS.md, save-result Work Memory (useful/dead_end/corrected), Constrained Query Expansion, graphify query

## Ambiguous Edges - Review These
- `Pendência: PWA (manifest.json + service worker)` → `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS]
  CLAUDE.md · relation: semantically_similar_to

## Knowledge Gaps
- **40 isolated node(s):** `iniciar.sh script`, `Instalação Windows com Python`, `Executável único (.exe) via build_windows.bat`, `Instalação Linux/macOS via iniciar.sh`, `Passo a passo na tela (máscaras, UCs, kit gerador)` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pendência: PWA (manifest.json + service worker)` and `PWA Service Worker Registration (sw.js)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `graphify (knowledge graph tool)` connect `Documentação do Skill Graphify` to `Constrained Query Expansion`?**
  _High betweenness centrality (0.228) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `teste_planilha.py` to `Motor de Cálculo & Validação (engine.py)`, `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Why does `Dimensionador S2V (project)` connect `teste_planilha.py` to `Motor de Cálculo & Validação (engine.py)`, `Servidor Flask & API (app.py)`, `Geração de PDF da Proposta`, `Configuração & Documentação Geral`, `Integração com Internet (online.py)`?**
  _High betweenness centrality (0.217) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Instalação Windows com Python`, `Executável único (.exe) via build_windows.bat` to the rest of the system?**
  _40 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.12310606060606061 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.06031746031746032 - nodes in this community are weakly interconnected._