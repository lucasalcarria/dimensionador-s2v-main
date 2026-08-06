# Graph Report - dimensionador-s2v-main  (2026-08-05)

## Corpus Check
- 26 files · ~48,077 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 469 nodes · 805 edges · 29 communities (19 shown, 10 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ffcac6b8`
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
- _eh_consultor
- _ler_img_padrao
- _ip_local

## God Nodes (most connected - your core abstractions)
1. `carregar_config()` - 20 edges
2. `UC` - 20 edges
3. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
4. `graphify (knowledge graph tool)` - 20 edges
5. `calcular()` - 19 edges
6. `Entradas` - 18 edges
7. `api_proposta()` - 15 edges
8. `_textos()` - 13 edges
9. `gerar_proposta()` - 13 edges
10. `desenhar_svg()` - 11 edges

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

## Communities (29 total, 10 thin omitted)

### Community 0 - "Motor de Cálculo & Validação (engine.py)"
Cohesion: 0.05
Nodes (56): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, relatorio_conferencia(), dict (+48 more)

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.05
Nodes (42): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+34 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.11
Nodes (20): api_aneel_tarifa(), api_calcular(), api_conferencia(), _caminho_tarifa_cache(), favicon(), icones(), _ler_cache_tarifas(), manifest() (+12 more)

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.08
Nodes (38): Cartões da pág. 3 se reagrupam (string box/bateria), _ajustar_em_caixa(), _carregar_cards(), _carregar_deco(), _carregar_layout(), _desenhar_campo_cartao(), _desenhar_cards_p3(), _desenhar_fotos_p3() (+30 more)

### Community 4 - "Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)"
Cohesion: 0.29
Nodes (7): api_importar_resumo(), api_resumos_salvos(), _clientes_dir(), _pasta_base(), Lista os projetos que podem ser reabertos — qualquer pasta que tenha um     DAD, Devolve o payload de um projeto salvo, para repovoar a tela., Pasta raiz onde os projetos são salvos. Por padrão a 'clientes/' local;     se

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.09
Nodes (16): Tarifas da concessionária — tabela local sem depender de internet, addUC(), agendar(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT(), calc() (+8 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.07
Nodes (25): ANEEL removida de propósito / tarifas em tabela local, Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Usar no celular via QR code / mesma rede Wi-Fi, Parâmetros editáveis em config.json, Raspagem HTML do site da COPEL (sem Power BI), Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME) (+17 more)

### Community 7 - "UC"
Cohesion: 0.09
Nodes (45): api_drive_consultores(), api_drive_desconectar(), api_drive_status(), oauth2_callback(), oauth2_start(), Abre a autorização do Google (deve ser feita LOCALMENTE, no PC)., Recebe o código do Google e guarda o token., Pastas de consultor já existentes na pasta base do Drive (p/ o menu). (+37 more)

### Community 8 - "agendar"
Cohesion: 0.11
Nodes (36): _attr(), _campo_de(), converter(), _cor(), desenhar_svg(), _estilo(), _extrair_fontes_do_html(), _fonte() (+28 more)

### Community 19 - "teste_planilha.py"
Cohesion: 0.15
Nodes (12): Ainda calculado e não impresso, Como a proposta é montada, Garantias, Mapa dos dados da proposta, Números do sistema, Os 6 cartões do kit, Página 1 — capa, Página 2 — "Como a energia flui" (+4 more)

### Community 20 - "api_proposta"
Cohesion: 0.27
Nodes (10): api_proposta(), _img_bytes(), _limpar_nome(), _nome_projeto(), _pasta_projeto(), Ação única: calcula, salva o projeto inteiro (resumo, conferência, dados     e, Deixa um texto seguro para virar nome de pasta no Windows., Rótulo da pasta do projeto, ex.: '7,44KWP ONGRID CHINT 5K 220V COLONIAL'. (+2 more)

### Community 21 - "_pasta_base"
Cohesion: 0.20
Nodes (12): _achar_pacote(), api_pacotes(), _aplicar_pacote(), index(), _pacote_id(), _pacote_publico(), _pacotes(), Lista pública de pacotes (sem custos) — para o seletor do consultor. (+4 more)

### Community 22 - "_ip_local"
Cohesion: 0.22
Nodes (10): api_concessionarias(), api_copel_verificar(), api_irradiacao(), api_sugestao(), _f(), Raspagem leve do site da COPEL: resolução/vigência atual + ICMS., Converte número vindo da tela (aceita vírgula) — vazio vira `padrao`., Potência FV necessária p/ abater 100% do consumo (DD!B21). NÃO precisa de     p (+2 more)

### Community 23 - "_montar_entradas"
Cohesion: 0.13
Nodes (22): NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), buscar_tarifa_aneel(), geocodificar(), _get_html(), _get_json() (+14 more)

### Community 24 - "_f"
Cohesion: 0.14
Nodes (18): _acesso_path(), api_atualizar_tarifa(), api_salvar_config(), _caminho_pac_imgs(), _gravar_img_pacote(), _ler_acesso(), _ler_pac_imgs(), _obter_secret() (+10 more)

### Community 25 - "api_config"
Cohesion: 0.12
Nodes (17): _achar_consultor(), api_config(), _consultores(), _exige_login(), _impostos_copel(), _ler_img_pacote(), login(), _papel() (+9 more)

### Community 26 - "_eh_consultor"
Cohesion: 0.29
Nodes (10): api_atender_solic(), api_criar_solic(), api_listar_solic(), _caminho_solic(), _eh_consultor(), _ler_solic(), O consultor (ou admin) registra um pedido de cotação de kit., Admin vê todas; consultor vê só as suas. Devolve o total de pendentes. (+2 more)

### Community 27 - "_ler_img_padrao"
Cohesion: 0.22
Nodes (9): api_imagens_padrao(), api_salvar_imagens_padrao(), _caminho_img_padrao(), _gravar_img_padrao(), _ler_img_padrao(), Data URLs das imagens PADRÃO de módulo/inversor (para preencher o editor)., Salva/apaga as imagens padrão. Body: {modulo: dataURL|null, inversor: …}.     U, Data URL salvo da imagem padrão do módulo/inversor, ou None. (+1 more)

### Community 32 - "_ip_local"
Cohesion: 0.33
Nodes (6): api_rede(), _ip_local(), qr_png(), IP desta máquina na rede local (para acesso pelo celular)., URL para acessar o programa pelo celular (mesma rede Wi-Fi)., QR code da URL de rede (requer o pacote opcional 'qrcode').

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
- **Why does `Dimensionador S2V (project)` connect `Motor de Cálculo & Validação (engine.py)` to `Servidor Flask & API (app.py)`, `Geração de PDF da Proposta`, `Integração com Internet (online.py)`, `_montar_entradas`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `Motor de Cálculo & Validação (engine.py)` to `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa` to the rest of the system?**
  _50 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.05030834144758196 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.05110336817653891 - nodes in this community are weakly interconnected._
- **Should `Servidor Flask & API (app.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.11333333333333333 - nodes in this community are weakly interconnected._