def calculate_position_size_by_risk(
    capital: float,
    entry_price: float,
    stop_loss_price: float,
    risk_per_trade: float = 0.01
):
    """
    Calcola la size in base al rischio massimo.
    """

    risk_amount = capital * risk_per_trade

    if capital <= 0 or entry_price <= 0 or risk_per_trade <= 0:
        return 0

    stop_distance_pct = abs(
        (entry_price - stop_loss_price)
        / entry_price
    )

    if stop_distance_pct <= 0:
        return 0

    capital_to_allocate = (
        risk_amount / stop_distance_pct
    )

    return min(capital_to_allocate, capital)
