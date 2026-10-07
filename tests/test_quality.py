"""Testes de qualidade de dados e de integridade da previsão."""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import DB, HORIZON  # noqa: E402


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def metrics():
    return json.loads((ROOT / "outputs" / "metrics.json").read_text())


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_serie_sem_meses_faltantes(con):
    assert scalar(con, "select count(*) from stg_monthly_sales where sales is null") == 0


def test_um_registro_por_mes(con):
    assert scalar(con, "select count(*) - count(distinct month) from stg_monthly_sales") == 0


def test_vendas_positivas(con):
    assert scalar(con, "select count(*) from stg_monthly_sales where sales <= 0") == 0


def test_perfil_sazonal_soma_1200(con):
    assert abs(scalar(con, "select sum(index_vs_year_avg) from mart_month_profile") - 1200) < 1


def test_backtest_sem_vazamento(metrics):
    end = pd.Timestamp(metrics["series"]["end"])
    for o in metrics["backtest"]["origins"]:
        assert pd.Timestamp(o) + pd.DateOffset(months=HORIZON) <= end


def test_previsao_tem_horizonte_e_intervalos_ordenados(metrics):
    fc = metrics["forecast"]
    assert len(fc) == HORIZON
    for r in fc:
        assert r["lo95"] <= r["lo80"] <= r["forecast"] <= r["hi80"] <= r["hi95"]


def test_melhor_modelo_supera_a_base(metrics):
    s = {r["model"]: r["mape"] for r in metrics["backtest"]["summary"]}
    assert min(s.values()) < s["Sazonal ingênuo (base)"]
