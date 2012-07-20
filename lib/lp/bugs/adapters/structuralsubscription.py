# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapt IStructuralSubscription to other types."""

__metaclass__ = type
__all__ = [
    'subscription_to_product',
    ]


def subscription_to_product(subscription):
    """Adapt the `IStructuralSubscription` to an `IProduct`."""
    return subscription.product
