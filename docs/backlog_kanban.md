# Backlog do projeto (Kanban em sprints de 1 semana)

Quadro: **A fazer → Em andamento → Em revisão → Concluído**. Limite de 2 cartões em andamento.
O arquivo `issues_github.csv` traz os mesmos cartões para importar no GitHub Projects.

## Definição de pronto
- Código versionado no Git, com o SQL na pasta `sql/`
- Números conferidos contra uma consulta independente (ex.: medida DAX × `mart_rede_ano`)
- Documentação atualizada (README e dicionário de dados)

## Sprint 1: dados e ingestão
| # | História | Critério de aceite | Status |
|---|---|---|---|
| 1 | Como analista, quero baixar os microdados do Censo de vários anos automaticamente | Zips em `dados/raw/`, com mensagem clara quando o download falha | Concluído |
| 2 | Como analista, quero o dado bruto preservado (bronze) | Parquet por ano com arquivo de origem e ordem de carga | Concluído |
| 3 | Como analista, quero uma amostra para testar sem internet | `--amostra` gera arquivos no mesmo formato do INEP | Concluído |

## Sprint 2: modelagem e regras
| # | História | Critério de aceite | Status |
|---|---|---|---|
| 4 | Silver tipada, filtrada pela UF e sem duplicidade | `QUALIFY ROW_NUMBER()` garante 1 linha por escola e ano | Concluído |
| 5 | Modelo estrela no Data Warehouse | Fato escola × ano e 5 dimensões | Concluído |
| 6 | Índice de Infraestrutura Tecnológica | Pesos documentados e valor de 0 a 100 | Concluído |
| 7 | Data marts e consultas que respondem à pergunta | 5 consultas salvas em `dados/gold/analises/` | Concluído |
| 8 | Mesmo pipeline no Databricks | Notebook com Delta e Unity Catalog usando os arquivos SQL | Concluído |

## Sprint 3: entrega
| # | História | Critério de aceite | Status |
|---|---|---|---|
| 9 | Relatório Power BI com 5 páginas | Visão geral, indicadores, público x privado, municípios, sobre | Concluído |
| 10 | Medidas DAX organizadas em pastas | Ano anterior, variação, ranking e texto automático | Concluído |
| 11 | Planilha Excel para quem não usa Power BI | Tabela dinâmica, busca com dois critérios e gráfico | Concluído |
| 12 | Publicar no GitHub e no LinkedIn | README com prints e post com 3 conclusões | A fazer |

## Próximos passos (backlog)
- Cruzar com o IDEB (resultado de aprendizagem) por escola
- Publicar o relatório na web pelo Power BI Service
- Agendar a atualização anual (Databricks Jobs)
