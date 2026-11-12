# Databricks notebook source
# MAGIC %md
# MAGIC # Infraestrutura tecnológica das escolas: pipeline medalhão no Databricks
# MAGIC
# MAGIC **Pergunta:** como a infraestrutura tecnológica mudou ao longo dos anos, comparando rede municipal, estadual e privada?
# MAGIC
# MAGIC Este notebook faz no Databricks o mesmo ELT do pipeline local (`pipeline/run_pipeline.py`):
# MAGIC
# MAGIC | Camada | O que tem | Formato |
# MAGIC |---|---|---|
# MAGIC | raw | zips oficiais do INEP num Volume do Unity Catalog | zip |
# MAGIC | bronze | CSV como veio + arquivo de origem e ordem de carga | Delta |
# MAGIC | silver | tipado, filtrado pela UF, sem duplicidade | Delta |
# MAGIC | gold | modelo estrela (dimensões + fato) e data marts | Delta |
# MAGIC
# MAGIC As transformações silver e gold usam **os mesmos arquivos SQL** da pasta `sql/` (ANSI, compatíveis com DuckDB e Spark SQL).
# MAGIC
# MAGIC **Como rodar (funciona no Databricks Free Edition):**
# MAGIC 1. Importe o repositório como *Git folder* (Workspace → Create → Git folder).
# MAGIC 2. Crie um Volume e envie os zips do Censo (`microdados_censo_escolar_AAAA.zip`) para ele.
# MAGIC 3. Ajuste os widgets abaixo e rode todas as células.

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace", "Catálogo")
dbutils.widgets.text("schema", "infra_tec_escolas", "Schema")
dbutils.widgets.text("volume", "raw", "Volume com os zips")
dbutils.widgets.text("uf", "MG", "UF")

catalogo = dbutils.widgets.get("catalogo")
schema = dbutils.widgets.get("schema")
volume = dbutils.widgets.get("volume")
uf = dbutils.widgets.get("uf").upper()

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalogo}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalogo}.{schema}.{volume}")
spark.sql(f"USE {catalogo}.{schema}")
caminho_volume = f"/Volumes/{catalogo}/{schema}/{volume}"
print("Envie os zips para:", caminho_volume)

# COMMAND ----------

# MAGIC %md ## 1. Raw → extrair o CSV de escolas de cada zip

# COMMAND ----------

import os
import re
import shutil
import zipfile

pasta_extraida = f"{caminho_volume}/extraido"
os.makedirs(pasta_extraida, exist_ok=True)

csvs = []
for nome in sorted(os.listdir(caminho_volume)):
    if not nome.lower().endswith(".zip"):
        continue
    with zipfile.ZipFile(f"{caminho_volume}/{nome}") as z:
        alvo = [n for n in z.namelist() if n.lower().endswith(".csv") and "ed_basica" in n.lower()]
        if not alvo:
            print("sem CSV de escolas:", nome)
            continue
        destino = f"{pasta_extraida}/{os.path.basename(alvo[0])}"
        if not os.path.exists(destino):
            with z.open(alvo[0]) as src, open(destino, "wb") as dst:
                shutil.copyfileobj(src, dst)
        csvs.append(destino)
print(csvs)

# COMMAND ----------

# MAGIC %md ## 2. Bronze → Delta com o dado bruto

# COMMAND ----------

from functools import reduce
from pyspark.sql import functions as F

COLUNAS_NECESSARIAS = [
    "NU_ANO_CENSO", "CO_ENTIDADE", "NO_ENTIDADE", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO",
    "NO_MESORREGIAO", "NO_MICRORREGIAO", "TP_DEPENDENCIA", "TP_LOCALIZACAO", "TP_SITUACAO_FUNCIONAMENTO",
    "IN_INTERNET", "IN_BANDA_LARGA", "IN_INTERNET_ALUNOS", "IN_INTERNET_ADMINISTRATIVO",
    "IN_INTERNET_APRENDIZAGEM", "IN_INTERNET_COMUNIDADE", "IN_ACESSO_INTERNET_COMPUTADOR",
    "IN_ACES_INTERNET_DISP_PESSOAIS", "IN_LABORATORIO_INFORMATICA", "IN_DESKTOP_ALUNO",
    "IN_COMP_PORTATIL_ALUNO", "IN_TABLET_ALUNO", "TP_REDE_LOCAL", "QT_DESKTOP_ALUNO",
    "QT_COMP_PORTATIL_ALUNO", "QT_TABLET_ALUNO", "QT_EQUIP_MULTIMIDIA", "QT_MAT_BAS",
]

frames = []
for ordem, caminho in enumerate(csvs):
    df = (spark.read
          .option("header", True)
          .option("sep", ";")
          .option("encoding", "ISO-8859-1")
          .csv(caminho)
          .withColumn("_arquivo_origem", F.lit(os.path.basename(caminho)))
          .withColumn("_ordem_carga", F.lit(ordem)))
    frames.append(df)

bronze = reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), frames)
for c in COLUNAS_NECESSARIAS:
    if c not in bronze.columns:
        bronze = bronze.withColumn(c, F.lit(None).cast("string"))

(bronze.write.mode("overwrite").option("overwriteSchema", True)
       .saveAsTable("bronze_censo_escolar"))
display(spark.sql("SELECT NU_ANO_CENSO AS ano, COUNT(*) AS linhas FROM bronze_censo_escolar GROUP BY 1 ORDER BY 1"))

# COMMAND ----------

# MAGIC %md ## 3. Silver e Gold → os mesmos arquivos SQL do projeto

# COMMAND ----------

pasta_sql = os.path.abspath(os.path.join(os.getcwd(), "..", "sql"))

def rodar_sql(arquivo: str) -> None:
    texto = open(os.path.join(pasta_sql, arquivo), encoding="utf-8").read().replace("{{UF}}", uf)
    for comando in re.split(r";\s*\n", texto):
        linhas = [l for l in comando.splitlines() if l.strip() and not l.strip().startswith("--")]
        if linhas:
            spark.sql(comando.strip().rstrip(";"))
    print("ok:", arquivo)

for arquivo in ["01_silver_escolas.sql", "02_gold_dimensoes.sql", "03_gold_fato.sql", "04_gold_marts.sql"]:
    rodar_sql(arquivo)

# COMMAND ----------

# MAGIC %md ## 4. Resultado: índice médio por rede e ano

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT ano, rede, escolas, ROUND(indice_infra_tec, 1) AS indice, ROUND(100 * pct_internet, 1) AS pct_internet,
# MAGIC        ROUND(delta_indice_ano_anterior, 1) AS delta_ano_anterior, posicao_no_ano
# MAGIC FROM mart_rede_ano
# MAGIC ORDER BY ano, ordem_rede

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Conectar o Power BI
# MAGIC No Power BI Desktop: **Obter dados → Azure Databricks**, informe o *Server hostname* e o *HTTP path* do SQL Warehouse
# MAGIC e selecione as tabelas `dim_*` e `fato_infraestrutura` deste schema. O modelo e as medidas DAX são os mesmos do projeto local.
