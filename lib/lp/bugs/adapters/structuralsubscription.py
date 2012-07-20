# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapt IStructuralSubscription to other types."""

__metaclass__ = type
__all__ = [
    'subscription_to_distribution',
    'subscription_to_product',
    ]


def subscription_to_distribution(subscription):
    """Adapt the `IStructuralSubscription` to an `IDistribution`."""
    if subscription.distroseries is not None:
        return subscription.distroseries.distribution
    return subscription.distribution


def subscription_to_product(subscription):
    """Adapt the `IStructuralSubscription` to an `IProduct`."""
    if subscription.productseries is not None:
        return subscription.productseries.product
    return subscription.product
