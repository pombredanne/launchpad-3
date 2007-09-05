# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions/classes to be used when testing Personal Package Archives."""

__metaclass__ = type

from zope.component import getUtility

from canonical.database.constants import UTC_NOW

from canonical.launchpad.database.publishing import SecureSourcePackagePublishingHistory
from canonical.launchpad.database.sourcepackagerelease import SourcePackageRelease
from canonical.launchpad.interfaces import (
    IComponentSet, IDistributionSet, IPersonSet, ISourcePackageNameSet)
from canonical.lp.dbschema import PackagePublishingStatus, PackagePublishingPocket


def publishToTeamPPA(team=None, distroseries=None, sourcepackagerelease=None,
                     team_member=None):
    """Publish a signed package in a team PPA.

    It defaults to publishing mozilla-firefox signed by name16 in the ubuntu-team PPA for
    the ubuntutest distroseries.

    The team PPA must already be created.
    """
    if team is None:
        team = getUtility(IPersonSet).getByName("ubuntu-team")
    if distroseries is None:
        distroseries = getUtility(IDistributionSet)['ubuntutest']
    if sourcepackagerelease is None:
        firefox_name = getUtility(ISourcePackageNameSet)['mozilla-firefox']
        sourcepackagerelease = SourcePackageRelease.selectOneBy(
            sourcepackagenameID=firefox_name.id, version='0.9')
    if team_member is None:
        team_member = getUtility(IPersonSet).getByName("name16")

    sourcepackagerelease.dscsigningkey = team_member.gpgkeys[0]
    main_component = getUtility(IComponentSet)['main']
    SecureSourcePackagePublishingHistory(
        distroseries=distroseries,
        sourcepackagerelease=sourcepackagerelease,
        component=main_component,
        section=sourcepackagerelease.section,
        status=PackagePublishingStatus.PENDING,
        datecreated=UTC_NOW,
        pocket=PackagePublishingPocket.RELEASE,
        embargo=False,
        archive=team.archive)


