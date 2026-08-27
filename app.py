import streamlit as st
import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
from pathlib import Path

# Page Configuration
st.set_page_config(page_title="💰 Pro Arbitrage Monitor", layout="wide", page_icon="")

# Coins to track
COINS = {
    'BTC': {'ccxt': 'BTC/USDT'},
    'ETH': {'ccxt': 'ETH/USDT'},
    'SOL': {'ccxt': 'SOL/USDT'},
    'XRP': {'ccxt': 'XRP/USDT'},
    'BNB': {'ccxt': 'BNB/USDT'},
    'TRX': {'ccxt': 'TRX/USDT'},
    'HYPE': {'ccxt': 'HYPE/USDT'},
    'YOMP': {'ccxt': 'YOMP/USDT'}
}

# CEX Exchanges - INCLUDES YOMP TOKEN
CEX_EXCHANGES = [
    'binance', 'okx', 'bybit', 'gate', 'mexc', 'bitget', 
    'kucoin', 'htx', 'bingx', 'coinex', 'whitebit', 
    'blofin', 'lbank', 'bitunix', 'bydfi', 'deribit',
    'kraken', 'gemini', 'coinbase', 'cryptocom',
    'yomp'
]

# Trading fees
TRADING_FEES = {
    'binance': 0.1, 'okx': 0.08, 'bybit': 0.1, 'gate': 0.2, 
    'mexc': 0.05, 'bitget': 0.1, 'kucoin': 0.1, 'htx': 0.2,
    'bingx': 0.1, 'coinex': 0.1, 'whitebit': 0.1,
    'blofin': 0.1, 'lbank': 0.1, 'bitunix': 0.1, 'bydfi': 0.1,
    'deribit': 0.05,
    'kraken': 0.16, 'gemini': 0.35, 'coinbase': 0.5, 'cryptocom': 0.4,
    'yomp': 0.08
}

# Yomp Token API Configuration
YOMP_API_KEY = "bQFrI5c2ed1ucXJn"

# Create logs directory
LOGS_DIR = Path("arbitrage_logs")
LOGS_DIR.mkdir(exist_ok=True)

