"""
Pipeline ELT do projeto "Infraestrutura tecnológica das escolas".

Arquitetura medalhão (Data Lake local em Parquet + Data Warehouse em DuckDB):
  raw     -> zips oficiais do INEP (ou a amostra sintética)
  bronze  -> CSV carregado como veio, com o arquivo de origem e a ordem de carga
  silver  -> dados tipados, filtrados pela UF e sem duplicidade (SQL)
  gold    -> modelo estrela (dimensões + fato) e data marts (SQL)

O mesmo SQL roda no Databricks (pasta databricks/).

Uso:
  python pipeline/run_pipeline.py                  # baixa os anos do INEP e processa
  python pipeline/run_pipeline.py --anos 2019-2024 --uf MG
  python pipeline/run_pipeline.py --amostra        # usa a amostra sintética (teste)
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
RAW, BRONZE, SILVER, GOLD = (DADOS / p for p in ("raw", "bronze", "silver", "gold"))
SQL = RAIZ / "sql"
DW = DADOS / "dw_infra_tec.duckdb"
URL_INEP = "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ano}.zip"

COLUNAS_NECESSARIAS = [
    "NU_ANO_CENSO", "CO_ENTIDADE", "NO_ENTIDADE", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO",
    "NO_MESORREGIAO", "NO_MICRORREGIAO", "TP_DEPENDENCIA", "TP_LOCALIZACAO", "TP_SITUACAO_FUNCIONAMENTO",
    "IN_INTERNET", "IN_BANDA_LARGA", "IN_INTERNET_ALUNOS", "IN_INTERNET_ADMINISTRATIVO",
    "IN_INTERNET_APRENDIZAGEM", "IN_INTERNET_COMUNIDADE", "IN_ACESSO_INTERNET_COMPUTADOR",
    "IN_ACES_INTERNET_DISP_PESSOAIS", "IN_LABORATORIO_INFORMATICA", "IN_DESKTOP_ALUNO",
    "IN_COMP_PORTATIL_ALUNO", "IN_TABLET_ALUNO", "TP_REDE_LOCAL", "QT_DESKTOP_ALUNO",
    "QT_COMP_PORTATIL_ALUNO", "QT_TABLET_ALUNO", "QT_EQUIP_MULTIMIDIA", "QT_MAT_BAS",
]

TABELAS_GOLD = ["dim_ano", "dim_rede", "dim_localizacao", "dim_municipio", "dim_escola",
                "fato_infraestrutura", "mart_rede_ano", "mart_municipio_ano"]


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


# ---------------------------------------------------------------- 1. RAW
def obter_zips(anos: list[int], amostra: bool) -> list[Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    if amostra:
        sys.path.insert(0, str(Path(__file__).parent))
        import gerar_amostra
        gerar_amostra.main()
        return sorted(RAW.glob("AMOSTRA_*.zip"))

    zips = []
    for ano in anos:
        destino = RAW / f"microdados_censo_escolar_{ano}.zip"
        if not destino.exists():
            url = URL_INEP.format(ano=ano)
            log(f"baixando {url}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=300) as r, open(destino, "wb") as f:
                    shutil.copyfileobj(r, f)
            except Exception as e:  # noqa: BLE001
                destino.unlink(missing_ok=True)
                log(f"  não consegui baixar {ano} ({e}). Baixe manualmente em "
                    f"https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar "
                    f"e salve como {destino.name} em dados/raw/")
                continue
        zips.append(destino)
    if not zips:
        sys.exit("Nenhum zip do Censo disponível em dados/raw/. Rode com --amostra para testar.")
    return zips


def extrair_csv(zip_path: Path) -> Path:
    """Extrai o CSV de escolas (microdados_ed_basica_AAAA.csv) do zip do INEP."""
    pasta = RAW / "extraido"
    pasta.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        candidatos = [n for n in z.namelist() if n.lower().endswith(".csv") and "ed_basica" in n.lower()]
        if not candidatos:
            candidatos = sorted((i for i in z.infolist() if i.filename.lower().endswith(".csv")),
                                key=lambda i: i.file_size, reverse=True)
            candidatos = [candidatos[0].filename] if candidatos else []
        if not candidatos:
            raise RuntimeError(f"CSV de escolas não encontrado em {zip_path.name}")
        nome = candidatos[0]
        destino = pasta / Path(nome).name
        if not destino.exists():
            with z.open(nome) as src, open(destino, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return destino


# ---------------------------------------------------------------- 2. BRONZE
def carregar_bronze(con: duckdb.DuckDBPyConnection, csvs: list[Path]) -> None:
    BRONZE.mkdir(parents=True, exist_ok=True)
    con.execute("DROP TABLE IF EXISTS bronze_censo_escolar")
    for i, csv_path in enumerate(csvs):
        ano = re.search(r"(20\d\d)", csv_path.name).group(1)
        log(f"bronze: lendo {csv_path.name}")
        rel = f"""
            SELECT *, '{csv_path.name}' AS _arquivo_origem, {i} AS _ordem_carga
            FROM read_csv('{csv_path.as_posix()}', delim=';', header=true, all_varchar=true,
                          encoding='latin-1', ignore_errors=true)
        """
        parquet = BRONZE / f"censo_escolar_{ano}.parquet"
        con.execute(f"COPY ({rel}) TO '{parquet.as_posix()}' (FORMAT PARQUET)")
        if i == 0:
            con.execute(f"CREATE TABLE bronze_censo_escolar AS SELECT * FROM read_parquet('{parquet.as_posix()}')")
        else:
            con.execute(f"INSERT INTO bronze_censo_escolar BY NAME SELECT * FROM read_parquet('{parquet.as_posix()}')"
                        if _colunas_iguais(con, parquet) else
                        f"""CREATE OR REPLACE TABLE bronze_censo_escolar AS
                            SELECT * FROM bronze_censo_escolar
                            UNION ALL BY NAME SELECT * FROM read_parquet('{parquet.as_posix()}')""")
    # garante que toda coluna usada exista (anos antigos podem não ter algumas)
    existentes = {r[0].upper() for r in con.execute("DESCRIBE bronze_censo_escolar").fetchall()}
    for c in COLUNAS_NECESSARIAS:
        if c not in existentes:
            log(f"  coluna {c} ausente em todos os anos: criada como nula")
            con.execute(f"ALTER TABLE bronze_censo_escolar ADD COLUMN {c} VARCHAR")
    n = con.execute("SELECT COUNT(*) FROM bronze_censo_escolar").fetchone()[0]
    log(f"bronze: {n:,} linhas".replace(",", "."))


def _colunas_iguais(con, parquet: Path) -> bool:
    a = [r[0] for r in con.execute("DESCRIBE bronze_censo_escolar").fetchall()]
    b = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{parquet.as_posix()}')").fetchall()]
    return set(a) == set(b)


# ---------------------------------------------------------------- 3/4. SILVER e GOLD
def rodar_sql(con, arquivo: str, uf: str) -> None:
    texto = (SQL / arquivo).read_text(encoding="utf-8").replace("{{UF}}", uf)
    log(f"executando sql/{arquivo}")
    con.execute(texto)


def exportar(con, eh_amostra: bool, uf: str) -> None:
    SILVER.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    (GOLD / "analises").mkdir(exist_ok=True)
    con.execute(f"COPY silver_escolas TO '{(SILVER / 'silver_escolas.parquet').as_posix()}' (FORMAT PARQUET)")
    for t in TABELAS_GOLD:
        con.execute(f"COPY {t} TO '{(GOLD / (t + '.csv')).as_posix()}' (HEADER, DELIMITER ',')")
        con.execute(f"COPY {t} TO '{(GOLD / (t + '.parquet')).as_posix()}' (FORMAT PARQUET)")

    anos = [r[0] for r in con.execute("SELECT ano FROM dim_ano ORDER BY ano").fetchall()]
    fonte = ("Dados fictícios para demonstração, no formato dos microdados do Censo Escolar (INEP)"
             if eh_amostra else "INEP, Censo Escolar da Educação Básica (microdados)")
    con.execute("CREATE OR REPLACE TABLE metadados AS SELECT ? AS fonte, ? AS uf, ? AS anos, ? AS eh_amostra",
                [fonte, uf, f"{anos[0]} a {anos[-1]}", int(eh_amostra)])
    con.execute(f"COPY metadados TO '{(GOLD / 'metadados.csv').as_posix()}' (HEADER, DELIMITER ',')")

    # consultas analíticas: cada bloco "-- @nome:" vira um CSV
    texto = (SQL / "05_consultas_analiticas.sql").read_text(encoding="utf-8")
    for bloco in texto.split("-- @nome:")[1:]:
        nome, corpo = bloco.split("\n", 1)
        consulta = corpo.strip().rstrip(";")
        con.execute(f"COPY ({consulta}) TO '{(GOLD / 'analises' / (nome.strip() + '.csv')).as_posix()}' (HEADER, DELIMITER ',')")
        log(f"análise salva: {nome.strip()}.csv")


def configurar_power_bi() -> None:
    """Grava o caminho absoluto da pasta gold no parâmetro PastaDados do projeto Power BI."""
    expr = RAIZ / "InfraTecEscolas.SemanticModel" / "definition" / "expressions.tmdl"
    if not expr.exists():
        return
    caminho = str(GOLD.resolve()) + ("\\" if sys.platform.startswith("win") else "/")
    caminho_m = caminho.replace('"', '""')
    texto = expr.read_text(encoding="utf-8")
    novo = re.sub(r'expression PastaDados = ".*?" meta',
                  lambda _: f'expression PastaDados = "{caminho_m}" meta', texto, count=1)
    expr.write_text(novo, encoding="utf-8")
    log(f"Power BI: parâmetro PastaDados = {caminho}")


def atualizar_excel() -> None:
    try:
        sys.path.insert(0, str(RAIZ / "excel"))
        import atualizar_excel as ax
        ax.atualizar()
    except Exception as e:  # noqa: BLE001
        log(f"Excel não atualizado ({e})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", default=f"2019-{dt.date.today().year - 1}",
                    help="intervalo, ex.: 2019-2024")
    ap.add_argument("--uf", default="MG")
    ap.add_argument("--amostra", action="store_true", help="usa a amostra sintética")
    args = ap.parse_args()
    ini, fim = (int(x) for x in args.anos.split("-"))
    anos = list(range(ini, fim + 1))

    zips = obter_zips(anos, args.amostra)
    csvs = [extrair_csv(z) for z in zips]

    DW.unlink(missing_ok=True)
    con = duckdb.connect(str(DW))
    carregar_bronze(con, csvs)
    rodar_sql(con, "01_silver_escolas.sql", args.uf.upper())
    rodar_sql(con, "02_gold_dimensoes.sql", args.uf.upper())
    rodar_sql(con, "03_gold_fato.sql", args.uf.upper())
    rodar_sql(con, "04_gold_marts.sql", args.uf.upper())
    exportar(con, args.amostra, args.uf.upper())
    resumo = con.execute("""SELECT COUNT(DISTINCT co_entidade), COUNT(*), MIN(ano), MAX(ano)
                            FROM fato_infraestrutura""").fetchone()
    con.close()
    log(f"gold: {resumo[0]} escolas, {resumo[1]} linhas escola-ano, {resumo[2]}-{resumo[3]}")
    configurar_power_bi()
    atualizar_excel()
    log("pronto. Abra InfraTecEscolas.pbip e clique em Atualizar.")


if __name__ == "__main__":
    main()
