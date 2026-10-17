"""Gera as imagens estáticas usadas no README."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config import DOCS, OUT  # noqa: E402

INK, MUTED, COBALT, AMBER, GRID, NEUTRAL = "#0C1E46", "#4B5B7E", "#1F4FD8", "#C27C0E", "#E3E9F4", "#A9B4CB"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 13,
                     "axes.titlecolor": INK, "axes.titlelocation": "left"})
m = json.loads((OUT / "metrics.json").read_text())
img = DOCS / "img"; img.mkdir(parents=True, exist_ok=True)

h = pd.DataFrame(m["history"]); h["month"] = pd.to_datetime(h.month); h = h[h.month >= "2010-01-01"]
f = pd.DataFrame(m["forecast"]); f["month"] = pd.to_datetime(f.month)
fig, ax = plt.subplots(figsize=(9, 4), dpi=150)
ax.fill_between(f.month, f.lo95 / 1e3, f.hi95 / 1e3, color=AMBER, alpha=0.12, lw=0, label="IC 95%")
ax.fill_between(f.month, f.lo80 / 1e3, f.hi80 / 1e3, color=AMBER, alpha=0.25, lw=0, label="IC 80%")
ax.plot(h.month, h.sales / 1e3, color=COBALT, lw=1.8, label="Real")
ax.plot(h.month, h.trend / 1e3, color=NEUTRAL, lw=1.6, ls=":", label="Tendência")
ax.plot(f.month, f.forecast / 1e3, color=AMBER, lw=1.8, marker="o", ms=3, label="Previsão")
ax.set_ylabel("US$ bilhões / mês"); ax.legend(frameon=False, ncol=5, loc="upper left", fontsize=9)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("Vendas do varejo dos EUA: histórico e previsão de 12 meses")
fig.tight_layout(); fig.savefig(img / "previsao.png"); plt.close(fig)

MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
p = m["month_profile"]
v = [r["index_vs_year_avg"] - 100 for r in p]
fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
b = ax.bar(MES, v, color=[AMBER if abs(x) >= 10 else COBALT for x in v], width=0.6)
ax.bar_label(b, labels=[f"{x:+.1f}%".replace(".", ",") for x in v], padding=3, color=INK, fontsize=9)
ax.axhline(0, color=MUTED, lw=1); ax.set_ylim(-17, 24); ax.grid(axis="x", visible=False)
ax.set_ylabel("Diferença p/ média do ano"); ax.set_title("Perfil sazonal das vendas")
fig.tight_layout(); fig.savefig(img / "sazonalidade.png"); plt.close(fig)
bt = pd.DataFrame(m["backtest"]["detail"]); bt["ano"] = bt.origin.str[:4].astype(int) + 1
estilo = {"Sazonal ingênuo (base)": (NEUTRAL, "--", "s", 0), "Holt-Winters (ETS)": (COBALT, "-", "o", 0.18),
          "SARIMA": (AMBER, "-", "D", -0.18)}
fig, ax = plt.subplots(figsize=(9, 3.8), dpi=150)
for nome, (cor, ls, mk, dy) in estilo.items():
    g = bt[bt.model == nome]
    ax.plot(g.ano, g.mape, color=cor, ls=ls, lw=2, marker=mk, ms=7, label=nome)
    ax.text(g.ano.iloc[-1] + 0.12, g.mape.iloc[-1] + dy, nome.split(" (")[0], va="center", color=INK, fontsize=9)
ax.set_xticks(bt.ano.unique()); ax.set_xticklabels([f"jun/{a-1}–mai/{a}" for a in bt.ano.unique()], fontsize=9)
ax.set_xlim(bt.ano.min() - 0.3, bt.ano.max() + 1.1); ax.set_ylim(0, 7.2)
ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0f}%"); ax.set_ylabel("MAPE (12 meses)")
ax.legend(frameon=False, ncol=3, loc="upper right", fontsize=9)
ax.set_title("Backtest: erro de cada modelo em 5 anos que ele não viu")
fig.tight_layout(); fig.savefig(img / "backtest.png"); plt.close(fig)

y = [r for r in m["yearly"] if r["yoy_pct"] == r["yoy_pct"]]
fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
b = ax.bar([str(r["year"]) for r in y], [r["yoy_pct"] for r in y], color=[AMBER if r["yoy_pct"] < 0 else COBALT for r in y], width=0.65)
ax.axhline(0, color=MUTED, lw=1); ax.axhline(m["cagr_full_years_pct"], color=NEUTRAL, lw=1.2, ls="--")
ax.text(len(y) - 0.4, m["cagr_full_years_pct"] + 0.4, f'média {m["cagr_full_years_pct"]:.1f}'.replace(".", ",") + "% a.a.",
        ha="right", color=MUTED, fontsize=9)
ax.bar_label(b, labels=[f'{r["yoy_pct"]:+.1f}'.replace(".", ",") if r["yoy_pct"] < 0 else "" for r in y], padding=3, color=INK, fontsize=9)
ax.tick_params(axis="x", labelrotation=90, labelsize=9); ax.set_ylim(-9.5, 10); ax.grid(axis="x", visible=False)
ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0f}%"); ax.set_ylabel("Crescimento anual")
ax.set_title("Crescimento das vendas ano a ano")
fig.tight_layout(); fig.savefig(img / "crescimento_anual.png"); plt.close(fig)
print("OK: docs/img/previsao.png, docs/img/sazonalidade.png, docs/img/backtest.png, docs/img/crescimento_anual.png")
