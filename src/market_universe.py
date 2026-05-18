from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from market_cache import (
    load_symbol_metadata,
    load_universe_records,
    save_provider_error,
    save_symbol_metadata,
    save_universe_records
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

NASDAQ_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
)
OTHER_LISTED_URL = (
    "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
)

OVERRIDES_FILE = Path("reports/market_catalog_overrides.csv")
ITALY_CATALOG_FILE = Path("reports/market_catalog_italy.csv")
EUROPE_CATALOG_FILE = Path("reports/market_catalog_europe_core.csv")


ITALY_SEED = [
    ("ENEL.MI", "Enel S.p.A."),
    ("ENI.MI", "Eni S.p.A."),
    ("ISP.MI", "Intesa Sanpaolo S.p.A."),
    ("UCG.MI", "UniCredit S.p.A."),
    ("STLAM.MI", "Stellantis N.V."),
    ("RACE.MI", "Ferrari N.V."),
    ("STM.MI", "STMicroelectronics N.V."),
    ("G.MI", "Assicurazioni Generali S.p.A."),
    ("PRY.MI", "Prysmian S.p.A."),
    ("MONC.MI", "Moncler S.p.A."),
    ("LDO.MI", "Leonardo S.p.A."),
    ("TEN.MI", "Tenaris S.A."),
    ("TIT.MI", "Telecom Italia S.p.A."),
    ("BAMI.MI", "Banco BPM S.p.A."),
    ("BMED.MI", "Banca Mediolanum S.p.A."),
    ("TIP.MI", "Tamburi Investment Partners S.p.A."),
    ("A2A.MI", "A2A S.p.A."),
    ("AMP.MI", "Amplifon S.p.A."),
    ("AZM.MI", "Azimut Holding S.p.A."),
    ("BPE.MI", "BPER Banca S.p.A."),
    ("CPR.MI", "Davide Campari-Milano N.V."),
    ("DIA.MI", "DiaSorin S.p.A."),
    ("FBK.MI", "FinecoBank Banca Fineco S.p.A."),
    ("HER.MI", "Hera S.p.A."),
    ("IG.MI", "Italgas S.p.A."),
    ("IP.MI", "Interpump Group S.p.A."),
    ("MB.MI", "Mediobanca Banca di Credito Finanziario S.p.A."),
    ("NEXI.MI", "Nexi S.p.A."),
    ("REC.MI", "Recordati S.p.A."),
    ("PST.MI", "Poste Italiane S.p.A."),
    ("SRG.MI", "Snam S.p.A."),
    ("TRN.MI", "Terna S.p.A."),
    ("ERG.MI", "ERG S.p.A."),
    ("UNI.MI", "Unipol Gruppo S.p.A."),
    ("BFF.MI", "BFF Bank S.p.A."),
    ("DOV.MI", "doValue S.p.A."),
    ("MARR.MI", "MARR S.p.A."),
    ("SFER.MI", "Salvatore Ferragamo S.p.A."),
    ("SOL.MI", "SOL S.p.A."),
    ("ZV.MI", "Zignago Vetro S.p.A.")
]

