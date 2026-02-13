import streamlit as st
import pymysql
import pandas as pd
import time

conn = pymysql.connect(
    host = "localhost",
    port = 3306,
    user = "root",
    password = "arun",
    database = "CrossMarket"
)

cursor = conn.cursor()

st.set_page_config(
    page_title="Cross Market Analysis",
    page_icon="📊",
    layout="wide"   # ⭐ This expands UI
)


st.sidebar.title("📌 Navigation")

page = st.sidebar.radio("Go to",["📊 Market Overview", "🧾 SQL Query Runner", "🪙 Top 5 Crypto Analysis"])

# Page 1: Filters & Data Exploration

if page == "📊 Market Overview":

    st.title("📊 Cross-Market Overview")
    st.caption("Crypto • Oil • Stock Market | SQL-powered analytics")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date")

    with col2:
        end_date = st.date_input("End Date")

    def safe_value(val):
        if val is None:
            return "No Data"
        return f"{val:,.2f}"

    if start_date and end_date:

        avg_query = """
        SELECT
            AVG(CASE WHEN cp.coin_id='bitcoin' THEN cp.price_inr END),
            AVG(o.Price),
            AVG(CASE WHEN sp.ticker='^GSPC' THEN sp.close END),
            AVG(CASE WHEN sp.ticker='^NSEI' THEN sp.close END)
        FROM Crypto_prices cp
        LEFT JOIN Stock_prices sp ON cp.date = sp.Date
        LEFT JOIN oil_prices o ON cp.date = o.Date
        WHERE cp.date BETWEEN %s AND %s
        """

        cursor.execute(avg_query, (start_date, end_date))
        result = cursor.fetchone() or (None, None, None, None)

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("₿ Bitcoin Avg", safe_value(result[0]))
        m2.metric("🛢 Oil Avg", safe_value(result[1]))
        m3.metric("📊 S&P 500 Avg", safe_value(result[2]))
        m4.metric("📈 NIFTY Avg", safe_value(result[3]))

        snapshot_query = """
        SELECT
            cp.date,
            cp.price_inr,
            MAX(o.Price),
            MAX(CASE WHEN sp.ticker='^GSPC' THEN sp.close END),
            MAX(CASE WHEN sp.ticker='^NSEI' THEN sp.close END)
        FROM Crypto_prices cp
        LEFT JOIN Stock_prices sp ON cp.date = sp.Date
        LEFT JOIN oil_prices o ON cp.date = o.Date
        WHERE cp.coin_id='bitcoin'
        AND cp.date BETWEEN %s AND %s
        GROUP BY cp.date, cp.price_inr
        ORDER BY cp.date DESC
        """

        cursor.execute(snapshot_query, (start_date, end_date))
        data = cursor.fetchall()

        df = pd.DataFrame(
            data,
            columns=["Date", "Bitcoin", "Oil", "S&P 500", "NIFTY"]
        )

        st.subheader("📋 Daily Market Snapshot")

        if df.empty:
            st.warning("No data available for selected date range")
        else:
            st.dataframe(df, use_container_width=True)

# Page 2: SQL Query Runner

