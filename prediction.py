import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

SAFE_CAGR_CAP = 0.15  # warning threshold

def safe_fetch_history(ticker, period="5y"):
    for t in [ticker, f"{ticker}.NS", f"{ticker}.BO"]:
        df = yf.Ticker(t).history(period=period, auto_adjust=True)
        if not df.empty:
            return df["Close"].rename(t)
    return pd.Series(dtype=float)

def compute_cagr_5y(prices):
    days = (prices.index[-1] - prices.index[0]).days
    years = days / 365
    return (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1

def analyze_ticker(ticker, amount, proj_years):
    prices = safe_fetch_history(ticker.strip().upper())
    if prices.empty:
        raise ValueError(f"No data for {ticker}")
    cagr = compute_cagr_5y(prices)
    actual = prices.name
    info = yf.Ticker(actual).info
    current = info.get("previousClose", prices.iloc[-1])
    future = []
    for year in range(1, int(proj_years)+1):
        proj_price = current * (1 + cagr * year)
        profit_pct = cagr * year * 100
        profit_amt = amount * (1 + profit_pct/100) - amount
        future.append({
            "year": year,
            "proj_price": round(proj_price,2),
            "profit_pct": round(profit_pct,2),
            "profit_amt": round(profit_amt,2),
        })
    return prices, {
        "ticker": actual,
        "sector": info.get("sector","N/A"),
        "cagr5_pct": round(cagr*100,2),
        "buy_price": round(current,2),
        "future": future,
        "warning": f"CAGR {cagr*100:.2f}% > cap" if cagr > SAFE_CAGR_CAP else None
    }

def run_app():
    st.title("Year‑by‑Year Price Projections")
    ticker = st.sidebar.text_input("Ticker", "HDFCBANK")
    amount = st.sidebar.number_input("Amount (₹)", min_value=1.0, value=100000.0)
    years = st.sidebar.number_input("Projection Years", min_value=1, value=5, step=1)
    if st.sidebar.button("Analyze"):
        try:
            prices, info = analyze_ticker(ticker, amount, years)
        except Exception as e:
            st.error(f"${ticker}: {e}")
            return

        st.header(f"Analysis for {info['ticker']}")
        st.write(f"Sector: {info['sector']}")
        st.write(f"5‑Year CAGR: {info['cagr5_pct']}%")
        st.write(f"Buy Price: ₹{info['buy_price']:.2f}")
        st.write("Future Year‑by‑Year Projections:")
        for f in info["future"]:
            st.write(f"Year {f['year']}: ₹{f['proj_price']} → Profit ₹{f['profit_amt']} ({f['profit_pct']}%)")
        if info["warning"]:
            st.warning(info["warning"])

        df_hist = prices.reset_index().rename(columns={prices.name:"price"})
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_hist["Date"], y=df_hist["price"],
                                 mode="lines", name="Historical Price"))
        # Add markers with hover data for each future year
        future_dates = df_hist["Date"].iloc[-1] + pd.to_timedelta(
            [365*i for i in range(1, len(info["future"])+1)], unit="D"
        )
        proj_prices = [f["proj_price"] for f in info["future"]]
        hoverdata = [
            f"Year {f['year']}<br>Price: ₹{f['proj_price']}<br>Profit: ₹{f['profit_amt']} ({f['profit_pct']}%)"
            for f in info["future"]
        ]
        fig.add_trace(go.Scatter(x=future_dates,
                                 y=proj_prices,
                                 mode="markers+lines",
                                 name="Future Projections",
                                 marker=dict(size=8, color="orange"),
                                 hovertext=hoverdata,
                                 hoverinfo="text"))
        fig.add_hline(y=info["buy_price"], line_dash="dash", line_color="green", annotation_text="Buy Price")
        fig.update_layout(title="Price History + Future Projections",
                          xaxis_title="Date", yaxis_title="₹ Price")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
