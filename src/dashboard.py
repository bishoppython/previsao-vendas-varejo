"""Monta o dashboard a partir das métricas calculadas em analyze.py."""
import json

import plotly.graph_objects as go

from config import DOCS, OUT
from report import AMBER, COBALT, NEUTRAL, br, fig_html, kpi, render

m = json.loads((OUT / "metrics.json").read_text())
MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes_ano(iso):
    return f'{MES[int(iso[5:7]) - 1]}/{iso[:4]}'
B = 1e6  # milhões -> trilhões? (série em milhões de US$; exibimos em US$ bilhões)

hist = [h for h in m["history"] if h["month"] >= "2008-01-01"]
fc = m["forecast"]
f1 = go.Figure()
f1.add_trace(go.Scatter(x=[r["month"] for r in fc] + [r["month"] for r in fc][::-1],
                        y=[r["hi95"] / 1e3 for r in fc] + [r["lo95"] / 1e3 for r in fc][::-1],
                        fill="toself", fillcolor="rgba(194,124,14,0.12)", line=dict(width=0), hoverinfo="skip", name="IC 95%"))
f1.add_trace(go.Scatter(x=[r["month"] for r in fc] + [r["month"] for r in fc][::-1],
                        y=[r["hi80"] / 1e3 for r in fc] + [r["lo80"] / 1e3 for r in fc][::-1],
                        fill="toself", fillcolor="rgba(194,124,14,0.25)", line=dict(width=0), hoverinfo="skip", name="IC 80%"))
f1.add_trace(go.Scatter(x=[h["month"] for h in hist], y=[h["sales"] / 1e3 for h in hist], mode="lines",
                        line=dict(color=COBALT, width=2), name="Real",
                        hovertemplate="%{x|%b/%Y}<br>Real: US$ %{y:,.1f} bi<extra></extra>"))
f1.add_trace(go.Scatter(x=[h["month"] for h in hist], y=[h["trend"] / 1e3 for h in hist], mode="lines",
                        line=dict(color=NEUTRAL, width=2, dash="dot"), name="Tendência",
                        hovertemplate="%{x|%b/%Y}<br>Tendência: US$ %{y:,.1f} bi<extra></extra>"))
f1.add_trace(go.Scatter(x=[r["month"] for r in fc], y=[r["forecast"] / 1e3 for r in fc], mode="lines+markers",
                        line=dict(color=AMBER, width=2), marker=dict(size=6), name="Previsão",
                        customdata=[[r["lo80"] / 1e3, r["hi80"] / 1e3] for r in fc],
                        hovertemplate="%{x|%b/%Y}<br>Previsão: US$ %{y:,.1f} bi<br>IC 80%: %{customdata[0]:,.1f}–%{customdata[1]:,.1f}<extra></extra>"))
f1.update_layout(showlegend=True, legend=dict(orientation="h", y=1.08, x=0))
f1.update_yaxes(title="Vendas mensais (US$ bilhões)")

