# Graph Report - dimensionador-s2v-main  (2026-07-26)

## Corpus Check
- 24 files · ~38,221 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 347 nodes · 543 edges · 31 communities (16 shown, 15 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `691b007a`
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
- api_proposta
- _pasta_base
- _ip_local
- _montar_entradas
- _f
- api_config
- api_atualizar_tarifa
- api_concessionarias
- icones
- service_worker
- Uso no celular via QR code / LAN

## God Nodes (most connected - your core abstractions)
1. `calcular()` - 20 edges
2. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
3. `graphify (knowledge graph tool)` - 20 edges
4. `UC` - 16 edges
5. `Entradas` - 16 edges
6. `carregar_config()` - 14 edges
7. `_textos()` - 13 edges
8. `gerar_proposta()` - 13 edges
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

## Communities (31 total, 15 thin omitted)

### Community 0 - "Motor de Cálculo & Validação (engine.py)"
Cohesion: 0.07
Nodes (49): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, relatorio_conferencia(), dict (+41 more)

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.05
Nodes (42): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+34 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.18
Nodes (8): api_copel_verificar(), _exige_login(), index(), login(), manifest(), Descreve o app para o celular (nome, ícones, cor) — vira ícone na tela., Raspagem leve do site da COPEL: resolução/vigência atual + ICMS., _senha_acesso()

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.08
Nodes (38): Cartões da pág. 3 se reagrupam (string box/bateria), _ajustar_em_caixa(), _carregar_cards(), _carregar_deco(), _carregar_layout(), _desenhar_campo_cartao(), _desenhar_cards_p3(), _desenhar_fotos_p3() (+30 more)

### Community 4 - "Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)"
Cohesion: 0.08
Nodes (24): Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Usar no celular via QR code / mesma rede Wi-Fi, Conferência do retorno financeiro, Parâmetros editáveis em config.json, Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME), Estrutura de pastas do projeto (+16 more)

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.09
Nodes (16): Tarifas da concessionária — tabela local sem depender de internet, addUC(), agendar(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT(), calc() (+8 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.13
Nodes (20): ANEEL removida de propósito / tarifas em tabela local, Raspagem HTML do site da COPEL (sem Power BI), NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), geocodificar(), _get_html() (+12 more)

### Community 7 - "UC"
Cohesion: 0.21
Nodes (3): Uma unidade consumidora — linha 6..14 de PR + linha 31..39., % noturno aplicado no faturamento com solar.          Na planilha (coluna M):, UC

### Community 8 - "agendar"
Cohesion: 0.11
Nodes (36): _attr(), _campo_de(), converter(), _cor(), desenhar_svg(), _estilo(), _extrair_fontes_do_html(), _fonte() (+28 more)

### Community 19 - "teste_planilha.py"
Cohesion: 0.15
Nodes (12): Ainda calculado e não impresso, Como a proposta é montada, Garantias, Mapa dos dados da proposta, Números do sistema, Os 6 cartões do kit, Página 1 — capa, Página 2 — "Como a energia flui" (+4 more)

### Community 20 - "api_proposta"
Cohesion: 0.24
Nodes (10): api_proposta(), _img_bytes(), _limpar_nome(), _nome_projeto(), _pasta_projeto(), Deixa um texto seguro para virar nome de pasta no Windows., Rótulo da pasta do projeto, ex.: '7,44KWP ONGRID CHINT 5K 220V COLONIAL'., <base>/<consultor>/<NOME>/<7,44KWP ONGRID …>/ — cria e devolve o caminho.     O (+2 more)

### Community 21 - "_pasta_base"
Cohesion: 0.29
Nodes (7): api_importar_resumo(), api_resumos_salvos(), _clientes_dir(), _pasta_base(), Pasta raiz onde os projetos são salvos. Por padrão a 'clientes/' local;     se ', Lista os projetos que podem ser reabertos — qualquer pasta que tenha um     DADO, Devolve o payload de um projeto salvo, para repovoar a tela.

### Community 22 - "_ip_local"
Cohesion: 0.33
Nodes (6): api_rede(), _ip_local(), qr_png(), IP desta máquina na rede local (para acesso pelo celular)., URL para acessar o programa pelo celular (mesma rede Wi-Fi)., QR code da URL de rede (requer o pacote opcional 'qrcode').

### Community 23 - "_montar_entradas"
Cohesion: 0.40
Nodes (5): api_calcular(), api_conferencia(), _montar_entradas(), Devolve o detalhamento passo a passo do retorno financeiro., _resumo()

### Community 24 - "_f"
Cohesion: 0.40
Nodes (5): api_irradiacao(), api_salvar_config(), _f(), Converte número vindo da tela (aceita vírgula) — vazio vira `padrao`., Grava as pré-definições editadas, preservando o resto do config.json     (coment

### Community 25 - "api_config"
Cohesion: 0.50
Nodes (4): api_config(), _impostos_copel(), Alíquotas atuais da COPEL (% já convertido) para o editor., Devolve só os parâmetros de negócio que a tela pode editar.

## Ambiguous Edges - Review These
- `Pendência: PWA (manifest.json + service worker)` → `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS]
  CLAUDE.md · relation: semantically_similar_to

## Knowledge Gaps
- **50 isolated node(s):** `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa`, `Página 2 — "Como a energia flui"`, `Os 6 cartões do kit` (+45 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pendência: PWA (manifest.json + service worker)` and `PWA Service Worker Registration (sw.js)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `Dimensionador S2V (project)` connect `Motor de Cálculo & Validação (engine.py)` to `Servidor Flask & API (app.py)`, `Geração de PDF da Proposta`, `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)`, `Integração com Internet (online.py)`, `Uso no celular via QR code / LAN`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `Motor de Cálculo & Validação (engine.py)` to `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa` to the rest of the system?**
  _50 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.07138535995160314 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.05110336817653891 - nodes in this community are weakly interconnected._
- **Should `Geração de PDF da Proposta` be split into smaller, more focused modules?**
  _Cohesion score 0.08367071524966262 - nodes in this community are weakly interconnected._