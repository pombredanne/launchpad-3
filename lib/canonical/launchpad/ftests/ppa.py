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


def publishToTeamPPA(team_name=None, distroseries_name=None, sourcepackage_name=None,
                     sourcepackage_version=None, team_member_name=None):
    """Publish a signed package in a team PPA.

    It defaults to publishing mozilla-firefox 0.9 signed by name16 in the ubuntu-team
    PPA for the ubuntutest distroseries.

    The team PPA must already be created.
    """
    if team_name is None:
        team_name = "ubuntu-team"
    if distroseries_name is None:
        distroseries_name = "ubuntutest"
    if sourcepackage_name is None:
        sourcepackage_name = "mozilla-firefox"
    if sourcepackage_version is None:
        sourcepackage_version = "0.9"
    if team_member_name is None:
        team_member_name = "name16"

    team = getUtility(IPersonSet).getByName(team_name)
    distroseries = getUtility(IDistributionSet)[distroseries_name]
    name = getUtility(ISourcePackageNameSet)[sourcepackage_name]
    sourcepackagerelease = SourcePackageRelease.selectOneBy(
            sourcepackagenameID=name.id, version=sourcepackage_version)
    team_member = getUtility(IPersonSet).getByName(team_member_name)

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