elif page == "🧾 SQL Query Runner":

    st.title("🧾 SQL Query Runner")
    queries = {
        "top 3 cryptocurrencies by market cap":
        """
        SELECT name, market_cap FROM Cryptocurrencies ORDER BY market_cap DESC
        LIMIT 3;
        """,
        
        "coins where circulating supply exceeds 90% of total supply":
        """
        SELECT name, circulating_supply, total_supply FROM Cryptocurrencies WHERE circulating_supply >= 0.9 * total_supply;
        """,

        "coins that are within 10% of their all-time-high (ATH)":
        """
        SELECT name, current_price, ath FROM Cryptocurrencies WHERE current_price >= 0.9 * ath;
        """,

        "the average market cap rank of coins with volume above $1B":
        """
        SELECT AVG(market_cap_rank) AS avg_rank FROM Cryptocurrencies WHERE total_volume > 1000000000;
        """,

        "the most recently updated coin":
        """
        SELECT name, date_only FROM Cryptocurrencies ORDER BY date_only DESC
        LIMIT 1;
        """,
# CRYPTO PRICES

        "the highest daily price of Bitcoin in the last 365 days":
        """
        SELECT MAX(price_inr) AS highest_price
        FROM Crypto_prices WHERE coin_id = 'bitcoin' AND date >= CURDATE() - INTERVAL 365 DAY;
        """,

        "the average daily price of Ethereum in the past 1 year":
        """
        SELECT AVG(price_inr) AS eth_avg_price FROM Crypto_prices WHERE coin_id = 'ethereum' AND date >= CURDATE() - INTERVAL 1 YEAR;
        """,

        "the daily price trend of Bitcoin in February 2025":
        """
        SELECT date, price_inr FROM Crypto_prices WHERE coin_id = 'bitcoin' AND YEAR(date)=2025 AND MONTH(date)=2
        ORDER BY date;
        """,

        "the coin with the highest average price over 1 year":
        """
        SELECT coin_id, AVG(price_inr) AS avg_price FROM Crypto_prices WHERE date >= CURDATE() - INTERVAL 1 YEAR GROUP BY coin_id
        ORDER BY avg_price DESC
        LIMIT 1;
        """,

        "the % change in Bitcoin’s price between Feb 2024 and Feb 2025":
        """
        SELECT 
        ((SELECT AVG(price_inr) FROM Crypto_prices WHERE coin_id='bitcoin' AND date BETWEEN '2026-02-01' AND '2026-02-28') -
        (SELECT AVG(price_inr) FROM Crypto_prices WHERE coin_id='bitcoin' AND date BETWEEN '2025-02-01' AND '2025-02-28')) / 
        (SELECT AVG(price_inr) FROM Crypto_prices WHERE coin_id='bitcoin' AND date BETWEEN '2025-02-01' AND '2025-02-28') * 100 
        AS percentage_change;
        """,


# OIL PRICES
        "the highest oil price in the last 5 years":
        """
        SELECT MAX(Price) AS highest_oil_price FROM oil_prices WHERE Date >= CURDATE() - INTERVAL 5 YEAR;
        """,

        "the average oil price per year":
        """
        SELECT YEAR(Date) AS year, AVG(Price) AS avg_price FROM oil_prices GROUP BY YEAR(Date) ORDER BY year;
        """,

        "oil prices during COVID crash (March–April 2020)":
        """
        SELECT Date, Price FROM oil_prices WHERE Date BETWEEN '2020-03-01' AND '2020-04-30';
        """,

        "the lowest price of oil in the last 10 years":
        """
        SELECT MIN(Price) AS lowest_price FROM oil_prices WHERE Date >= CURDATE() - INTERVAL 10 YEAR;
        """,

        "the volatility of oil prices":
        """
        SELECT YEAR(Date) AS year, MAX(Price) - MIN(Price) AS volatility FROM oil_prices GROUP BY YEAR(Date);
        """,


# STOCK PRICES
        "all stock prices for a given ticker":
        """
        SELECT * FROM Stock_prices WHERE ticker='^IXIC';
        """,

        "highest closing price for NASDAQ (^IXIC)":
        """
        SELECT MAX(close) AS highest_close FROM Stock_prices WHERE ticker='^IXIC';
        """,

        "Top 5 S&P 500 Price Difference Days":
        """
        SELECT Date, High, Low, (High-Low) AS difference FROM Stock_prices WHERE ticker='^GSPC' ORDER BY difference DESC
        LIMIT 5;
        """,

        "Monthly Average Closing Price Per Ticker":
        """
        SELECT ticker, YEAR(Date) AS year, MONTH(Date) AS month, AVG(close) AS avg_close FROM Stock_prices GROUP BY ticker, YEAR(Date), MONTH(Date);
        """,

        "Average NSEI Trading Volume 2024":
        """
        SELECT AVG(Volume) AS avg_volume FROM Stock_prices WHERE ticker='^NSEI' AND YEAR(Date)=2024;
        """,


#CROSS MARKET
        "Bitcoin vs Oil Average Price 2025":
        """
        SELECT AVG(cp.price_inr) AS btc_avg, AVG(o.Price) AS oil_avg FROM Crypto_prices cp
        JOIN oil_prices o ON cp.date=o.Date WHERE cp.coin_id='bitcoin' AND YEAR(cp.date)=2025;
        """,

        "Bitcoin vs S&P500 Daily Comparison":
        """
        SELECT cp.date, cp.price_inr, sp.close FROM Crypto_prices cp
        JOIN Stock_prices sp ON cp.date=sp.Date WHERE cp.coin_id='bitcoin' AND sp.ticker='^GSPC';
        """,

        " Ethereum and NASDAQ daily prices for 2025":
        """
        SELECT cp.date, cp.price_inr, sp.close FROM Crypto_prices cp
        JOIN Stock_prices sp ON cp.date=sp.Date WHERE cp.coin_id='ethereum' AND sp.ticker='^IXIC' AND YEAR(cp.date)=2025;
        """,

        "oil price spiked and comparition with Bitcoin Price":
        """
        SELECT o.Date, o.Price, cp.price_inr FROM oil_prices o
        JOIN Crypto_prices cp ON o.Date=cp.date WHERE cp.coin_id='bitcoin' ORDER BY o.Price DESC
        LIMIT 20;
        """,

        "top 3 coins daily price trend vs Nifty (^NSEI)":
        """
        SELECT cp.coin_id, cp.date, cp.price_inr, sp.close FROM Crypto_prices cp
        JOIN Stock_prices sp ON cp.date=sp.Date WHERE sp.ticker='^NSEI' AND cp.coin_id IN (SELECT id FROM Cryptocurrencies ORDER BY market_cap DESC
        LIMIT 3 );
        """,

        "stock prices (^GSPC) with crude oil prices on the same dates":
        """
        SELECT sp.Date, sp.close, o.Price FROM Stock_prices sp
        JOIN oil_prices o ON sp.Date=o.Date WHERE sp.ticker='^GSPC';
        """,

        "Bitcoin closing price with crude oil closing price ":
        """
        SELECT cp.date, cp.price_inr, o.Price FROM Crypto_prices cp
        JOIN oil_prices o ON cp.date=o.Date WHERE cp.coin_id='bitcoin';
        """,

        "NASDAQ (^IXIC) with Ethereum price trends":
        """
        SELECT cp.date, cp.price_inr, sp.close FROM Crypto_prices cp
        JOIN Stock_prices sp ON cp.date=sp.Date WHERE cp.coin_id='ethereum' AND sp.ticker='^IXIC';
        """,

        "top 3 crypto coins with stock indices for 2025":
        """
        SELECT cp.coin_id, cp.date, cp.price_inr, sp.ticker, sp.close FROM Crypto_prices cp
        JOIN Stock_prices sp ON cp.date=sp.Date
        JOIN (SELECT id FROM Cryptocurrencies ORDER BY market_cap DESC LIMIT 3) top3 ON cp.coin_id=top3.id
        WHERE YEAR(cp.date)=2025;
        """,

        "stock prices, oil prices, and Bitcoin prices for daily comparison":
        """
        SELECT cp.date, cp.price_inr AS bitcoin_price,
        MAX(CASE WHEN sp.ticker='^GSPC' THEN sp.close END) AS sp500,
        MAX(CASE WHEN sp.ticker='^IXIC' THEN sp.close END) AS nasdaq,
        MAX(CASE WHEN sp.ticker='^NSEI' THEN sp.close END) AS nifty,
        MAX(o.Price) AS oil_price FROM Crypto_prices cp
        LEFT JOIN Stock_prices sp ON cp.date=sp.Date
        LEFT JOIN oil_prices o ON cp.date=o.Date WHERE cp.coin_id='bitcoin' GROUP BY cp.date;
        """
}
    selected_query = st.selectbox("📌 Select Query", sorted(queries.keys()))
    if st.button("▶ Run Query"):
        df = pd.read_sql(queries[selected_query], conn)
        st.dataframe(df)

