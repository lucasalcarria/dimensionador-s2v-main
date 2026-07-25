# Graph Report - dimensionador-s2v-main  (2026-07-25)

## Corpus Check
- 24 files · ~37,272 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 338 nodes · 525 edges · 20 communities (10 shown, 10 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `60c1c629`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Motor de Cálculo & Validação (engine.py)
- Documentação do Skill Graphify
- Servidor Flask & API (app.py)
- Geração de PDF da Proposta
- Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)
- Interface do Usuário (JS da index.html)
- Integração com Internet (online.py)
- UC
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

## God Nodes (most connected - your core abstractions)
1. `calcular()` - 20 edges
2. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
3. `graphify (knowledge graph tool)` - 20 edges
4. `UC` - 16 edges
5. `Entradas` - 15 edges
6. `gerar_proposta()` - 13 edges
7. `carregar_config()` - 12 edges
8. `_textos()` - 12 edges
9. `desenhar_svg()` - 11 edges
10. `converter()` - 11 edges

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
Cohesion: 0.08
Nodes (45): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, relatorio_conferencia(), dict (+37 more)

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.05
Nodes (42): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+34 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.05
Nodes (53): api_atualizar_tarifa(), api_calcular(), api_concessionarias(), api_conferencia(), api_config(), api_copel_verificar(), api_importar_resumo(), api_irradiacao() (+45 more)

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.08
Nodes (40): Cartões da pág. 3 se reagrupam (string box/bateria), Fidelidade do PDF (comparação pixel a pixel com o Excel), Melhorias gráficas da proposta impressa, _ajustar_em_caixa(), _carregar_cards(), _carregar_deco(), _carregar_layout(), _desenhar_campo_cartao() (+32 more)

### Community 4 - "Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)"
Cohesion: 0.08
Nodes (23): ANEEL removida de propósito / tarifas em tabela local, Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Usar no celular via QR code / mesma rede Wi-Fi, Parâmetros editáveis em config.json, Raspagem HTML do site da COPEL (sem Power BI), Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME) (+15 more)

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.09
Nodes (16): Tarifas da concessionária — tabela local sem depender de internet, addUC(), agendar(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT(), calc() (+8 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.15
Nodes (18): NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), geocodificar(), _get_html(), _get_json(), _get_json_curl() (+10 more)

### Community 7 - "UC"
Cohesion: 0.21
Nodes (3): Uma unidade consumidora — linha 6..14 de PR + linha 31..39., % noturno aplicado no faturamento com solar.          Na planilha (coluna M):, UC

### Community 8 - "agendar"
Cohesion: 0.11
Nodes (36): _attr(), _campo_de(), converter(), _cor(), desenhar_svg(), _estilo(), _extrair_fontes_do_html(), _fonte() (+28 more)

### Community 19 - "teste_planilha.py"
Cohesion: 0.15
Nodes (12): Ainda calculado e não impresso, Como a proposta é montada, Garantias, Mapa dos dados da proposta, Números do sistema, Os 6 cartões do kit, Página 1 — capa, Página 2 — "Como a energia flui" (+4 more)

## Ambiguous Edges - Review These
- `Pendência: PWA (manifest.json + service worker)` → `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS]
  CLAUDE.md · relation: semantically_similar_to

## Knowledge Gaps
- **50 isolated node(s):** `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa`, `Página 2 — "Como a energia flui"`, `Os 6 cartões do kit` (+45 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pendência: PWA (manifest.json + service worker)` and `PWA Service Worker Registration (sw.js)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `Dimensionador S2V (project)` connect `Motor de Cálculo & Validação (engine.py)` to `Servidor Flask & API (app.py)`, `Geração de PDF da Proposta`, `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)`, `Integração com Internet (online.py)`?**
  _High betweenness centrality (0.150) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `Motor de Cálculo & Validação (engine.py)` to `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa` to the rest of the system?**
  _50 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.05110336817653891 - nodes in this community are weakly interconnected._
- **Should `Servidor Flask & API (app.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.05263157894736842 - nodes in this community are weakly interconnected._