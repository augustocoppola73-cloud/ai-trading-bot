import pandas as pd


SCREENER_PRESETS = [
    "Custom",
    "Candidati long",
    "RSI ipervenduto",
    "Volume sopra media",
    "Bassa volatilita",
    "Alta volatilita",
    "Uscite/Sell",
    "Watchlist"
]

SCREENER_SORT_OPTIONS = [
    "Setup score",
    "Scanner score",
    "RSI crescente",
    "Vol Ratio decrescente",
    "ATR crescente",
    "ATR decrescente",
    "Prezzo crescente",
    "Prezzo decrescente"
]

SCREENER_COLUMN_VIEWS = {
    "Compatta": [
        "watchlist",
        "ticker",
        "name",
        "close",
        "setup_score",
        "scanner_score",
        "signal",
        "market_regime",
        "rsi",
        "volatility_%",
        "volume_ratio",
        "opportunity_label"
    ],
    "Tecnica": [
        "watchlist",
        "market",
        "ticker",
        "name",
        "data_ultima_chiusura",
        "close",
        "setup_score",
        "scanner_score",
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
        "bb_bandwidth",
        "bb_percent_b",
        "data_status",
        "data_quality_reason",
        "price_rows",
        "buy_gate_passed",
        "buy_gate_fail_reasons",
        "score_consistency_status"
    ],
    "Completa": []
}


def get_screener_preset_defaults(preset_name: str) -> dict:
    defaults = {
        "only_watchlist": False,
        "signal_filter": "ALL",
        "regime_filter": "ALL",
        "opportunity_filter": "Tutti",
        "price_min": None,
        "price_max": None,
        "rsi_min": None,
        "rsi_max": None,
        "volume_ratio_min": None,
        "atr_min": None,
        "atr_max": None,
        "sort_by": "Setup score",
        "column_view": "Compatta"
    }

    if preset_name == "Candidati long":
        defaults.update({
            "signal_filter": "BUY",
            "regime_filter": "BULL",
            "opportunity_filter": "Solo candidati long",
            "sort_by": "Setup score"
        })
    elif preset_name == "RSI ipervenduto":
        defaults.update({
            "rsi_max": 35.0,
            "sort_by": "RSI crescente"
        })
    elif preset_name == "Volume sopra media":
        defaults.update({
            "volume_ratio_min": 1.0,
            "sort_by": "Vol Ratio decrescente"
        })
    elif preset_name == "Bassa volatilita":
        defaults.update({
            "atr_max": 3.0,
            "sort_by": "ATR crescente"
        })
    elif preset_name == "Alta volatilita":
        defaults.update({
            "atr_min": 6.0,
            "sort_by": "ATR decrescente"
        })
    elif preset_name == "Uscite/Sell":
        defaults.update({
            "signal_filter": "SELL",
            "opportunity_filter": "Solo sell/uscita",
            "sort_by": "Setup score"
        })
    elif preset_name == "Watchlist":
        defaults.update({
            "only_watchlist": True,
            "sort_by": "Setup score"
        })

    return defaults


def filter_screener_dataframe(
    screener: pd.DataFrame,
    market_filter: list,
    search_text: str,
    only_watchlist: bool,
    signal_filter: str,
    regime_filter: str,
    opportunity_filter: str,
    min_score: float | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    rsi_min: float | None = None,
    rsi_max: float | None = None,
    volume_ratio_min: float | None = None,
    atr_min: float | None = None,
    atr_max: float | None = None
) -> pd.DataFrame:
    filtered = screener.copy()

    if market_filter:
        filtered = filtered[filtered["market"].isin(market_filter)]

    if search_text:
        search_text = search_text.strip().lower()
        filtered = filtered[
            filtered["ticker"].str.lower().str.contains(
                search_text,
                na=False
            ) |
            filtered["name"].astype(str).str.lower().str.contains(
                search_text,
                na=False
            )
        ]

    if only_watchlist:
        filtered = filtered[filtered["watchlist"]]

    if signal_filter != "ALL":
        filtered = filtered[filtered["signal"] == signal_filter]

    if regime_filter != "ALL":
        filtered = filtered[filtered["market_regime"] == regime_filter]

    if opportunity_filter == "Solo candidati long":
        filtered = filtered[
            filtered["opportunity_label"].isin(["Strong BUY", "BUY"])
        ]
    elif opportunity_filter == "Solo sell/uscita":
        filtered = filtered[filtered["signal"] == "SELL"]

    if min_score is not None:
        filtered = filtered[
            filtered["scanner_score"].fillna(float("-inf")) >= min_score
        ]

    filtered = apply_numeric_range(filtered, "close", price_min, price_max)
    filtered = apply_numeric_range(filtered, "rsi", rsi_min, rsi_max)
    filtered = apply_numeric_range(
        filtered,
        "volume_ratio",
        volume_ratio_min,
        None
    )
    filtered = apply_numeric_range(
        filtered,
        "volatility_%",
        atr_min,
        atr_max
    )

    return filtered.reset_index(drop=True)


def apply_numeric_range(
    data: pd.DataFrame,
    column: str,
    minimum: float | None,
    maximum: float | None
) -> pd.DataFrame:
    if column not in data.columns:
        return data

    filtered = data
    values = pd.to_numeric(filtered[column], errors="coerce")

    if minimum is not None:
        filtered = filtered[values >= minimum]
        values = pd.to_numeric(filtered[column], errors="coerce")

    if maximum is not None:
        filtered = filtered[values <= maximum]

    return filtered


def sort_screener_dataframe(
    screener: pd.DataFrame,
    sort_by: str
) -> pd.DataFrame:
    sort_map = {
        "Setup score": ("setup_score", False),
        "Scanner score": ("scanner_score", False),
        "RSI crescente": ("rsi", True),
        "Vol Ratio decrescente": ("volume_ratio", False),
        "ATR crescente": ("volatility_%", True),
        "ATR decrescente": ("volatility_%", False),
        "Prezzo crescente": ("close", True),
        "Prezzo decrescente": ("close", False),
    }
    column, ascending = sort_map.get(sort_by, ("setup_score", False))

    if column not in screener.columns:
        return screener.reset_index(drop=True)

    sorted_data = screener.copy()
    sorted_data[column] = pd.to_numeric(sorted_data[column], errors="coerce")

    return (
        sorted_data
        .sort_values(
            by=["watchlist", column, "ticker"],
            ascending=[False, ascending, True],
            na_position="last"
        )
        .reset_index(drop=True)
    )


def get_screener_columns(
    screener: pd.DataFrame,
    column_view: str
) -> list:
    view_columns = SCREENER_COLUMN_VIEWS.get(column_view, [])

    if not view_columns:
        return screener.columns.tolist()

    return [
        column for column in view_columns
        if column in screener.columns
    ]
