"""
Gera uma AMOSTRA SINTÉTICA no mesmo formato dos microdados do Censo Escolar
(CSV separado por ';', codificação latin-1, mesmos nomes de coluna do INEP).

Serve só para testar o pipeline e abrir o Power BI antes de baixar os dados
reais. Os números NÃO são reais e o relatório avisa isso na tela enquanto a
fonte for esta amostra.

Uso:  python pipeline/gerar_amostra.py
"""
import csv
import io
import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "dados" / "raw"
ANOS = list(range(2019, 2025))
random.seed(42)

MESOS = ["Metropolitana de BH", "Sul/Sudoeste", "Triângulo", "Zona da Mata", "Norte", "Vale do Rio Doce"]
MUNICIPIOS = [(3199000 + i, f"Município Exemplo {i:02d}", MESOS[i % len(MESOS)]) for i in range(1, 49)]

# probabilidade-base por rede (1 Federal, 2 Estadual, 3 Municipal, 4 Privada) no 1º ano
# e ganho anual, para gerar tendências plausíveis
PERFIL = {
    1: dict(internet=.97, banda=.85, alunos=.80, aprend=.75, lab=.80, comp=.85, rede=.90, ganho=.015),
    2: dict(internet=.88, banda=.62, alunos=.42, aprend=.48, lab=.46, comp=.52, rede=.70, ganho=.040),
    3: dict(internet=.70, banda=.45, alunos=.22, aprend=.30, lab=.28, comp=.33, rede=.50, ganho=.055),
    4: dict(internet=.96, banda=.82, alunos=.55, aprend=.70, lab=.42, comp=.60, rede=.88, ganho=.020),
}

COLUNAS = [
    "NU_ANO_CENSO", "NO_REGIAO", "CO_REGIAO", "NO_UF", "SG_UF", "CO_UF", "NO_MUNICIPIO", "CO_MUNICIPIO",
    "NO_MESORREGIAO", "CO_MESORREGIAO", "NO_MICRORREGIAO", "CO_MICRORREGIAO", "NO_ENTIDADE", "CO_ENTIDADE",
    "TP_DEPENDENCIA", "TP_LOCALIZACAO", "TP_SITUACAO_FUNCIONAMENTO", "IN_LABORATORIO_INFORMATICA",
    "IN_DESKTOP_ALUNO", "QT_DESKTOP_ALUNO", "IN_COMP_PORTATIL_ALUNO", "QT_COMP_PORTATIL_ALUNO",
    "IN_TABLET_ALUNO", "QT_TABLET_ALUNO", "IN_INTERNET", "IN_INTERNET_ALUNOS", "IN_INTERNET_ADMINISTRATIVO",
    "IN_INTERNET_APRENDIZAGEM", "IN_INTERNET_COMUNIDADE", "IN_ACESSO_INTERNET_COMPUTADOR",
    "IN_ACES_INTERNET_DISP_PESSOAIS", "TP_REDE_LOCAL", "IN_BANDA_LARGA", "QT_EQUIP_MULTIMIDIA", "QT_MAT_BAS",
]


def escolas_base():
    escolas = []
    cod = 31000000
    for co_mun, nome, meso in MUNICIPIOS:
        n = random.randint(12, 60)
        for _ in range(n):
            cod += 1
            rede = random.choices([3, 2, 4, 1], weights=[52, 30, 17, 1])[0]
            loc = 2 if (rede in (2, 3) and random.random() < .28) else 1
            escolas.append(dict(cod=cod, mun=co_mun, nome_mun=nome, meso=meso, rede=rede, loc=loc,
                                nome=f"Escola {'Municipal' if rede == 3 else 'Estadual' if rede == 2 else 'Federal' if rede == 1 else 'Particular'} {cod % 10000:04d}",
                                mat=max(30, int(random.gauss(380 if rede != 4 else 260, 160))),
                                sorte=random.uniform(-.12, .12)))
    return escolas


def b(p):
    return 1 if random.random() < max(0.0, min(1.0, p)) else 0


