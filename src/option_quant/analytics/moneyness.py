# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 19, 2026


def calculate_moneyness(
    strike: float,
    underlying_price: float,
) -> float:
    """
    Calculate option moneyness.

    Moneyness is defined as:

        strike / underlying_price

    Examples
    --------
    Strike = 190
    Underlying price = 220

    Moneyness = 190 / 220 = 0.8636

    Parameters
    ----------
    strike : float
        Option strike price.

    underlying_price : float
        Current underlying price.

    Returns
    -------
    float
        Moneyness ratio.

    Raises
    ------
    ValueError
        If strike or underlying price is not positive.
    """

    if strike <= 0:
        raise ValueError(
            "Strike must be greater than zero."
        )

    if underlying_price <= 0:
        raise ValueError(
            "Underlying price must be greater than zero."
        )

    return strike / underlying_price