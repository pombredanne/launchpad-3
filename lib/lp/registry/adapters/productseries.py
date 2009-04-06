# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters for ProductSeries."""

__metaclass__ = type
__all__ = [
    'productseries_to_product',
    ]

def productseries_to_product(productseries):
    """Adapts `IProductSeries` object to `IProduct`.

    This is useful for adapting to `IHasExternalBugTracker`
    or `ILaunchpadUsage`.
    """
    return productseries.product
