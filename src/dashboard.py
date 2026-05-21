import json
import inspect
import time
from datetime import date
from glob import glob
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

from basket_backtest import run_static_basket_backtest
from dashboard_content import (
    STRATEGY_NAME,
    STRATEGY_PARAMETERS,
    STRATEGY_RULES,
    TRADING_TERMS
)
from date_ranges import BACKTEST_DATE_RANGE_PRESETS, get_start_date_for_range
from indicators import add_indicators
from market_data import download_data
from market_universe import (
    get_all_market_asset_records_with_status,
    get_market_groups,
    get_market_names,
    get_markets_for_groups,
    save_verified_symbol
)
from market_cache import get_price_cache_status
from paper_trading import run_paper_trading_for_tickers
from portfolio_backtest import (
    build_price_data_session_key,
    load_market_price_data,
    run_portfolio_backtest,
    scan_preloaded_market_on_date
)
from portfolio_performance import calculate_portfolio_performance
from prompt_generator import generate_prompt
from screener_filters import (
    SCREENER_COLUMN_VIEWS,
    SCREENER_PRESETS,
    SCREENER_SORT_OPTIONS,
    filter_screener_dataframe,
    get_screener_columns,
    get_screener_preset_defaults,
    sort_screener_dataframe
)


st.set_page_config(
    page_title="AI Trading Bot Workstation",
    layout="wide"
)


WATCHLIST_FILE = Path("reports/watchlist.json")
PRESETS_FILE = Path("reports/backtest_presets.json")

DEFAULT_BACKTEST_PRESETS = {
    "1 - Defensive Trend": {
        "ma_type": "SMA",
        "fast_ma_period": 50,
        "slow_ma_period": 100,
        "long_ma_period": 200,
        "rsi_period": 14,
        "rsi_buy_min": 52,
        "rsi_buy_max": 66,
        "rsi_sell_above": 70,
        "atr_period": 14,
        "max_volatility_pct": 3.5,
        "adx_period": 14,
        "adx_min": 24,
        "use_adx_filter": True,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "use_macd_filter": True,
        "volume_sma_period": 20,
        "volume_ratio_min": 1.05,
        "use_volume_filter": True,
        "min_ai_score": 80,
        "min_scanner_score": 130,
        "min_hold_weeks": 8,
        "persistence_weeks": 3,
        "switch_score_margin": 30,
        "top_n_candidates": 3,
        "commission_pct": 0.0008,
        "slippage_pct": 0.0008,
        "use_engine_basket": True,
        "engine_basket_size": 4
    },
    "2 - Conservative Rotation": {
        "ma_type": "EMA",
        "fast_ma_period": 30,
        "slow_ma_period": 75,
        "long_ma_period": 200,
        "rsi_period": 14,
        "rsi_buy_min": 52,
        "rsi_buy_max": 68,
        "rsi_sell_above": 72,
        "atr_period": 14,
        "max_volatility_pct": 4.5,
        "adx_period": 14,
        "adx_min": 22,
        "use_adx_filter": True,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "use_macd_filter": True,
        "volume_sma_period": 20,
        "volume_ratio_min": 1.0,
        "use_volume_filter": True,
        "min_ai_score": 75,
        "min_scanner_score": 120,
        "min_hold_weeks": 6,
        "persistence_weeks": 2,
        "switch_score_margin": 25,
        "top_n_candidates": 4,
        "commission_pct": 0.0008,
        "slippage_pct": 0.0008,
        "use_engine_basket": True,
        "engine_basket_size": 5
    },
    "3 - Balanced Rotation": {
        "ma_type": "EMA",
        "fast_ma_period": 20,
        "slow_ma_period": 50,
        "long_ma_period": 200,
        "rsi_period": 14,
        "rsi_buy_min": 50,
        "rsi_buy_max": 70,
        "rsi_sell_above": 75,
        "atr_period": 14,
        "max_volatility_pct": 6.0,
        "adx_period": 14,
        "adx_min": 18,
        "use_adx_filter": False,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "use_macd_filter": False,
        "volume_sma_period": 20,
        "volume_ratio_min": 0.8,
        "use_volume_filter": False,
        "min_ai_score": 70,
        "min_scanner_score": 100,
        "min_hold_weeks": 4,
        "persistence_weeks": 2,
        "switch_score_margin": 15,
        "top_n_candidates": 5,
        "commission_pct": 0.001,
        "slippage_pct": 0.001,
        "use_engine_basket": True,
        "engine_basket_size": 5
    },
    "4 - Growth Momentum": {
        "ma_type": "EMA",
        "fast_ma_period": 10,
        "slow_ma_period": 30,
        "long_ma_period": 150,
        "rsi_period": 14,
        "rsi_buy_min": 48,
        "rsi_buy_max": 76,
        "rsi_sell_above": 82,
        "atr_period": 14,
        "max_volatility_pct": 10.0,
        "adx_period": 14,
        "adx_min": 15,
        "use_adx_filter": False,
        "macd_fast": 8,
        "macd_slow": 21,
        "macd_signal": 5,
        "use_macd_filter": True,
        "volume_sma_period": 20,
        "volume_ratio_min": 0.7,
        "use_volume_filter": False,
        "min_ai_score": 65,
        "min_scanner_score": 85,
        "min_hold_weeks": 2,
        "persistence_weeks": 1,
        "switch_score_margin": 5,
        "top_n_candidates": 8,
        "commission_pct": 0.001,
        "slippage_pct": 0.0015,
        "use_engine_basket": True,
        "engine_basket_size": 6
    },
    "5 - Aggressive Breakout": {
        "ma_type": "EMA",
        "fast_ma_period": 8,
        "slow_ma_period": 21,
        "long_ma_period": 100,
        "rsi_period": 14,
        "rsi_buy_min": 45,
        "rsi_buy_max": 82,
        "rsi_sell_above": 88,
        "atr_period": 14,
        "max_volatility_pct": 14.0,
        "adx_period": 14,
        "adx_min": 12,
        "use_adx_filter": False,
        "macd_fast": 8,
        "macd_slow": 21,
        "macd_signal": 5,
        "use_macd_filter": True,
        "volume_sma_period": 20,
        "volume_ratio_min": 0.6,
        "use_volume_filter": False,
        "min_ai_score": 55,
        "min_scanner_score": 70,
        "min_hold_weeks": 1,
        "persistence_weeks": 1,
        "switch_score_margin": 0,
        "top_n_candidates": 10,
        "commission_pct": 0.0012,
        "slippage_pct": 0.002,
        "use_engine_basket": True,
        "engine_basket_size": 8
    },
    "6 - ETF Dual SMA RSI": {
        "ma_type": "SMA",
        "fast_ma_period": 20,
        "slow_ma_period": 50,
        "long_ma_period": 200,
        "rsi_period": 14,
        "rsi_buy_min": 40,
        "rsi_buy_max": 65,
        "rsi_sell_above": 70,
        "atr_period": 14,
        "max_volatility_pct": 4.5,
        "adx_period": 14,
        "adx_min": 18,
        "use_adx_filter": False,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "use_macd_filter": False,
        "volume_sma_period": 20,
        "volume_ratio_min": 0.8,
        "use_volume_filter": False,
        "min_ai_score": 70,
        "min_scanner_score": 100,
        "min_hold_weeks": 4,
        "persistence_weeks": 2,
        "switch_score_margin": 15,
        "top_n_candidates": 3,
        "commission_pct": 0.0008,
        "slippage_pct": 0.0008,
        "use_engine_basket": True,
        "engine_basket_size": 3
    }
}

PRESET_GUIDANCE = {
    "1 - Defensive Trend": {
        "risk": "Molto prudente",
        "description": "Cerca trend maturi e confermati, accetta poche rotazioni.",
        "behavior": "Riduce rumore e volatilita, ma puo restare fuori da molti movimenti.",
        "tools": "SMA, RSI stretto, ATR basso, ADX, MACD, volume"
    },
    "2 - Conservative Rotation": {
        "risk": "Prudente",
        "description": "Ruota solo quando il trend e abbastanza stabile.",
        "behavior": "Compromesso difensivo per mercati direzionali ma non estremi.",
        "tools": "EMA, RSI, ATR moderato, ADX, MACD, volume"
    },
    "3 - Balanced Rotation": {
        "risk": "Bilanciato",
        "description": "Profilo centrale, vicino alla logica storica del motore.",
        "behavior": "Bilancia qualita del segnale, rotazione e permanenza in posizione.",
        "tools": "EMA, RSI, ATR, AI score, scanner score"
    },
    "4 - Growth Momentum": {
        "risk": "Dinamico",
        "description": "Cerca momentum piu rapidi e accetta rotazioni frequenti.",
        "behavior": "Puo intercettare trend prima, con piu falsi segnali.",
        "tools": "EMA rapide, RSI ampio, ATR alto, MACD"
    },
    "5 - Aggressive Breakout": {
        "risk": "Aggressivo",
        "description": "Massima sensibilita a breakout e accelerazioni di prezzo.",
        "behavior": "Aumenta opportunita e rotazioni, ma anche rumore e drawdown.",
        "tools": "EMA molto rapide, RSI elastico, ATR alto, MACD rapido"
    },
    "6 - ETF Dual SMA RSI": {
        "risk": "Prudente ETF",
        "description": "Replica una logica semplice SMA 20/50 con RSI non esteso.",
        "behavior": (
            "Pensato per ETF liquidi: entra solo su trend confermato e momentum "
            "moderato, accettando meno operazioni."
        ),
        "tools": "SMA 20/50/200, RSI 40-65, ATR moderato, basket ristretto"
    }
}

ASSET_RANGE_OPTIONS = {
    "1D": {"period": "5d", "title": "oggi", "default_candle": "5m"},
    "1W": {"period": "1mo", "title": "ultima settimana", "default_candle": "1h"},
    "1M": {"period": "3mo", "title": "ultimo mese", "default_candle": "4h"},
    "6M": {"period": "6mo", "title": "ultimi 6 mesi", "default_candle": "1d"},
    "YTD": {"period": "1y", "title": "YTD", "default_candle": "1d"},
    "1A": {"period": "1y", "title": "ultimo anno", "default_candle": "1d"},
    "5A": {"period": "5y", "title": "ultimi 5 anni", "default_candle": "1wk"}
}

CHART_CANDLE_OPTIONS = {
    "5m": {"interval": "5m", "resample": None, "label": "5m"},
    "15m": {"interval": "15m", "resample": None, "label": "15m"},
    "30m": {"interval": "30m", "resample": None, "label": "30m"},
    "1h": {"interval": "60m", "resample": None, "label": "1h"},
    "4h": {"interval": "60m", "resample": "4h", "label": "4h"},
    "1d": {"interval": "1d", "resample": None, "label": "1D"},
    "1wk": {"interval": "1wk", "resample": None, "label": "1W"}
}

CHART_CANDLES_BY_RANGE = {
    "1D": ["5m", "15m", "30m", "1h"],
    "1W": ["15m", "30m", "1h", "4h"],
    "1M": ["1h", "4h", "1d"],
    "6M": ["4h", "1d", "1wk"],
    "YTD": ["1d", "1wk"],
    "1A": ["1d", "1wk"],
    "5A": ["1wk", "1d"]
}

def get_latest_file(pattern: str):
    files = sorted(glob(pattern))

    if not files:
        return None

    return files[-1]


def get_previous_file(pattern: str):
    files = sorted(glob(pattern))

    if len(files) < 2:
        return None

    return files[-2]


def load_csv_or_empty(path):
    if not path:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def parse_custom_tickers(raw_tickers: str) -> list:
    if not raw_tickers:
        return []

    tickers = []

    for raw_ticker in raw_tickers.split(","):
        ticker = raw_ticker.strip().upper().replace(".", "-")

        if ticker and ticker not in tickers:
            tickers.append(ticker)

    return tickers


def merge_unique_tickers(*ticker_groups) -> list:
    merged_tickers = []

    for ticker_group in ticker_groups:
        for ticker in ticker_group:
            if pd.notna(ticker) and ticker not in merged_tickers:
                merged_tickers.append(ticker)

    return merged_tickers


