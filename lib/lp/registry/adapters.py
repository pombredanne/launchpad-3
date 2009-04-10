# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Adapters for regisrty objects."""

__metaclass__ = type

__all__ = [
    'distroseries_to_launchpadusage',
    'PollSubset',
    'PollOptionSubset',
    'productseries_to_product',
    ]


from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal

from lp.registry.interfaces.poll import (
    IPollSet, IPollSubset, PollAlgorithm, PollStatus)


def distroseries_to_launchpadusage(distroseries):
    """Adapts `IDistroSeries` object to `ILaunchpadUsage`."""
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


class PollSubset:
    """Adapt an `IPoll` to an `IPollSubset`."""
    implements(IPollSubset)

    title = 'Team polls'

    def __init__(self, team=None):
        self.team = team

    def new(self, name, title, proposition, dateopens, datecloses,
            secrecy, allowspoilt, poll_type=PollAlgorithm.SIMPLE):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).new(
            self.team, name, title, proposition, dateopens,
            datecloses, secrecy, allowspoilt, poll_type)

    def getByName(self, name, default=None):
        """See IPollSubset."""
        assert self.team is not None
        pollset = getUtility(IPollSet)
        return pollset.getByTeamAndName(self.team, name, default)

    def getAll(self):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(self.team)

    def getOpenPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, [PollStatus.OPEN], orderBy='datecloses', when=when)

    def getClosedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, [PollStatus.CLOSED], orderBy='datecloses', when=when)

    def getNotYetOpenedPolls(self, when=None):
        """See IPollSubset."""
        assert self.team is not None
        return getUtility(IPollSet).selectByTeam(
            self.team, [PollStatus.NOT_YET_OPENED],
            orderBy='dateopens', when=when)


def productseries_to_product(productseries):
    """Adapts `IProductSeries` object to `IProduct`.

    This is useful for adapting to `IHasExternalBugTracker`
    or `ILaunchpadUsage`.
    """
    return productseries.product