prof = m["month_profile"]
dev = [round(r["index_vs_year_avg"] - 100, 1) for r in prof]
f2 = go.Figure(go.Bar(x=MES, y=dev,
                      marker=dict(color=[AMBER if abs(v) >= 10 else COBALT for v in dev], cornerradius=4),
                      text=[("+" if v > 0 else "") + br(v) + "%" for v in dev], textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}: %{y:+.1f}% em relação à média do ano<extra></extra>"))
f2.update_yaxes(title="Diferença para a média do ano (%)", range=[-16, 23], zeroline=True, zerolinecolor=NEUTRAL)

bt = m["backtest"]["summary"]
f3 = go.Figure(go.Bar(x=[r["mape"] for r in bt][::-1], y=[r["model"] for r in bt][::-1], orientation="h",
                      marker=dict(color=[COBALT if r["model"] == m["backtest"]["best_model"] else NEUTRAL for r in bt][::-1], cornerradius=4),
                      text=[f'{br(r["mape"], 2)}%' for r in bt][::-1], textposition="outside", cliponaxis=False,
                      customdata=[[r["mape_max"], r["mase"]] for r in bt][::-1],
                      hovertemplate="%{y}<br>MAPE médio: %{x:.2f}%<br>Pior janela: %{customdata[0]:.2f}%<br>MASE: %{customdata[1]:.2f}<extra></extra>"))
f3.update_xaxes(title="Erro percentual médio (MAPE) em 12 meses", range=[0, 4.8])

yr = [r for r in m["yearly"] if r["yoy_pct"] is not None]
f4 = go.Figure(go.Bar(x=[str(r["year"]) for r in yr], y=[r["yoy_pct"] for r in yr],
                      marker=dict(color=[AMBER if r["yoy_pct"] < 0 else COBALT for r in yr], cornerradius=4),
                      hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
f4.update_yaxes(title="Crescimento anual (%)"); f4.update_xaxes(type="category", tickangle=-45)

s = m["shock_2008"]; best = next(r for r in bt if r["model"] == m["backtest"]["best_model"])
base = next(r for r in bt if "ingênuo" in r["model"])
dec = prof[11]["index_vs_year_avg"]; jan = prof[0]["index_vs_year_avg"]
sections = [
    {"title": "Os próximos 12 meses devem crescer 2,5%".replace("2,5", br(m["forecast_growth_pct"])),
     "insight": f'O modelo prevê US$ {br(m["forecast_total_next12"]/B, 2)} trilhões em vendas de junho de 2016 a maio de 2017, '
                f'{br(m["forecast_growth_pct"])}% acima dos 12 meses anteriores. As faixas mostram a incerteza: 80% e 95% de confiança.',
     "chart": fig_html(f1, 400), "note": "Histórico exibido a partir de 2008. Tendência estimada por decomposição STL."},
    {"title": "Dezembro vende 18% acima da média; janeiro e fevereiro, 12% abaixo".replace("18", br(dec - 100, 0)),
     "insight": f'O ano tem dois movimentos claros: o pico de fim de ano (dezembro vende {br(dec - 100)}% acima da média) e a ressaca do começo do ano (janeiro vende {br(100 - jan)}% abaixo). '
                'Estoque e equipe precisam acompanhar esse ciclo.',
     "chart": fig_html(f2, 320)},
    {"title": "O modelo erra em média 1,4% ao prever um ano inteiro".replace("1,4", br(best["mape"], 1)),
     "insight": f'Em 5 testes com dados que o modelo não viu, o SARIMA errou em média {br(best["mape"], 2)}%, '
                f'quase {br(base["mape"]/best["mape"], 1)} vezes menos que repetir o ano anterior ({br(base["mape"], 2)}%).',
     "chart": fig_html(f3, 260), "note": "Backtest com origem móvel: cada modelo treina até maio de um ano e prevê os 12 meses seguintes (2011 a 2015)."},
    {"title": "A crise de 2008 foi o único ano de queda forte",
     "insight": f'A tendência caiu {br(abs(s["drop_pct"]))}% entre {mes_ano(s["trend_peak"])} e {mes_ano(s["trend_trough"])} e só voltou ao nível anterior em {mes_ano(s["recovered_month"])}. '
                'Choques assim não aparecem nos modelos baseados apenas em histórico.',
     "chart": fig_html(f4, 300)},
]
kpis = [kpi(f'{br(best["mape"], 1)}%', "erro médio em 12 meses (backtest)"),
        kpi(f'{br(base["mape"]/best["mape"], 1)}x', "mais preciso que repetir o ano anterior"),
        kpi(f'+{br(m["forecast_growth_pct"], 1)}%', "de crescimento previsto em 12 meses"),
        kpi(f'+{br(dec - 100, 0)}%', "vendas de dezembro acima da média")]
render(DOCS / "index.html",
       title="Quanto o varejo vai vender nos próximos 12 meses",
       level="Nível ouro · Séries temporais e previsão",
       question="Como as vendas do varejo dos EUA devem se comportar no próximo ano, quais padrões sazonais e de tendência existem e qual a confiança que se pode ter na previsão.",
       kpis=kpis, sections=sections,
       method="SQL no DuckDB para calendário completo e marts anuais e sazonais; decomposição STL; comparação de três modelos (sazonal ingênuo, Holt-Winters e SARIMA) em backtest com origem móvel; previsão final com intervalos de 80% e 95%. Testes de dados e de vazamento no GitHub Actions.",
       source=f'Vendas mensais do varejo dos EUA (US Census Bureau), de {mes_ano(m["series"]["start"])} a {mes_ano(m["series"]["end"])}, sem ajuste sazonal, distribuídas como dataset de exemplo do Prophet. Valores em milhões de dólares.',
       repo_url="https://github.com/bishoppython/previsao-vendas-varejo")
print("OK: docs/index.html")