def load_json_file(path: Path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json_file(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def load_watchlist() -> list:
    watchlist = load_json_file(WATCHLIST_FILE, [])

    if not isinstance(watchlist, list):
        return []

    return [
        str(ticker).upper()
        for ticker in watchlist
        if str(ticker).strip()
    ]


def save_watchlist(watchlist: list):
    save_json_file(WATCHLIST_FILE, sorted(set(watchlist)))


def load_backtest_presets() -> dict:
    presets = {
        name: values.copy()
        for name, values in DEFAULT_BACKTEST_PRESETS.items()
    }
    saved_presets = load_json_file(PRESETS_FILE, {})

    if isinstance(saved_presets, dict):
        for name, values in saved_presets.items():
            if isinstance(values, dict):
                merged_values = DEFAULT_BACKTEST_PRESETS[
                    "3 - Balanced Rotation"
                ].copy()
                merged_values.update(values)
                presets[name] = merged_values

    return presets


def save_backtest_presets(presets: dict):
    custom_presets = {
        name: values
        for name, values in presets.items()
        if name not in DEFAULT_BACKTEST_PRESETS or (
            values != DEFAULT_BACKTEST_PRESETS[name]
        )
    }
    save_json_file(PRESETS_FILE, custom_presets)


def format_asset_label(asset: dict) -> str:
    return f"{asset['ticker']} - {asset.get('name', asset['ticker'])}"


def build_asset_lookup(asset_records: list) -> dict:
    return {
        asset["ticker"]: asset
        for asset in asset_records
        if asset.get("ticker")
    }


def get_universe_preset_groups(preset_name: str) -> list:
    preset_groups = {
        "Globale progressivo": ["USA", "ETF", "Italy", "Europe", "Crypto"],
        "Tutto USA": ["USA"],
        "Tutti ETF": ["ETF"],
        "Italia": ["Italy"],
        "Europa Core": ["Europe"],
        "Crypto": ["Crypto"],
        "Custom": ["Custom"]
    }

    return preset_groups.get(preset_name, ["USA", "ETF", "Italy", "Europe"])


def validate_custom_ticker(ticker: str) -> dict:
    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker:
        raise ValueError("Ticker vuoto.")

    data = download_data(
        ticker=normalized_ticker,
        period="1mo",
        interval="1d"
    )

    if data.empty:
        raise ValueError(f"Nessun dato trovato per {normalized_ticker}.")

    return {
        "group": "Custom",
        "market": "Custom / Verified",
        "ticker": normalized_ticker,
        "name": normalized_ticker,
        "asset_type": "Custom",
        "exchange": "yfinance",
        "currency": "",
        "source": "user_verified"
    }


def search_asset_records(
    asset_records: list,
    search_text: str,
    preferred_markets: list | None = None
) -> list:
    query = search_text.strip().lower()

    if not query:
        return []

    query_no_suffix = query.split(".")[0]
    preferred_market_set = set(preferred_markets or [])
    ranked_matches = []

    for asset in asset_records:
        ticker = str(asset.get("ticker", "")).lower()
        ticker_root = ticker.split(".")[0]
        name = str(asset.get("name", "")).lower()
        market = asset.get("market", "")

        rank = None

        if query == ticker:
            rank = 0
        elif query == ticker_root or query_no_suffix == ticker_root:
            rank = 1
        elif ticker.startswith(query) or ticker_root.startswith(query_no_suffix):
            rank = 2
        elif query in ticker:
            rank = 3
        elif query in name:
            rank = 4

        if rank is not None:
            preferred_rank = 0 if market in preferred_market_set else 1
            ranked_matches.append((preferred_rank, rank, ticker, asset))

    ranked_matches = sorted(
        ranked_matches,
        key=lambda item: (item[0], item[1], item[2])
    )

    return [asset for _, _, _, asset in ranked_matches]


def add_ticker_to_watchlist(ticker: str):
    watchlist = st.session_state.setdefault("favorite_watchlist", [])

    if ticker not in watchlist:
        watchlist.append(ticker)
        st.session_state["favorite_watchlist"] = watchlist
        save_watchlist(watchlist)


def add_ticker_to_manual_basket(ticker: str):
    basket = st.session_state.setdefault("manual_basket_assets", [])

    if ticker not in basket:
        basket.append(ticker)
        st.session_state["manual_basket_assets"] = basket


def set_asset_focus(ticker: str):
    st.session_state["asset_focus_ticker"] = ticker


def render_global_asset_search(
    asset_records: list,
    selected_market_names: list,
    key_prefix: str,
    allow_basket: bool = True,
    layout: str = "full"
):
    compact = layout == "compact"
    search_text = st.text_input(
        "Ricerca globale asset",
        value="",
        key=f"{key_prefix}_global_asset_search",
        help=(
            "Cerca in tutto il catalogo caricato, anche fuori dai mercati "
            "attivi. Esempi: BYSI, TIP, TIP.MI."
        )
    )

    matches = search_asset_records(
        asset_records,
        search_text,
        preferred_markets=selected_market_names
    )

    if not search_text.strip():
        st.caption("Inserisci ticker o nome per cercare nel catalogo globale.")
        return None

    if not matches:
        st.caption(
            "Nessun risultato nel catalogo globale. Puoi validare il ticker "
            "con yfinance."
        )
        if st.button(
            "Valida con yfinance",
            key=f"{key_prefix}_validate_global",
            width="stretch"
        ):
            try:
                verified_record = validate_custom_ticker(search_text)
                save_verified_symbol(verified_record)
                add_ticker_to_watchlist(verified_record["ticker"])
                set_asset_focus(verified_record["ticker"])
                st.success(
                    f"{verified_record['ticker']} validato e aggiunto."
                )
                st.rerun()
            except Exception as error:
                st.warning(f"Ticker non validato: {error}")
        return None

    match_options = matches[:100]
    selected_asset = st.selectbox(
        "Risultati catalogo globale",
        options=match_options,
        format_func=lambda asset: (
            f"{asset['ticker']} - {asset.get('name', asset['ticker'])} "
            f"({asset.get('market', '-')})"
        ),
        key=f"{key_prefix}_global_asset_result"
    )

    if selected_asset["market"] not in selected_market_names:
        st.info(
            "Questo asset esiste nel catalogo globale ma non nei mercati "
            "attivi dello screener."
        )

    detail_items = [
        ("Gruppo", selected_asset.get("group", "-")),
        ("Mercato", selected_asset.get("market", "-")),
        ("Tipo", selected_asset.get("asset_type", "-")),
        ("Exchange", selected_asset.get("exchange", "-")),
        ("Valuta", selected_asset.get("currency", "-"))
    ]

    if compact:
        st.caption(
            " | ".join(
                f"{label}: {value}"
                for label, value in detail_items
                if value
            )
        )

        if st.button(
            "Aggiungi a watchlist",
            key=f"{key_prefix}_add_watchlist",
            width="stretch"
        ):
            add_ticker_to_watchlist(selected_asset["ticker"])
            st.success(f"{selected_asset['ticker']} aggiunto alla watchlist.")
            st.rerun()

        if allow_basket and st.button(
            "Aggiungi al paniere",
            key=f"{key_prefix}_add_basket",
            width="stretch"
        ):
            add_ticker_to_manual_basket(selected_asset["ticker"])
            st.success(f"{selected_asset['ticker']} aggiunto al paniere.")
            st.rerun()

        if st.button(
            "Imposta focus",
            key=f"{key_prefix}_set_focus",
            width="stretch"
        ):
            set_asset_focus(selected_asset["ticker"])
            st.rerun()
    else:
        detail_columns = st.columns(5)

        for column, (label, value) in zip(detail_columns, detail_items):
            column.metric(label, value)

        action_columns = st.columns(3 if allow_basket else 2)

        if action_columns[0].button(
            "Aggiungi a watchlist",
            key=f"{key_prefix}_add_watchlist",
            width="stretch"
        ):
            add_ticker_to_watchlist(selected_asset["ticker"])
            st.success(f"{selected_asset['ticker']} aggiunto alla watchlist.")
            st.rerun()

        if action_columns[1].button(
            "Imposta focus",
            key=f"{key_prefix}_set_focus",
            width="stretch"
        ):
            set_asset_focus(selected_asset["ticker"])
            st.rerun()

        if allow_basket and action_columns[2].button(
            "Aggiungi al paniere",
            key=f"{key_prefix}_add_basket",
            width="stretch"
        ):
            add_ticker_to_manual_basket(selected_asset["ticker"])
            st.success(f"{selected_asset['ticker']} aggiunto al paniere.")
            st.rerun()

    return selected_asset


def get_preset_value(preset: dict, key: str):
    return preset.get(key, DEFAULT_BACKTEST_PRESETS["3 - Balanced Rotation"][key])


def get_preset_guidance(name: str, preset: dict) -> dict:
    if name in PRESET_GUIDANCE:
        return PRESET_GUIDANCE[name]

    active_tools = ["EMA" if preset.get("ma_type") == "EMA" else "SMA"]
    if preset.get("use_adx_filter"):
        active_tools.append("ADX")
    if preset.get("use_macd_filter"):
        active_tools.append("MACD")
    if preset.get("use_volume_filter"):
        active_tools.append("volume")

    return {
        "risk": "Personalizzato",
        "description": "Preset creato dall'utente.",
        "behavior": (
            "Usa i parametri salvati nel tuo profilo custom; controlla la "
            "sezione avanzata per il dettaglio."
        ),
        "tools": ", ".join(active_tools)
    }


def summarize_preset_behavior(preset: dict) -> str:
    filters = []

    if preset.get("use_adx_filter"):
        filters.append(f"ADX >= {preset['adx_min']}")
    if preset.get("use_macd_filter"):
        filters.append("MACD positivo")
    if preset.get("use_volume_filter"):
        filters.append(f"volume >= {preset['volume_ratio_min']}x media")

    filter_text = ", ".join(filters) if filters else "senza conferme extra"

    return (
        f"Trend {preset['ma_type']} "
        f"{preset['fast_ma_period']}/{preset['slow_ma_period']}/"
        f"{preset['long_ma_period']}; RSI buy "
        f"{preset['rsi_buy_min']}-{preset['rsi_buy_max']}; "
        f"volatilita max {preset['max_volatility_pct']}%; "
        f"hold minimo {preset['min_hold_weeks']} settimane; {filter_text}."
    )


def render_watchlist_button(ticker: str, key: str):
    watchlist = st.session_state.setdefault("favorite_watchlist", [])
    is_favorite = ticker in watchlist
    label = "★" if is_favorite else "☆"

    if st.button(label, key=key, width="stretch"):
        if is_favorite:
            watchlist = [item for item in watchlist if item != ticker]
        else:
            watchlist = merge_unique_tickers(watchlist, [ticker])

        st.session_state["favorite_watchlist"] = watchlist
        save_watchlist(watchlist)
        st.rerun()


def render_asset_catalog(asset_records: list, key_prefix: str):
    if not asset_records:
        st.info("Catalogo asset non disponibile per i mercati caricati.")
        return

    catalog = pd.DataFrame(asset_records)
    search_text = st.text_input(
        "Cerca ticker o nome",
        value="",
        key=f"{key_prefix}_asset_search"
    ).strip().lower()

    if search_text:
        catalog = catalog[
            catalog["ticker"].str.lower().str.contains(search_text) |
            catalog["name"].astype(str).str.lower().str.contains(search_text)
        ]

    st.caption(f"Asset in catalogo: {len(catalog)}")

    for market_name in get_market_names():
        market_catalog = catalog[catalog["market"] == market_name]

        if market_catalog.empty:
            continue

        with st.expander(
            f"{market_name} ({len(market_catalog)})",
            expanded=market_name == selected_market
        ):
            for _, asset in market_catalog.head(200).iterrows():
                col1, col2 = st.columns([7, 1])
                col1.caption(format_asset_label(asset))
                render_watchlist_button(
                    asset["ticker"],
                    key=f"{key_prefix}_star_{market_name}_{asset['ticker']}"
                )

            if len(market_catalog) > 200:
                st.caption("Mostrati i primi 200 risultati filtrati.")


def get_assets_for_markets(asset_records: list, market_names: list) -> list:
    assets = []
    seen_tickers = set()

    for asset in asset_records:
        ticker = asset.get("ticker")
        if asset.get("market") not in market_names or not ticker:
            continue

        if ticker not in seen_tickers:
            assets.append(asset)
            seen_tickers.add(ticker)

    return assets


def build_screener_dataframe(
    asset_records: list,
    scanner: pd.DataFrame,
    watchlist: list
) -> pd.DataFrame:
    screener = pd.DataFrame(asset_records)

    if screener.empty:
        return pd.DataFrame()

    scanner_columns = [
        "ticker",
        "data_ultima_chiusura",
        "close",
        "scanner_score",
        "setup_score",
        "opportunity_label",
        "reason",
        "signal",
        "market_regime",
        "rsi",
        "volatility_%",
        "adx",
        "macd",
        "macd_hist",
        "volume_ratio",
        "bb_lower",
        "bb_middle",
        "bb_upper",
        "bb_bandwidth",
        "bb_percent_b",
        "data_status",
        "data_quality_reason",
        "price_rows",
        "latest_price_date",
        "min_history_ok",
        "selection_score",
        "label_score",
        "score_schema_version",
        "buy_gate_passed",
        "buy_gate_fail_reasons",
        "score_consistency_status"
    ]
    available_columns = [
        column for column in scanner_columns
        if column in scanner.columns
    ]

    if available_columns:
        screener = screener.merge(
            scanner[available_columns],
            on="ticker",
            how="left"
        )

    screener["watchlist"] = screener["ticker"].isin(watchlist)
    display_columns = [
        "watchlist",
        "group",
        "market",
        "ticker",
        "name",
        "asset_type",
        "exchange",
        "currency",
        "data_ultima_chiusura",
        "close",
        "scanner_score",
        "setup_score",
        "opportunity_label",
        "signal",
        "market_regime",
        "reason",
        "rsi",
        "volatility_%",
        "adx",
        "macd",
        "macd_hist",
        "volume_ratio",
        "bb_lower",
        "bb_middle",
        "bb_upper",
        "bb_bandwidth",
        "bb_percent_b",
        "data_status",
        "data_quality_reason",
        "price_rows",
        "latest_price_date",
        "min_history_ok",
        "selection_score",
        "label_score",
        "score_schema_version",
        "buy_gate_passed",
        "buy_gate_fail_reasons",
        "score_consistency_status"
    ]

    for column in display_columns:
        if column not in screener.columns:
            screener[column] = None

    return screener[display_columns].sort_values(
        by=["watchlist", "setup_score", "scanner_score", "market", "ticker"],
        ascending=[False, False, False, True, True],
        na_position="last"
    ).reset_index(drop=True)


def render_screener_editor(
    screener: pd.DataFrame,
    key: str,
    column_view: str = "Completa"
) -> pd.DataFrame:
    visible_columns = get_screener_columns(screener, column_view)
    visible_screener = screener[visible_columns].copy()

    return st.data_editor(
        visible_screener,
        key=key,
        width="stretch",
        height=520,
        hide_index=True,
        disabled=[
            column for column in visible_screener.columns
            if column != "watchlist"
        ],
        column_config={
            "watchlist": st.column_config.CheckboxColumn("Watchlist"),
            "group": "Gruppo",
            "market": "Mercato",
            "ticker": "Ticker",
            "name": "Nome",
            "asset_type": "Tipo",
            "exchange": "Exchange",
            "currency": "Valuta",
            "data_ultima_chiusura": "Ultima chiusura",
            "close": st.column_config.NumberColumn(
                "Prezzo",
                format="%.2f",
                width="small"
            ),
            "scanner_score": st.column_config.NumberColumn(
                "Scanner",
                format="%.2f",
                width="small"
            ),
            "setup_score": st.column_config.NumberColumn(
                "Setup",
                format="%.2f",
                width="small"
            ),
            "opportunity_label": "Opportunita",
            "signal": "Segnale",
            "market_regime": "Regime",
            "reason": "Motivo",
            "rsi": st.column_config.NumberColumn(
                "RSI",
                format="%.2f",
                width="small"
            ),
            "volatility_%": st.column_config.NumberColumn(
                "ATR %",
                format="%.2f",
                width="small"
            ),
            "adx": st.column_config.NumberColumn("ADX", format="%.2f"),
            "macd": st.column_config.NumberColumn("MACD", format="%.4f"),
            "macd_hist": st.column_config.NumberColumn(
                "MACD Hist",
                format="%.4f"
            ),
            "volume_ratio": st.column_config.NumberColumn(
                "Vol x",
                format="%.2f",
                width="small"
            ),
            "bb_lower": st.column_config.NumberColumn(
                "BB Low",
                format="%.2f"
            ),
            "bb_middle": st.column_config.NumberColumn(
                "BB Mid",
                format="%.2f"
            ),
            "bb_upper": st.column_config.NumberColumn(
                "BB High",
                format="%.2f"
            ),
            "bb_bandwidth": st.column_config.NumberColumn(
                "BB Width %",
                format="%.2f"
            ),
            "bb_percent_b": st.column_config.NumberColumn(
                "BB %B",
                format="%.2f"
            )
        }
    )


def sync_watchlist_from_editor(edited_screener: pd.DataFrame):
    if edited_screener.empty:
        return

    edited_tickers = set(edited_screener["ticker"].tolist())
    current_watchlist = set(st.session_state["favorite_watchlist"])
    unchanged_tickers = current_watchlist - edited_tickers
    selected_tickers = set(
        edited_screener[edited_screener["watchlist"]]["ticker"].tolist()
    )
    new_watchlist = sorted(unchanged_tickers | selected_tickers)

    if new_watchlist != sorted(current_watchlist):
        st.session_state["favorite_watchlist"] = new_watchlist
        save_watchlist(new_watchlist)


def calculate_drawdown_from_capital(history: pd.DataFrame) -> float:
    if history.empty or "capital" not in history.columns:
        return 0

    capital = history["capital"].dropna()

    if capital.empty:
        return 0

    peak = capital.cummax()
    drawdown = ((capital - peak) / peak) * 100

    return round(drawdown.min(), 2)


def to_float(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_equity_figure(
    equity: pd.DataFrame,
    portfolio: pd.DataFrame,
    title: str
):
    figure = go.Figure()

    if not equity.empty and {"date", "equity"}.issubset(equity.columns):
        equity = equity.copy()
        equity["date"] = pd.to_datetime(equity["date"])

        figure.add_trace(
            go.Scatter(
                x=equity["date"],
                y=equity["equity"],
                mode="lines",
                name="Single Asset",
                line=dict(color="deepskyblue", width=2)
            )
        )

    if not portfolio.empty and {"scan_date", "capital"}.issubset(
        portfolio.columns
    ):
        portfolio = portfolio.copy()
        portfolio["scan_date"] = pd.to_datetime(portfolio["scan_date"])

        figure.add_trace(
            go.Scatter(
                x=portfolio["scan_date"],
                y=portfolio["capital"],
                mode="lines",
                name="Portfolio",
                line=dict(color="orange", width=3)
            )
        )

    figure.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Portfolio Value",
        hovermode="x unified",
        height=420,
        margin=dict(l=20, r=20, t=50, b=30)
    )

    return figure


def build_backtest_figure(
    strategy_curves: list,
    benchmark_curves: list,
    selected_market: str
):
    figure = go.Figure()

    strategy_colors = [
        "orange",
        "deepskyblue",
        "limegreen",
        "violet",
        "gold",
        "tomato"
    ]

    for index, strategy in enumerate(strategy_curves):
        history = strategy["history"].copy()
        if history.empty:
            continue

        history["scan_date"] = pd.to_datetime(history["scan_date"])

        figure.add_trace(
            go.Scatter(
                x=history["scan_date"],
                y=history["capital"],
                mode="lines",
                name=strategy["name"],
                line=dict(
                    color=strategy_colors[index % len(strategy_colors)],
                    width=3
                )
            )
        )

    for benchmark in benchmark_curves:
        benchmark_history = benchmark["history"].copy()
        benchmark_history["date"] = pd.to_datetime(
            benchmark_history["date"]
        )

        figure.add_trace(
            go.Scatter(
                x=benchmark_history["date"],
                y=benchmark_history["capital"],
                mode="lines",
                name=benchmark["name"],
                line=dict(color=benchmark["color"], width=2)
            )
        )

    figure.update_layout(
        title=f"Dynamic Portfolio vs Benchmark - {selected_market}",
        xaxis_title="Date",
        yaxis_title="Portfolio Value",
        hovermode="x unified",
        height=460,
        margin=dict(l=20, r=20, t=50, b=30)
    )

    return figure


def format_seconds(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "fase finale in corso"

    total_seconds = int(seconds)
    minutes, remaining_seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"

    return f"{remaining_seconds}s"


def build_backtest_progress_tracker(total_steps: int):
    total_steps = max(total_steps, 1)
    start_time = time.time()
    state = {"current_step": 0}
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    def update(message: str, step_increment: int = 0):
        if step_increment:
            state["current_step"] = min(
                total_steps,
                state["current_step"] + step_increment
            )

        progress_ratio = min(state["current_step"] / total_steps, 1.0)
        elapsed = time.time() - start_time
        eta = None

        if state["current_step"] > 0 and progress_ratio < 1:
            eta = (elapsed / state["current_step"]) * (
                total_steps - state["current_step"]
            )

        progress_bar.progress(progress_ratio)
        eta_text = format_seconds(eta)

        if progress_ratio < 1 and eta is None:
            eta_text = "calcolo ETA"
        elif progress_ratio < 1 and eta is not None and eta < 1:
            eta_text = "<1s"
        elif progress_ratio >= 1 and "completato" not in message.lower():
            eta_text = "fase finale in corso"

        status_placeholder.info(
            f"{message} | Step {state['current_step']}/{total_steps} | "
            f"Tempo {format_seconds(elapsed)} | ETA {eta_text}"
        )

    def callback(event: dict):
        phase = event.get("phase", "Backtest")
        preset = event.get("preset")
        ticker = event.get("ticker")
        ticker_index = event.get("ticker_index")
        ticker_total = event.get("ticker_total")
        week_index = event.get("week_index")
        week_total = event.get("week_total")
        skipped_tickers = event.get("skipped_tickers")
        batch_index = event.get("batch_index")
        batch_total = event.get("batch_total")
        loaded_tickers = event.get("loaded_tickers")
        missing_tickers = event.get("missing_tickers")
        stale_tickers = event.get("stale_tickers")

        parts = [phase]

        if preset:
            parts.append(f"preset {preset}")
        if ticker:
            parts.append(f"ticker {ticker_index}/{ticker_total}: {ticker}")
        if week_index:
            parts.append(f"settimana {week_index}/{week_total}")
        if batch_index:
            parts.append(f"batch {batch_index}/{batch_total}")
        if loaded_tickers:
            parts.append(f"caricati {loaded_tickers}")
        if missing_tickers:
            parts.append(f"mancanti {missing_tickers}")
        if stale_tickers:
            parts.append(f"stale {stale_tickers}")
        if skipped_tickers:
            parts.append(f"esclusi {skipped_tickers}")

        update(
            " - ".join(parts),
            step_increment=int(event.get("step_increment", 0))
        )

    return update, callback


def supports_backtest_progress_callback() -> bool:
    signature = inspect.signature(run_portfolio_backtest)

    return "progress_callback" in signature.parameters


def get_chart_candle_options(range_label: str) -> list:
    return CHART_CANDLES_BY_RANGE.get(range_label, ["1d"])


def filter_chart_data_to_range(data: pd.DataFrame, range_label: str) -> pd.DataFrame:
    if data.empty or "date" not in data.columns:
        return data

    data = data.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.dropna(subset=["date"]).sort_values("date")

    if data.empty:
        return data

    latest_date = data["date"].max()

    if range_label == "1D":
        latest_day = latest_date.date()
        return data[data["date"].dt.date == latest_day]

    if range_label == "1W":
        start_date = latest_date - pd.DateOffset(weeks=1)
    elif range_label == "1M":
        start_date = latest_date - pd.DateOffset(months=1)
    elif range_label == "6M":
        start_date = latest_date - pd.DateOffset(months=6)
    elif range_label == "YTD":
        start_date = pd.Timestamp(latest_date.year, 1, 1)
    elif range_label == "1A":
        start_date = latest_date - pd.DateOffset(years=1)
    else:
        start_date = latest_date - pd.DateOffset(years=5)

    return data[data["date"] >= start_date]


def normalize_asset_price_data(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data

    normalized = data.copy()

    if "date" not in normalized.columns:
        date_alias = next(
            (
                column for column in ["datetime", "index"]
                if column in normalized.columns
            ),
            None
        )
        if date_alias:
            normalized = normalized.rename(columns={date_alias: "date"})

    required_columns = ["date", "open", "high", "low", "close", "volume"]
    if not all(column in normalized.columns for column in required_columns):
        return pd.DataFrame(columns=required_columns)

    normalized = normalized[required_columns].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")

    for column in ["open", "high", "low", "close", "volume"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = (
        normalized
        .dropna(subset=["date", "open", "high", "low", "close"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    return normalized


def resample_ohlcv(data: pd.DataFrame, rule: str) -> pd.DataFrame:
    if data.empty or "date" not in data.columns:
        return data

    required_columns = ["open", "high", "low", "close", "volume"]

    if not all(column in data.columns for column in required_columns):
        return data

    resampled = (
        data
        .copy()
        .set_index(pd.to_datetime(data["date"]))
        .resample(rule)
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )

    return resampled


def build_chart_price_attempts(range_label: str, candle_label: str) -> list:
    range_config = ASSET_RANGE_OPTIONS[range_label]
    candle_config = CHART_CANDLE_OPTIONS[candle_label]
    attempts = [
        (
            candle_label,
            {
                "period": range_config["period"],
                "interval": candle_config["interval"],
                "resample": candle_config["resample"],
                "filter_range": range_label,
            }
        )
    ]

    if candle_label in ["5m", "15m"]:
        attempts.append((
            "30m fallback",
            {
                "period": range_config["period"],
                "interval": "30m",
                "resample": None,
                "filter_range": range_label,
            }
        ))

    if candle_label in ["5m", "15m", "30m"]:
        attempts.append((
            "1h fallback",
            {
                "period": range_config["period"],
                "interval": "60m",
                "resample": None,
                "filter_range": range_label,
            }
        ))

    if range_label == "1D":
        attempts.append((
            "daily fallback",
            {
                "period": "1mo",
                "interval": "1d",
                "resample": None,
                "filter_range": "1M",
            }
        ))

    if candle_label != "1d":
        attempts.append((
            "1D fallback",
            {
                "period": range_config["period"] if range_label != "1D" else "1mo",
                "interval": "1d",
                "resample": None,
                "filter_range": range_label if range_label != "1D" else "1M",
            }
        ))

    return attempts


def load_asset_price_data_with_fallback(
    ticker: str,
    range_label: str,
    candle_label: str
):
    range_config = ASSET_RANGE_OPTIONS[range_label]
    attempts = build_chart_price_attempts(range_label, candle_label)

    last_error = None

    for attempt_label, attempt_config in attempts:
        try:
            data = download_data(
                ticker=ticker,
                period=attempt_config["period"],
                interval=attempt_config["interval"]
            )
            data = normalize_asset_price_data(data)

            if data.empty:
                last_error = ValueError("dataset vuoto o formato prezzi non valido")
                continue

            data = filter_chart_data_to_range(
                data=data,
                range_label=attempt_config["filter_range"]
            )

            if attempt_config.get("resample"):
                data = resample_ohlcv(
                    data=data,
                    rule=attempt_config["resample"]
                )

            if data.empty or len(data) < 2:
                last_error = ValueError("pochi punti nel range richiesto")
                continue

            fallback_note = None
            if attempt_label != candle_label:
                fallback_note = (
                    f"Candela {candle_label} non disponibile dal provider; "
                    f"mostro {attempt_label}."
                )

            return data, {**range_config, **attempt_config}, fallback_note

        except Exception as error:
            last_error = error

    raise ValueError(f"Nessun dato prezzo disponibile per {ticker}: {last_error}")


def get_chart_xaxis_range(data: pd.DataFrame):
    if data.empty or "date" not in data.columns:
        return None

    dates = pd.to_datetime(data["date"]).sort_values()

    if dates.empty:
        return None

    if len(dates) == 1:
        start = dates.iloc[0] - pd.Timedelta(days=1)
        end = dates.iloc[0] + pd.Timedelta(days=1)

        return [start, end]

    deltas = dates.diff().dropna()
    median_delta = deltas.median()

    if pd.isna(median_delta) or median_delta <= pd.Timedelta(0):
        median_delta = (dates.iloc[-1] - dates.iloc[0]) / 20

    padding = median_delta * 2

    return [dates.iloc[0] - padding, dates.iloc[-1] + padding]


def get_chart_rangebreaks(range_config: dict) -> list:
    interval = range_config.get("interval", "")
    rangebreaks = [dict(bounds=["sat", "mon"])]

    if interval.endswith("m") or interval.endswith("h"):
        rangebreaks.append(dict(bounds=[17, 9], pattern="hour"))

    return rangebreaks


def format_chart_volume(value) -> str:
    if pd.isna(value):
        return "-"

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"

    return f"{value:.0f}"


def build_klinechart_payload(data: pd.DataFrame) -> list:
    payload = []
    required_columns = ["date", "open", "high", "low", "close", "volume"]

    if data.empty or not all(column in data.columns for column in required_columns):
        return payload

    cleaned = data[required_columns].copy()
    cleaned = cleaned.dropna(subset=["date", "open", "high", "low", "close"])
    cleaned["date"] = pd.to_datetime(cleaned["date"])

    for _, row in cleaned.iterrows():
        payload.append({
            "timestamp": int(row["date"].timestamp() * 1000),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]) if pd.notna(row["volume"]) else 0
        })

    return payload


def build_klinechart_html(
    ticker: str,
    range_label: str,
    candle_label: str,
    data: pd.DataFrame
) -> str:
    payload = json.dumps(build_klinechart_payload(data), allow_nan=False)
    title = (
        f"{ticker} - {ASSET_RANGE_OPTIONS[range_label]['title']} "
        f"({CHART_CANDLE_OPTIONS[candle_label]['label']})"
    )

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://cdn.jsdelivr.net/npm/klinecharts@9.8.9/dist/umd/klinecharts.min.js"></script>
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      background: #0f1419;
      color: #d7dee8;
      font-family: Inter, Arial, sans-serif;
      overflow: hidden;
    }}
    .board {{
      height: 760px;
      display: flex;
      flex-direction: column;
      border: 1px solid #25313b;
      background: #0f1419;
    }}
    .topbar {{
      display: flex;
      gap: 8px;
      align-items: center;
      padding: 8px 10px;
      border-bottom: 1px solid #25313b;
      background: #111820;
      flex-wrap: wrap;
    }}
    .title {{
      font-weight: 700;
      margin-right: 8px;
      color: #f4f7fb;
      white-space: nowrap;
    }}
    .tool-group {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px;
      border: 1px solid #25313b;
      border-radius: 7px;
      background: #151d26;
    }}
    button, select {{
      border: 1px solid #344554;
      background: #19232d;
      color: #d7dee8;
      border-radius: 6px;
      min-height: 30px;
      padding: 5px 9px;
      font-weight: 600;
      outline: none;
    }}
    button {{
      cursor: pointer;
    }}
    button:hover, button.active, select:focus, button:focus {{
      border-color: #4aa3ff;
      background: #20364b;
      color: #ffffff;
    }}
    button.danger:hover {{
      border-color: #ff5a5f;
      background: #4b2028;
    }}
    button.subtle {{
      color: #aeb9c5;
    }}
    .section {{
      color: #8b9aaa;
      font-size: 12px;
      font-weight: 700;
      padding: 0 3px;
      white-space: nowrap;
    }}
    .fib-panel {{
      display: none;
      align-items: center;
      gap: 5px;
      color: #aeb9c5;
      font-size: 12px;
    }}
    .fib-panel.visible {{
      display: inline-flex;
    }}
    .fib-panel label {{
      display: inline-flex;
      align-items: center;
      gap: 3px;
      white-space: nowrap;
    }}
    #chart {{
      flex: 1;
      min-height: 0;
    }}
    .hint {{
      padding: 6px 10px;
      border-top: 1px solid #25313b;
      color: #9aa8b5;
      font-size: 12px;
      background: #111820;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .status {{
      color: #d7dee8;
    }}
    .error {{
      padding: 24px;
      color: #ffb4b4;
    }}
  </style>
</head>
<body>
  <div class="board">
    <div class="topbar">
      <div class="title">{title}</div>
      <div class="tool-group">
        <span class="section">Disegno</span>
        <select id="drawing-tool" title="Seleziona strumento di disegno">
          <option value="">Scegli strumento</option>
          <option value="segment">Segmento</option>
          <option value="rayLine">Raggio</option>
          <option value="straightLine">Retta</option>
          <option value="horizontalStraightLine">Orizzontale</option>
          <option value="priceLine">Linea prezzo</option>
          <option value="priceChannelLine">Canale</option>
          <option value="parallelStraightLine">Parallele</option>
          <option value="proFibonacci">Fibonacci</option>
          <option value="measureLine">Righello</option>
        </select>
        <button id="arm-tool" title="Attiva lo strumento selezionato">Attiva</button>
        <button id="idle-tool" class="subtle" title="Torna a navigazione">Naviga</button>
      </div>
      <div class="tool-group fib-panel" id="fib-panel">
        <span class="section">Fib</span>
        <label><input type="checkbox" data-fib="0" checked>0</label>
        <label><input type="checkbox" data-fib="0.236" checked>23.6</label>
        <label><input type="checkbox" data-fib="0.382" checked>38.2</label>
        <label><input type="checkbox" data-fib="0.5" checked>50</label>
        <label><input type="checkbox" data-fib="0.618" checked>61.8</label>
        <label><input type="checkbox" data-fib="0.786">78.6</label>
        <label><input type="checkbox" data-fib="1" checked>100</label>
        <label><input type="checkbox" data-fib="1.618">161.8</label>
      </div>
      <div class="tool-group">
        <span class="section">Azioni</span>
        <button id="delete-selected" title="Cancella il disegno selezionato">Elimina selezionato</button>
        <button class="danger" id="clear-overlays" title="Cancella tutti i disegni manuali">Cancella disegni</button>
      </div>
      <div class="tool-group">
        <span class="section">Indicatori</span>
        <select id="indicator-tool" title="Seleziona indicatore">
          <option value="">Aggiungi indicatore</option>
          <option value="MA" data-overlay="1">MA</option>
          <option value="EMA" data-overlay="1">EMA</option>
          <option value="BOLL" data-overlay="1">BOLL</option>
          <option value="SAR" data-overlay="1">SAR</option>
          <option value="VOL">VOL</option>
          <option value="MACD">MACD</option>
          <option value="RSI">RSI</option>
          <option value="KDJ">KDJ</option>
        </select>
        <button id="add-indicator" title="Aggiungi l'indicatore selezionato">Aggiungi</button>
        <button id="reset-indicators" class="subtle" title="Ripristina indicatori base">Reset</button>
      </div>
    </div>
    <div id="chart"></div>
    <div class="hint">
      <span>Disegna nel grafico senza ricaricare Streamlit. Tasto destro o Canc/Backspace eliminano il disegno selezionato.</span>
      <span class="status" id="tool-status">Navigazione pronta.</span>
    </div>
  </div>
  <script>
    const data = {payload};
    const overlayGroupId = 'manual';
    const overlayIds = new Set();
    let selectedOverlayId = null;

    function fail(message) {{
      document.getElementById('chart').innerHTML =
        '<div class="error">' + message + '</div>';
    }}

    function setStatus(message) {{
      const status = document.getElementById('tool-status');
      if (status) {{
        status.textContent = message;
      }}
    }}

    function getFibLevels() {{
      const levels = [];
      document.querySelectorAll('input[data-fib]').forEach(input => {{
        if (input.checked) {{
          levels.push(Number(input.dataset.fib));
        }}
      }});
      return levels.length ? levels : [0, 0.382, 0.5, 0.618, 1];
    }}

    if (!window.klinecharts) {{
      fail('KLineCharts non disponibile. Controlla la connessione al CDN o usa il fallback Plotly.');
    }} else if (!data.length) {{
      fail('Dati OHLCV insufficienti per la trading board.');
    }} else {{
      const chart = klinecharts.init('chart', {{
        styles: {{
          grid: {{
            horizontal: {{ color: 'rgba(215,222,232,0.12)' }},
            vertical: {{ color: 'rgba(215,222,232,0.12)' }}
          }},
          candle: {{
            bar: {{
              upColor: '#00a878',
              downColor: '#e5252a',
              noChangeColor: '#8b9aaa'
            }},
            tooltip: {{ showRule: 'always' }}
          }},
          crosshair: {{
            horizontal: {{ line: {{ color: '#d7dee8', style: 'dashed' }} }},
            vertical: {{ line: {{ color: '#d7dee8', style: 'dashed' }} }}
          }},
          overlay: {{
            point: {{
              color: '#4aa3ff',
              borderColor: '#f4f7fb',
              borderSize: 1,
              radius: 4,
              activeColor: '#f4c430',
              activeBorderColor: '#f4f7fb',
              activeBorderSize: 1,
              activeRadius: 5
            }},
            line: {{
              color: '#4aa3ff',
              size: 2,
              activeColor: '#f4c430',
              activeSize: 2
            }}
          }}
        }}
      }});

      klinecharts.registerOverlay({{
        name: 'measureLine',
        totalStep: 3,
        needDefaultPointFigure: true,
        needDefaultXAxisFigure: true,
        needDefaultYAxisFigure: true,
        mode: 'weak_magnet',
        modeSensitivity: 8,
        createPointFigures: (params) => {{
          const coordinates = params.coordinates || [];
          const points = (params.overlay && params.overlay.points) || [];
          if (coordinates.length < 2 || points.length < 2) {{
            return [];
          }}
          const p0 = points[0];
          const p1 = points[1];
          const valueDelta = (p1.value || 0) - (p0.value || 0);
          const pct = p0.value ? (valueDelta / p0.value) * 100 : 0;
          const bars = Math.abs((p1.dataIndex || 0) - (p0.dataIndex || 0));
          const direction = valueDelta >= 0 ? '+' : '';
          const midX = (coordinates[0].x + coordinates[1].x) / 2;
          const midY = (coordinates[0].y + coordinates[1].y) / 2;
          const startDate = p0.timestamp ? new Date(p0.timestamp).toISOString().slice(0, 10) : '';
          const endDate = p1.timestamp ? new Date(p1.timestamp).toISOString().slice(0, 10) : '';
          const text = direction + valueDelta.toFixed(2) + ' (' + direction + pct.toFixed(2) + '%) | ' + bars + ' barre' +
            (startDate && endDate ? ' | ' + startDate + ' -> ' + endDate : '');
          return [
            {{
              type: 'line',
              attrs: {{ coordinates }},
              styles: {{ color: '#f4c430', size: 2, style: 'dashed' }}
            }},
            {{
              type: 'text',
              attrs: {{
                x: midX + 8,
                y: midY - 8,
                text,
                align: 'left',
                baseline: 'bottom'
              }},
              styles: {{
                color: '#f4f7fb',
                size: 12,
                backgroundColor: 'rgba(15,20,25,0.86)',
                paddingLeft: 5,
                paddingRight: 5,
                paddingTop: 3,
                paddingBottom: 3,
                borderColor: '#f4c430',
                borderSize: 1,
                borderRadius: 4
              }}
            }}
          ];
        }}
      }});

      klinecharts.registerOverlay({{
        name: 'proFibonacci',
        totalStep: 3,
        needDefaultPointFigure: true,
        needDefaultXAxisFigure: true,
        needDefaultYAxisFigure: true,
        mode: 'weak_magnet',
        modeSensitivity: 8,
        createPointFigures: (params) => {{
          const coordinates = params.coordinates || [];
          const points = (params.overlay && params.overlay.points) || [];
          const levels = (params.overlay && params.overlay.extendData && params.overlay.extendData.levels) ||
            [0, 0.382, 0.5, 0.618, 1];
          if (coordinates.length < 2 || points.length < 2) {{
            return [];
          }}
          const x1 = Math.min(coordinates[0].x, coordinates[1].x);
          const x2 = Math.max(coordinates[0].x, coordinates[1].x);
          const figures = [{{
            type: 'line',
            attrs: {{ coordinates }},
            styles: {{ color: 'rgba(244,196,48,0.75)', size: 1, style: 'dashed' }}
          }}];
          levels.forEach(level => {{
            const y = coordinates[0].y + ((coordinates[1].y - coordinates[0].y) * level);
            const value = (points[0].value || 0) + (((points[1].value || 0) - (points[0].value || 0)) * level);
            const pctLabel = (level * 100).toFixed(level === 0 || level === 1 ? 0 : 1) + '%';
            figures.push({{
              type: 'line',
              attrs: {{ coordinates: [{{ x: x1, y }}, {{ x: x2, y }}] }},
              styles: {{ color: '#4aa3ff', size: level === 0 || level === 1 ? 2 : 1 }}
            }});
            figures.push({{
              type: 'text',
              attrs: {{
                x: x2 + 8,
                y: y - 3,
                text: pctLabel + '  ' + value.toFixed(2),
                align: 'left',
                baseline: 'bottom'
              }},
              styles: {{
                color: '#f4f7fb',
                size: 11,
                backgroundColor: 'rgba(15,20,25,0.84)',
                paddingLeft: 4,
                paddingRight: 4,
                paddingTop: 2,
                paddingBottom: 2,
                borderColor: 'rgba(74,163,255,0.6)',
                borderSize: 1,
                borderRadius: 3
              }}
            }});
          }});
          return figures;
        }}
      }});

      chart.applyNewData(data);
      chart.createIndicator('VOL');
      chart.createIndicator('MA', true, {{ id: 'candle_pane' }});

      function clearActiveButtons() {{
        document.querySelectorAll('button').forEach(item => item.classList.remove('active'));
      }}

      function rememberOverlay(event) {{
        if (event && event.overlay && event.overlay.id) {{
          overlayIds.add(event.overlay.id);
          selectedOverlayId = event.overlay.id;
        }}
        return true;
      }}

      function createManualOverlay(toolName) {{
        const overlayConfig = {{
          name: toolName,
          groupId: overlayGroupId,
          mode: 'weak_magnet',
          modeSensitivity: 8,
          needDefaultPointFigure: true,
          needDefaultXAxisFigure: true,
          needDefaultYAxisFigure: true,
          onDrawEnd: event => {{
            rememberOverlay(event);
            setStatus('Disegno creato. Selezionalo e premi Canc per eliminarlo.');
            return true;
          }},
          onSelected: event => {{
            rememberOverlay(event);
            setStatus('Disegno selezionato: pronto per modifica o eliminazione.');
            return true;
          }},
          onRemoved: event => {{
            if (event && event.overlay && event.overlay.id) {{
              overlayIds.delete(event.overlay.id);
              if (selectedOverlayId === event.overlay.id) {{
                selectedOverlayId = null;
              }}
            }}
            return true;
          }}
        }};
        if (toolName === 'proFibonacci') {{
          overlayConfig.extendData = {{ levels: getFibLevels() }};
        }}
        const overlayId = chart.createOverlay(overlayConfig);
        if (Array.isArray(overlayId)) {{
          overlayId.filter(Boolean).forEach(id => overlayIds.add(id));
        }} else if (overlayId) {{
          overlayIds.add(overlayId);
          selectedOverlayId = overlayId;
        }}
      }}

      function armSelectedTool() {{
        const select = document.getElementById('drawing-tool');
        const toolName = select.value;
        if (!toolName) {{
          setStatus('Scegli prima uno strumento di disegno.');
          return;
        }}
        clearActiveButtons();
        document.getElementById('arm-tool').classList.add('active');
        createManualOverlay(toolName);
        setStatus('Strumento attivo: ' + select.options[select.selectedIndex].text + '. Disegna sul grafico.');
      }}

      document.getElementById('drawing-tool').addEventListener('change', event => {{
        document.getElementById('fib-panel').classList.toggle('visible', event.target.value === 'proFibonacci');
        if (event.target.value) {{
          armSelectedTool();
        }} else {{
          setStatus('Navigazione pronta.');
        }}
      }});

      document.getElementById('arm-tool').addEventListener('click', armSelectedTool);
      document.getElementById('idle-tool').addEventListener('click', () => {{
        document.getElementById('drawing-tool').value = '';
        document.getElementById('fib-panel').classList.remove('visible');
        clearActiveButtons();
        document.getElementById('idle-tool').classList.add('active');
        setStatus('Navigazione pronta.');
      }});

      document.querySelectorAll('input[data-fib]').forEach(input => {{
        input.addEventListener('change', () => {{
          setStatus('Livelli Fibonacci aggiornati per il prossimo disegno.');
        }});
      }});

      function deleteSelectedOverlay() {{
        if (selectedOverlayId) {{
          const removed = chart.removeOverlay({{ id: selectedOverlayId }});
          if (removed) {{
            overlayIds.delete(selectedOverlayId);
            selectedOverlayId = null;
            setStatus('Disegno selezionato eliminato.');
            return;
          }}
        }}
        setStatus('Nessun disegno selezionato da eliminare.');
      }}

      document.getElementById('delete-selected').addEventListener('click', deleteSelectedOverlay);
      document.getElementById('clear-overlays').addEventListener('click', () => {{
        const removed = chart.removeOverlay({{ groupId: overlayGroupId }});
        overlayIds.clear();
        selectedOverlayId = null;
        setStatus(removed ? 'Tutti i disegni sono stati eliminati.' : 'Nessun disegno da eliminare.');
      }});

      document.getElementById('add-indicator').addEventListener('click', () => {{
        const select = document.getElementById('indicator-tool');
        const name = select.value;
        if (!name) {{
          setStatus('Scegli prima un indicatore.');
          return;
        }}
        const option = select.options[select.selectedIndex];
        if (option.dataset.overlay === '1') {{
          chart.createIndicator(name, true, {{ id: 'candle_pane' }});
        }} else {{
          chart.createIndicator(name);
        }}
        clearActiveButtons();
        document.getElementById('add-indicator').classList.add('active');
        setStatus('Indicatore aggiunto: ' + name + '.');
      }});

      document.getElementById('reset-indicators').addEventListener('click', () => {{
        ['MA', 'EMA', 'BOLL', 'SAR', 'VOL', 'MACD', 'RSI', 'KDJ'].forEach(name => {{
          chart.removeIndicator({{ name }});
        }});
        chart.createIndicator('VOL');
        chart.createIndicator('MA', true, {{ id: 'candle_pane' }});
        clearActiveButtons();
        document.getElementById('reset-indicators').classList.add('active');
        setStatus('Indicatori ripristinati: VOL e MA.');
      }});

      window.addEventListener('keydown', event => {{
        if (event.key === 'Delete' || event.key === 'Backspace') {{
          deleteSelectedOverlay();
        }}
        if (event.key === 'Escape') {{
          document.getElementById('drawing-tool').value = '';
          document.getElementById('fib-panel').classList.remove('visible');
          clearActiveButtons();
          setStatus('Navigazione pronta.');
        }}
      }});

      window.addEventListener('resize', () => chart.resize());
    }}
  </script>
</body>
</html>
"""


def add_chart_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:
    indicator_data = data.copy()

    for period in [20, 50, 200]:
        indicator_data[f"sma_{period}"] = (
            indicator_data["close"].rolling(period).mean()
        )
        indicator_data[f"ema_{period}"] = (
            indicator_data["close"].ewm(span=period, adjust=False).mean()
        )

    if all(column in indicator_data.columns for column in ["high", "low", "close", "volume"]):
        typical_price = (
            indicator_data["high"] +
            indicator_data["low"] +
            indicator_data["close"]
        ) / 3
        cumulative_volume = indicator_data["volume"].cumsum()
        cumulative_value = (typical_price * indicator_data["volume"]).cumsum()
        indicator_data["vwap"] = cumulative_value / cumulative_volume

    return indicator_data


def build_asset_price_figure(
    ticker: str,
    range_label: str,
    candle_label: str,
    chart_mode: str = "Line",
    overlays: list | None = None,
    strategy_config: dict | None = None
):
    data, range_config, fallback_note = load_asset_price_data_with_fallback(
        ticker=ticker,
        range_label=range_label,
        candle_label=candle_label
    )

    overlays = overlays or []
    indicator_data = data

    if overlays:
        try:
            indicator_data = add_indicators(
                data,
                strategy_config=strategy_config
            )
            chart_indicator_data = add_chart_technical_indicators(
                indicator_data
            )
            for column in chart_indicator_data.columns:
                if column not in indicator_data.columns:
                    indicator_data[column] = chart_indicator_data[column]
        except Exception:
            indicator_data = add_chart_technical_indicators(data)

    has_volume = "volume" in data.columns and data["volume"].notna().any()
    figure = make_subplots(
        rows=2 if has_volume else 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.78, 0.22] if has_volume else [1.0]
    )
    price_row = 1

    if chart_mode == "Candles" and all(
        column in data.columns
        for column in ["open", "high", "low", "close"]
    ):
        figure.add_trace(
            go.Candlestick(
                x=data["date"],
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                name=ticker,
                increasing_line_color="#00a878",
                increasing_fillcolor="#00a878",
                decreasing_line_color="#e5252a",
                decreasing_fillcolor="#e5252a",
                whiskerwidth=0.4
            ),
            row=price_row,
            col=1
        )
    else:
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["close"],
                mode="lines",
                name=ticker,
                line=dict(color="deepskyblue", width=2)
            ),
            row=price_row,
            col=1
        )

    if has_volume:
        volume_colors = [
            "#00a878" if close_value >= open_value else "#e5252a"
            for open_value, close_value in zip(data["open"], data["close"])
        ] if all(column in data.columns for column in ["open", "close"]) else "#5b6b7a"
        figure.add_trace(
            go.Bar(
                x=data["date"],
                y=data["volume"],
                name="Volume",
                marker_color=volume_colors,
                opacity=0.7,
                hovertemplate="Volume: %{y:,.0f}<extra></extra>"
            ),
            row=2,
            col=1
        )

    if "Medie trend" in overlays:
        for column, label in [
            ("trend_fast_ma", "MA veloce"),
            ("trend_slow_ma", "MA lenta"),
            ("trend_long_ma", "MA lungo")
        ]:
            if column in indicator_data.columns:
                figure.add_trace(
                    go.Scatter(
                        x=indicator_data["date"],
                        y=indicator_data[column],
                        mode="lines",
                        name=label,
                        line=dict(width=1.2)
                    ),
                    row=price_row,
                    col=1
                )

    if "EMA 20/50/200" in overlays:
        for column, label in [
            ("ema_20", "EMA 20"),
            ("ema_50", "EMA 50"),
            ("ema_200", "EMA 200")
        ]:
            if column in indicator_data.columns:
                figure.add_trace(
                    go.Scatter(
                        x=indicator_data["date"],
                        y=indicator_data[column],
                        mode="lines",
                        name=label,
                        line=dict(width=1)
                    ),
                    row=price_row,
                    col=1
                )

    if "SMA 50/200" in overlays:
        for column, label in [
            ("sma_50", "SMA 50"),
            ("sma_200", "SMA 200")
        ]:
            if column in indicator_data.columns:
                figure.add_trace(
                    go.Scatter(
                        x=indicator_data["date"],
                        y=indicator_data[column],
                        mode="lines",
                        name=label,
                        line=dict(width=1.1, dash="dash")
                    ),
                    row=price_row,
                    col=1
                )

    if "VWAP" in overlays and "vwap" in indicator_data.columns:
        figure.add_trace(
            go.Scatter(
                x=indicator_data["date"],
                y=indicator_data["vwap"],
                mode="lines",
                name="VWAP",
                line=dict(color="#f4c430", width=1.4)
            ),
            row=price_row,
            col=1
        )

    if "Bollinger" in overlays:
        for column, label in [
            ("bb_upper", "BB alta"),
            ("bb_middle", "BB media"),
            ("bb_lower", "BB bassa")
        ]:
            if column in indicator_data.columns:
                figure.add_trace(
                    go.Scatter(
                        x=indicator_data["date"],
                        y=indicator_data[column],
                        mode="lines",
                        name=label,
                        line=dict(width=1, dash="dot")
                    ),
                    row=price_row,
                    col=1
                )

    latest = data.dropna(subset=["close"]).iloc[-1]
    previous_close = (
        data.dropna(subset=["close"]).iloc[-2]["close"]
        if len(data.dropna(subset=["close"])) > 1
        else latest["close"]
    )
    close_delta = latest["close"] - previous_close
    close_delta_pct = (
        (close_delta / previous_close) * 100
        if previous_close
        else 0
    )
    latest_color = "#00a878" if close_delta >= 0 else "#e5252a"
    latest_volume = latest.get("volume", None)
    ohlc_text = (
        f"O:{latest.get('open', latest['close']):,.2f} "
        f"H:{latest.get('high', latest['close']):,.2f} "
        f"L:{latest.get('low', latest['close']):,.2f} "
        f"C:{latest['close']:,.2f} "
        f"V:{format_chart_volume(latest_volume)}"
    )
    change_text = f"{close_delta:+.2f} ({close_delta_pct:+.2f}%)"

    figure.add_hline(
        y=latest["close"],
        line=dict(color=latest_color, width=1, dash="dot"),
        annotation_text=f"{latest['close']:,.2f}",
        annotation_position="right",
        row=price_row,
        col=1
    )
    figure.add_annotation(
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.99,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        text=f"<b>{ohlc_text}</b><br><span style='color:{latest_color}'>{change_text}</span>",
        bgcolor="rgba(17, 24, 31, 0.72)",
        bordercolor="rgba(255,255,255,0.05)",
        font=dict(size=12, color="#d7dee8")
    )

    figure.update_layout(
        title=(
            f"{ticker} - {ASSET_RANGE_OPTIONS[range_label]['title']} "
            f"({CHART_CANDLE_OPTIONS[candle_label]['label']})"
        ),
        xaxis_title="Date",
        hovermode="x",
        height=620,
        margin=dict(l=10, r=55, t=50, b=30),
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        uirevision=f"{ticker}-{range_label}-{candle_label}",
        selectionrevision=f"{ticker}-{range_label}-{candle_label}",
        editrevision=f"{ticker}-{range_label}-{candle_label}",
        newshape=dict(
            line=dict(color="#f4c430", width=2),
            fillcolor="rgba(244, 196, 48, 0.12)"
        ),
        template="plotly_dark",
        paper_bgcolor="#0f1419",
        plot_bgcolor="#121a21",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1
        )
    )
    figure.update_xaxes(
        range=get_chart_xaxis_range(data),
        rangebreaks=get_chart_rangebreaks(range_config),
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="#d7dee8",
        spikethickness=1,
        showgrid=True,
        gridcolor="rgba(215,222,232,0.16)",
        zeroline=False
    )
    figure.update_yaxes(
        fixedrange=False,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="#d7dee8",
        spikethickness=1,
        showgrid=True,
        gridcolor="rgba(215,222,232,0.16)",
        zeroline=False,
        side="right",
        title_text="Prezzo",
        row=price_row,
        col=1
    )

    if has_volume:
        figure.update_yaxes(
            title_text="Volume",
            showgrid=False,
            side="right",
            fixedrange=True,
            row=2,
            col=1
        )

    return figure, fallback_note


def render_file_reference(label: str, path):
    if path:
        st.caption(f"{label}: {path}")
    else:
        st.caption(f"{label}: non disponibile")


def render_asset_focus(
    selected_ticker: str,
    scanner: pd.DataFrame,
    key_prefix: str,
    asset_lookup: dict,
    strategy_config: dict | None = None
):
    if not selected_ticker:
        st.info("Seleziona un ticker dalla watchlist per aprire il focus asset.")
        return

    asset_name = asset_lookup.get(selected_ticker, {}).get("name")
    title = selected_ticker if not asset_name else f"{selected_ticker} - {asset_name}"

    st.subheader(f"Asset Focus - {title}")

    scanner_row = pd.DataFrame()

    if not scanner.empty and "ticker" in scanner.columns:
        scanner_row = scanner[scanner["ticker"] == selected_ticker]

    if scanner_row.empty:
        st.caption(
            "Nessun dato scanner disponibile per questo ticker nei report."
        )
    else:
        row = scanner_row.iloc[0]
        metric_items = [
            ("Close", row.get("close", "-")),
            ("RSI", row.get("rsi", "-")),
            ("ATR %", row.get("volatility_%", "-")),
            ("Regime", row.get("market_regime", "-")),
            ("Signal", row.get("signal", "-")),
            ("ADX", row.get("adx", "-")),
            ("Vol Ratio", row.get("volume_ratio", "-")),
            ("Setup", row.get("setup_score", "-")),
            ("Opportunita", row.get("opportunity_label", "-"))
        ]

        for start in range(0, len(metric_items), 3):
            metric_columns = st.columns(3)
            for column, (label, value) in zip(
                metric_columns,
                metric_items[start:start + 3]
            ):
                column.metric(label, value)

        st.caption(
            "Lettura motore: ranking basato su AI score deterministico, "
            "regime, segnale, distanza EMA e penalita volatilita."
        )

    range_label = st.radio(
        "Range grafico",
        options=list(ASSET_RANGE_OPTIONS.keys()),
        index=list(ASSET_RANGE_OPTIONS.keys()).index("1A"),
        horizontal=True,
        key=f"{key_prefix}_asset_range_{selected_ticker}"
    )
    candle_options = get_chart_candle_options(range_label)
    default_candle = ASSET_RANGE_OPTIONS[range_label]["default_candle"]
    candle_label = st.radio(
        "Candela",
        options=candle_options,
        index=(
            candle_options.index(default_candle)
            if default_candle in candle_options
            else 0
        ),
        format_func=lambda value: CHART_CANDLE_OPTIONS[value]["label"],
        horizontal=True,
        key=f"{key_prefix}_candle_{selected_ticker}_{range_label}"
    )
    chart_engine = st.radio(
        "Motore grafico",
        ["Trading board pro (beta)", "Plotly fallback"],
        horizontal=True,
        key=f"{key_prefix}_chart_engine_{selected_ticker}"
    )

    if chart_engine == "Trading board pro (beta)":
        with st.spinner(f"Caricamento trading board {selected_ticker}..."):
            try:
                data, _, fallback_note = load_asset_price_data_with_fallback(
                    ticker=selected_ticker,
                    range_label=range_label,
                    candle_label=candle_label
                )
                components.html(
                    build_klinechart_html(
                        ticker=selected_ticker,
                        range_label=range_label,
                        candle_label=candle_label,
                        data=data
                    ),
                    height=790,
                    scrolling=False
                )
                if fallback_note:
                    st.caption(fallback_note)
            except Exception as error:
                st.warning(
                    "Trading board non disponibile: "
                    f"{error}. Usa il fallback Plotly."
                )
        return

    chart_col1, chart_col2 = st.columns([1, 2])
    chart_mode = chart_col1.radio(
        "Tipo grafico",
        ["Line", "Candles"],
        index=1,
        horizontal=True,
        key=f"{key_prefix}_chart_mode_{selected_ticker}"
    )
    chart_overlays = chart_col2.multiselect(
        "Overlay",
        [
            "Medie trend",
            "EMA 20/50/200",
            "SMA 50/200",
            "VWAP",
            "Bollinger"
        ],
        default=[],
        key=f"{key_prefix}_chart_overlays_{selected_ticker}"
    )
    st.caption(
        "Strumenti manuali: usa la toolbar del grafico per pan, zoom, linea, "
        "rettangolo e gomma. La gomma cancella il disegno selezionato; "
        "cambiare tool dalla toolbar non ricarica la pagina."
    )

    with st.spinner(f"Caricamento grafico {selected_ticker}..."):
        try:
            figure, fallback_note = build_asset_price_figure(
                selected_ticker,
                range_label,
                candle_label,
                chart_mode=chart_mode,
                overlays=chart_overlays,
                strategy_config=strategy_config
            )
            st.plotly_chart(
                figure,
                width="stretch",
                config={
                    "scrollZoom": True,
                    "doubleClick": "reset+autosize",
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToAdd": [
                        "drawline",
                        "drawrect",
                        "eraseshape"
                    ],
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    "edits": {"shapePosition": True}
                },
                key=f"{key_prefix}_plotly_chart_{selected_ticker}"
            )
            if fallback_note:
                st.caption(fallback_note)
        except Exception as error:
            st.warning(f"Grafico non disponibile: {error}")


def load_latest_reports():
    reports = {
        "trades": load_csv_or_empty("reports/trades.csv"),
        "equity": load_csv_or_empty("reports/equity_curve.csv"),
        "portfolio": load_csv_or_empty("reports/portfolio_backtest.csv"),
        "scanner": load_csv_or_empty(get_latest_file(
            "reports/live_scanner_*.csv"
        )),
        "paper": load_csv_or_empty(get_latest_file(
            "reports/paper_portfolio_plan_*.csv"
        )),
        "summary": load_csv_or_empty(get_latest_file(
            "reports/paper_summary_*.csv"
        )),
        "decisions": load_csv_or_empty(get_latest_file(
            "reports/paper_decision_log_*.csv"
        ))
    }

    return reports


st.title("AI Trading Bot Workstation")
st.caption(
    "Workspace operativa per scanner, paper portfolio, backtest e controllo "
    "del rischio. Nessun ordine reale viene inviato."
)

reports = load_latest_reports()

if "favorite_watchlist" not in st.session_state:
    st.session_state["favorite_watchlist"] = load_watchlist()

if "backtest_presets" not in st.session_state:
    st.session_state["backtest_presets"] = load_backtest_presets()

if "manual_basket_assets" not in st.session_state:
    st.session_state["manual_basket_assets"] = []

if "asset_focus_ticker" not in st.session_state:
    st.session_state["asset_focus_ticker"] = None

if "backtest_price_data_cache" not in st.session_state:
    st.session_state["backtest_price_data_cache"] = {
        "key": None,
        "data": {},
        "metadata": {}
    }


# ====================
# SIDEBAR CONTROLS
# ====================

st.sidebar.header("Workspace")

with st.spinner("Caricamento catalogo asset per mercato..."):
    (
        all_asset_records,
        catalog_loaded_markets,
        catalog_failed_markets
    ) = get_all_market_asset_records_with_status()

available_market_names = [
    item["market"]
    for item in catalog_loaded_markets
]

if not available_market_names:
    available_market_names = get_market_names()

available_group_names = get_market_groups()

universe_preset = st.sidebar.selectbox(
    "Preset universo",
    [
        "Globale progressivo",
        "Tutto USA",
        "Tutti ETF",
        "Italia",
        "Europa Core",
        "Crypto",
        "Custom"
    ],
    index=0
)

selected_group_names = st.sidebar.multiselect(
    "Gruppi mercato",
    options=available_group_names,
    default=[
        group for group in get_universe_preset_groups(universe_preset)
        if group in available_group_names
    ]
)

if not selected_group_names:
    selected_group_names = get_universe_preset_groups("Globale progressivo")
    st.sidebar.warning("Seleziono i gruppi del preset globale.")

market_options_for_groups = [
    market
    for market in get_markets_for_groups(selected_group_names)
    if market in available_market_names
]

selected_market_names = st.sidebar.multiselect(
    "Mercati attivi",
    options=market_options_for_groups,
    default=market_options_for_groups
)

if not selected_market_names:
    selected_market_names = market_options_for_groups
    st.sidebar.warning("Seleziono i mercati dei gruppi attivi.")

market_asset_records = get_assets_for_markets(
    all_asset_records,
    selected_market_names
)
market_assets = [asset["ticker"] for asset in market_asset_records]
price_cache_status = get_price_cache_status(market_assets)
cached_market_assets = [
    ticker for ticker in market_assets
    if ticker in price_cache_status
]
fresh_cached_market_assets = [
    ticker for ticker in market_assets
    if price_cache_status.get(ticker, {}).get("status") == "loaded"
]
stale_cached_market_assets = [
    ticker for ticker in market_assets
    if price_cache_status.get(ticker, {}).get("status") == "stale"
]
missing_cache_assets = [
    ticker for ticker in market_assets
    if ticker not in price_cache_status
]
market_loaded = bool(market_assets)
market_label = " + ".join(selected_market_names)

if market_loaded:
    st.sidebar.caption(
        f"{market_label}: {len(market_assets)} asset disponibili."
    )
    st.sidebar.caption(
        f"Cache prezzi daily: {len(cached_market_assets)} / "
        f"{len(market_assets)} ticker."
    )
    st.sidebar.caption(
        f"Fresh: {len(fresh_cached_market_assets)} | "
        f"Stale: {len(stale_cached_market_assets)} | "
        f"Mancanti: {len(missing_cache_assets)}"
    )
else:
    st.sidebar.warning("Nessun asset disponibile per i mercati selezionati.")

if catalog_failed_markets:
    failed_labels = [
        f"{item['market']}: {item['error']}"
        for item in catalog_failed_markets
    ]
    st.sidebar.warning("Provider non disponibili: " + " | ".join(
        failed_labels
    ))

asset_lookup = build_asset_lookup(all_asset_records)

st.sidebar.subheader("Asset rapido")
st.sidebar.caption(
    "Cerca un ticker una sola volta, poi mandalo a watchlist, paniere o focus."
)
render_global_asset_search(
    all_asset_records,
    selected_market_names,
    key_prefix="quick_asset",
    allow_basket=True,
    layout="compact"
)

with st.sidebar.expander("Paniere e benchmark", expanded=False):
    use_manual_basket = st.checkbox(
        "Confronta con paniere scelto da me",
        value=True
    )

    manual_basket_assets = st.session_state["manual_basket_assets"]
    manual_basket_label = "Manual Basket Active Markets"

    if use_manual_basket:
        max_manual_basket_assets = st.slider(
            "Max asset",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )

        custom_manual_tickers = parse_custom_tickers(
            st.text_input(
                "Ticker extra rapidi",
                value="",
                help="Esempio: SPY, QQQ, BTC-USD"
            )
        )

        manual_basket_assets = merge_unique_tickers(
            manual_basket_assets,
            custom_manual_tickers
        )

        if len(manual_basket_assets) > max_manual_basket_assets:
            st.warning(
                "Numero massimo superato: usero solo i primi "
                f"{max_manual_basket_assets} ticker."
            )
            manual_basket_assets = manual_basket_assets[
                :max_manual_basket_assets
            ]

        st.session_state["manual_basket_assets"] = manual_basket_assets

        if manual_basket_assets:
            st.caption("Asset nel paniere")

            for ticker in manual_basket_assets:
                asset_name = asset_lookup.get(
                    ticker,
                    {"name": ticker}
                ).get("name", ticker)
                st.markdown(f"**{ticker}**")
                st.caption(asset_name)

                if st.button(
                    f"Rimuovi {ticker}",
                    key=f"manual_basket_remove_{ticker}",
                    width="stretch"
                ):
                    st.session_state["manual_basket_assets"] = [
                        item for item in manual_basket_assets
                        if item != ticker
                    ]
                    st.rerun()

        st.caption(
            f"{len(manual_basket_assets)} asset selezionati su "
            f"{len(all_asset_records)} disponibili nel catalogo globale."
        )

with st.sidebar.expander("Setup strategia e backtest", expanded=False):
    presets = st.session_state["backtest_presets"]
    preset_names = list(presets.keys())

    active_preset_name = st.selectbox(
        "Profilo strategia",
        preset_names,
        index=0 if preset_names else None
    )

    active_preset = presets.get(
        active_preset_name,
        DEFAULT_BACKTEST_PRESETS["3 - Balanced Rotation"]
    )
    preset_guidance = get_preset_guidance(active_preset_name, active_preset)

    st.caption(f"Rischio: {preset_guidance['risk']}")
    st.info(preset_guidance["description"])
    st.caption("Comportamento: " + preset_guidance["behavior"])
    st.caption("Strumenti attivi: " + preset_guidance["tools"])

    selected_preset_names = st.multiselect(
        "Confronta preset nel backtest",
        options=preset_names,
        default=[active_preset_name] if active_preset_name else []
    )

    portfolio_initial_capital = st.number_input(
        "Capitale iniziale",
        min_value=100,
        value=1000,
        step=100
    )

    if "backtest_end_date" not in st.session_state:
        st.session_state["backtest_end_date"] = date.today()
    if "backtest_range_preset" not in st.session_state:
        st.session_state["backtest_range_preset"] = "1M"
    if "backtest_start_date" not in st.session_state:
        st.session_state["backtest_start_date"] = get_start_date_for_range(
            st.session_state["backtest_end_date"],
            st.session_state["backtest_range_preset"]
        )

    st.caption("Range backtest")
    selected_range_preset = st.selectbox(
        "Preset rapido",
        options=list(BACKTEST_DATE_RANGE_PRESETS.keys()),
        index=list(BACKTEST_DATE_RANGE_PRESETS.keys()).index(
            st.session_state["backtest_range_preset"]
        ),
        format_func=lambda value: (
            "Q - Ultimo quarto" if value == "Ultimo quarto" else value
        ),
        key="backtest_range_preset"
    )
    previous_range_anchor = st.session_state.get("backtest_range_anchor")
    current_range_anchor = (
        selected_range_preset,
        st.session_state["backtest_end_date"]
    )

    if previous_range_anchor != current_range_anchor:
        st.session_state["backtest_start_date"] = get_start_date_for_range(
            st.session_state["backtest_end_date"],
            selected_range_preset
        )
        st.session_state["backtest_range_anchor"] = current_range_anchor

    date_col1, date_col2 = st.columns(2)
    start_date_value = date_col1.date_input(
        "Start date",
        key="backtest_start_date"
    )
    end_date_value = date_col2.date_input(
        "End date",
        key="backtest_end_date"
    )
    start_date = start_date_value.isoformat()
    end_date = end_date_value.isoformat()

    with st.expander("Cosa sta facendo questo preset", expanded=True):
        st.caption(summarize_preset_behavior(active_preset))

    use_full_backtest_universe = st.checkbox(
        "Usa tutto l'universo selezionato",
        value=True,
        help="Il backtest usera tutti i ticker dei mercati attivi."
    )
    use_only_cached_assets = st.checkbox(
        "Usa solo asset con cache valida",
        value=False,
        help="Riduce download e rate limit usando solo ticker gia presenti in cache."
    )

    estimated_backtest_assets = (
        len(cached_market_assets)
        if use_only_cached_assets
        else len(market_assets)
    )
    st.caption(
        f"Backtest stimato: {estimated_backtest_assets} ticker. "
        f"Cache disponibile: {len(cached_market_assets)} ticker."
    )

    if estimated_backtest_assets > 500:
        st.warning(
            "Universo molto grande: il primo run puo richiedere tempo per "
            "popolare la cache dati."
        )

    with st.expander("Modifica avanzata", expanded=False):
        st.caption(
            "Usa questi controlli solo se vuoi creare un profilo tuo. "
            "I preset base sono gia ordinati dal piu prudente al piu aggressivo."
        )
        st.markdown("**Trend**")
        ma_type = st.radio(
            "Tipo media",
            ["EMA", "SMA"],
            index=0 if get_preset_value(active_preset, "ma_type") == "EMA" else 1,
            horizontal=True,
            help="EMA reagisce piu rapidamente; SMA e piu lenta e stabile."
        )
        fast_ma_period = st.number_input(
            "Media veloce",
            min_value=2,
            max_value=100,
            value=int(get_preset_value(active_preset, "fast_ma_period")),
            step=1,
            help="Periodo della media che misura il trend breve."
        )
        slow_ma_period = st.number_input(
            "Media lenta",
            min_value=5,
            max_value=200,
            value=int(get_preset_value(active_preset, "slow_ma_period")),
            step=1,
            help="Periodo della media usata come confronto del trend."
        )
        long_ma_period = st.number_input(
            "Media lungo periodo",
            min_value=20,
            max_value=300,
            value=int(get_preset_value(active_preset, "long_ma_period")),
            step=5,
            help="Filtro di fondo: il prezzo deve stare sopra questa media."
        )

        st.markdown("**Momentum**")
        rsi_period = st.number_input(
            "RSI periodo",
            min_value=2,
            max_value=50,
            value=int(get_preset_value(active_preset, "rsi_period")),
            step=1,
            help="Numero di barre usate per calcolare il momentum RSI."
        )
        rsi_buy_min = st.slider(
            "RSI buy minimo",
            min_value=1,
            max_value=99,
            value=int(get_preset_value(active_preset, "rsi_buy_min")),
            step=1,
            help="Sotto questa soglia il momentum e considerato debole."
        )
        rsi_buy_max = st.slider(
            "RSI buy massimo",
            min_value=1,
            max_value=99,
            value=int(get_preset_value(active_preset, "rsi_buy_max")),
            step=1,
            help="Sopra questa soglia il setup puo essere gia troppo esteso."
        )
        rsi_sell_above = st.slider(
            "RSI sell sopra",
            min_value=1,
            max_value=99,
            value=int(get_preset_value(active_preset, "rsi_sell_above")),
            step=1,
            help="Soglia di uscita quando RSI segnala eccesso."
        )
        use_macd_filter = st.checkbox(
            "Usa filtro MACD",
            value=bool(get_preset_value(active_preset, "use_macd_filter")),
            help="Richiede istogramma MACD positivo per confermare momentum."
        )
        macd_fast = st.number_input(
            "MACD fast",
            min_value=2,
            max_value=50,
            value=int(get_preset_value(active_preset, "macd_fast")),
            step=1,
            help="Media veloce del MACD."
        )
        macd_slow = st.number_input(
            "MACD slow",
            min_value=3,
            max_value=100,
            value=int(get_preset_value(active_preset, "macd_slow")),
            step=1,
            help="Media lenta del MACD."
        )
        macd_signal = st.number_input(
            "MACD signal",
            min_value=2,
            max_value=50,
            value=int(get_preset_value(active_preset, "macd_signal")),
            step=1,
            help="Linea segnale del MACD."
        )

        st.markdown("**Rischio e volatilita**")
        atr_period = st.number_input(
            "ATR periodo",
            min_value=2,
            max_value=50,
            value=int(get_preset_value(active_preset, "atr_period")),
            step=1,
            help="Periodo usato per misurare la volatilita media."
        )
        max_volatility_pct = st.slider(
            "Volatilita massima ATR %",
            min_value=1.0,
            max_value=20.0,
            value=float(get_preset_value(active_preset, "max_volatility_pct")),
            step=0.5,
            help="Limite massimo di volatilita accettato per comprare."
        )
        min_hold_weeks = st.slider(
            "Hold minimo settimane",
            min_value=1,
            max_value=12,
            value=int(get_preset_value(active_preset, "min_hold_weeks")),
            step=1,
            help="Tempo minimo prima di ruotare verso un altro asset."
        )

        st.markdown("**Conferme**")
        use_adx_filter = st.checkbox(
            "Usa filtro ADX",
            value=bool(get_preset_value(active_preset, "use_adx_filter")),
            help="Richiede forza trend minima prima di comprare."
        )
        adx_period = st.number_input(
            "ADX periodo",
            min_value=2,
            max_value=50,
            value=int(get_preset_value(active_preset, "adx_period")),
            step=1,
            help="Periodo di calcolo della forza trend."
        )
        adx_min = st.slider(
            "ADX minimo",
            min_value=1,
            max_value=60,
            value=int(get_preset_value(active_preset, "adx_min")),
            step=1
        )
        use_volume_filter = st.checkbox(
            "Usa filtro volume",
            value=bool(get_preset_value(active_preset, "use_volume_filter")),
            help="Richiede volume sopra la media per confermare interesse."
        )
        volume_sma_period = st.number_input(
            "Volume SMA periodo",
            min_value=2,
            max_value=100,
            value=int(get_preset_value(active_preset, "volume_sma_period")),
            step=1,
            help="Periodo della media volume."
        )
        volume_ratio_min = st.number_input(
            "Volume ratio minimo",
            min_value=0.0,
            max_value=5.0,
            value=float(get_preset_value(active_preset, "volume_ratio_min")),
            step=0.1,
            help="1.0 significa volume almeno pari alla sua media."
        )

        st.markdown("**Rotazione e costi**")
        min_ai_score = st.slider(
            "AI score minimo",
            min_value=0,
            max_value=120,
            value=int(get_preset_value(active_preset, "min_ai_score")),
            step=5,
            help="Punteggio tecnico minimo prima di considerare un asset."
        )
        min_scanner_score = st.slider(
            "Scanner score minimo",
            min_value=50,
            max_value=220,
            value=int(get_preset_value(active_preset, "min_scanner_score")),
            step=5,
            help="Soglia di ranking minima per entrare nel paniere candidato."
        )
        persistence_weeks = st.slider(
            "Persistenza segnale settimane",
            min_value=1,
            max_value=6,
            value=int(get_preset_value(active_preset, "persistence_weeks")),
            step=1,
            help="Quante settimane il segnale deve restare valido."
        )
        switch_score_margin = st.slider(
            "Margine minimo rotazione",
            min_value=0,
            max_value=50,
            value=int(get_preset_value(active_preset, "switch_score_margin")),
            step=5,
            help="Vantaggio richiesto per sostituire l'asset corrente."
        )
        top_n_candidates = st.slider(
            "Top candidati",
            min_value=1,
            max_value=10,
            value=int(get_preset_value(active_preset, "top_n_candidates")),
            step=1,
            help="Numero massimo di asset candidati valutati a ogni rotazione."
        )
        commission_pct = st.number_input(
            "Commissione %",
            min_value=0.0,
            max_value=2.0,
            value=(
                float(get_preset_value(active_preset, "commission_pct")) *
                100
            ),
            step=0.01,
            help="Costo percentuale applicato a entrata e uscita."
        ) / 100
        slippage_pct = st.number_input(
            "Slippage %",
            min_value=0.0,
            max_value=2.0,
            value=(
                float(get_preset_value(active_preset, "slippage_pct")) *
                100
            ),
            step=0.01,
            help="Peggioramento simulato del prezzo di esecuzione."
        ) / 100
        use_engine_basket = st.checkbox(
            "Confronta con paniere scelto dal motore",
            value=bool(get_preset_value(active_preset, "use_engine_basket")),
            help="Aggiunge benchmark statico costruito dai migliori asset iniziali."
        )
        engine_basket_size = st.slider(
            "Asset paniere motore",
            min_value=1,
            max_value=20,
            value=int(get_preset_value(active_preset, "engine_basket_size")),
            step=1,
            help="Numero di asset nel benchmark statico del motore."
        )

    edited_preset = {
        "ma_type": ma_type,
        "fast_ma_period": fast_ma_period,
        "slow_ma_period": slow_ma_period,
        "long_ma_period": long_ma_period,
        "rsi_period": rsi_period,
        "rsi_buy_min": rsi_buy_min,
        "rsi_buy_max": rsi_buy_max,
        "rsi_sell_above": rsi_sell_above,
        "atr_period": atr_period,
        "max_volatility_pct": max_volatility_pct,
        "adx_period": adx_period,
        "adx_min": adx_min,
        "use_adx_filter": use_adx_filter,
        "macd_fast": macd_fast,
        "macd_slow": macd_slow,
        "macd_signal": macd_signal,
        "use_macd_filter": use_macd_filter,
        "volume_sma_period": volume_sma_period,
        "volume_ratio_min": volume_ratio_min,
        "use_volume_filter": use_volume_filter,
        "min_ai_score": min_ai_score,
        "min_scanner_score": min_scanner_score,
        "min_hold_weeks": min_hold_weeks,
        "persistence_weeks": persistence_weeks,
        "switch_score_margin": switch_score_margin,
        "top_n_candidates": top_n_candidates,
        "commission_pct": commission_pct,
        "slippage_pct": slippage_pct,
        "use_engine_basket": use_engine_basket,
        "engine_basket_size": engine_basket_size
    }

    preset_action_col1, preset_action_col2 = st.columns(2)

    if preset_action_col1.button("Salva modifiche", width="stretch"):
        if active_preset_name in DEFAULT_BACKTEST_PRESETS:
            st.warning(
                "I preset base restano protetti: usa 'Salva come nuovo'."
            )
        else:
            presets[active_preset_name] = edited_preset
            save_backtest_presets(presets)
            st.success("Preset salvato.")

    new_preset_name = st.text_input("Nome preset custom", value="")

    if preset_action_col2.button("Salva come nuovo", width="stretch"):
        if new_preset_name.strip():
            presets[new_preset_name.strip()] = edited_preset
            st.session_state["backtest_presets"] = presets
            save_backtest_presets(presets)
            st.rerun()

    rename_col1, rename_col2 = st.columns(2)

    if rename_col1.button("Rinomina", width="stretch"):
        if active_preset_name in DEFAULT_BACKTEST_PRESETS:
            st.warning(
                "I preset base restano protetti: usa 'Salva come nuovo'."
            )
        elif new_preset_name.strip() and active_preset_name in presets:
            presets[new_preset_name.strip()] = presets.pop(active_preset_name)
            st.session_state["backtest_presets"] = presets
            save_backtest_presets(presets)
            st.rerun()

    if rename_col2.button("Elimina", width="stretch"):
        if active_preset_name not in DEFAULT_BACKTEST_PRESETS:
            presets.pop(active_preset_name, None)
            st.session_state["backtest_presets"] = presets
            save_backtest_presets(presets)
            st.rerun()
        else:
            st.warning("I preset di base non vengono eliminati.")

    st.divider()
    st.subheader("Importa strategia da JSON")
    st.caption(
        "Carica un file JSON con la configurazione strategia "
        "(es. output di un LLM dopo l'analisi)."
    )

    imported_file = st.file_uploader(
        "Seleziona file JSON",
        type=["json"],
        key="import_strategy_json"
    )

    import_preset_name = st.text_input(
        "Nome per la strategia importata",
        value="",
        key="import_preset_name"
    )

    if st.button("Importa e salva", width="stretch"):
        if imported_file is not None:
            try:
                imported_data = json.loads(
                    imported_file.read().decode("utf-8")
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                st.error("File JSON non valido.")
                imported_data = None

            if imported_data is not None:
                # Accept both flat param dicts and wrapped objects
                if isinstance(imported_data, dict):
                    # If the JSON has a nested strategy key, extract it
                    for key in (
                        "configurazione_strategia",
                        "strategy_config",
                        "params",
                        "parameters",
                    ):
                        if key in imported_data and isinstance(
                            imported_data[key], dict
                        ):
                            imported_data = imported_data[key]
                            break

                valid_keys = set(edited_preset.keys())
                filtered = {
                    k: v
                    for k, v in imported_data.items()
                    if k in valid_keys
                }

                if not filtered:
                    st.error(
                        "Nessun parametro valido trovato nel JSON. "
                        "Verifica che contenga chiavi come "
                        "'ma_type', 'fast_ma_period', ecc."
                    )
                else:
                    # Merge with current preset as base (fills missing keys)
                    merged = {**edited_preset, **filtered}
                    name = (
                        import_preset_name.strip()
                        if import_preset_name.strip()
                        else f"Importato {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    presets[name] = merged
                    st.session_state["backtest_presets"] = presets
                    save_backtest_presets(presets)
                    st.success(
                        f"Strategia importata come '{name}' "
                        f"({len(filtered)}/{len(valid_keys)} parametri dal JSON)."
                    )
                    st.rerun()
        else:
            st.warning("Carica un file JSON prima di importare.")

    run_market_backtest = st.button(
        "Esegui Portfolio Backtest",
        width="stretch"
    )

# ====================
# WORKSPACE STATE
# ====================

scanner = reports["scanner"]
paper = reports["paper"]
summary = reports["summary"]
portfolio = reports["portfolio"]
equity = reports["equity"]

screener = build_screener_dataframe(
    asset_records=market_asset_records,
    scanner=scanner,
    watchlist=st.session_state["favorite_watchlist"]
)


# ====================
# WORKSTATION TABS
# ====================

overview_tab, scanner_tab, portfolio_tab, backtest_tab, glossary_tab = st.tabs(
    [
        "Overview",
        "Trova asset",
        "Portfolio",
        "Testa strategia",
        "Glossario & Strategia"
    ]
)


with overview_tab:
    st.subheader("Workspace Overview")

    final_equity = (
        round(equity["equity"].iloc[-1], 2)
        if not equity.empty and "equity" in equity.columns
        else 0
    )
    final_portfolio = (
        round(portfolio["capital"].iloc[-1], 2)
        if not portfolio.empty and "capital" in portfolio.columns
        else 0
    )
    max_drawdown = calculate_drawdown_from_capital(portfolio)

    if not summary.empty:
        capital = to_float(summary.get("capital", pd.Series([0])).iloc[0])
        invested = to_float(
            summary.get("invested_capital", pd.Series([0])).iloc[0]
        )
        cash = to_float(
            summary.get("remaining_cash", pd.Series([0])).iloc[0]
        )
        exposure = to_float(
            summary.get("exposure_%", pd.Series([0])).iloc[0]
        )
    else:
        capital = 0
        invested = 0
        cash = 0
        exposure = 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Paper Capital", f"${capital:.2f}")
    col2.metric("Invested", f"${invested:.2f}")
    col3.metric("Cash", f"${cash:.2f}")
    col4.metric("Exposure", f"{exposure:.2f}%")
    col5.metric("Max DD", f"{max_drawdown:.2f}%")

    st.plotly_chart(
        build_equity_figure(
            equity=equity,
            portfolio=portfolio,
            title="Equity Curve Monitor"
        ),
        width="stretch"
    )

    st.subheader("Watchlist & Asset Focus")

    favorite_rows = pd.DataFrame([
        {
            "ticker": ticker,
            "name": asset_lookup.get(
                ticker,
                {"name": ticker}
            ).get("name", ticker)
        }
        for ticker in st.session_state["favorite_watchlist"]
    ])

    if not favorite_rows.empty:
        favorite_tickers = favorite_rows["ticker"].tolist()
        selected_watch_ticker = st.selectbox(
            "Ticker focus",
            favorite_tickers,
            index=(
                favorite_tickers.index(st.session_state["asset_focus_ticker"])
                if st.session_state["asset_focus_ticker"] in favorite_tickers
                else 0
            ),
            format_func=lambda ticker: format_asset_label(
                asset_lookup.get(
                    ticker,
                    {"ticker": ticker, "name": ticker}
                )
            ),
            key="overview_focus"
        )
        render_asset_focus(
            selected_watch_ticker,
            scanner,
            key_prefix="overview",
            asset_lookup=asset_lookup,
            strategy_config=edited_preset
        )
    else:
        st.info(
            "La watchlist si popola dalla tabella screener nella sezione "
            "Trova asset o dalla ricerca rapida in sidebar."
        )

    st.subheader("Ultimo Paper Portfolio")

    if paper.empty:
        st.warning("Nessun report paper trading disponibile.")
    else:
        st.dataframe(paper, width="stretch")


with scanner_tab:
    st.subheader("Trova asset")
    st.caption(
        "La tabella mostra solo i mercati attivi. Per cercare fuori dai "
        "filtri usa la ricerca globale rapida nella sidebar o il pannello "
        "sotto."
    )

    scanner_asset_count = (
        int(screener["scanner_score"].notna().sum())
        if not screener.empty and "scanner_score" in screener.columns
        else 0
    )
    favorite_count = len(st.session_state["favorite_watchlist"])
    status_columns = st.columns(5)
    status_columns[0].metric("Mercati", len(selected_market_names))
    status_columns[1].metric("Asset", len(screener))
    status_columns[2].metric("Scanner", scanner_asset_count)
    status_columns[3].metric(
        "Cache prezzi",
        f"{len(cached_market_assets)}",
        delta=f"{len(fresh_cached_market_assets)} fresh"
    )
    status_columns[4].metric("Watchlist", favorite_count)

    if catalog_failed_markets:
        failed_labels = [
            f"{item['market']}: {item['error']}"
            for item in catalog_failed_markets
        ]
        st.warning("Mercati non caricati: " + " | ".join(failed_labels))

    if screener.empty:
        st.warning("Nessun asset disponibile per i mercati selezionati.")
    elif scanner.empty:
        st.warning(
            "Nessun live scanner trovato in reports/. Genera un paper run "
            "per popolare metriche e segnali; il catalogo resta filtrabile."
        )

    scan_col1, scan_col2, scan_col3 = st.columns([1.4, 0.9, 1.7])
    run_live_scanner = scan_col1.button(
        "Esegui Scanner Live",
        width="stretch",
        help=(
            "Scansiona tutti gli asset dei mercati attivi, genera segnali "
            "e aggiorna i report in reports/."
        )
    )
    scan_only_cached = scan_col2.checkbox(
        "Solo asset in cache",
        value=True,
        help="Scansiona solo i ticker con dati gia scaricati per velocizzare."
    )
    estimated_scan_tickers = (
        len(cached_market_assets) if scan_only_cached else len(market_assets)
    )
    estimated_download_tickers = 0 if scan_only_cached else len(
        missing_cache_assets + stale_cached_market_assets
    )
    scan_col3.caption(
        f"Ticker stimati: {estimated_scan_tickers} | "
        f"download potenziali: {estimated_download_tickers} | "
        f"provider falliti: {len(catalog_failed_markets)}"
    )

    if run_live_scanner:
        scan_tickers = (
            cached_market_assets if scan_only_cached else market_assets
        )

        if not scan_tickers:
            st.error("Nessun ticker disponibile per lo scanner.")
        else:
            total_scan_steps = len(scan_tickers) + estimated_download_tickers
            progress_update, progress_callback = build_backtest_progress_tracker(
                total_scan_steps
            )
            progress_update(
                f"Scanner in corso su {len(scan_tickers)} ticker"
            )
            try:
                scan_result, plan_result, summary_result = (
                    run_paper_trading_for_tickers(
                        tickers=scan_tickers,
                        market_label=market_label,
                        capital=portfolio_initial_capital,
                        top_n=int(get_preset_value(
                            active_preset, "top_n_candidates"
                        )),
                        min_score=float(get_preset_value(
                            active_preset, "min_scanner_score"
                        )),
                        risk_per_trade=0.01,
                        atr_multiplier=2.0,
                        strategy_config=edited_preset,
                        download_missing=not scan_only_cached,
                        progress_callback=progress_callback,
                        progress_context={"preset": active_preset}
                    )
                )
                progress_update("Scanner completato")
                st.success(
                    f"Scanner completato: {len(scan_result)} asset "
                    f"analizzati, {len(plan_result)} posizioni nel piano."
                )
                st.rerun()
            except Exception as scan_error:
                st.error(f"Errore scanner: {scan_error}")

    if not screener.empty:
        st.divider()
        st.caption("Screener")
        quick_col1, quick_col2, quick_col3, quick_col4, quick_col5 = st.columns(
            [1.15, 1.45, 1, 1, 0.85]
        )

        with quick_col1:
            screener_preset = st.selectbox(
                "Preset screener",
                SCREENER_PRESETS,
                key="screener_preset"
            )
            preset_defaults = get_screener_preset_defaults(screener_preset)

        with quick_col2:
            search_text = st.text_input(
                "Cerca ticker o nome",
                value="",
                key=f"screener_search_{screener_preset}"
            )

        with quick_col3:
            sort_by = st.selectbox(
                "Ordina per",
                SCREENER_SORT_OPTIONS,
                index=SCREENER_SORT_OPTIONS.index(
                    preset_defaults["sort_by"]
                ),
                key=f"screener_sort_{screener_preset}"
            )

        with quick_col4:
            column_view = st.selectbox(
                "Vista colonne",
                list(SCREENER_COLUMN_VIEWS.keys()),
                index=list(SCREENER_COLUMN_VIEWS.keys()).index(
                    preset_defaults["column_view"]
                ),
                key=f"screener_column_view_{screener_preset}"
            )

        with quick_col5:
            only_watchlist = st.checkbox(
                "Solo watchlist",
                value=preset_defaults["only_watchlist"],
                key=f"screener_only_watchlist_{screener_preset}"
            )

        with st.expander(
            "Filtri avanzati",
            expanded=screener_preset == "Custom"
        ):
            universe_col, score_col, technical_col = st.columns(3)

            with universe_col:
                screener_market_filter = st.multiselect(
                    "Mercati",
                    options=selected_market_names,
                    default=selected_market_names,
                    key=f"screener_market_filter_{screener_preset}"
                )
                signal_options = ["ALL", "BUY", "SELL", "HOLD"]
                signal_default = preset_defaults["signal_filter"]
                selected_signal = st.selectbox(
                    "Segnale",
                    signal_options,
                    index=(
                        signal_options.index(signal_default)
                        if signal_default in signal_options
                        else 0
                    ),
                    key=f"screener_signal_{screener_preset}"
                )
                regime_options = ["ALL", "BULL", "SIDEWAYS", "BEAR"]
                regime_default = preset_defaults["regime_filter"]
                selected_regime = st.selectbox(
                    "Regime",
                    regime_options,
                    index=(
                        regime_options.index(regime_default)
                        if regime_default in regime_options
                        else 0
                    ),
                    key=f"screener_regime_{screener_preset}"
                )
                opportunity_options = [
                    "Tutti",
                    "Solo candidati long",
                    "Solo sell/uscita"
                ]
                selected_opportunity = st.selectbox(
                    "Opportunita",
                    opportunity_options,
                    index=opportunity_options.index(
                        preset_defaults["opportunity_filter"]
                    ),
                    key=f"screener_opportunity_{screener_preset}"
                )

            with score_col:
                min_score_filter = st.number_input(
                    "Score minimo",
                    value=(
                        float(screener["scanner_score"].min())
                        if screener["scanner_score"].notna().any()
                        else -999.0
                    ),
                    step=5.0,
                    key=f"screener_min_score_{screener_preset}"
                )
                close_values = pd.to_numeric(
                    screener["close"],
                    errors="coerce"
                )
                default_price_min = (
                    float(close_values.min())
                    if close_values.notna().any()
                    else 0.0
                )
                default_price_max = (
                    float(close_values.max())
                    if close_values.notna().any()
                    else 1000.0
                )
                price_min_filter = st.number_input(
                    "Prezzo minimo",
                    min_value=0.0,
                    value=preset_defaults["price_min"] or default_price_min,
                    step=0.5,
                    key=f"screener_price_min_{screener_preset}"
                )
                price_max_filter = st.number_input(
                    "Prezzo massimo",
                    min_value=0.0,
                    value=preset_defaults["price_max"] or default_price_max,
                    step=0.5,
                    key=f"screener_price_max_{screener_preset}"
                )

            with technical_col:
                rsi_min_filter = st.number_input(
                    "RSI minimo",
                    min_value=0.0,
                    max_value=100.0,
                    value=preset_defaults["rsi_min"] or 0.0,
                    step=1.0,
                    key=f"screener_rsi_min_{screener_preset}"
                )
                rsi_max_filter = st.number_input(
                    "RSI massimo",
                    min_value=0.0,
                    max_value=100.0,
                    value=preset_defaults["rsi_max"] or 100.0,
                    step=1.0,
                    key=f"screener_rsi_max_{screener_preset}"
                )
                volume_ratio_min_filter = st.number_input(
                    "Vol ratio minimo",
                    min_value=0.0,
                    value=preset_defaults["volume_ratio_min"] or 0.0,
                    step=0.1,
                    key=f"screener_volume_min_{screener_preset}"
                )
                default_atr_max = (
                    float(screener["volatility_%"].max())
                    if screener["volatility_%"].notna().any()
                    else 100.0
                )
                atr_min_filter = st.number_input(
                    "ATR % minimo",
                    min_value=0.0,
                    value=preset_defaults["atr_min"] or 0.0,
                    step=0.5,
                    key=f"screener_atr_min_{screener_preset}"
                )
                atr_max_filter = st.number_input(
                    "ATR % massimo",
                    min_value=0.0,
                    value=preset_defaults["atr_max"] or default_atr_max,
                    step=0.5,
                    key=f"screener_atr_max_{screener_preset}"
                )

        with st.expander("Ricerca globale fuori dai filtri", expanded=False):
            render_global_asset_search(
                all_asset_records,
                selected_market_names,
                key_prefix="scanner_global",
                allow_basket=True,
                layout="full"
            )

        screener_view = filter_screener_dataframe(
            screener=screener,
            market_filter=screener_market_filter,
            search_text=search_text,
            only_watchlist=only_watchlist,
            signal_filter=selected_signal,
            regime_filter=selected_regime,
            opportunity_filter=selected_opportunity,
            min_score=min_score_filter,
            price_min=price_min_filter,
            price_max=price_max_filter,
            rsi_min=rsi_min_filter,
            rsi_max=rsi_max_filter,
            volume_ratio_min=volume_ratio_min_filter,
            atr_min=atr_min_filter,
            atr_max=atr_max_filter
        )
        screener_view = sort_screener_dataframe(screener_view, sort_by)

        st.caption(
            f"Risultati: {len(screener_view)} / {len(screener)} | "
            f"Preset: {screener_preset} | Ordinamento: {sort_by}"
        )

        edited_screener = render_screener_editor(
            screener_view,
            key="market_screener_editor",
            column_view=column_view
        )
        sync_watchlist_from_editor(edited_screener)

        focus_options = edited_screener["ticker"].tolist()
        selected_scanner_ticker = None

        with st.expander("Asset focus", expanded=False):
            if focus_options:
                default_focus = st.session_state.get("asset_focus_ticker")
                focus_in_active_view = default_focus in focus_options
                selected_scanner_ticker = st.selectbox(
                    "Asset",
                    focus_options,
                    index=(
                        focus_options.index(default_focus)
                        if focus_in_active_view
                        else 0
                    ),
                    format_func=lambda ticker: format_asset_label(
                        asset_lookup.get(
                            ticker,
                            {"ticker": ticker, "name": ticker}
                        )
                    ),
                    key="scanner_focus"
                )
                if focus_in_active_view or default_focus is None:
                    set_asset_focus(selected_scanner_ticker)
                else:
                    st.caption(
                        "Il focus attuale arriva dalla ricerca globale e resta "
                        "visibile anche se fuori dai filtri dello screener."
                    )

            persisted_focus_ticker = st.session_state.get("asset_focus_ticker")

            if persisted_focus_ticker:
                render_asset_focus(
                    persisted_focus_ticker,
                    scanner,
                    key_prefix="scanner",
                    asset_lookup=asset_lookup,
                    strategy_config=edited_preset
                )

    if not reports["decisions"].empty:
        with st.expander("Decision log scanner", expanded=False):
            st.dataframe(reports["decisions"], width="stretch")


with portfolio_tab:
    st.subheader("Paper Portfolio")

    paper_files = sorted(glob("reports/paper_portfolio_plan_*.csv"))
    summary_file = get_latest_file("reports/paper_summary_*.csv")
    manifest_file = get_latest_file("reports/run_manifest_*.json")
    universe_file = get_latest_file("reports/universe_snapshot_*.csv")

    if paper.empty:
        st.warning("Nessun paper portfolio trovato.")
    else:
        st.dataframe(paper, width="stretch")

    previous_paper_file = get_previous_file(
        "reports/paper_portfolio_plan_*.csv"
    )

    if previous_paper_file and not paper.empty:
        previous_portfolio = load_csv_or_empty(previous_paper_file)
        current_tickers = set(paper.get("ticker", []))
        previous_tickers = set(previous_portfolio.get("ticker", []))

        comparison_df = pd.DataFrame([
            {
                "status": "ADDED",
                "tickers": ", ".join(sorted(
                    current_tickers - previous_tickers
                )) or "-"
            },
            {
                "status": "REMOVED",
                "tickers": ", ".join(sorted(
                    previous_tickers - current_tickers
                )) or "-"
            },
            {
                "status": "UNCHANGED",
                "tickers": ", ".join(sorted(
                    current_tickers & previous_tickers
                )) or "-"
            }
        ])

        st.subheader("Confronto con run precedente")
        st.dataframe(comparison_df, width="stretch")

    with st.expander("Audit files", expanded=False):
        render_file_reference(
            "paper plan",
            paper_files[-1] if paper_files else None
        )
        render_file_reference("summary", summary_file)
        render_file_reference("manifest", manifest_file)
        render_file_reference("universe snapshot", universe_file)

        if manifest_file:
            with open(manifest_file, "r", encoding="utf-8") as file:
                st.json(json.load(file))


with backtest_tab:
    st.subheader("Testa strategia")
    st.caption(
        f"Universo attivo: {len(market_assets)} ticker; "
        f"{len(cached_market_assets)} gia presenti in cache prezzi daily."
    )
    setup_col1, setup_col2, setup_col3 = st.columns(3)
    setup_col1.metric("Preset attivo", active_preset_name)
    setup_col2.metric("Preset confronto", len(selected_preset_names))
    setup_col3.metric("Asset stimati", estimated_backtest_assets)
    st.caption(
        "I controlli completi sono nel pannello laterale 'Setup strategia e "
        "backtest'. Qui resta visibile l'azione principale e l'esito del run."
    )
    page_run_market_backtest = st.button(
        "Esegui backtest",
        type="primary",
        width="stretch"
    )
    backtest_requested = run_market_backtest or page_run_market_backtest

    if not market_loaded:
        st.warning(
            "I mercati selezionati non sono disponibili ora. Cambia mercato o "
            "riprova piu tardi."
        )
    elif backtest_requested:
        if start_date_value >= end_date_value:
            st.warning("La data iniziale deve essere precedente alla finale.")
            st.stop()


        strategy_curves = []
        strategy_metrics_list = []
        benchmark_curves = []
        benchmark_metrics_list = []
        backtest_assets = market_assets

        if use_only_cached_assets:
            backtest_assets = cached_market_assets

        if not use_full_backtest_universe:
            backtest_assets = (
                st.session_state["favorite_watchlist"] or manual_basket_assets
            )

        if not backtest_assets:
            st.warning("Nessun asset disponibile per il backtest.")
            st.stop()

        strategy_names_to_run = (
            selected_preset_names
            if selected_preset_names
            else [active_preset_name]
        )
        estimated_weeks = max(
            len(pd.date_range(
                start=start_date,
                end=end_date,
                freq="W-MON"
            )) - 1,
            0
        )
        total_progress_steps = (
            len(backtest_assets) +
            len(strategy_names_to_run) *
            (len(backtest_assets) + estimated_weeks)
        )

        if use_manual_basket and manual_basket_assets:
            total_progress_steps += 1

        if use_engine_basket:
            total_progress_steps += 1

        progress_update, progress_callback = build_backtest_progress_tracker(
            total_progress_steps
        )
        progress_update(
            f"Avvio backtest: {len(strategy_names_to_run)} preset, "
            f"{len(backtest_assets)} ticker, {estimated_weeks} settimane"
        )

        price_session_key = build_price_data_session_key(
            tickers=backtest_assets
        )
        cached_price_session = st.session_state.get(
            "backtest_price_data_cache",
            {}
        )

        if cached_price_session.get("key") == price_session_key:
            price_data_by_ticker = cached_price_session.get("data", {})
            price_load_metadata = cached_price_session.get("metadata", {})
            price_load_metadata = {
                **price_load_metadata,
                "memory_reused": True
            }
            progress_update(
                f"Prezzi riusati dalla memoria sessione: "
                f"{len(price_data_by_ticker)} ticker",
                step_increment=len(backtest_assets)
            )
        else:
            progress_update("Caricamento prezzi bulk")
            price_data_by_ticker, price_load_metadata = load_market_price_data(
                tickers=backtest_assets,
                progress_callback=progress_callback,
                return_metadata=True,
                download_missing=not use_only_cached_assets
            )
            price_load_metadata["memory_reused"] = False
            st.session_state["backtest_price_data_cache"] = {
                "key": price_session_key,
                "data": price_data_by_ticker,
                "metadata": price_load_metadata
            }

        skipped_price_assets = (
            len(backtest_assets) - len(price_data_by_ticker)
        )
        if skipped_price_assets > 0:
            st.warning(
                f"{skipped_price_assets} asset esclusi: prezzi non "
                "disponibili o non caricabili."
            )

        if not price_data_by_ticker:
            st.warning("Nessun prezzo disponibile per il backtest.")
            st.stop()

        st.caption(
            "Prezzi backtest: "
            f"{len(price_data_by_ticker)} in memoria/run; "
            f"{price_load_metadata.get('from_cache', 0)} da cache fresca; "
            f"{price_load_metadata.get('downloaded', 0)} scaricati ora; "
            f"{price_load_metadata.get('excluded', 0)} esclusi."
        )

        primary_backtest_details = None

        for strategy_index, strategy_name in enumerate(strategy_names_to_run):
            strategy_params = (
                edited_preset
                if strategy_name == active_preset_name
                else presets[strategy_name]
            )

            progress_update(f"Preparazione preset {strategy_name}")
            backtest_kwargs = {
                "tickers": backtest_assets,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": portfolio_initial_capital,
                "commission_pct": strategy_params["commission_pct"],
                "slippage_pct": strategy_params["slippage_pct"],
                "min_hold_weeks": strategy_params["min_hold_weeks"],
                "max_volatility_pct": strategy_params["max_volatility_pct"],
                "min_scanner_score": strategy_params["min_scanner_score"],
                "persistence_weeks": strategy_params["persistence_weeks"],
                "switch_score_margin": strategy_params["switch_score_margin"],
                "top_n_candidates": strategy_params["top_n_candidates"],
                "strategy_config": strategy_params,
                "price_data_by_ticker": price_data_by_ticker,
                "return_details": strategy_index == 0
            }

            if supports_backtest_progress_callback():
                backtest_kwargs.update({
                    "progress_callback": progress_callback,
                    "progress_context": {"preset": strategy_name}
                })

            backtest_result = run_portfolio_backtest(**backtest_kwargs)

            if strategy_index == 0:
                (
                    portfolio_history,
                    portfolio_final_capital,
                    primary_backtest_details
                ) = backtest_result
            else:
                portfolio_history, portfolio_final_capital = backtest_result

            portfolio_metrics = calculate_portfolio_performance(
                portfolio_history=portfolio_history,
                initial_capital=portfolio_initial_capital,
                final_capital=portfolio_final_capital
            )

            strategy_curves.append({
                "name": strategy_name,
                "history": portfolio_history,
                "metrics": portfolio_metrics,
                "params": strategy_params,
                "details": primary_backtest_details if strategy_index == 0 else None
            })
            strategy_metrics_list.append({
                "strategy": strategy_name,
                "ma": (
                    f"{strategy_params['ma_type']} "
                    f"{strategy_params['fast_ma_period']}/"
                    f"{strategy_params['slow_ma_period']}/"
                    f"{strategy_params['long_ma_period']}"
                ),
                "rsi": (
                    f"{strategy_params['rsi_buy_min']}-"
                    f"{strategy_params['rsi_buy_max']}"
                ),
                "adx_filter": strategy_params["use_adx_filter"],
                "macd_filter": strategy_params["use_macd_filter"],
                "volume_filter": strategy_params["use_volume_filter"],
                **portfolio_metrics
            })

        primary_strategy = strategy_curves[0]
        primary_params = primary_strategy["params"]

        if use_manual_basket and manual_basket_assets:
            progress_update("Benchmark manuale in corso")
            manual_history, manual_final_capital = (
                run_static_basket_backtest(
                    tickers=manual_basket_assets,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=portfolio_initial_capital
                )
            )
            progress_update("Benchmark manuale completato", step_increment=1)

            manual_metrics = calculate_portfolio_performance(
                portfolio_history=manual_history.rename(
                    columns={"date": "scan_date"}
                ),
                initial_capital=portfolio_initial_capital,
                final_capital=manual_final_capital
            )

            benchmark_curves.append({
                "name": manual_basket_label,
                "assets": manual_basket_assets,
                "history": manual_history,
                "metrics": manual_metrics,
                "color": "deepskyblue"
            })
            benchmark_metrics_list.append({
                "benchmark": manual_basket_label,
                "assets": ", ".join(manual_basket_assets),
                **manual_metrics
            })

        if use_engine_basket:
            progress_update("Selezione paniere motore")
            scanner_start = scan_preloaded_market_on_date(
                market_data=(primary_backtest_details or {}).get("market_data", {}),
                scan_date=start_date,
            )

            if scanner_start.empty:
                engine_basket_assets = []
            else:
                valid_opportunities = scanner_start[
                    (scanner_start["signal"] == "BUY") &
                    (scanner_start["market_regime"] == "BULL") &
                    (
                        scanner_start["scanner_score"] >=
                        primary_params["min_scanner_score"]
                    ) &
                    (
                        scanner_start["volatility_%"] <=
                        primary_params["max_volatility_pct"]
                    )
                ]

                if not valid_opportunities.empty:
                    engine_basket_assets = (
                        valid_opportunities.head(
                            primary_params["engine_basket_size"]
                        )["ticker"].tolist()
                    )
                else:
                    engine_basket_assets = (
                        scanner_start.head(
                            primary_params["engine_basket_size"]
                        )["ticker"].tolist()
                    )

            engine_history, engine_final_capital = (
                run_static_basket_backtest(
                    tickers=engine_basket_assets,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=portfolio_initial_capital
                )
            )
            progress_update("Benchmark motore completato", step_increment=1)

            engine_metrics = calculate_portfolio_performance(
                portfolio_history=engine_history.rename(
                    columns={"date": "scan_date"}
                ),
                initial_capital=portfolio_initial_capital,
                final_capital=engine_final_capital
            )

            benchmark_curves.append({
                "name": "Engine Basket",
                "assets": engine_basket_assets,
                "history": engine_history,
                "metrics": engine_metrics,
                "color": "limegreen"
            })
            benchmark_metrics_list.append({
                "benchmark": "Engine Basket",
                "assets": ", ".join(engine_basket_assets),
                **engine_metrics
            })

        progress_update("Backtest completato")

        st.session_state["backtest_results"] = {
            "strategy_curves": strategy_curves,
            "strategy_metrics_list": strategy_metrics_list,
            "benchmark_curves": benchmark_curves,
            "benchmark_metrics_list": benchmark_metrics_list,
            "market_label": market_label
        }

    backtest_results = st.session_state.get("backtest_results")

    if backtest_results:
        strategy_curves = backtest_results["strategy_curves"]
        strategy_metrics_list = backtest_results["strategy_metrics_list"]
        benchmark_curves = backtest_results["benchmark_curves"]
        benchmark_metrics_list = backtest_results["benchmark_metrics_list"]
        result_market_label = backtest_results["market_label"]

        col1, col2, col3, col4 = st.columns(4)
        best_strategy = max(
            strategy_curves,
            key=lambda item: item["metrics"]["final_capital"]
        )
        best_metrics = best_strategy["metrics"]
        col1.metric("Best preset", best_strategy["name"])
        col2.metric("Return", f"{best_metrics['total_return_%']}%")
        col3.metric("Final Capital", f"${best_metrics['final_capital']}")
        col4.metric("Max DD", f"{best_metrics['max_drawdown_%']}%")

        st.plotly_chart(
            build_backtest_figure(
                strategy_curves=strategy_curves,
                benchmark_curves=benchmark_curves,
                selected_market=result_market_label
            ),
            width="stretch"
        )

        st.subheader("Confronto preset")
        st.dataframe(
            pd.DataFrame(strategy_metrics_list),
            width="stretch"
        )

        if benchmark_metrics_list:
            st.subheader("Benchmark Baskets")
            st.dataframe(
                pd.DataFrame(benchmark_metrics_list),
                width="stretch"
            )

        result_tab1, result_tab2, result_tab3, result_tab4 = st.tabs([
            "Portfolio dinamico",
            "Basket benchmark",
            "Download",
            "Prompt LLM"
        ])

        with result_tab1:
            selected_result_name = st.selectbox(
                "Risultato preset",
                [item["name"] for item in strategy_curves]
            )
            selected_result = next(
                item for item in strategy_curves
                if item["name"] == selected_result_name
            )
            st.dataframe(selected_result["history"], width="stretch")

        with result_tab2:
            for benchmark in benchmark_curves:
                st.subheader(benchmark["name"])
                st.caption("Asset: " + ", ".join(benchmark["assets"]))
                st.dataframe(benchmark["history"], width="stretch")

        with result_tab3:
            for strategy in strategy_curves:
                st.download_button(
                    label=f"Scarica CSV {strategy['name']}",
                    data=strategy["history"].to_csv(index=False),
                    file_name=(
                        f"{strategy['name'].lower().replace(' ', '_')}_"
                        f"{result_market_label}.csv"
                    ),
                    mime="text/csv"
                )

            for benchmark in benchmark_curves:
                st.download_button(
                    label=f"Scarica CSV {benchmark['name']}",
                    data=benchmark["history"].to_csv(index=False),
                    file_name=(
                        f"{benchmark['name'].lower().replace(' ', '_')}_"
                        f"{result_market_label}.csv"
                    ),
                    mime="text/csv"
                )

        with result_tab4:
            st.subheader("Prompt per analisi LLM")
            st.caption(
                "Genera un prompt completo da incollare in ChatGPT, "
                "Claude, Gemini o qualsiasi altro LLM."
            )

            prompt_preset = st.selectbox(
                "Preset da analizzare",
                [item["name"] for item in strategy_curves],
                key="prompt_preset_select"
            )

            prompt_strategy = next(
                item for item in strategy_curves
                if item["name"] == prompt_preset
            )

            if st.button("Genera Prompt", type="primary"):
                prompt_text = generate_prompt(
                    portfolio_history=prompt_strategy["history"],
                    portfolio_metrics=prompt_strategy["metrics"],
                    strategy_config=prompt_strategy["params"],
                    market_label=result_market_label
                )
                st.session_state["llm_prompt_text"] = prompt_text

            prompt_text = st.session_state.get("llm_prompt_text")
            if prompt_text:
                st.text_area(
                    "Prompt (copia e incolla nel tuo LLM preferito)",
                    value=prompt_text,
                    height=500,
                    key="llm_prompt_area"
                )
                st.download_button(
                    label="Scarica prompt come .txt",
                    data=prompt_text,
                    file_name=(
                        f"prompt_analisi_{prompt_preset.lower().replace(' ', '_')}"
                        f"_{result_market_label}.txt"
                    ),
                    mime="text/plain"
                )


    else:
        st.info(
            "Imposta i parametri nella sidebar e premi "
            "'Esegui Portfolio Backtest'."
        )


with glossary_tab:
    st.subheader("Strategia utilizzata dal motore")
    st.info(f"Strategia motore: {STRATEGY_NAME}")

    st.dataframe(
        pd.DataFrame(STRATEGY_RULES),
        width="stretch",
        hide_index=True
    )

    st.subheader("Parametri strategia")
    st.dataframe(
        pd.DataFrame(STRATEGY_PARAMETERS),
        width="stretch",
        hide_index=True
    )

    st.subheader("Legenda termini")
    st.dataframe(
        pd.DataFrame(TRADING_TERMS),
        width="stretch",
        hide_index=True
    )
