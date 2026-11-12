-- =====================================================================
-- CAMADA GOLD  |  fato_infraestrutura (grão: 1 escola x 1 ano)
-- Inclui o Índice de Infraestrutura Tecnológica (IIT), de 0 a 100.
--
-- Pesos do IIT (autorais, documentados em docs/dicionario_de_dados.md):
--   Internet .......................... 20
--   Banda larga ....................... 15
--   Internet para uso dos alunos ...... 15
--   Internet no ensino-aprendizagem ... 10
--   Laboratório de informática ........ 15
--   Computador/tablet para alunos ..... 15
--   Rede local (cabo ou sem fio) ...... 10
-- =====================================================================
CREATE OR REPLACE TABLE fato_infraestrutura AS
WITH base AS (
    SELECT
        ano,
        co_entidade,
        co_municipio,
        tp_dependencia                         AS id_rede,
        tp_localizacao                         AS id_localizacao,
        in_internet,
        in_banda_larga,
        in_internet_alunos,
        in_internet_aprendizagem,
        in_laboratorio_informatica,
        CASE WHEN in_desktop_aluno = 1
               OR in_comp_portatil_aluno = 1
               OR in_tablet_aluno = 1
               OR (qt_desktop_aluno + qt_comp_portatil_aluno + qt_tablet_aluno) > 0
             THEN 1 ELSE 0 END                 AS in_computador_aluno,
        CASE WHEN tp_rede_local IN (1, 2, 3) THEN 1 ELSE 0 END AS in_rede_local,
        CASE WHEN tp_rede_local IN (2, 3)    THEN 1 ELSE 0 END AS in_rede_sem_fio,
        qt_desktop_aluno,
        qt_comp_portatil_aluno,
        qt_tablet_aluno,
        qt_desktop_aluno + qt_comp_portatil_aluno + qt_tablet_aluno AS qt_computadores_alunos,
        qt_equip_multimidia,
        qt_mat_bas
    FROM silver_escolas
    WHERE tp_dependencia IN (1, 2, 3, 4)
)
SELECT
    b.*,
    CAST(
          20 * in_internet
        + 15 * in_banda_larga
        + 15 * in_internet_alunos
        + 10 * in_internet_aprendizagem
        + 15 * in_laboratorio_informatica
        + 15 * in_computador_aluno
        + 10 * in_rede_local
    AS DOUBLE)                                 AS indice_infra_tec,
    -- Escola que ganhou internet em relação ao ano anterior em que apareceu no Censo
    CASE WHEN in_internet = 1
          AND LAG(in_internet) OVER (PARTITION BY co_entidade ORDER BY ano) = 0
         THEN 1 ELSE 0 END                     AS in_ganhou_internet
FROM base b;