EUROPE_CORE_SEED = [
    ("AIR.PA", "Airbus SE", "France - Euronext Paris", "EUR"),
    ("OR.PA", "L'Oreal S.A.", "France - Euronext Paris", "EUR"),
    ("MC.PA", "LVMH Moet Hennessy Louis Vuitton", "France - Euronext Paris", "EUR"),
    ("SAN.PA", "Sanofi S.A.", "France - Euronext Paris", "EUR"),
    ("TTE.PA", "TotalEnergies SE", "France - Euronext Paris", "EUR"),
    ("SAP.DE", "SAP SE", "Germany - Xetra", "EUR"),
    ("SIE.DE", "Siemens AG", "Germany - Xetra", "EUR"),
    ("ALV.DE", "Allianz SE", "Germany - Xetra", "EUR"),
    ("DTE.DE", "Deutsche Telekom AG", "Germany - Xetra", "EUR"),
    ("BAS.DE", "BASF SE", "Germany - Xetra", "EUR"),
    ("ASML.AS", "ASML Holding N.V.", "Netherlands - Euronext Amsterdam", "EUR"),
    ("INGA.AS", "ING Groep N.V.", "Netherlands - Euronext Amsterdam", "EUR"),
    ("SAN.MC", "Banco Santander S.A.", "Spain - Bolsa de Madrid", "EUR"),
    ("ITX.MC", "Industria de Diseno Textil S.A.", "Spain - Bolsa de Madrid", "EUR"),
    ("NESN.SW", "Nestle S.A.", "Switzerland - SIX", "CHF"),
    ("NOVN.SW", "Novartis AG", "Switzerland - SIX", "CHF"),
    ("ROG.SW", "Roche Holding AG", "Switzerland - SIX", "CHF"),
    ("AZN.L", "AstraZeneca PLC", "UK - London Stock Exchange", "GBp"),
    ("SHEL.L", "Shell PLC", "UK - London Stock Exchange", "GBp"),
    ("HSBA.L", "HSBC Holdings PLC", "UK - London Stock Exchange", "GBp")
]


MARKET_DEFINITIONS = [
    {
        "group": "USA",
        "market": "USA - Nasdaq Listed",
        "loader": "nasdaq_listed"
    },
    {
        "group": "USA",
        "market": "USA - NYSE / AMEX / ARCA / Other Listed",
        "loader": "other_listed"
    },
    {
        "group": "ETF",
        "market": "USA - ETF",
        "loader": "usa_etf"
    },
    {
        "group": "Italy",
        "market": "Italy - Borsa Italiana",
        "loader": "italy_seed"
    },
    {
        "group": "Europe",
        "market": "Europe - Core",
        "loader": "europe_seed"
    },
    {
        "group": "Crypto",
        "market": "Crypto Top 100",
        "loader": "crypto_top"
    },
    {
        "group": "Custom",
        "market": "Custom / Verified",
        "loader": "custom_verified"
    }
]


def normalize_ticker(ticker: str) -> str:
    return str(ticker).strip().upper().replace(".", "-")


def normalize_yfinance_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()


def read_delimited_url(url: str, separator: str = "|") -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    rows = [
        line
        for line in response.text.splitlines()
        if line and not line.startswith("File Creation Time")
    ]

    return pd.read_csv(StringIO("\n".join(rows)), sep=separator)


def read_html_tables(url: str):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    return pd.read_html(response.text)


def asset_record(
    group: str,
    market: str,
    ticker: str,
    name: str,
    asset_type: str,
    exchange: str = "",
    currency: str = "USD",
    source: str = ""
) -> dict:
    return {
        "group": group,
        "market": market,
        "ticker": ticker,
        "name": name,
        "asset_type": asset_type,
        "exchange": exchange,
        "currency": currency,
        "source": source
    }


def load_or_fetch_market(market_name: str, fetcher) -> list:
    cached_records = load_universe_records(market_name)

    if cached_records:
        return cached_records

    records = fetcher()
    save_universe_records(market_name, records)

    return records


def get_nasdaq_listed_assets() -> list:
    market_name = "USA - Nasdaq Listed"

    def fetcher():
        table = read_delimited_url(NASDAQ_LISTED_URL)
        table = table[
            (table["Test Issue"] == "N") &
            (table["Symbol"].notna())
        ]

        return [
            asset_record(
                group="USA",
                market=market_name,
                ticker=normalize_ticker(row["Symbol"]),
                name=row["Security Name"],
                asset_type="Stock",
                exchange="NASDAQ",
                currency="USD",
                source="nasdaqtrader"
            )
            for _, row in table.iterrows()
        ]

    return load_or_fetch_market(market_name, fetcher)


