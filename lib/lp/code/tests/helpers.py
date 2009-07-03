# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Helper functions for code testing live here."""

__metaclass__ = type
__all__ = []


from datetime import timedelta
from itertools import count

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from zope.security.proxy import isinstance as zisinstance

from lp.code.interfaces.seriessourcepackagebranch import (
    IMakeOfficialBranchLinks)
from lp.registry.interfaces.distroseries import DistroSeriesStatus
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from lp.testing import time_counter


def consistent_branch_names():
    """Provide a generator for getting consistent branch names.

    This generator does not finish!
    """
    for name in ['trunk', 'testing', 'feature-x', 'feature-y', 'feature-z']:
        yield name
    index = count(1)
    while True:
        yield "branch-%s" % index.next()


def make_package_branches(factory, series, sourcepackagename, branch_count,
                          official_count=0, owner=None, registrant=None):
    """Make some package branches.

    Make `branch_count` branches, and make `official_count` of those
    official branches.
    """
    if zisinstance(sourcepackagename, basestring):
        sourcepackagename = factory.getOrMakeSourcePackageName(
            sourcepackagename)
    # Make the branches created in the past in order.
    time_gen = time_counter(delta=timedelta(days=-1))
    branch_names = consistent_branch_names()
    branches = [
        factory.makePackageBranch(
            distroseries=series,
            sourcepackagename=sourcepackagename,
            date_created=time_gen.next(),
            name=branch_names.next(), owner=owner, registrant=registrant)
        for i in range(branch_count)]

    official = []
    # We don't care about who can make things official, so get rid of the
    # security proxy.
    series_set = removeSecurityProxy(getUtility(IMakeOfficialBranchLinks))
    # Sort the pocket items so RELEASE is last, and thus first popped.
    pockets = sorted(PackagePublishingPocket.items, reverse=True)
    # Since there can be only one link per pocket, max out the number of
    # official branches at the pocket count.
    for i in range(min(official_count, len(pockets))):
        branch = branches.pop()
        pocket = pockets.pop()
        sspb = series_set.new(
            series, pocket, sourcepackagename, branch, branch.owner)
        official.append(branch)

    return series, branches, official


def make_mint_distro_with_branches(factory):
    """This method makes a distro called mint with many branches.

    The mint distro has the following series and status:
        wild - experimental
        dev - development
        stable - current
        old - supported
        very-old - supported
        ancient - supported
        mouldy - supported
        dead - obsolete

    The mint distro has a team: mint-team, which has Albert, Bob, and Charlie
    as members.

    There are four different source packages:
        twisted, zope, bzr, python
    """
    albert, bob, charlie = [
        factory.makePerson(
            name=name, email=("%s@mint.example.com" % name), password="test")
        for name in ('albert', 'bob', 'charlie')]
    mint_team = factory.makeTeam(owner=albert, name="mint-team")
    mint_team.addMember(bob, albert)
    mint_team.addMember(charlie, albert)
    mint = factory.makeDistribution(
        name='mint', displayname='Mint', owner=albert, members=mint_team)
    series = [
        ("wild", "5.5", DistroSeriesStatus.EXPERIMENTAL),
        ("dev", "4.0", DistroSeriesStatus.DEVELOPMENT),
        ("stable", "3.0", DistroSeriesStatus.CURRENT),
        ("old", "2.0", DistroSeriesStatus.SUPPORTED),
        ("very-old", "1.5", DistroSeriesStatus.SUPPORTED),
        ("ancient", "1.0", DistroSeriesStatus.SUPPORTED),
        ("mouldy", "0.6", DistroSeriesStatus.SUPPORTED),
        ("dead", "0.1", DistroSeriesStatus.OBSOLETE),
        ]
    for name, version, status in series:
        factory.makeDistroRelease(
            distribution=mint, version=version, status=status, name=name)

    for pkg_index, name in enumerate(['twisted', 'zope', 'bzr', 'python']):
        for series_index, series in enumerate(mint.serieses):
            # Over the series and source packages, we want to have different
            # combinations of official and branch counts.
            # Make the more recent series have most official branches.
            official_count = 6 - series_index
            branch_count = official_count + pkg_index
            make_package_branches(
                factory, series, name, branch_count, official_count,
                owner=mint_team, registrant=albert)
