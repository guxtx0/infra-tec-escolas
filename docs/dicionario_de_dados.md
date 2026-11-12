# Dicionário de dados

## Fonte
Microdados do Censo Escolar da Educação Básica (INEP), arquivo de escolas (`microdados_ed_basica_AAAA.csv`, separado por `;`, codificação latin-1). Só entram escolas em atividade (`TP_SITUACAO_FUNCIONAMENTO = 1`) da UF escolhida.

## Camada gold: `fato_infraestrutura` (grão: 1 escola × 1 ano)

| Coluna | Origem no INEP | Descrição |
|---|---|---|
| ano | NU_ANO_CENSO | Ano do Censo |
| co_entidade | CO_ENTIDADE | Código INEP da escola |
| co_municipio | CO_MUNICIPIO | Código IBGE do município |
| id_rede | TP_DEPENDENCIA | 1 Federal, 2 Estadual, 3 Municipal, 4 Privada |
| id_localizacao | TP_LOCALIZACAO | 1 Urbana, 2 Rural |
| in_internet | IN_INTERNET | Tem internet |
| in_banda_larga | IN_BANDA_LARGA | Tem internet banda larga |
| in_internet_alunos | IN_INTERNET_ALUNOS | Internet disponível para uso dos alunos |
| in_internet_aprendizagem | IN_INTERNET_APRENDIZAGEM | Internet usada nos processos de ensino e aprendizagem |
| in_laboratorio_informatica | IN_LABORATORIO_INFORMATICA | Tem laboratório de informática |
| in_computador_aluno | IN_DESKTOP_ALUNO, IN_COMP_PORTATIL_ALUNO, IN_TABLET_ALUNO e quantidades | Tem computador, notebook ou tablet para alunos |
| in_rede_local | TP_REDE_LOCAL | Tem rede local (cabo, sem fio ou ambos) |
| in_rede_sem_fio | TP_REDE_LOCAL | Tem rede local sem fio |
| qt_desktop_aluno, qt_comp_portatil_aluno, qt_tablet_aluno | QT_* | Quantidade de equipamentos para alunos |
| qt_computadores_alunos | soma | Total de equipamentos para alunos |
| qt_equip_multimidia | QT_EQUIP_MULTIMIDIA | Projetores e equipamentos multimídia |
| qt_mat_bas | QT_MAT_BAS | Matrículas na educação básica |
| indice_infra_tec | calculado | Índice de Infraestrutura Tecnológica (0 a 100) |
| in_ganhou_internet | calculado (LAG) | 1 se a escola passou a ter internet em relação ao ano anterior em que apareceu |

## Índice de Infraestrutura Tecnológica (0 a 100)

| Componente | Peso |
|---|---|
| Internet | 20 |
| Banda larga | 15 |
| Internet para uso dos alunos | 15 |
| Internet no ensino e aprendizagem | 10 |
| Laboratório de informática | 15 |
| Computador, notebook ou tablet para alunos | 15 |
| Rede local | 10 |

A escola soma os pesos dos itens que declara ter. A média do índice resume várias dimensões num número só, e cada componente continua disponível separadamente no relatório.

## Dimensões

| Tabela | Chave | Atributos |
|---|---|---|
| dim_ano | ano | ano_texto |
| dim_rede | id_rede | rede, grupo_rede (Pública/Privada), ordem_rede |
| dim_localizacao | id_localizacao | localizacao, ordem_localizacao |
| dim_municipio | co_municipio | municipio, mesorregiao, microrregiao, uf (nome do ano mais recente) |
| dim_escola | co_entidade | escola, primeiro e último ano no Censo (versão mais recente, SCD tipo 1) |

## Data marts

- `mart_rede_ano`: indicadores por rede e ano, variação ano a ano (`LAG`), variação desde o início (`FIRST_VALUE`) e posição no ano (`RANK`).
- `mart_municipio_ano`: índice por município e ano, quartil estadual (`NTILE`) e ranking (`ROW_NUMBER`).
