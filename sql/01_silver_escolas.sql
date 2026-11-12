-- =====================================================================
-- CAMADA SILVER  |  silver_escolas
-- Origem: bronze_censo_escolar (CSV do INEP carregado sem tratamento)
-- Objetivo: tipar, padronizar, filtrar a UF e remover duplicidades.
-- Dialeto: SQL ANSI compatível com DuckDB e Databricks (Spark SQL).
-- {{UF}} é substituído pelo pipeline (padrão: MG).
-- =====================================================================
CREATE OR REPLACE TABLE silver_escolas AS
WITH tipado AS (
    SELECT
        TRY_CAST(NU_ANO_CENSO AS INT)                    AS ano,
        TRY_CAST(CO_ENTIDADE AS BIGINT)                  AS co_entidade,
        TRIM(NO_ENTIDADE)                                AS no_entidade,
        TRIM(SG_UF)                                      AS sg_uf,
        TRY_CAST(CO_MUNICIPIO AS BIGINT)                 AS co_municipio,
        TRIM(NO_MUNICIPIO)                               AS no_municipio,
        TRIM(NO_MESORREGIAO)                             AS no_mesorregiao,
        TRIM(NO_MICRORREGIAO)                            AS no_microrregiao,
        TRY_CAST(TP_DEPENDENCIA AS INT)                  AS tp_dependencia,
        TRY_CAST(TP_LOCALIZACAO AS INT)                  AS tp_localizacao,
        TRY_CAST(TP_SITUACAO_FUNCIONAMENTO AS INT)       AS tp_situacao_funcionamento,
        -- Indicadores 0/1. Valor ausente vira 0 (a escola não declarou o recurso).
        COALESCE(TRY_CAST(IN_INTERNET AS INT), 0)                    AS in_internet,
        COALESCE(TRY_CAST(IN_BANDA_LARGA AS INT), 0)                 AS in_banda_larga,
        COALESCE(TRY_CAST(IN_INTERNET_ALUNOS AS INT), 0)             AS in_internet_alunos,
        COALESCE(TRY_CAST(IN_INTERNET_ADMINISTRATIVO AS INT), 0)     AS in_internet_administrativo,
        COALESCE(TRY_CAST(IN_INTERNET_APRENDIZAGEM AS INT), 0)       AS in_internet_aprendizagem,
        COALESCE(TRY_CAST(IN_INTERNET_COMUNIDADE AS INT), 0)         AS in_internet_comunidade,
        COALESCE(TRY_CAST(IN_ACESSO_INTERNET_COMPUTADOR AS INT), 0)  AS in_acesso_internet_computador,
        COALESCE(TRY_CAST(IN_ACES_INTERNET_DISP_PESSOAIS AS INT), 0) AS in_aces_internet_disp_pessoais,
        COALESCE(TRY_CAST(IN_LABORATORIO_INFORMATICA AS INT), 0)     AS in_laboratorio_informatica,
        COALESCE(TRY_CAST(IN_DESKTOP_ALUNO AS INT), 0)               AS in_desktop_aluno,
        COALESCE(TRY_CAST(IN_COMP_PORTATIL_ALUNO AS INT), 0)         AS in_comp_portatil_aluno,
        COALESCE(TRY_CAST(IN_TABLET_ALUNO AS INT), 0)                AS in_tablet_aluno,
        -- TP_REDE_LOCAL: 0 = não há, 1 = a cabo, 2 = sem fio, 3 = a cabo e sem fio
        COALESCE(TRY_CAST(TP_REDE_LOCAL AS INT), 0)                  AS tp_rede_local,
        -- Quantidades: negativos ou ausentes viram 0.
        GREATEST(COALESCE(TRY_CAST(QT_DESKTOP_ALUNO AS INT), 0), 0)       AS qt_desktop_aluno,
        GREATEST(COALESCE(TRY_CAST(QT_COMP_PORTATIL_ALUNO AS INT), 0), 0) AS qt_comp_portatil_aluno,
        GREATEST(COALESCE(TRY_CAST(QT_TABLET_ALUNO AS INT), 0), 0)        AS qt_tablet_aluno,
        GREATEST(COALESCE(TRY_CAST(QT_EQUIP_MULTIMIDIA AS INT), 0), 0)    AS qt_equip_multimidia,
        GREATEST(COALESCE(TRY_CAST(QT_MAT_BAS AS INT), 0), 0)             AS qt_mat_bas,
        _arquivo_origem,
        _ordem_carga
    FROM bronze_censo_escolar
)
SELECT *
FROM tipado
WHERE sg_uf = '{{UF}}'
  AND tp_situacao_funcionamento = 1          -- somente escolas em atividade
  AND ano IS NOT NULL
  AND co_entidade IS NOT NULL
-- Deduplicação: se o mesmo ano for carregado duas vezes, fica o último arquivo carregado.
QUALIFY ROW_NUMBER() OVER (PARTITION BY ano, co_entidade ORDER BY _ordem_carga DESC) = 1;
