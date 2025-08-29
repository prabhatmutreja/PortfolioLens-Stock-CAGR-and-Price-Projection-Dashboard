"""
PortfolioLens: Stock CAGR and Price Projection Dashboard
This app fetches stock price history (mainly Indian stocks from NSE/BSE),
calculates 5-year CAGR, and projects year-by-year prices and profits using compounding.
Built with Streamlit + yFinance + Plotly.
"""

import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Maximum CAGR threshold for warnings (if CAGR > 15% → high risk)
SAFE_CAGR_CAP = 0.15  


# ---------------------- Data Fetching ----------------------
def fetch_stock_history(ticker: str, period: str = "5y") -> pd.Series:
    """
    Try to fetch historical prices for a stock.
    - Prefer NSE (.NS) and BSE (.BO) tickers for Indian stocks.
    - Fall back to plain ticker if necessary.
    
    Returns:
        Pandas Series of adjusted Close prices (auto-adjusted for splits/dividends).
    """
    ticker = ticker.strip().upper()

    # Candidate formats: NSE, BSE, and plain ticker
    candidates = [f"{ticker}.NS", f"{ticker}.BO", ticker]

    for symbol in candidates:
        try:
            history = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        except Exception:
            history = pd.DataFrame()

        if not history.empty:
            return history["Close"].rename(symbol)

    # Return empty Series if nothing worked
    return pd.Series(dtype=float)

def compute_cagr(prices: pd.Series) -> float:
    """
    Compute the 5-year CAGR (Compounded Annual Growth Rate)
    from historical price data.
    """
    days = (prices.index[-1] - prices.index[0]).days
    years = days / 365.0
    return (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1

def analyze_stock(ticker: str, invested_amount: float, projection_years: int):
    """
    Main function:
    - Fetch stock prices
    - Calculate CAGR
    - Estimate future year-by-year projections using compounding
    """
    prices = fetch_stock_history(ticker)
    if prices.empty:
        raise ValueError(f"No price data available for {ticker}")

    final_ticker = prices.name  # actual symbol used (e.g., INFY.NS)
    stock_info = {}
    try:
        stock_info = yf.Ticker(final_ticker).info
    except Exception:
        stock_info = {}

    # Calculate CAGR and latest buy price
    cagr = compute_cagr(prices)
    current_price = prices.iloc[-1]

    # Build projections
    projections = []
    for year in range(1, projection_years + 1):
        growth_factor = (1 + cagr) ** year
        projected_price = current_price * growth_factor
        profit_pct = (growth_factor - 1) * 100
        profit_amt = invested_amount * (growth_factor - 1)

        projections.append({
            "year": year,
            "proj_price": round(projected_price, 2),
            "profit_pct": round(profit_pct, 2),
            "profit_amt": round(profit_amt, 2),
        })

    return prices, {
        "ticker": final_ticker,
        "sector": stock_info.get("sector", "N/A"),
        "currency": stock_info.get("currency", "N/A"),
        "cagr_pct": round(cagr * 100, 2),
        "buy_price": round(current_price, 2),
        "projections": projections,
        "warning": f"CAGR {cagr*100:.2f}% > {SAFE_CAGR_CAP*100:.0f}% cap"
                    if cagr > SAFE_CAGR_CAP else None
    }


# streamlit app
def run_app():
    """Streamlit UI for the dashboard."""
    st.title("Stock CAGR & Price Projection Dashboard")

    # Sidebar inputs
    ticker = st.sidebar.text_input("Enter Stock Ticker", "HDFCBANK")
    invested_amount = st.sidebar.number_input("Investment Amount (₹)", min_value=1.0, value=100000.0)
    years = st.sidebar.number_input("Projection Years", min_value=1, value=5, step=1)

    if st.sidebar.button("Analyze"):
        try:
            prices, analysis = analyze_stock(ticker, invested_amount, years)
        except Exception as e:
            st.error(f"Error: {e}")
            return

        # --- Display Analysis ---
        st.header(f"Analysis for {analysis['ticker']}")
        st.write(f"**Sector:** {analysis['sector']}")
        st.write(f"**Currency:** {analysis['currency']}")
        st.write(f"**5-Year CAGR:** {analysis['cagr_pct']}%")
        st.write(f"**Buy Price:** ₹{analysis['buy_price']:.2f}")

        st.subheader("Future Year-by-Year Projections")
        for proj in analysis["projections"]:
            st.write(f"Year {proj['year']}: "
                     f"₹{proj['proj_price']} → Profit ₹{proj['profit_amt']} "
                     f"({proj['profit_pct']}%)")

        if analysis["warning"]:
            st.warning(analysis["warning"])

        # --- Chart ---
        df_hist = prices.reset_index().rename(columns={prices.name: "Price"})
        fig = go.Figure()

        # Historical line
        fig.add_trace(go.Scatter(x=df_hist["Date"], y=df_hist["Price"],
                                 mode="lines", name="Historical Price"))

        # Projection points
        future_dates = df_hist["Date"].iloc[-1] + pd.to_timedelta(
            [365 * i for i in range(1, len(analysis["projections"]) + 1)], unit="D"
        )
        proj_prices = [p["proj_price"] for p in analysis["projections"]]
        hover_text = [
            f"Year {p['year']}<br>Price: ₹{p['proj_price']}<br>"
            f"Profit: ₹{p['profit_amt']} ({p['profit_pct']}%)"
            for p in analysis["projections"]
        ]

        fig.add_trace(go.Scatter(
            x=future_dates, y=proj_prices,
            mode="markers+lines", name="Future Projections",
            marker=dict(size=8, color="orange"),
            hovertext=hover_text, hoverinfo="text"
        ))

        # Buy Price line
        fig.add_hline(y=analysis["buy_price"], line_dash="dash", line_color="green",
                      annotation_text="Buy Price")

        # Layout
        fig.update_layout(title="Price History + Future Projections",
                          xaxis_title="Date", yaxis_title="₹ Price")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    run_app()
