# Dimensionador S2V — proposta solar fotovoltaica

Programa **offline** que substitui a planilha `PLANILHA S2V ENGENHARIA - 1 OPÇÃO NOVA.xlsm`:
mesmas entradas, mesmos cálculos e a **mesma proposta de 5 páginas em PDF**, gerada em
menos de 1 segundo — sem Excel, sem macro e sem deformar o layout.

---

## 1. Como usar

### Opção A — Windows com Python (mais simples)
1. Instale o **Python 3.10 ou superior** uma única vez: https://www.python.org/downloads/
   (na instalação, marque **"Add Python to PATH"**).
2. Dê dois cliques em **`instalar.bat`** (só na primeira vez — baixa as bibliotecas).
3. Dê dois cliques em **`iniciar.bat`**.
   O navegador abre sozinho em `http://127.0.0.1:8177` com a tela do programa.
   Deixe a janela preta aberta enquanto usa; feche-a para encerrar.

### Opção B — Executável único (.exe), sem Python nos outros PCs
1. Em **um** computador com Python, dê dois cliques em **`build_windows.bat`**.
2. Ele cria `dist\DimensionadorS2V.exe`. Copie esse arquivo (junto com o
   `config.json`, se quiser editar parâmetros) para qualquer Windows e use
   com dois cliques — nada mais precisa ser instalado.

### Opção C — Linux / macOS
```bash
./iniciar.sh
```

> As propostas geradas ficam salvas na pasta **`propostas/`**, criada ao lado do
> programa, além de baixarem pelo navegador.

---

## 2. Passo a passo na tela

Os campos já vêm com **máscaras no padrão brasileiro**: valores em reais aparecem
como `R$ 1.234,56`, percentuais como `12,50`, capacidade da bateria como `10,24 kWh`
e o CEP como `00.000-000`. Basta digitar os números — a formatação é automática.

1. **Cliente** — nome, endereço, cidade e nº da UC (só números). O botão *buscar*
   preenche endereço/cidade pelo **CEP** (internet, opcional).
2. **Unidades consumidoras** — até 9 UCs, como na planilha. Para cada UC:
   tipo (geradora/beneficiária), ligação (mono/bi/trifásico), iluminação pública (R$)
   e consumo. Pode digitar só o **consumo médio** (vale para os 12 meses) ou abrir
   *"consumo mês a mês"*. Tarifas TE/TUSD são digitadas **sem impostos** (como na
   fatura da concessionária) e as alíquotas ICMS/PIS/COFINS em **porcentagem**;
   a **tarifa cheia com impostos** aparece logo abaixo, para conferência.
   Bandeira tarifária no mesmo bloco, tudo já pré-preenchido.
3. **Irradiação** — escolha o perfil da planilha (`23° NORTE`, `3.3`, `3.8`, `4`, `4.2`)
   **ou** clique em *buscar* para puxar pela internet a irradiação média da cidade
   (NASA POWER — climatologia de 20 anos, sem chave de API).
4. **Kit gerador** — módulo (marca/potência/quantidade), inversor
   (marca/kW/tensão/conexão), estrutura e **valor do kit**. As marcas, a conexão e
   a estrutura são **listas suspensas** com todas as opções; se a que você precisa
   não estiver na lista, escolha **"Outro (digitar)…"** e digite livremente. O programa
   mostra ao lado a quantidade de módulos **sugerida** para 100 % de compensação.
   Logo abaixo ficam os **componentes opcionais da página 3 da proposta**:
   *String box CC* e *Bateria de lítio*. Desmarque para que o cartão **suma** da
   proposta; marcando, dá para informar quantidade, marca, entradas/saídas
   (ex.: 2E/2S para string box) e capacidade da bateria em kWh.
   Quando um componente não é incluído, os cartões restantes se **reorganizam
   automaticamente** para não deixar buracos, e a **garantia da bateria** só aparece
   na proposta quando há bateria no orçamento.
5. **Custos & margem** — **mão de obra, material extra e alíquota de imposto são
   editáveis** (deixe em branco para usar a regra automática da planilha; o valor
   automático aparece ao lado). Também: entrada, deslocamento, comissão, seguro,
   margem desejada (vazio = automática por faixa de porte) e financiamento.
6. Os **resultados aparecem em tempo real** no painel à direita (valor de venda,
   faturas com/sem, economia, payback, retorno em 25 anos, composição do preço).
