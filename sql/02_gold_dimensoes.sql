-- =====================================================================
-- CAMADA GOLD  |  Dimensões do Data Warehouse (modelo estrela)
-- =====================================================================

-- dim_ano: um registro por ano carregado
CREATE OR REPLACE TABLE dim_ano AS
SELECT DISTINCT
    ano,
    CAST(ano AS STRING) AS ano_texto
FROM silver_escolas;

-- dim_rede: dependência administrativa (código oficial do INEP)
CREATE OR REPLACE TABLE dim_rede AS
SELECT 3 AS id_rede, 'Municipal' AS rede, 'Pública' AS grupo_rede, 1 AS ordem_rede
UNION ALL SELECT 2, 'Estadual', 'Pública', 2
UNION ALL SELECT 1, 'Federal',  'Pública', 3
UNION ALL SELECT 4, 'Privada',  'Privada', 4;

-- dim_localizacao
CREATE OR REPLACE TABLE dim_localizacao AS
SELECT 1 AS id_localizacao, 'Urbana' AS localizacao, 1 AS ordem_localizacao
UNION ALL SELECT 2, 'Rural', 2;

-- dim_municipio: nome do município no ano mais recente (nomes podem mudar)
CREATE OR REPLACE TABLE dim_municipio AS
SELECT
    co_municipio,
    no_municipio   AS municipio,
    no_mesorregiao AS mesorregiao,
    no_microrregiao AS microrregiao,
    sg_uf          AS uf
FROM silver_escolas
QUALIFY ROW_NUMBER() OVER (PARTITION BY co_municipio ORDER BY ano DESC) = 1;

-- dim_escola: atributos descritivos da escola (versão mais recente, SCD tipo 1)
CREATE OR REPLACE TABLE dim_escola AS
SELECT
    co_entidade,
    no_entidade   AS escola,
    co_municipio,
    tp_dependencia AS id_rede_atual,
    MIN(ano) OVER (PARTITION BY co_entidade) AS primeiro_ano_no_censo,
    MAX(ano) OVER (PARTITION BY co_entidade) AS ultimo_ano_no_censo
FROM silver_escolas
QUALIFY ROW_NUMBER() OVER (PARTITION BY co_entidade ORDER BY ano DESC) = 1;
