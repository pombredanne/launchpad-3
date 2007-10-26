# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper functions/classes to be used when testing Personal Package Archives."""

__metaclass__ = type

from zope.component import getUtility

from canonical.database.constants import UTC_NOW

from canonical.launchpad.database.publishing import (
    SecureBinaryPackagePublishingHistory,
    SecureSourcePackagePublishingHistory)
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IComponentSet, IDistributionSet, IPersonSet,
    ISourcePackageNameSet, PackagePublishingStatus, PackagePublishingPocket,
    PackagePublishingPriority)


def publishToTeamPPA(team_name=None,
                     distribution_name=None, distroseries_name=None,
                     sourcepackage_name=None, sourcepackage_version=None,
                     team_member_name=None, binarypackage_version=None,
                     publishing_status=None, arch=None):
    """Publish a signed package in a team PPA.

    It defaults to publishing mozilla-firefox 0.9 signed by name16 in
    the ubuntu-team PPA for the ubuntutest distroseries.

    The team PPA must already be created.
    """
    if team_name is None:
        team_name = "ubuntu-team"
    if distribution_name is None:
        distribution_name = "ubuntutest"
    if distroseries_name is None:
        distroseries_name = "breezy-autotest"
    if sourcepackage_name is None:
        sourcepackage_name = "mozilla-firefox"
    if sourcepackage_version is None:
        sourcepackage_version = "0.9"
    if team_member_name is None:
        team_member_name = "name16"
    if publishing_status is None:
        publishing_status = PackagePublishingStatus.PENDING
    if binarypackage_version is None:
        binarypackage_version = "0.9"
    if arch is None:
        arch = "i386"

    team = getUtility(IPersonSet).getByName(team_name)
    distribution = getUtility(IDistributionSet)[distribution_name]
    distroseries = distribution[distroseries_name]
    sourcepackagename = getUtility(ISourcePackageNameSet)[sourcepackage_name]
    sourcepackagerelease = SourcePackageRelease.selectOneBy(
            sourcepackagenameID=sourcepackagename.id,
            version=sourcepackage_version)
    team_member = getUtility(IPersonSet).getByName(team_member_name)

    if team_member.gpgkeys:
        sourcepackagerelease.dscsigningkey = team_member.gpgkeys[0]
    main_component = getUtility(IComponentSet)['main']
    SecureSourcePackagePublishingHistory(
        distroseries=distroseries,
        sourcepackagerelease=sourcepackagerelease,
        component=main_component,
        section=sourcepackagerelease.section,
        status=publishing_status,
        datecreated=UTC_NOW,
        pocket=PackagePublishingPocket.RELEASE,
        embargo=False,
        archive=team.archive)

    binarypackagename = getUtility(IBinaryPackageNameSet)[sourcepackage_name]
    binarypackagerelease = BinaryPackageRelease.selectOneBy(
        binarypackagenameID=binarypackagename.id,
        version=binarypackage_version)
    distroarchseries = distroseries[arch]
    SecureBinaryPackagePublishingHistory(
        binarypackagerelease=binarypackagerelease,
        distroarchseries=distroarchseries,
        component=main_component,
        section=sourcepackagerelease.section,
        priority=PackagePublishingPriority.STANDARD,
        status=publishing_status,
        datecreated=UTC_NOW,
        pocket=PackagePublishingPocket.RELEASE,
        embargo=False,
        archive=team.archive)