7. Clique em **Gerar proposta (PDF)** — o arquivo `NOME DO CLIENTE.pdf` é baixado
   e salvo em `propostas/`.

---

## 3. Parâmetros editáveis — `config.json`

Abra o `config.json` em qualquer editor de texto (Bloco de Notas serve). Cada chave
tem um comentário `_explicando` a origem na planilha. Principais:

| Chave | O que controla | Origem |
|---|---|---|
| `perfis_irradiacao` | Os 5 perfis mensais de irradiação | `DADOS!B3:N7` |
| `performance_ratio` | Fator de desempenho da geração (0,75) | `DADOS!D22` |
| `faixas_margem` | Margem automática por porte do sistema | `DADOS!B78` |
| `material_extra_faixas` + `material_markup` | Material por faixa de kWp (×1,6) | `DADOS!G26:G35` |
| `trafos` | Tabela de autotransformadores (≥12 kW em 380 V) | `DADOS!R25:T47` |
| `mao_de_obra_minima` / `por_modulo` | R$ 850 até 9 módulos; R$ 85/módulo a partir de 10 | `PR!Q21` |
| `aliquota_imposto` | 8 % sobre (venda − kit) | `DADOS!D26` |
| `fio_b_rs_mwh` + `fio_b_escalonamento` | Fio B (Lei 14.300) e % por ano | `DADOS!J47:J59` |
| `bandeiras` | Adicional por bandeira tarifária | `DADOS!J54:J57` |
| `reajuste_tarifa_aa`, `degradacao_*` | Projeção de 25 anos | `DADOS!O43:Q67` |
| `garantias_fixas` | `null` = regras da planilha por marca; ou fixe um número | `DADOS!O30:O32` |
| `tarifas_padrao`, `financiamento_padrao` | Valores pré-preenchidos na tela | `PR!D31:M31`, `DADOS!M35:M36` |
| `formato_ptbr` | `true` = R$ 8.758,12 · `false` = R$ 8,758.12 (como a planilha salvava) | — |
| `compat_planilha` | `true` reproduz o "retorno 25 anos" da planilha (ver §5) | — |

O arquivo é lido a cada cálculo — basta salvar e recalcular, sem reiniciar.

---

## 4. Recursos de internet (opcionais)

O programa funciona 100 % offline. Se houver conexão, você pode:
* **Buscar irradiação por cidade** — NASA POWER (média 2001-2020, Wh/m²/dia),
  aplicada como perfil customizado;
* **Buscar CEP** — ViaCEP preenche endereço e cidade.

---

## 5. Diferenças e correções em relação à planilha

Tudo foi reproduzido **fórmula por fórmula** (validado com o caso salvo na planilha,
com igualdade até os centavos). Quatro pontos foram *melhorados* — todos com opção
de voltar ao comportamento antigo:

1. **Preço/Wp sempre convergido.** Na planilha, a macro colava o valor do Wp em
   `DADOS!B75` e ele **ficava desatualizado** quando entradas mudavam sem rodar a
   macro (no arquivo enviado: colado 2,3543 vs 2,3248 recalculado). O programa
   itera até convergir a cada cálculo. Se precisar reproduzir um PDF antigo,
   use o campo *"Preço/Wp manual"*.
2. **"Economia em 25 anos" com modelo realista.** A fórmula da planilha dividia a
   tarifa média por **9** (todas as linhas de UC, mesmo vazias — `COUNTA` em
   `DADOS!P42`), subestimando o valor ~9× quando só 1 UC era usada. O programa
   agora parte da **economia mensal efetiva** (fatura sem − fatura com, que já
   considera Fio B, custo de disponibilidade, bandeira e iluminação pública),
   reajusta a tarifa em 5 % a.a. e aplica a degradação dos módulos (−2,5 % no 2º
   ano, −0,7 % a.a. depois). No caso de exemplo: **R$ 141.253** em 25 anos, em vez
   dos R$ 16.651 da planilha. Para reproduzir o valor antigo:
   `"compat_planilha": true`.
3. **Fio B automático por ano.** A planilha fixava o escalonamento de 2026 (60 %);
   o programa escolhe o percentual do ano corrente (editável no config).
4. **Formato brasileiro e data automática.** A planilha salvava números como
   `R$ 8,758.12` e o rodapé "referentes a jun/2026" era manual. O programa usa
   `R$ 8.758,12` (desligável em `formato_ptbr`) e o mês/ano atual no rodapé.

