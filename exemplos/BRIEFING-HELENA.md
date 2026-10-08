# Helena → Dimensionador S2V: como ler faturas e montar o JSON

Documento de referência para a Helena (assistente da S2V). Cole na base de
conhecimento dela. Tudo aqui foi apurado contra **faturas reais da COPEL** e está
travado em testes automatizados do dimensionador.

---

## 1. Divisão de trabalho

| Quem | Faz |
|---|---|
| **Helena** | conversa com o cliente, **lê a fatura**, monta o JSON |
| **Dimensionador** | faz **todas** as contas: tarifas com impostos, compensação, Fio B, demanda, payback, retorno de 25 anos |

**Nunca calcule economia, payback, kWp ou valor de conta por conta própria.**
Monte o JSON, envie, e use os números que voltarem. Suas contas de cabeça vão
divergir do programa — e o programa é quem reproduz a fatura centavo a centavo.

Endpoint: `POST /api/calcular` (JSON). Precisa de sessão autenticada.
**Grupo A exige sessão de ADMINISTRADOR** — num payload de consultor o servidor
força grupo B e descarta a demanda silenciosamente.

Exemplos validados que você pode usar de molde:
`exemplos/fatura_real_grupo_b.json` · `exemplos/fatura_real_grupo_a.json`

---

## 2. ⚠ A fatura MENTE quando a UC já tem usina

Este é o conceito que mais causa erro. O medidor da concessionária **não enxerga**
o que a usina gera e a casa consome **no mesmo instante**. Essa parcela
desaparece da fatura, mas não deixou de existir — e ela falta nos **dois** lados:

```
consumo real = consumo medido na fatura + autoconsumo
geração real = energia injetada         + autoconsumo    ← o MESMO autoconsumo
```

Consequências práticas:

- **`GERAC` / "ENERGIA INJETADA" não é a geração da usina.** É só o que sobrou e
  foi para a rede. A usina gerou mais.
- **Não estime a potência da usina existente dividindo o injetado pela
  produtividade.** Dá um número menor que o real. Se precisar da potência, peça
  ao cliente ou marque para a visita técnica.
- **A geração real só existe no app de monitoramento** (Goodwe, Solarman, Growatt…).
  Peça ao cliente. Sem ela, mande `geracao_kwh: 0` — é seguro, o programa passa a
  conhecer só o que o medidor viu, e o **dimensionamento não muda** (o autoconsumo
  entra nos dois lados e se cancela). O que se perde é mostrar o consumo
  verdadeiro do cliente.

---

## 3. Como ler a fatura — GRUPO B (baixa tensão)

Exemplo real: COPEL, UC 000000000000002, ref. 09/2026, total **R$ 117,53**.

| Linha da fatura | Vai para |
|---|---|
| `ENERGIA ELET CONSUMO` → coluna **Quant.** | `consumos` (os 12 meses) |
| coluna **Tarifa unit.** dessa linha | `te` |
| `ENERGIA ELET USO SISTEMA` → **Tarifa unit.** | `tusd` |
| `ENERGIA INJETADA ...` → **Quant.** (sem o sinal) | `gds_existentes[].injetado_kwh` |
| `CONT ILUMIN PUBLICA MUNICIPIO` → Valor | `ilum_publica` |
| quadro **Tributo**: ICMS / COFINS / PIS → coluna Alíquota | `icms`, `cofins`, `pis` |
| `Periodos Band.Tarif.` | `bandeira` |
| `Bifasico / 50A` | `ligacao: "BIFASICO"` |

**Use sempre a coluna "Tarifa unit."**, que é sem tributos — nunca a "Preço unit.
com tributos". O programa embute os impostos sozinho.

**Se o medidor tiver registrador `GERAC`**, o cliente já é microgerador: o número
do GERAC é o injetado do mês.

---

## 4. Como ler a fatura — GRUPO A (média tensão)

Exemplo real: COPEL, UC 000000000000001, A4 Industrial Verde, ref. 09/2026,
total **R$ 17.648,07**.