def get_other_listed_assets() -> list:
    market_name = "USA - NYSE / AMEX / ARCA / Other Listed"

    def fetcher():
        table = read_delimited_url(OTHER_LISTED_URL)
        table = table[
            (table["Test Issue"] == "N") &
            (table["ACT Symbol"].notna())
        ]
        exchange_names = {
            "A": "NYSE American",
            "N": "NYSE",
            "P": "NYSE Arca",
            "Z": "Cboe BZX",
            "V": "IEX"
        }

        return [
            asset_record(
                group="USA",
                market=market_name,
                ticker=normalize_ticker(row["ACT Symbol"]),
                name=row["Security Name"],
                asset_type=(
                    "ETF" if bool(row.get("ETF", "N") == "Y") else "Stock"
                ),
                exchange=exchange_names.get(row.get("Exchange"), ""),
                currency="USD",
                source="nasdaqtrader"
            )
            for _, row in table.iterrows()
        ]

    return load_or_fetch_market(market_name, fetcher)


def get_usa_etf_assets() -> list:
    market_name = "USA - ETF"

    def fetcher():
        etf_records = []
        for record in get_other_listed_assets() + get_nasdaq_listed_assets():
            name = record["name"].upper()
            is_etf = (
                record["asset_type"] == "ETF" or
                " ETF" in name or
                "EXCHANGE TRADED" in name or
                " FUND" in name or
                " TRUST" in name
            )

            if is_etf:
                etf_record = record.copy()
                etf_record["group"] = "ETF"
                etf_record["market"] = market_name
                etf_record["asset_type"] = "ETF"
                etf_records.append(etf_record)

        return etf_records

    return load_or_fetch_market(market_name, fetcher)


def ensure_seed_file(path: Path, rows: list, columns: list):
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def get_italy_assets() -> list:
    ensure_seed_file(
        ITALY_CATALOG_FILE,
        ITALY_SEED,
        ["ticker", "name"]
    )
    table = pd.read_csv(ITALY_CATALOG_FILE)

    return [
        asset_record(
            group="Italy",
            market="Italy - Borsa Italiana",
            ticker=normalize_yfinance_ticker(row["ticker"]),
            name=row["name"],
            asset_type=row.get("asset_type", "Stock"),
            exchange=row.get("exchange", "Borsa Italiana"),
            currency=row.get("currency", "EUR"),
            source="local_seed"
        )
        for _, row in table.iterrows()
    ]


def get_europe_core_assets() -> list:
    ensure_seed_file(
        EUROPE_CATALOG_FILE,
        EUROPE_CORE_SEED,
        ["ticker", "name", "exchange", "currency"]
    )
    table = pd.read_csv(EUROPE_CATALOG_FILE)

    return [
        asset_record(
            group="Europe",
            market="Europe - Core",
            ticker=normalize_yfinance_ticker(row["ticker"]),
            name=row["name"],
            asset_type=row.get("asset_type", "Stock"),
            exchange=row.get("exchange", ""),
            currency=row.get("currency", "EUR"),
            source="local_seed"
        )
        for _, row in table.iterrows()
    ]


def get_crypto_top_assets(limit: int = 100) -> list:
    market_name = f"Crypto Top {limit}"

    def fetcher():
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false"
        }
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

        return [
            asset_record(
                group="Crypto",
                market=market_name,
                ticker=f"{coin['symbol'].upper()}-USD",
                name=coin.get("name", coin["symbol"].upper()),
                asset_type="Crypto",
                exchange="CoinGecko",
                currency="USD",
                source="coingecko"
            )
            for coin in response.json()
        ]

    return load_or_fetch_market(market_name, fetcher)