---

## 6. Conferência do retorno financeiro

No painel de resultados há o botão **"🧮 Conferir contas do retorno financeiro"**,
que abre um detalhamento passo a passo de todas as contas: rateio da geração
entre as UCs, "maior(consumo, geração)", % noturno aplicado, faturado, compensado,
tarifas e abatimentos, fatura sem e com solar por UC, totais e a projeção de 25
anos. Também dá para gerar esse relatório no terminal com `py -3 conferencia_retorno.py`.

**Regra do % noturno (igual à planilha):** a **GERADORA** usa o % noturno informado
(ex.: 65 %); toda **BENEFICIÁRIA** usa sempre **100 %** — na planilha isso vem das
células M32:M39 = `SE(tipo="BENEFICIÁRIA"; 1; ...)`. Quando a geração é maior que o
consumo, o faturado de cada UC parte da geração rateada:
`faturado = TRUNC(rateio × geração_total × %noturno)`. Ex.: para geração de
1424 kWh/mês, A geradora (60 %, 65 %) → TRUNC(0,60×1424×0,65) = 555 kWh; B
beneficiária (40 %, 100 %) → TRUNC(0,40×1424×1,0) = 569 kWh. Na versão anterior a
beneficiária usava 65 % por engano; isso foi corrigido.

## 7. Salvar na pasta do cliente & tarifas ao vivo (ANEEL)

**Salvar resumo:** no painel de resultados, o botão **"💾 Salvar resumo na pasta do
cliente"** grava, em `clientes/NOME DO CLIENTE/`, o **RESUMO** (dados do cliente,
dimensionamento, composição do preço e retorno) e a **CONFERÊNCIA** (detalhamento
passo a passo), cada um com data/hora no nome. O PDF gerado também é salvo nessa
pasta (além de uma cópia em `propostas/`).

**Tarifas da concessionária (tabela local, sem depender de internet):** dentro de
cada UC, escolha a **Concessionária** (1º dropdown) e a **Modalidade** (2º: B1 –
Residencial, B2 – Rural, B3 – Demais) e clique em **"aplicar tarifas e impostos"** —
TE, TUSD, ICMS, PIS e COFINS entram na hora, da tabela local do `config.json`
(alíquotas conforme a página de tributos da COPEL: ICMS 19%, 18% rural).

Quando a COPEL reajustar (todo 24 de junho), atualizar leva menos de um minuto:
clique em **"atualizar valores…"**, abra o site da concessionária pelo link do
próprio modal, copie TUSD e TE e cole. Como o site da COPEL publica os valores
**com impostos**, deixe a opção "com impostos" marcada — o programa converte para
"sem impostos" com as alíquotas da UC (sem = com × (1−ICMS) × (1−PIS−COFINS)) e
grava na tabela com resolução/vigência. O botão **"verificar resolução/ICMS no site
da COPEL"** faz uma consulta leve à página (HTML) e mostra a resolução vigente e o
ICMS atual, para você saber quando a tabela local ficou para trás. Tudo continua
100% editável campo a campo, para qualquer concessionária.

> Por que não busca os números sozinho? A tabela de tarifas do site da COPEL é um
> painel Power BI embutido, que não dá para ler de forma confiável por um programa
> offline — por isso a tabela local + atualização em 1 minuto é o caminho robusto.

## 8. Usar no celular (passo a passo)

O programa roda no computador e o celular acessa pela mesma rede Wi-Fi:

1. No computador, abra o programa normalmente (`iniciar.bat` ou o `.exe`).
2. A janela preta mostrará duas linhas: `http://127.0.0.1:8177` (o próprio PC) e
   **📱 No celular (mesmo Wi-Fi): http://SEU-IP:8177**.
3. No rodapé da página no PC também aparece o bloco **"📱 Usar no celular"** com a
   mesma URL e um **QR code** — aponte a câmera do celular para ele.
4. No celular, conectado ao **mesmo Wi-Fi**, abra o navegador e acesse a URL (ou
   leia o QR). A tela é responsiva: os campos se reorganizam para a tela pequena.
5. Tudo funciona no celular: calcular, conferir contas, salvar resumo e **gerar o
   PDF** (ele baixa direto no celular, pronto para enviar por WhatsApp).

