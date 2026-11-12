-- =====================================================================
-- CAMADA GOLD  |  Data marts agregados (consumo em Excel e conferência)
-- =====================================================================

-- mart_rede_ano: indicadores por rede e ano, com variação ano a ano (LAG)
-- e posição de cada rede no ano (RANK).
CREATE OR REPLACE TABLE mart_rede_ano AS
WITH agregado AS (
    SELECT
        f.ano,
        r.rede,
        r.grupo_rede,
        r.ordem_rede,
        COUNT(*)                                        AS escolas,
        SUM(f.qt_mat_bas)                               AS matriculas,
        AVG(CAST(f.in_internet AS DOUBLE))              AS pct_internet,
        AVG(CAST(f.in_banda_larga AS DOUBLE))           AS pct_banda_larga,
        AVG(CAST(f.in_internet_alunos AS DOUBLE))       AS pct_internet_alunos,
        AVG(CAST(f.in_internet_aprendizagem AS DOUBLE)) AS pct_internet_aprendizagem,
        AVG(CAST(f.in_laboratorio_informatica AS DOUBLE)) AS pct_laboratorio,
        AVG(CAST(f.in_computador_aluno AS DOUBLE))      AS pct_computador_aluno,
        AVG(CAST(f.in_rede_sem_fio AS DOUBLE))          AS pct_rede_sem_fio,
        SUM(f.qt_computadores_alunos)                   AS computadores_alunos,
        AVG(f.indice_infra_tec)                         AS indice_infra_tec
    FROM fato_infraestrutura f
    JOIN dim_rede r ON r.id_rede = f.id_rede
    GROUP BY f.ano, r.rede, r.grupo_rede, r.ordem_rede
)
SELECT
    a.*,
    CASE WHEN a.computadores_alunos > 0
         THEN CAST(a.matriculas AS DOUBLE) / a.computadores_alunos END        AS alunos_por_computador,
    a.indice_infra_tec
      - LAG(a.indice_infra_tec) OVER (PARTITION BY a.rede ORDER BY a.ano)    AS delta_indice_ano_anterior,
    a.pct_internet
      - LAG(a.pct_internet) OVER (PARTITION BY a.rede ORDER BY a.ano)        AS delta_pct_internet_ano_anterior,
    a.indice_infra_tec
      - FIRST_VALUE(a.indice_infra_tec) OVER (
            PARTITION BY a.rede ORDER BY a.ano
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)                 AS delta_indice_desde_inicio,
    RANK() OVER (PARTITION BY a.ano ORDER BY a.indice_infra_tec DESC)        AS posicao_no_ano
FROM agregado a;

-- mart_municipio_ano: índice por município, rede e ano, com quartil estadual (NTILE)
CREATE OR REPLACE TABLE mart_municipio_ano AS
WITH m AS (
    SELECT
        f.ano,
        f.co_municipio,
        d.municipio,
        d.mesorregiao,
        COUNT(*)                   AS escolas,
        AVG(f.indice_infra_tec)    AS indice_infra_tec,
        AVG(CAST(f.in_internet AS DOUBLE)) AS pct_internet
    FROM fato_infraestrutura f
    JOIN dim_municipio d ON d.co_municipio = f.co_municipio
    GROUP BY f.ano, f.co_municipio, d.municipio, d.mesorregiao
)
SELECT
    m.*,
    NTILE(4) OVER (PARTITION BY m.ano ORDER BY m.indice_infra_tec)           AS quartil_estadual,
    ROW_NUMBER() OVER (PARTITION BY m.ano ORDER BY m.indice_infra_tec DESC,
                                                   m.escolas DESC)           AS ranking_no_ano
FROM m;