| Linha da fatura | Vai para |
|---|---|
| `ENERGIA ELETRICA TE PONTA` → Quant. | `consumos_ponta` |
| `ENERGIA ELETRICA TE F PONTA` → Quant. | `consumos` (fora ponta!) |
| `TE PONTA` / `USD PONTA` → **Tarifa unit.** | `te_ponta` / `tusd_kwh_ponta` |
| `TE F PONTA` / `USD F PONTA` → **Tarifa unit.** | `te_fora` / `tusd_kwh_fora` |
| `DEMANDA USD` → **Tarifa unit.** | `tusd_demanda` (preço do kW) |
| `DEMANDA USD` → **Quant.** | `demanda_faturada_kw` |
| GRANDEZAS CONTRATADAS → Demanda | `demanda_kw` (contratada) |
| `ENERGIA REAT EXCED` + `DEMANDA REATIVA EXCED` → somar os Valores | `outros_rs` |
| `ENERGIA INJETADA ...` → Quant. | `gds_existentes[].injetado_kwh` |
| Classificação (`A4 Industrial`) | `subgrupo_a: "A4"` |

**Como saber a modalidade:** se GRANDEZAS CONTRATADAS traz **"Demanda Todos os
Períodos"**, é **VERDE** (uma demanda só). Se traz demanda de ponta e fora ponta
separadas, é **AZUL**.

**Não estranhe a TUSD da ponta ser altíssima** (ex.: 1,46 contra 0,146 fora
ponta). Na modalidade Verde é assim: a ponta é cara no kWh, não na demanda.

**A demanda cobrada pode ser diferente da contratada** (a FATURA-A contratou 175 kW
e pagou 167,47). Mande sempre o que está impresso em `demanda_faturada_kw`.

---

## 5. O contrato do JSON

### Armadilhas de formato

1. **Percentuais vão em %, não em fração.** `icms: 19`, nunca `0.19`. Vale para
   `icms`, `cofins`, `pis`, `pct_noturno`, `margem_desejada`, `comissao_pct`,
   `seguro_pct`.
2. **`consumos` tem 12 posições**, de janeiro a dezembro. Se só houver o consumo
   médio, repita o mesmo valor 12 vezes.
3. **No grupo A, `consumos` é o FORA PONTA** e `consumos_ponta` é a ponta.
4. **O Fio B NÃO vai no JSON.** Ele vem das pré-definições do programa. Não tente
   mandar.

### `pct_noturno` — a armadilha que mais erra

| Situação | Valor |
|---|---|
| Cliente **sem** usina (consumo é o total dele) | o padrão (65) |
| Cliente **com** usina — consumo da fatura já é o medido | **100** |
| Grupo A | **não existe**, nem mande |

Aplicar o % noturno sobre um consumo que já está líquido do autoconsumo cobra o
autoconsumo duas vezes.

### Usinas existentes

```json
"gds_existentes": [
  { "nome": "usina 2021", "kwp": 135, "injetado_kwh": 5490,
    "geracao_kwh": 0, "isento_icms": false }
]
```

- `injetado_kwh` — da fatura. **Obrigatório** se o cliente já gera.
- `geracao_kwh` — só do app de monitoramento. `0` quando não souber.
- `isento_icms` — **ver seção 6**. Uma usina com mais de ~4 anos: `false`.

**Se o cliente já gera e você não mandar `gds_existentes`, a proposta fica
errada**: o programa vai achar que ele não gera nada, vai superdimensionar o
sistema e vai prometer uma economia que o cliente **já tem**.

---

## 6. Regras de negócio que mudam o número

### Convênio ICMS 16/2015 — tem prazo, e corre por PARECER DE ACESSO

A energia compensada é isenta de ICMS, mas o benefício dura ~4 anos **contados
por parecer de acesso** — não por estado nem por cliente. Numa mesma UC, a usina
de 2019 pode já ter perdido e a de 2024 ainda ter.

- Cada usina existente tem o seu `isento_icms`.
- O projeto **novo** tem parecer novo: `abat_te_inclui_icms: true` e
  `isencao_icms_anos: 4` (isso faz a projeção de 25 anos descer de patamar quando
  o prazo acabar).

**Como ler na fatura:** olhe a linha `ENERGIA INJETADA ... TE`. Se ela tiver
**ICMS negativo**, a isenção está valendo (`true`). Se tiver **ICMS 0,00** e o
preço unitário for menor que o da TE consumida, o prazo acabou (`false`).

### Grupo A tem regras próprias

