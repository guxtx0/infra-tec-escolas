-- =====================================================================
-- CONSULTAS ANALÍTICAS  |  respostas diretas à pergunta do projeto
-- "Como a infraestrutura tecnológica mudou ao longo dos anos,
--  comparando rede municipal, estadual e privada?"
-- Cada consulta tem um marcador de nome; o pipeline salva o resultado em
-- dados/gold/analises/<nome>.csv.
-- =====================================================================

-- @nome: q1_pivot_indice_rede_por_ano
-- Pivot com agregação condicional: índice médio de cada rede, um ano por linha.
SELECT
    f.ano,
    ROUND(AVG(CASE WHEN f.id_rede = 3 THEN f.indice_infra_tec END), 1) AS municipal,
    ROUND(AVG(CASE WHEN f.id_rede = 2 THEN f.indice_infra_tec END), 1) AS estadual,
    ROUND(AVG(CASE WHEN f.id_rede = 4 THEN f.indice_infra_tec END), 1) AS privada,
    ROUND(AVG(CASE WHEN f.id_rede = 4 THEN f.indice_infra_tec END)
        - AVG(CASE WHEN f.id_rede IN (2, 3) THEN f.indice_infra_tec END), 1) AS gap_privada_vs_publica
FROM fato_infraestrutura f
GROUP BY f.ano
ORDER BY f.ano;

-- @nome: q2_variacao_total_por_rede
-- Variação entre o primeiro e o último ano, em pontos percentuais, por indicador.
WITH serie AS (
    SELECT rede, ano, pct_internet, pct_banda_larga, pct_laboratorio,
           pct_computador_aluno, indice_infra_tec,
           MIN(ano) OVER (PARTITION BY rede) AS ano_ini,
           MAX(ano) OVER (PARTITION BY rede) AS ano_fim
    FROM mart_rede_ano
)
SELECT
    rede,
    MIN(ano_ini) AS ano_inicial,
    MAX(ano_fim) AS ano_final,
    ROUND(100 * (MAX(CASE WHEN ano = ano_fim THEN pct_internet END)
               - MAX(CASE WHEN ano = ano_ini THEN pct_internet END)), 1)         AS pp_internet,
    ROUND(100 * (MAX(CASE WHEN ano = ano_fim THEN pct_banda_larga END)
               - MAX(CASE WHEN ano = ano_ini THEN pct_banda_larga END)), 1)      AS pp_banda_larga,
    ROUND(100 * (MAX(CASE WHEN ano = ano_fim THEN pct_laboratorio END)
               - MAX(CASE WHEN ano = ano_ini THEN pct_laboratorio END)), 1)      AS pp_laboratorio,
    ROUND(100 * (MAX(CASE WHEN ano = ano_fim THEN pct_computador_aluno END)
               - MAX(CASE WHEN ano = ano_ini THEN pct_computador_aluno END)), 1) AS pp_computador_aluno,
    ROUND(MAX(CASE WHEN ano = ano_fim THEN indice_infra_tec END)
        - MAX(CASE WHEN ano = ano_ini THEN indice_infra_tec END), 1)             AS pontos_indice
FROM serie
GROUP BY rede
ORDER BY pontos_indice DESC;

-- @nome: q3_escolas_que_ganharam_internet
-- Quantas escolas passaram a ter internet em cada ano, por rede.
SELECT
    f.ano,
    r.rede,
    SUM(f.in_ganhou_internet) AS escolas_que_ganharam_internet,
    COUNT(*)                  AS escolas
FROM fato_infraestrutura f
JOIN dim_rede r ON r.id_rede = f.id_rede
GROUP BY f.ano, r.rede
HAVING SUM(f.in_ganhou_internet) > 0
ORDER BY f.ano, escolas_que_ganharam_internet DESC;

-- @nome: q4_top5_municipios_por_ano
-- Os 5 municípios com maior índice em cada ano (mínimo de 10 escolas).
SELECT ano, ranking, municipio, escolas, ROUND(indice_infra_tec, 1) AS indice_infra_tec
FROM (
    SELECT m.*,
           ROW_NUMBER() OVER (PARTITION BY m.ano ORDER BY m.indice_infra_tec DESC) AS ranking
    FROM mart_municipio_ano m
    WHERE m.escolas >= 10
) t
WHERE ranking <= 5
ORDER BY ano, ranking;

-- @nome: q5_mediana_alunos_por_computador
-- Mediana de alunos por computador (escolas com ao menos 1 computador para alunos).
SELECT
    f.ano,
    r.rede,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY CAST(f.qt_mat_bas AS DOUBLE) / f.qt_computadores_alunos), 1) AS mediana_alunos_por_computador,
    COUNT(*) AS escolas_com_computador
FROM fato_infraestrutura f
JOIN dim_rede r ON r.id_rede = f.id_rede
WHERE f.qt_computadores_alunos > 0 AND f.qt_mat_bas > 0
GROUP BY f.ano, r.rede
ORDER BY f.ano, r.rede;
