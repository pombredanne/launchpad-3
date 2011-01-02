# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for regisrty objects."""

__metaclass__ = type

__all__ = [
    'distroseries_to_distribution',
    'person_from_principal',
    'productseries_to_product',
    ]


from zope.component.interfaces import ComponentLookupError

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal


def distroseries_to_distribution(distroseries):
    """Adapts `IDistroSeries` object to `IDistribution`.

    This is useful for adapting to `IServiceUsage`
    or `ILaunchpadUsage`."""
    return distroseries.distribution


def person_from_principal(principal):
    """Adapt `ILaunchpadPrincipal` to `IPerson`."""
    if ILaunchpadPrincipal.providedBy(principal):
        if principal.person is None:
            raise ComponentLookupError
        return principal.person
    else:
        # This is not actually necessary when this is used as an adapter
        # from ILaunchpadPrincipal, as we know we always have an
        # ILaunchpadPrincipal.
        #
        # When Zope3 interfaces allow returning None for "cannot adapt"
        # we can return None here.
        ##return None
        raise ComponentLookupError


def productseries_to_product(productseries):
    """Adapts `IProductSeries` object to `IProduct`.

    This is useful for adapting to `IHasExternalBugTracker`
    or `ILaunchpadUsage`.
    """
    return productseries.product
