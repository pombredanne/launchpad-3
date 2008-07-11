# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters for ProductSeries."""

__metaclass__ = type
__all__ = [
    'productseries_to_hasexternalbugtracker',
    'productseries_to_launchpadusage',
    ]

def productseries_to_hasexternalbugtracker(productseries):
    """Adapts IProductSeries object to IHasExternalBugTracker."""
    return productseries.product

def productseries_to_launchpadusage(productseries):
    """Adapts IProductSeries object to ILaunchpadUsage."""
    return productseries.product