Se o celular não abrir a página:
* confirme que os dois estão na **mesma rede** (o 4G/5G não funciona; use o Wi-Fi);
* no primeiro uso, o Windows pergunta sobre o **Firewall** — clique em
  **Permitir acesso** (rede privada). Se não perguntou, libere em
  Painel de Controle → Firewall do Windows → Permitir um aplicativo;
* redes de convidados/corporativas às vezes isolam os aparelhos entre si — teste
  num Wi-Fi doméstico ou no hotspot do próprio notebook.

## 9. Melhorias gráficas da proposta impressa

Sobre o modelo original da planilha, esta versão do gerador de PDF traz:

* **Círculos das "Etapas do Projeto" (pág. 4) perfeitos e idênticos.** No arquivo
  original esses marcadores saíam levemente ovais e de tamanhos diferentes; agora
  são redesenhados em vetor, todos iguais, ligados por uma linha limpa.
* **Foto das placas na capa em sangria total.** A imagem de fundo agora vai até a
  borda direita da página, sem a faixa branca que sobrava antes.
* **Preço à vista e economia em fonte branca**, como no material original — o texto
  fica legível sobre as caixas azul e verde (antes saíam em preto).
* **Cartões da página 3 padronizados e em alta resolução** (renderizados a 600 dpi),
  além do reagrupamento automático quando falta string box e/ou bateria.
* Os parâmetros desses elementos ficam em `assets/deco.json` (posições dos círculos,
  sangria da capa), caso precise ajustar.

## 10. Fidelidade do PDF

As 5 páginas de fundo (`assets/fundo.pdf`) foram **extraídas em vetor** das páginas
PG1–PG5 da planilha original — logotipos, ícones, bandeiras de cartão e textos fixos
são exatamente os mesmos. Os 31 campos dinâmicos e o gráfico da página 4 são
desenhados por cima nas posições medidas (`assets/layout.json`), com as mesmas
fontes (Inter, Sora, Carlito). A comparação pixel a pixel com o PDF exportado pelo
Excel deu diferença **zero** na página 2 e apenas suavização de fonte nas demais.

O alinhamento de cada campo (esquerda/centro) foi calibrado contra o PDF original,
e textos longos **encolhem e são cortados com reticências** automaticamente para
nunca invadirem as linhas e cartões vizinhos. Os cartões *String box* e *Bateria*
da página 3 são cobertos quando o componente não existe no sistema.

## 11. Teste automatizado contra a planilha

O arquivo **`teste_planilha.py`** confere mais de 60 valores contra as células
gravadas na planilha original: faturas, economia, retorno, preço de venda
convergido, preço por faixa de margem, payback, parcela, textos da proposta,
tabelas de trafo/material/mão de obra e as sobreposições manuais. Rode quando
quiser (ou depois de editar o `config.json`):

```
py -3 teste_planilha.py        (Windows)
python3 teste_planilha.py      (Linux/macOS)
```

Saída esperada: `✓ TODAS as verificações passaram — os valores batem com a planilha.`

> Lembrete sobre o preço de venda: o programa reproduz o que a **macro** da
> planilha produz ao rodar. Se você comparar com um arquivo salvo **sem rodar a
> macro**, o valor da planilha pode estar desatualizado (era o caso do arquivo
> enviado: Wp colado 2,3543 ≠ 2,3248 recalculado). Para reproduzir um PDF
> antigo à risca, use o campo *Preço/Wp manual*.

## 12. O que ficou de fora (por instrução)

* Abas **CÁLCULO DEMANDA** (Grupo A) e **OFFGRID**;
* As páginas alternativas **SICREDI** (a macro original exporta só PG1–PG5).

A estrutura é modular (`engine.py` cálculos · `proposta.py` PDF · `app.py` tela),
então essas extensões podem ser adicionadas depois sem mexer no que já funciona.

## 13. Estrutura de pastas

```
s2v_app/
├── app.py               servidor local + tela (Flask)
├── engine.py            todos os cálculos da planilha
├── proposta.py          gerador do PDF (fundos + textos + gráfico)
├── online.py            irradiação NASA / ViaCEP (opcional)
├── config.json          parâmetros de negócio editáveis
├── templates/index.html interface
├── assets/              fundo.pdf, layout.json, fontes
├── propostas/           PDFs gerados (criada no 1º uso)
├── instalar.bat · iniciar.bat · iniciar.sh · build_windows.bat
├── teste_planilha.py    validação automática contra a planilha
└── requirements.txt
```