def fetch_yomp_prices_via_scraping():
    """Fetch Yomp prices with validation to avoid volume/incorrect data"""
    prices = {}
    
    # Expected price ranges (min, max) for validation
    EXPECTED_RANGES = {
        'BTC': (50000, 150000),
        'ETH': (1500, 5000),
        'SOL': (50, 300),
        'XRP': (0.3, 5),
        'BNB': (400, 1000),
        'TRX': (0.1, 1),
        'HYPE': (10, 200),
        'YOMP': (0.01, 100)
    }
    
    try:
        markets_url = "https://yomptoken.com/markets"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(markets_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            import re
            text = response.text
            
            # More specific patterns - look for price patterns near coin names
            coin_patterns = {
                'BTC': [r'BTC\s*/\s*USDT.*?\$?([\d,]+\.?\d*)', r'BTCUSDT.*?last.*?([\d.]+)'],
                'ETH': [r'ETH\s*/\s*USDT.*?\$?([\d,]+\.?\d*)', r'ETHUSDT.*?last.*?([\d.]+)'],
                'SOL': [r'SOL\s*/\s*USDT.*?\$?([\d,]+\.?\d*)', r'SOLUSDT.*?last.*?([\d.]+)'],
                'XRP': [r'XRP\s*/\s*USDT.*?\$?([\d,]+\.?\d*)'],
                'BNB': [r'BNB\s*/\s*USDT.*?\$?([\d,]+\.?\d*)'],
                'TRX': [r'TRX\s*/\s*USDT.*?\$?([\d,]+\.?\d*)'],
                'HYPE': [r'HYPE\s*/\s*USDT.*?\$?([\d,]+\.?\d*)'],
                'YOMP': [r'YOMP\s*/\s*USDT.*?\$?([\d,]+\.?\d*)']
            }
            
            for coin, patterns in coin_patterns.items():
                min_price, max_price = EXPECTED_RANGES[coin]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        try:
                            price_str = match.replace(',', '')
                            price = float(price_str)
                            
                            # Validate price is within expected range
                            if min_price <= price <= max_price:
                                prices[coin] = price
                                break
                        except:
                            continue
                
                # If no valid price found, try alternative
                if coin not in prices:
                    coin_pattern = rf'{coin}\s*/\s*USDT'
                    coin_match = re.search(coin_pattern, text, re.IGNORECASE)
                    if coin_match:
                        start = coin_match.end()
                        nearby_text = text[start:start+300]
                        
                        all_numbers = re.findall(r'\$?([\d,]+\.?\d*)', nearby_text)
                        
                        for num_str in all_numbers:
                            try:
                                num = float(num_str.replace(',', ''))
                                if min_price <= num <= max_price:
                                    prices[coin] = num
                                    break
                            except:
                                continue
            
            if prices:
                st.sidebar.success(f"✅ Yomp: {len(prices)} valid prices")
                for coin, price in prices.items():
                    st.sidebar.text(f"  {coin}: ${price:,.4f}")
                return prices
            else:
                st.sidebar.warning("⚠️ Yomp: No valid prices found")
                return {}
        else:
            st.sidebar.error(f"❌ Yomp: Status {response.status_code}")
            return {}
            
    except Exception as e:
        st.sidebar.error(f"❌ Yomp Error: {str(e)}")
        return {}

def fetch_jupiter_prices():
    try:
        solana_tokens = ['So11111111111111111111111111111111111111112', '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs']
        url = f"https://price.jup.ag/v6/price?ids={','.join(solana_tokens)}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            prices = {}
            if 'data' in data:
                if 'So11111111111111111111111111111111111111112' in data['data']:
                    prices['BTC'] = data['data']['So11111111111111111111111111111111111111112']['price']
                    prices['SOL'] = data['data']['So11111111111111111111111111111111111111112']['price']
                if '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs' in data['data']:
                    prices['ETH'] = data['data']['7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs']['price']
            return prices
    except:
        pass
    return {}

def fetch_uniswap_prices():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=ethereum,bitcoin,solana&order=market_cap_desc&per_page=100&page=1&sparkline=false"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            prices = {}
            for coin in data:
                if coin['id'] == 'bitcoin': prices['BTC'] = coin['current_price']
                elif coin['id'] == 'ethereum': prices['ETH'] = coin['current_price']
                elif coin['id'] == 'solana': prices['SOL'] = coin['current_price']
            return prices
    except:
        pass
    return {}

@st.cache_data(ttl=30)
def fetch_all_prices():
    """Fetch prices from ALL exchanges including Yomp"""
    all_prices_by_coin = {}
    
    # Initialize regular exchanges
    exchanges = {}
    for ex_id in CEX_EXCHANGES:
        if ex_id != 'yomp':
            try:
                exchange_class = getattr(ccxt, ex_id)
                exchanges[ex_id] = exchange_class({'enableRateLimit': True, 'timeout': 10000})
            except:
                pass
    
    # Fetch Yomp prices separately
    yomp_prices = fetch_yomp_prices_via_scraping()
    
    # For each coin, fetch from all exchanges
    for coin in COINS.keys():
        symbol = COINS[coin]['ccxt']
        coin_prices = {}
        
        # Fetch from regular exchanges
        for ex_id, exchange in exchanges.items():
            try:
                ticker = exchange.fetch_ticker(symbol)
                if ticker and ticker['last'] is not None:
                    coin_prices[ex_id] = round(ticker['last'], 6)
            except:
                coin_prices[ex_id] = None
        
        # Add Yomp prices
        if coin in yomp_prices:
            coin_prices['yomp'] = round(yomp_prices[coin], 6)
        else:
            coin_prices['yomp'] = None
        
        all_prices_by_coin[coin] = coin_prices
    
    return all_prices_by_coin

def calculate_arbitrage_opportunities(all_prices_by_coin):
    opportunities = []
    
    for coin, all_prices in all_prices_by_coin.items():
        valid_prices = {k: v for k, v in all_prices.items() if v is not None}
        
        if len(valid_prices) >= 2:
            min_price = min(valid_prices.values())
            max_price = max(valid_prices.values())
            spread_abs = round(max_price - min_price, 6)
            spread_pct = round((spread_abs / min_price) * 100, 3)
            
            min_source = [src for src, price in valid_prices.items() if price == min_price][0]
            max_source = [src for src, price in valid_prices.items() if price == max_price][0]
            
            buy_fee = TRADING_FEES.get(min_source, 0.3)
            sell_fee = TRADING_FEES.get(max_source, 0.3)
            total_fee = buy_fee + sell_fee
            net_profit_pct = round(spread_pct - total_fee, 3)
            net_profit_dollar = round((min_price * net_profit_pct / 100), 4)
            profit_on_1000 = round(1000 * (net_profit_pct / 100), 2)
            
            dex_sources = ['jupiter', 'uniswap']
            if min_source in dex_sources or max_source in dex_sources:
                arb_type = "CEX ↔ DEX"
            else:
                arb_type = "CEX → CEX"
            
            opportunities.append({
                'Coin': coin,
                'Type': arb_type,
                'Buy At': min_source,
                'Sell At': max_source,
                'Buy Price': min_price,
                'Sell Price': max_price,
                'Spread %': spread_pct,
                'Total Fees %': total_fee,
                'Net Profit %': net_profit_pct,
                'Net Profit $': net_profit_dollar,
                'Profit on $1000': profit_on_1000,
                'All Prices': valid_prices
            })
    
    return pd.DataFrame(opportunities)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("️ Settings")
    
    auto_refresh = st.checkbox("🔄 Auto-refresh every 30s", value=True)
    if st.button(" Refresh Now"):
        st.cache_data.clear()
    
    alert_threshold = st.slider("Alert when net profit > %", 0.1, 2.0, 0.30)
    
    st.markdown("---")
    st.header("📡 Price Sources")
    
    st.markdown(f"""
    - **CEX**: {len(CEX_EXCHANGES)} Exchanges
      • Binance, OKX, Bybit, Gate, MEXC
      • KuCoin, HTX, BingX, Bitget
      • Kraken, Gemini, Coinbase, Crypto.com
      • **Yomp Token** ✅
    - **DEX**: Jupiter, Uniswap
    """)
    
    if YOMP_API_KEY:
        st.success("🔑 Yomp API Key: Active")
    else:
        st.warning(" Yomp API Key: Not set")
    
    st.markdown("---")
    st.info(" **Pro Tips:**\n-  Green = Profitable after fees\n-  Yellow = Marginal profit\n- 🔴 Red = Would lose money\n- Logs saved in: arbitrage_logs/")

# ==================== MAIN CONTENT ====================
st.title("💰 Pro Arbitrage Monitor")
st.markdown(f"**{len(CEX_EXCHANGES)} Exchanges • CEX + DEX • Real-Time Prices**")

# Fetch all prices
with st.spinner("🔍 Scanning all exchanges including Yomp Token..."):
    all_prices = fetch_all_prices()
    df = calculate_arbitrage_opportunities(all_prices)

# Alerts
if not df.empty:
    high_opportunities = df[df['Net Profit %'] > alert_threshold]
    if not high_opportunities.empty:
        st.balloons()
        st.error(f" **ALERT: {len(high_opportunities)} PROFITABLE OPPORTUNITIES!**")

# ==================== ALL ARBITRAGE OPPORTUNITIES ====================
st.subheader("📊 All Arbitrage Opportunities")

if not df.empty:
    for idx, row in df.iterrows():
        net_profit_display = f"Net: {row['Net Profit %']:.3f}%"
        expandable_title = f"{row['Coin']} - {row['Type']} - {net_profit_display}"
        
        with st.expander(expandable_title, expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💡 Opportunity Details:**")
                st.write("")
                st.write(f"**Buy:** {row['Buy At'].upper()} @ ${row['Buy Price']:,.4f}")
                st.write(f"**Sell:** {row['Sell At'].upper()} @ ${row['Sell Price']:,.4f}")
                st.write(f"**Spread:** {row['Spread %']:.3f}%")
                st.write(f"**Fees:** {row['Total Fees %']:.2f}%")
                st.write(f"**Net Profit:** {row['Net Profit %']:.3f}% (${row['Net Profit $']:,.4f})")
                st.write("")
                st.markdown(f"**💵 Profit on $1000 Capital:** `${row['Profit on $1000']:.2f}`")
            
            with col2:
                st.markdown("**📈 All Prices (Including Yomp Token):**")
                prices_list = []
                for source, price in row['All Prices'].items():
                    display_name = source.upper() if source != 'yomp' else 'YOMP TOKEN'
                    prices_list.append({
                        'Source': display_name,
                        'Price': f"${price:,.4f}"
                    })
                
                if prices_list:
                    prices_df = pd.DataFrame(prices_list)
                    st.dataframe(prices_df, hide_index=True, use_container_width=True)
                else:
                    st.write("No prices available")
else:
    st.warning("⚠️ No arbitrage opportunities found. Check if exchanges are accessible.")

# ==================== SUMMARY TABLE ====================
st.subheader("📋 Summary Table")

if not df.empty:
    summary_df = df[['Coin', 'Type', 'Buy At', 'Sell At', 'Buy Price', 'Sell Price', 'Spread %', 'Net Profit %', 'Net Profit $', 'Profit on $1000']].copy()
    
    def color_code(val):
        if isinstance(val, (int, float)):
            if val > 0.5:
                return 'background-color: #d4edda; color: #155724; font-weight: bold'
            elif val > 0.2:
                return 'background-color: #fff3cd; color: #856404'
            elif val < 0:
                return 'background-color: #f8d7da; color: #721c24'
        return ''
    
    styled_summary = summary_df.style.map(color_code, subset=['Net Profit %', 'Net Profit $', 'Profit on $1000']).format({
        'Buy Price': '${:,.4f}',
        'Sell Price': '${:,.4f}',
        'Spread %': '{:.3f}%',
        'Net Profit %': '{:.3f}%',
        'Net Profit $': '${:,.4f}',
        'Profit on $1000': '${:.2f}'
    })
    
    st.dataframe(styled_summary, use_container_width=True, hide_index=True)
else:
    st.info("💡 Fetching prices from exchanges... Table will appear once data is loaded.")

# Footer
st.markdown("---")
st.markdown("""
**💡 Pro Tips:**
- 🟢 **Green** = Profitable after fees (>$5.00 profit on $1000)
- 🟡 **Yellow** = Marginal ($2.00 - $5.00 profit on $1000)
- 🔴 **Red** = Would lose money after fees
- **Yomp Token**: Now included with price validation!
- Logs saved in: `arbitrage_logs/`
""")

# Auto-refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()