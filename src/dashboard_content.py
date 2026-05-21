STRATEGY_NAME = "Rotazione trend-following configurabile"


STRATEGY_RULES = [
    {
        "Area": "Trend",
        "Regola": (
            "Il prezzo deve essere sopra la media di lungo periodo e la media "
            "veloce deve essere sopra quella lenta."
        )
    },
    {
        "Area": "Momentum",
        "Regola": (
            "RSI deve rimanere nel range buy del preset; MACD puo essere "
            "richiesto come conferma opzionale."
        )
    },
    {
        "Area": "Rischio",
        "Regola": (
            "ATR % deve restare sotto la volatilita massima definita dal "
            "preset."
        )
    },
    {
        "Area": "Conferme",
        "Regola": (
            "ADX e volume possono essere attivati per richiedere trend forte "
            "e partecipazione sopra media."
        )
    },
    {
        "Area": "Rotazione",
        "Regola": (
            "Il motore valuta i migliori candidati, richiede persistenza del "
            "segnale e ruota solo se il nuovo asset supera il margine minimo."
        )
    }
]


STRATEGY_PARAMETERS = [
    {
        "Parametro": "Tipo media",
        "Significato": "EMA reagisce piu in fretta; SMA e piu stabile.",
        "Impatto": "Controlla quanto rapidamente la strategia legge il trend."
    },
    {
        "Parametro": "Media veloce / lenta / lungo periodo",
        "Significato": "Periodi delle medie usate per trend breve, medio e filtro principale.",
        "Impatto": "Periodi piu bassi aumentano sensibilita e rotazioni."
    },
    {
        "Parametro": "RSI periodo",
        "Significato": "Numero di barre usate per calcolare il momentum RSI.",
        "Impatto": "Periodi bassi reagiscono prima ma sono piu rumorosi."
    },
    {
        "Parametro": "RSI buy range",
        "Significato": "Intervallo RSI accettato per aprire o mantenere setup BUY.",
        "Impatto": "Range stretto filtra di piu; range ampio e piu aggressivo."
    },
    {
        "Parametro": "RSI sell sopra",
        "Significato": "Soglia RSI oltre cui il setup viene considerato troppo esteso.",
        "Impatto": "Soglie basse escono prima, soglie alte lasciano correre."
    },
    {
        "Parametro": "ATR periodo",
        "Significato": "Periodo della misura di volatilita Average True Range.",
        "Impatto": "Determina quanto e stabile il filtro di volatilita."
    },
    {
        "Parametro": "Volatilita massima ATR %",
        "Significato": "ATR diviso prezzo, espresso in percentuale.",
        "Impatto": "Valori bassi riducono rischio ma scartano asset veloci."
    },
    {
        "Parametro": "ADX periodo / minimo",
        "Significato": "Misura la forza del trend, non la direzione.",
        "Impatto": "Richiedere ADX alto evita trend deboli o laterali."
    },
    {
        "Parametro": "MACD fast / slow / signal",
        "Significato": "Parametri del MACD e della linea segnale.",
        "Impatto": "MACD rapido intercetta prima ma aumenta falsi segnali."
    },
    {
        "Parametro": "MACD histogram",
        "Significato": "Differenza tra MACD e linea segnale.",
        "Impatto": "Istogramma positivo conferma momentum crescente."
    },
    {
        "Parametro": "Volume SMA / volume ratio",
        "Significato": "Volume corrente rispetto alla media volume.",
        "Impatto": "Richiede partecipazione del mercato sopra media."
    },
    {
        "Parametro": "AI score minimo",
        "Significato": "Punteggio tecnico deterministico calcolato dal motore.",
        "Impatto": "Soglie alte selezionano setup piu puliti."
    },
    {
        "Parametro": "Scanner score minimo",
        "Significato": "Ranking composito usato per ordinare gli asset.",
        "Impatto": "Soglie alte riducono il numero di candidati."
    },
    {
        "Parametro": "Persistenza segnale",
        "Significato": "Settimane in cui il segnale deve restare valido.",
        "Impatto": "Aumentarla riduce rotazioni impulsive."
    },
    {
        "Parametro": "Margine rotazione",
        "Significato": "Vantaggio minimo richiesto per sostituire l'asset corrente.",
        "Impatto": "Margini alti favoriscono stabilita del portafoglio."
    },
    {
        "Parametro": "Top candidati",
        "Significato": "Numero massimo di asset valutati a ogni ribilanciamento.",
        "Impatto": "Valori alti cercano piu opportunita ma aumentano rumore."
    },
    {
        "Parametro": "Commissione",
        "Significato": "Costo percentuale simulato per ogni entrata e uscita.",
        "Impatto": "Riduce il rendimento netto del backtest."
    },
    {
        "Parametro": "Slippage",
        "Significato": "Peggioramento simulato del prezzo eseguito.",
        "Impatto": "Rende il backtest piu prudente e realistico."
    }
]


TRADING_TERMS = [
    {
        "Termine": "ATR",
        "Significato": "Average True Range: misura di volatilita."
    },
    {
        "Termine": "RSI",
        "Significato": "Relative Strength Index: misura momentum ed eccessi."
    },
    {
        "Termine": "EMA",
        "Significato": "Media mobile esponenziale, piu reattiva ai prezzi recenti."
    },
    {
        "Termine": "SMA",
        "Significato": "Media mobile semplice, piu lenta e regolare."
    },
    {
        "Termine": "ADX",
        "Significato": "Indicatore di forza del trend."
    },
    {
        "Termine": "MACD",
        "Significato": "Indicatore momentum basato su differenza tra medie."
    },
    {
        "Termine": "Volume ratio",
        "Significato": "Volume corrente diviso per volume medio."
    },
    {
        "Termine": "BULL",
        "Significato": "Regime positivo con trend impostato al rialzo."
    },
    {
        "Termine": "BEAR",
        "Significato": "Regime negativo con trend impostato al ribasso."
    },
    {
        "Termine": "SIDEWAYS",
        "Significato": "Regime laterale senza direzione chiara."
    },
    {
        "Termine": "CASH",
        "Significato": "Portafoglio senza asset selezionato."
    },
    {
        "Termine": "Scanner Score",
        "Significato": "Punteggio composito che ordina gli asset."
    },
    {
        "Termine": "Drawdown",
        "Significato": "Perdita percentuale dal precedente picco di capitale."
    },
    {
        "Termine": "PnL",
        "Significato": "Profit and Loss: profitto o perdita."
    },
    {
        "Termine": "Slippage",
        "Significato": "Costo simulato causato da esecuzione non perfetta."
    }
]
