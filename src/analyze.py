"""Decomposição, backtest de modelos de previsão e previsão final com incerteza."""
import json
import warnings

import duckdb
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX

from config import BACKTEST_ORIGINS, DB, HORIZON, OUT

warnings.filterwarnings("ignore")


def seasonal_naive(train, h):
    last = train.iloc[-12:].to_numpy()
    return np.array([last[i % 12] for i in range(h)]), None


def ets(train, h):
    fit = ExponentialSmoothing(np.log(train), trend="add", damped_trend=True, seasonal="add", seasonal_periods=12).fit()
    return np.exp(fit.forecast(h).to_numpy()), None


def sarima(train, h, alpha=0.2):
    fit = SARIMAX(np.log(train), order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)
    fc = fit.get_forecast(h)
    ci = np.exp(fc.conf_int(alpha=alpha).to_numpy())
    return np.exp(fc.predicted_mean.to_numpy()), ci


MODELS = {"Sazonal ingênuo (base)": seasonal_naive, "Holt-Winters (ETS)": ets, "SARIMA": sarima}


def mape(a, f):
    return float(np.mean(np.abs((a - f) / a)) * 100)


def mase(a, f, train):
    scale = np.mean(np.abs(train.to_numpy()[12:] - train.to_numpy()[:-12]))
    return float(np.mean(np.abs(a - f)) / scale)


def main():
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    s = con.execute("select month, sales from stg_monthly_sales order by month").df().set_index("month")["sales"]
    s.index = pd.DatetimeIndex(s.index, freq="MS")
    yearly = con.execute("select * from mart_yearly").df()
    profile = con.execute("select * from mart_month_profile").df()

    # Decomposição STL (em log, sazonalidade multiplicativa).
    stl = STL(np.log(s), period=12, robust=True).fit()
    trend = np.exp(stl.trend)
    peak_2008 = trend["2007-01":"2009-12"].idxmax(); trough = trend[peak_2008:"2010-12"].idxmin()
    recovered = trend[trough:][trend[trough:] >= trend[peak_2008]].index.min()

    # Backtest com origem móvel: treina até a origem, prevê os 12 meses seguintes.
    origins = [s.index[-HORIZON - 12 * k - 1] for k in range(BACKTEST_ORIGINS)][::-1]
    rows, coverage = [], []
    for o in origins:
        train = s[:o]; test = s[o + pd.offsets.MonthBegin(1):][:HORIZON]
        assert train.index.max() < test.index.min()
        for name, fn in MODELS.items():
            f, ci = fn(train, len(test))
            rows.append({"origin": str(o.date()), "model": name, "mape": mape(test.to_numpy(), f),
                         "mase": mase(test.to_numpy(), f, train)})
            if ci is not None:
                coverage.append(float(np.mean((test.to_numpy() >= ci[:, 0]) & (test.to_numpy() <= ci[:, 1]))))
    bt = pd.DataFrame(rows)
    summary = bt.groupby("model").agg(mape=("mape", "mean"), mape_max=("mape", "max"), mase=("mase", "mean")).round(3).reset_index().sort_values("mape")
    best = summary.iloc[0]["model"]

    # Previsão final: SARIMA (com intervalos) ajustado em toda a série.
    fit = SARIMAX(np.log(s), order=(1, 1, 1), seasonal_order=(0, 1, 1, 12)).fit(disp=False)
    fc = fit.get_forecast(HORIZON)
    idx = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZON, freq="MS")
    mean = np.exp(fc.predicted_mean.to_numpy())
    ci80 = np.exp(fc.conf_int(alpha=0.2).to_numpy()); ci95 = np.exp(fc.conf_int(alpha=0.05).to_numpy())
    forecast = pd.DataFrame({"month": idx.date.astype(str), "forecast": mean.round(0), "lo80": ci80[:, 0].round(0),
                             "hi80": ci80[:, 1].round(0), "lo95": ci95[:, 0].round(0), "hi95": ci95[:, 1].round(0)})
    same_months_last_year = s[-12:].sum()

    metrics = {
        "series": {"start": str(s.index.min().date()), "end": str(s.index.max().date()), "months": int(len(s)),
                   "missing_months": int(s.isna().sum()), "first": float(s.iloc[0]), "last": float(s.iloc[-1])},
        "cagr_full_years_pct": round(100 * ((yearly.sales.iloc[-1] / yearly.sales.iloc[0]) ** (1 / (len(yearly) - 1)) - 1), 2),
        "yearly": yearly.to_dict(orient="records"),
        "month_profile": profile.to_dict(orient="records"),
        "shock_2008": {"trend_peak": str(peak_2008.date()), "trend_trough": str(trough.date()),
                       "drop_pct": round(100 * (trend[trough] / trend[peak_2008] - 1), 1),
                       "recovered_month": str(recovered.date()) if pd.notna(recovered) else None},
        "backtest": {"origins": [str(o.date()) for o in origins], "horizon": HORIZON,
                     "summary": summary.to_dict(orient="records"), "detail": bt.round(3).to_dict(orient="records"),
                     "best_model": best, "sarima_80_coverage_pct": round(100 * float(np.mean(coverage)), 1)},
        "forecast": forecast.to_dict(orient="records"),
        "forecast_total_next12": float(mean.sum().round(0)),
        "last12_actual_total": float(same_months_last_year),
        "forecast_growth_pct": round(100 * (mean.sum() / same_months_last_year - 1), 2),
        "history": [{"month": str(d.date()), "sales": float(v), "trend": float(round(trend[d], 0))} for d, v in s.items()],
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=float))
    forecast.to_csv(OUT / "forecast.csv", index=False); bt.to_csv(OUT / "backtest.csv", index=False)
    print(json.dumps({k: metrics[k] for k in ["series", "cagr_full_years_pct", "shock_2008", "forecast_total_next12", "last12_actual_total", "forecast_growth_pct"]}, indent=1))
    print(summary.to_string(index=False)); print("coverage80", metrics["backtest"]["sarima_80_coverage_pct"])
    print(bt.pivot(index="origin", columns="model", values="mape").round(2).to_string())
    print(profile.to_string(index=False)); print(yearly.tail(10).to_string(index=False)); print(forecast.to_string(index=False))


if __name__ == "__main__":
    main()
