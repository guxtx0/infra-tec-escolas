# Infraestrutura tecnológica das escolas de Minas Gerais

> **Pergunta do projeto:** como a infraestrutura tecnológica mudou ao longo dos anos, comparando rede municipal, estadual e privada?

Projeto de dados de ponta a ponta com os microdados do **Censo Escolar (INEP)**: ingestão, Data Lake em camadas, Data Warehouse em modelo estrela, SQL analítico, notebook no Databricks, relatório no Power BI e análise em Excel.

Autor: **Gustavo Oliveira**

> **Sobre os dados:** os números exibidos são **fictícios**, gerados no mesmo formato, com os mesmos nomes de coluna e a mesma codificação dos microdados do INEP, para demonstrar a lógica e as ferramentas. O pipeline já processa os dados reais com um único comando (veja "Como rodar").

 **Explicação completa das ferramentas e decisões:** [docs/Ferramentas_e_metodos.pdf](docs/Ferramentas_e_metodos.pdf)

---

## O que tem aqui

| Pasta / arquivo | O que é |
|---|---|
| `InfraTecEscolas.pbip` | Projeto do Power BI (abre no Power BI Desktop). Modelo em TMDL e relatório em PBIR, versionáveis no Git |
| `pipeline/run_pipeline.py` | Pipeline ELT em Python + DuckDB: baixa os zips do INEP e gera as camadas bronze, silver e gold |
| `pipeline/gerar_amostra.py` | Gera uma amostra sintética no formato do INEP, para testar sem baixar nada |
| `sql/` | Todo o SQL do projeto (silver, dimensões, fato, data marts e consultas analíticas). Roda no DuckDB e no Databricks |
| `databricks/01_pipeline_medalhao.py` | Notebook do Databricks: o mesmo pipeline com Spark, Delta Lake e Unity Catalog |
| `excel/Analise_Infra_Tec.xlsx` | Planilha com tabela dinâmica, fórmulas de busca com dois critérios, validação de dados, formatação condicional e gráfico |
| `docs/` | PDF com as ferramentas e métodos, dicionário de dados e backlog do projeto (Kanban em sprints) |
| `tema/LousaDigital.json` | Tema de cores do relatório |
| `dados/gold/` | Saída do pipeline, lida pelo Power BI (vem com a amostra sintética) |

## Arquitetura

```
INEP (zips)  ──►  RAW  ──►  BRONZE  ──►  SILVER  ──►  GOLD  ──►  Power BI / Excel
                  zip       Parquet/     tipagem,     estrela +
                            Delta        filtro UF,   data marts
                            (bruto)      dedup (SQL)  (SQL)
```

- **ELT em camadas (arquitetura medalhão).** O dado bruto entra sem tratamento (bronze). As regras ficam em SQL versionado (silver e gold).
- **Data Lake:** arquivos Parquet por camada em `dados/` (local) ou tabelas Delta num Volume/Unity Catalog (Databricks).
- **Data Warehouse:** `dados/dw_infra_tec.duckdb`, com modelo estrela:
  - `fato_infraestrutura` (grão escola × ano), com o Índice de Infraestrutura Tecnológica
  - `dim_ano`, `dim_rede`, `dim_localizacao`, `dim_municipio`, `dim_escola`
  - data marts `mart_rede_ano` e `mart_municipio_ano`
- **Nuvem:** o notebook `databricks/` roda no Databricks (inclusive no Free Edition) com o mesmo SQL. O Power BI pode ler direto do SQL Warehouse pelo conector Azure Databricks.

## SQL usado

CTEs, `CASE` e agregação condicional (pivot), funções de janela (`LAG`, `FIRST_VALUE`, `RANK`, `ROW_NUMBER`, `NTILE`), `QUALIFY` para deduplicação, `PERCENTILE_CONT` para medianas e `TRY_CAST` para tipagem segura. As respostas diretas à pergunta estão em `sql/05_consultas_analiticas.sql`, e os resultados são salvos em `dados/gold/analises/`.

## Power BI

- **Power Query:** parâmetro `PastaDados`, tipagem explícita, renomeação, limpeza de texto e coluna derivada ("Porte da escola").
- **Modelagem:** modelo estrela com relacionamentos 1:N, colunas de ordenação (`Rede` por `Ordem`), chaves ocultas e medidas numa tabela própria, em pastas.
- **DAX:** `CALCULATE`, `DIVIDE`, `REMOVEFILTERS`, `ALLSELECTED`, `RANKX`, `ISINSCOPE`, `SUMMARIZE`, `CONCATENATEX`, variáveis e inteligência de tempo por ano (ano anterior, primeiro e último ano do filtro).
- **Páginas:** Visão geral, Indicadores ao longo do tempo, Público x privado, Municípios e Sobre o projeto.
- **Cores (tema "Lousa Digital"):** cada rede tem sempre a mesma cor. Verde-lousa para a municipal, azul para a estadual, amarelo-giz para a federal e coral para a privada, com cabeçalho azul-marinho.

## Excel

Tabela estruturada (`tbRedeAno`), tabela dinâmica (atualiza ao abrir), seletores com validação de dados, `ÍNDICE`+`CORRESP` com dois critérios (fórmula de matriz), `SOMASES`, `MÉDIASES`, `CONT.SES`, `SEERRO`, escala de cores e gráfico de linhas.

---

## Como rodar

### 1. Pré-requisitos
- Python 3.10 ou superior
- `pip install -r pipeline/requirements.txt`
- Power BI Desktop (versão recente, com suporte a arquivos .pbip)

### 2. Testar com a amostra (1 minuto)
```bash
python pipeline/run_pipeline.py --amostra
```
O relatório mostra um aviso de dados fictícios enquanto a fonte for a amostra.

### 3. Rodar com os dados reais do INEP
```bash
python pipeline/run_pipeline.py --anos 2019-2024 --uf MG
```
O script tenta baixar `https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_AAAA.zip`. Se o download falhar, baixe os zips na página de microdados do Censo Escolar do INEP e salve em `dados/raw/` com o nome `microdados_censo_escolar_AAAA.zip`.

### 4. Abrir no Power BI
1. Abra `InfraTecEscolas.pbip`.
2. Clique em **Atualizar**. O pipeline já gravou o caminho da pasta `dados/gold` no parâmetro `PastaDados`.
3. Se a pasta não for encontrada, o projeto usa a cópia da amostra guardada dentro dele, e o aviso de dados fictícios aparece. Para usar os dados reais, rode o pipeline ou informe a pasta em **Transformar dados → Editar parâmetros → PastaDados** (caminho completo de `dados\gold\`, terminando com `\`).
4. Para salvar como arquivo único: **Arquivo → Salvar como → .pbix**.

## Limitações
- Os dados são declarados pelas próprias escolas ao Censo.
- Ter internet ou computador não garante uso pedagógico nem qualidade da conexão.
- Algumas colunas mudam de nome ou de regra entre os anos do Censo. O pipeline cria como vazias as colunas que não existirem em nenhum ano.
- Os pesos do índice são uma escolha do autor, documentada em `docs/dicionario_de_dados.md`.
