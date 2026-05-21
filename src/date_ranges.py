from datetime import date

import pandas as pd


BACKTEST_DATE_RANGE_PRESETS = {
    "1W": pd.DateOffset(weeks=1),
    "2W": pd.DateOffset(weeks=2),
    "1M": pd.DateOffset(months=1),
    "3M": pd.DateOffset(months=3),
    "Ultimo quarto": pd.DateOffset(months=3),
    "6M": pd.DateOffset(months=6),
    "1Y": pd.DateOffset(years=1)
}


def get_start_date_for_range(end_date: date, range_label: str) -> date:
    offset = BACKTEST_DATE_RANGE_PRESETS[range_label]
    start_timestamp = pd.Timestamp(end_date) - offset

    return start_timestamp.date()