def load_override_assets() -> list:
    if not OVERRIDES_FILE.exists():
        OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            columns=[
                "group",
                "market",
                "ticker",
                "name",
                "asset_type",
                "exchange",
                "currency",
                "source"
            ]
        ).to_csv(OVERRIDES_FILE, index=False)

    table = pd.read_csv(OVERRIDES_FILE)

    if table.empty:
        return []

    return [
        asset_record(
            group=row.get("group", "Custom"),
            market=row.get("market", "Custom / Verified"),
            ticker=normalize_yfinance_ticker(row["ticker"]),
            name=row.get("name", row["ticker"]),
            asset_type=row.get("asset_type", "Custom"),
            exchange=row.get("exchange", ""),
            currency=row.get("currency", ""),
            source=row.get("source", "user_override")
        )
        for _, row in table.iterrows()
        if pd.notna(row.get("ticker"))
    ]


def get_custom_verified_assets() -> list:
    return load_symbol_metadata() + load_override_assets()


def get_market_definitions() -> list:
    return MARKET_DEFINITIONS


def get_market_groups() -> list:
    groups = []

    for definition in MARKET_DEFINITIONS:
        if definition["group"] not in groups:
            groups.append(definition["group"])

    return groups


def get_markets_for_groups(groups: list) -> list:
    return [
        definition["market"]
        for definition in MARKET_DEFINITIONS
        if definition["group"] in groups
    ]


def get_market_names() -> list:
    return [definition["market"] for definition in MARKET_DEFINITIONS]


def get_asset_records_for_market(market_name: str) -> list:
    loaders = {
        "USA - Nasdaq Listed": get_nasdaq_listed_assets,
        "USA - NYSE / AMEX / ARCA / Other Listed": get_other_listed_assets,
        "USA - ETF": get_usa_etf_assets,
        "Italy - Borsa Italiana": get_italy_assets,
        "Europe - Core": get_europe_core_assets,
        "Crypto Top 100": lambda: get_crypto_top_assets(limit=100),
        "Custom / Verified": get_custom_verified_assets
    }
    loader = loaders.get(market_name)

    if loader is None:
        return []

    return loader()


def get_assets_for_market(market_name: str) -> list:
    return [
        record["ticker"]
        for record in get_asset_records_for_market(market_name)
    ]


def get_asset_records_for_market_with_status(market_name: str) -> tuple:
    try:
        assets = get_asset_records_for_market(market_name)

        return assets, True, ""

    except Exception as error:
        save_provider_error("market_universe", market_name, str(error))

        return [], False, str(error)


def get_assets_for_market_with_status(market_name: str) -> tuple:
    assets, loaded, error = get_asset_records_for_market_with_status(
        market_name
    )

    return [asset["ticker"] for asset in assets], loaded, error


def merge_asset_records(asset_groups: list) -> list:
    assets = []
    seen_assets = set()

    for asset_group in asset_groups:
        for asset in asset_group:
            ticker = asset["ticker"]
            market = asset["market"]
            key = (ticker, market)

            if key not in seen_assets:
                assets.append(asset)
                seen_assets.add(key)

    return assets


def get_all_market_asset_records_with_status() -> tuple:
    market_asset_groups = []
    loaded_markets = []
    failed_markets = []

    for market_name in get_market_names():
        try:
            market_assets = get_asset_records_for_market(market_name)
            market_asset_groups.append(market_assets)
            loaded_markets.append({
                "market": market_name,
                "assets": len(market_assets)
            })
        except Exception as error:
            failed_markets.append({
                "market": market_name,
                "error": str(error)
            })
            save_provider_error("market_universe", market_name, str(error))

    assets = merge_asset_records(market_asset_groups)

    return assets, loaded_markets, failed_markets


def get_all_market_assets_with_status() -> tuple:
    assets, loaded_markets, failed_markets = (
        get_all_market_asset_records_with_status()
    )

    return [asset["ticker"] for asset in assets], loaded_markets, failed_markets


def get_all_market_assets() -> list:
    assets, _, _ = get_all_market_assets_with_status()

    return assets


def save_verified_symbol(record: dict):
    save_symbol_metadata(record)
