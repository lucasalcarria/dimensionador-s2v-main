# Graph Report - dimensionador-s2v-main  (2026-08-20)

## Corpus Check
- 26 files · ~51,224 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 474 nodes · 817 edges · 41 communities (30 shown, 11 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `68eb7995`
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
- _senha_acesso
- _eh_consultor
- _ler_img_padrao
- _gravar_img_pacote
- Entradas
- engine.py
- calcular
- _ip_local
- _textos
- proposta.py
- dir_execucao
- _carregar_deco
- Estrutura de pastas do projeto
- teste_correcoes.py
- _ajustar_em_caixa
- _pdf_grafico

## God Nodes (most connected - your core abstractions)
1. `carregar_config()` - 21 edges
2. `UC` - 20 edges
3. `calcular()` - 20 edges
4. `Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)` - 20 edges
5. `graphify (knowledge graph tool)` - 20 edges
6. `Entradas` - 18 edges
7. `api_proposta()` - 15 edges
8. `gerar_proposta()` - 14 edges
9. `_textos()` - 13 edges
10. `_montar_entradas()` - 11 edges

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

## Communities (41 total, 11 thin omitted)

### Community 0 - "Motor de Cálculo & Validação (engine.py)"
Cohesion: 0.15
Nodes (8): _faturas_uc(), % noturno aplicado no faturamento com solar.          Na planilha (coluna M):, Fator de ICMS na TE: (1-ICMS) onde incide, 1,0 onde não (icms_te)., Fator de ICMS na TUSD: (1-ICMS) onde incide, 1,0 onde não., Fatura SEM e COM sistema para um nível de geração média e um ano (→ Fio B     e, Uma unidade consumidora — linha 6..14 de PR + linha 31..39., _trunc(), UC

### Community 1 - "Documentação do Skill Graphify"
Cohesion: 0.05
Nodes (42): /graphify command trigger (.claude/CLAUDE.md), /graphify add <url>, --watch folder monitor, Wiki Export (agent-crawlable), Confidence Score Rubric (discrete values), Node ID Format Rule ({stem}_{entity}), Extraction Subagent Prompt, graphify clone (+34 more)

### Community 2 - "Servidor Flask & API (app.py)"
Cohesion: 0.09
Nodes (17): api_concessionarias(), api_copel_verificar(), api_drive_desconectar(), favicon(), icones(), manifest(), Raspagem leve do site da COPEL: resolução/vigência atual + ICMS., Lê uma regra booleana vinda do front/JSON (True/'false'/0/…). (+9 more)

### Community 3 - "Geração de PDF da Proposta"
Cohesion: 0.17
Nodes (15): _carregar_cards(), _carregar_layout(), _desenhar_campo_cartao(), _desenhar_cards_p3(), _font_key(), gerar_proposta(), Encolhe a fonte até caber em max_w; se não couber, corta com reticências.     R, Desenha qtd/desc de um cartão dado o topo-esq (x0, top) do tile. (+7 more)

### Community 4 - "Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME)"
Cohesion: 0.29
Nodes (7): api_importar_resumo(), api_resumos_salvos(), _clientes_dir(), _pasta_base(), Lista os projetos que podem ser reabertos — qualquer pasta que tenha um     DAD, Devolve o payload de um projeto salvo, para repovoar a tela., Pasta raiz onde os projetos são salvos. Por padrão a 'clientes/' local;     se

### Community 5 - "Interface do Usuário (JS da index.html)"
Cohesion: 0.07
Nodes (19): Salvar resumo na pasta do cliente, Tarifas da concessionária — tabela local sem depender de internet, addUC(), agendar(), aplicarConc(), aplicarMascaras(), blurKWH(), blurPCT() (+11 more)

### Community 6 - "Integração com Internet (online.py)"
Cohesion: 0.12
Nodes (16): Usar no celular via QR code / mesma rede Wi-Fi, Conferência do retorno financeiro, Dimensionador S2V — proposta solar fotovoltaica (LEIA-ME), Executável único (.exe) via build_windows.bat, Fidelidade do PDF (comparação pixel a pixel com o Excel), Fio B automático por ano (correção), O que ficou de fora (CÁLCULO DEMANDA, OFFGRID, SICREDI), Formato brasileiro e data automática (correção) (+8 more)

### Community 7 - "UC"
Cohesion: 0.09
Nodes (44): api_drive_consultores(), api_drive_status(), oauth2_callback(), oauth2_start(), Abre a autorização do Google (deve ser feita LOCALMENTE, no PC)., Recebe o código do Google e guarda o token., Pastas de consultor já existentes na pasta base do Drive (p/ o menu)., _redirect_uri() (+36 more)

### Community 8 - "agendar"
Cohesion: 0.11
Nodes (36): _attr(), _campo_de(), converter(), _cor(), desenhar_svg(), _estilo(), _extrair_fontes_do_html(), _fonte() (+28 more)

### Community 19 - "teste_planilha.py"
Cohesion: 0.17
Nodes (11): Como a proposta é montada, Garantias, Mapa dos dados da proposta, Números do sistema, Os 6 cartões do kit, Página 1 — capa, Página 2 — "Como a energia flui", Página 3 — dimensionamento (+3 more)

### Community 20 - "api_proposta"
Cohesion: 0.27
Nodes (10): api_proposta(), _img_bytes(), _limpar_nome(), _nome_projeto(), _pasta_projeto(), Ação única: calcula, salva o projeto inteiro (resumo, conferência, dados     e, Deixa um texto seguro para virar nome de pasta no Windows., Rótulo da pasta do projeto, ex.: '7,44KWP ONGRID CHINT 5K 220V COLONIAL'. (+2 more)

### Community 21 - "_pasta_base"
Cohesion: 0.18
Nodes (14): _achar_pacote(), api_config(), api_pacotes(), _impostos_copel(), index(), _pacote_id(), _pacote_publico(), _pacotes() (+6 more)

### Community 22 - "_ip_local"
Cohesion: 0.32
Nodes (8): api_calcular(), api_conferencia(), api_pacote_preco(), _montar_entradas(), Prévia (SÓ admin) do preço e da margem de UM pacote enquanto o kit é     editad, Devolve o detalhamento passo a passo do retorno financeiro., _resumo(), carregar_config()

### Community 23 - "_montar_entradas"
Cohesion: 0.11
Nodes (24): ANEEL removida de propósito / tarifas em tabela local, Raspagem HTML do site da COPEL (sem Power BI), NASA POWER irradiance API, ViaCEP API, buscar_cep(), buscar_irradiacao(), buscar_tarifa_aneel(), geocodificar() (+16 more)

### Community 24 - "_f"
Cohesion: 0.20
Nodes (12): _acesso_path(), api_irradiacao(), api_salvar_config(), api_sugestao(), _f(), _ler_acesso(), _obter_secret(), Converte número vindo da tela (aceita vírgula) — vazio vira `padrao`. (+4 more)

### Community 25 - "_senha_acesso"
Cohesion: 0.18
Nodes (11): _achar_consultor(), _consultores(), _exige_login(), login(), _papel(), admin' ou 'consultor'. Sem senha de admin (local), tudo é admin., Rotas que só o ADMIN pode acessar (o consultor recebe 403/redirect)., Lista [{nome, senha}] cadastrada pelo admin (acesso.json). (+3 more)

### Community 26 - "_eh_consultor"
Cohesion: 0.23
Nodes (12): api_atender_solic(), api_criar_solic(), api_listar_solic(), _aplicar_pacote(), _caminho_solic(), _eh_consultor(), _ler_solic(), O consultor (ou admin) registra um pedido de cotação de kit. (+4 more)

### Community 27 - "_ler_img_padrao"
Cohesion: 0.22
Nodes (9): api_imagens_padrao(), api_salvar_imagens_padrao(), _caminho_img_padrao(), _gravar_img_padrao(), _ler_img_padrao(), Data URLs das imagens PADRÃO de módulo/inversor (para preencher o editor)., Salva/apaga as imagens padrão. Body: {modulo: dataURL|null, inversor: …}.     U, Data URL salvo da imagem padrão do módulo/inversor, ou None. (+1 more)

### Community 28 - "_gravar_img_pacote"
Cohesion: 0.33
Nodes (7): _caminho_pac_imgs(), _gravar_img_pacote(), _ler_img_pacote(), _ler_pac_imgs(), Data URL da imagem do pacote (qual='modulo'|'inversor'), ou None., Grava/apaga a imagem de um pacote no arquivo único., _salvar_pac_imgs()

### Community 29 - "Entradas"
Cohesion: 0.19
Nodes (10): _exemplo_enunciado(), Reproduz o caso descrito: A=600 (geradora), B=400 (beneficiária),     geração ~1, Entradas, _marca_micro(), Lista normalizada de inversores. Vazia => usa os campos legados         (marca/, Detecta micro-inversor pela marca (garantia padrão de 12 anos)., Autotrafo de UM inversor (DD!R25:S34): só p/ ≥12 kW em 380 V., Soma o autotrafo de cada inversor (um sistema pode ter vários). (+2 more)

### Community 30 - "engine.py"
Cohesion: 0.26
Nodes (10): Dimensionador S2V (project), Regra número 1: engine.py réplica validada da planilha, Caso de validação NEUZA ZAMFERRARI (UC 16285387), % noturno: GERADORA usa valor informado, BENEFICIÁRIA sempre 100%, Teste automatizado contra a planilha, caso_planilha(), identidade(), ok() (+2 more)

### Community 31 - "calcular"
Cohesion: 0.23
Nodes (11): relatorio_conferencia(), calcular(), fator_fio_b(), fmt_num(), _material_extra(), moeda(), DD!J47:K52 — escalonamento da Lei 14.300. Na planilha o ano estava     fixado e, DD!G26:G35 — material por faixa de potência (custo base × 1,6). (+3 more)

### Community 32 - "_ip_local"
Cohesion: 0.33
Nodes (6): api_rede(), _ip_local(), qr_png(), IP desta máquina na rede local (para acesso pelo celular)., URL para acessar o programa pelo celular (mesma rede Wi-Fi)., QR code da URL de rede (requer o pacote opcional 'qrcode').

### Community 33 - "_textos"
Cohesion: 0.17
Nodes (12): dict, _dec(), _excel_round(), fmt_general(), ROUND do Excel (half away from zero)., ROUNDUP do Excel (afasta de zero), seguro contra ruído de float., dict com acesso por atributo, para deixar o app legível., Formato 'Geral' do Excel: sem zeros à direita. (+4 more)

### Community 34 - "proposta.py"
Cohesion: 0.21
Nodes (11): Cartões da pág. 3 se reagrupam (string box/bateria), _ajustar_cartao_p5(), _cm_antes(), Retorna o operando-lista do `cm` imediatamente anterior ao índice idx., Pág. 5, editando o fluxo do fundo (página já anexada ao writer):       1. APAGA, Dependências Python do projeto (requirements.txt), flask>=3.0, matplotlib>=3.8 (+3 more)

### Community 35 - "dir_execucao"
Cohesion: 0.22
Nodes (11): api_aneel_tarifa(), api_atualizar_tarifa(), _caminho_tarifa_cache(), _ler_cache_tarifas(), TE/TUSD vigentes (SEM impostos) de uma concessionária, da ANEEL Dados     Abert, Grava TE/TUSD de uma concessionária+subgrupo na tabela local.      Aceita valo, _salvar_cache_tarifa(), caminho_config() (+3 more)

### Community 36 - "_carregar_deco"
Cohesion: 0.25
Nodes (8): _carregar_deco(), _desenhar_fotos_p3(), _estender_cover(), Estende a foto das placas (capa) até a borda direita, eliminando a     faixa br, Cobre as fotos genéricas (módulo/inversor) chapadas no fundo da pág. 3 e     de, Geometria dos elementos decorativos redesenhados em vetor., Cobre os 7 círculos deformados da 'ETAPAS DO PROJETO' (pág. 4) e os     redesen, _redesenhar_timeline()

### Community 37 - "Estrutura de pastas do projeto"
Cohesion: 0.40
Nodes (5): Dados do usuário: nunca versionar/sobrescrever, Retorno de 25 anos (compat_planilha, bug do COUNTA corrigido), config.json (parâmetros de negócio), Parâmetros editáveis em config.json, Estrutura de pastas do projeto

### Community 39 - "_ajustar_em_caixa"
Cohesion: 0.50
Nodes (4): _ajustar_em_caixa(), _quebrar(), Quebra o texto em linhas que cabem em `max_w`, cortando nos espaços., Encaixa o texto na área reservada do layout.      Primeiro tenta o tamanho nor

### Community 40 - "_pdf_grafico"
Cohesion: 0.50
Nodes (4): _pdf_grafico(), Passo 'redondo' semelhante ao automático do Excel (~6 divisões)., Gera o gráfico da página 4 como PDF vetorial transparente.      `consumo_mensa, _unidade_eixo()

## Ambiguous Edges - Review These
- `Pendência: PWA (manifest.json + service worker)` → `PWA Service Worker Registration (sw.js)`  [AMBIGUOUS]
  CLAUDE.md · relation: semantically_similar_to

## Knowledge Gaps
- **49 isolated node(s):** `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa`, `Página 2 — "Como a energia flui"`, `Os 6 cartões do kit` (+44 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Pendência: PWA (manifest.json + service worker)` and `PWA Service Worker Registration (sw.js)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `Dimensionador S2V (project)` connect `engine.py` to `Servidor Flask & API (app.py)`, `proposta.py`, `Estrutura de pastas do projeto`, `_montar_entradas`, `calcular`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `Regra número 1: engine.py réplica validada da planilha` connect `engine.py` to `Documentação do Skill Graphify`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **What connects `iniciar.sh script`, `Como a proposta é montada`, `Página 1 — capa` to the rest of the system?**
  _49 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Motor de Cálculo & Validação (engine.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.14619883040935672 - nodes in this community are weakly interconnected._
- **Should `Documentação do Skill Graphify` be split into smaller, more focused modules?**
  _Cohesion score 0.05110336817653891 - nodes in this community are weakly interconnected._
- **Should `Servidor Flask & API (app.py)` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._