# PAGE 3 : TOP CRYPTO ANALYSIS

elif page == "🪙 Top 5 Crypto Analysis":

    st.title("🪙 Top 5 Crypto Analysis")
    st.caption("Daily price analysis for top cryptocurrencies")
    
    top_crypto_query = """
    SELECT id, name
    FROM Cryptocurrencies
    ORDER BY market_cap DESC
    LIMIT 5;
    """

    top_crypto_df = pd.read_sql(top_crypto_query, conn)

    coin_dict = dict(zip(top_crypto_df["name"], top_crypto_df["id"]))

    selected_coin_name = st.selectbox(
        "Select a Cryptocurrency",
        list(coin_dict.keys())
    )

    selected_coin_id = coin_dict[selected_coin_name]

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date")

    with col2:
        end_date = st.date_input("End Date")

    if start_date and end_date:

        price_query = f"""
        SELECT date, price_inr
        FROM Crypto_prices
        WHERE coin_id = '{selected_coin_id}'
        AND date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date;
        """

        price_df = pd.read_sql(price_query, conn)

        if price_df.empty:
            st.warning("No data available for selected date range")
        else:

            price_df["date"] = pd.to_datetime(price_df["date"])

            st.subheader(f"📈 {selected_coin_name.upper()} Price Trend")

            st.line_chart(
                price_df.set_index("date")["price_inr"]
            )

            st.subheader("📊 Daily Price Table")

            st.dataframe(
                price_df,
                use_container_width=True
            )