- **A demanda (R$/kW) o solar NÃO abate.** É o piso da conta — por isso a
  economia percentual do grupo A é menor que a do grupo B. Nunca prometa "zerar a
  conta" para um cliente de média tensão.
- **Não existe Fio B no grupo A** (nem GD1 nem GD2) e **não existe custo de
  disponibilidade**.
- **Para abater 1 kWh de ponta são precisos ~1,6 kWh gerados fora ponta** (fator
  de correção = TE ponta ÷ TE fora ponta). Mande `fator_ponta_manual: 1.63` se o
  cliente for COPEL. **Nunca calcule esse fator pela tarifa cheia** — daria ~4,4 e
  inflaria a economia.
- **O programa considera sempre o PIOR CASO de autoconsumo no grupo A**: toda a
  geração do sistema novo é tratada como injetada (nada consumido na hora). É
  o critério da S2V — não "melhore" a economia por conta própria.
- **TUSD-G (demanda de geração)** é opcional, vale para GD1 e GD2, e contrata-se
  só o que a potência dos inversores — **do projeto novo MAIS os das usinas que
  a UC já tem** — passa da demanda de consumo já contratada. Deixe
  `demanda_g_kw: 0` que o programa calcula, e informe o `inversor_kw` de cada
  usina existente em `gds_existentes` (sem ele o programa usa o kWp). Molde:
  `exemplos/projeto_novo_grupo_a.json`.

### Grupo B: a regra do maior valor

Compensa-se **tudo**, e a conta final é o **maior** entre o custo de
disponibilidade (30/50/100 kWh) e a sobra de Fio B. Você não precisa calcular
isso — mas precisa saber para não se assustar quando o custo de disponibilidade
não aparecer na fatura de um cliente com consumo alto.

---

## 7. Erros já cometidos — não repita

Do pedido de orçamento de 05/10/2026 (ampliação para carro elétrico):

| Erro | Por quê está errado | O certo |
|---|---|---|
| "Potência: ~3,8 kWp (430/114)" | 430 é o **injetado**, não a geração | não estimar; perguntar ou deixar para a visita |
| "Ampliação ~0,9 kWp (120 kWh / 114)" | dimensionou só a carga nova, ignorando que a usina atual **já sobra** 123 kWh/mês e há 683 kWh de saldo | mandar o consumo **com** a carga nova + `gds_existentes`, e usar o kWp que o programa devolver |
| não registrou o saldo SCEE | é o dado que mais pesa numa decisão de ampliação | sempre anotar "Saldo Acumulado" do quadro SCEE |

Naquele caso, o dimensionador com a usina declarada respondeu **0 kWp** — a sobra
da usina atual já cobria o carro. A conta "carga ÷ produtividade" teria vendido um
sistema desnecessário.

---

## 8. O que você NÃO pode determinar sozinha — pergunte

- **Geração real da usina existente** → app de monitoramento do cliente
- **Potência e quantidade de módulos já instalados** → cliente ou visita técnica
- **Se o inversor existente comporta mais módulos** → visita técnica
- **Se o padrão de entrada aguenta a carga nova** (wallbox, por exemplo) → visita
- **Consumo dos meses faltantes** na fatura → peça faturas anteriores
- **Idade da usina / data do parecer de acesso** → cliente

Prefira dizer "preciso confirmar X" a estimar. Uma estimativa errada aqui vira um
sistema mal dimensionado.

---

## 9. Antes de enviar o JSON — confira

- [ ] Percentuais em % (19, não 0.19)
- [ ] `consumos` com 12 posições
- [ ] Cliente já gera? → `gds_existentes` preenchido **e** `pct_noturno: 100`
- [ ] Grupo A? → `consumos` = fora ponta, `consumos_ponta` preenchido, sessão de admin
- [ ] Grupo A? → `demanda_kw`, `demanda_faturada_kw`, `tusd_demanda`, `outros_rs`
- [ ] Tarifas da coluna "Tarifa unit." (sem tributos)
- [ ] `isento_icms` de cada usina conferido na linha ENERGIA INJETADA TE
- [ ] Nenhum número calculado por você — todos vieram da fatura ou do programa

**Teste de sanidade:** mande o JSON com `qtd_modulos_kit: 0` antes de orçar. O
`fatura_sem` que voltar tem que bater com o **total da fatura do cliente**. Se não
bater, há erro de leitura — não prossiga com o orçamento.