def linhas_do_ano(ano, escolas, estado):
    t = ano - ANOS[0]
    for e in escolas:
        if random.random() < .015 and ano > ANOS[0]:
            continue  # escola que não respondeu naquele ano
        p = PERFIL[e["rede"]]
        rural = -.18 if e["loc"] == 2 else 0
        g = p["ganho"] * t + e["sorte"] + rural
        st = estado.setdefault(e["cod"], {})
        # Internet raramente é perdida depois de conquistada
        internet = 1 if st.get("internet") else b(p["internet"] + g)
        st["internet"] = internet
        banda = internet * b(p["banda"] + 1.3 * g)
        alunos = internet * b(p["alunos"] + 1.4 * g)
        aprend = internet * b(p["aprend"] + 1.2 * g)
        lab = b(p["lab"] - 0.012 * t + e["sorte"] + rural)      # laboratórios em leve queda
        portateis = b(p["comp"] - .25 + 1.6 * g)                 # notebooks/Chromebooks em alta
        tablets = b(.08 + .5 * g if e["rede"] != 1 else .2)
        desktop = lab or b(p["comp"] - .2 + g * .5)
        qd = random.randint(8, 35) if desktop else 0
        qp = random.randint(10, 45) if portateis else 0
        qt = random.randint(5, 30) if tablets else 0
        rede_local = 0 if not internet else random.choices([1, 2, 3], weights=[2, 5 + 3 * t, 3])[0] if b(p["rede"] + g) else 0
        yield {
            "NU_ANO_CENSO": ano, "NO_REGIAO": "Sudeste", "CO_REGIAO": 3, "NO_UF": "Minas Gerais", "SG_UF": "MG",
            "CO_UF": 31, "NO_MUNICIPIO": e["nome_mun"], "CO_MUNICIPIO": e["mun"], "NO_MESORREGIAO": e["meso"],
            "CO_MESORREGIAO": 3100 + MESOS.index(e["meso"]), "NO_MICRORREGIAO": e["meso"],
            "CO_MICRORREGIAO": 31000 + MESOS.index(e["meso"]), "NO_ENTIDADE": e["nome"].upper(),
            "CO_ENTIDADE": e["cod"], "TP_DEPENDENCIA": e["rede"], "TP_LOCALIZACAO": e["loc"],
            "TP_SITUACAO_FUNCIONAMENTO": 1 if random.random() > .01 else 2,
            "IN_LABORATORIO_INFORMATICA": lab, "IN_DESKTOP_ALUNO": int(qd > 0), "QT_DESKTOP_ALUNO": qd or "",
            "IN_COMP_PORTATIL_ALUNO": int(qp > 0), "QT_COMP_PORTATIL_ALUNO": qp or "",
            "IN_TABLET_ALUNO": int(qt > 0), "QT_TABLET_ALUNO": qt or "", "IN_INTERNET": internet,
            "IN_INTERNET_ALUNOS": alunos, "IN_INTERNET_ADMINISTRATIVO": internet,
            "IN_INTERNET_APRENDIZAGEM": aprend, "IN_INTERNET_COMUNIDADE": internet * b(.1),
            "IN_ACESSO_INTERNET_COMPUTADOR": internet * int(qd + qp > 0),
            "IN_ACES_INTERNET_DISP_PESSOAIS": alunos * b(.5 + g),
            "TP_REDE_LOCAL": rede_local, "IN_BANDA_LARGA": banda,
            "QT_EQUIP_MULTIMIDIA": random.randint(0, 6), "QT_MAT_BAS": max(10, int(e["mat"] * random.uniform(.92, 1.06))),
        }
    # algumas linhas de outra UF, para testar o filtro da camada silver
    for i in range(30):
        yield {**{c: "" for c in COLUNAS}, "NU_ANO_CENSO": ano, "SG_UF": "SP", "CO_ENTIDADE": 35000000 + i,
               "TP_DEPENDENCIA": 3, "TP_SITUACAO_FUNCIONAMENTO": 1, "IN_INTERNET": 1, "CO_MUNICIPIO": 3550308,
               "NO_MUNICIPIO": "São Paulo", "NO_ENTIDADE": f"ESCOLA SP {i}"}


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    escolas = escolas_base()
    estado = {}
    for ano in ANOS:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUNAS, delimiter=";", lineterminator="\n")
        w.writeheader()
        for linha in linhas_do_ano(ano, escolas, estado):
            w.writerow(linha)
        nome_zip = DESTINO / f"AMOSTRA_microdados_censo_escolar_{ano}.zip"
        with zipfile.ZipFile(nome_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"microdados_censo_escolar_{ano}/dados/microdados_ed_basica_{ano}.csv",
                       buf.getvalue().encode("latin-1"))
        print(f"amostra gerada: {nome_zip.name}")


if __name__ == "__main__":
    main()
