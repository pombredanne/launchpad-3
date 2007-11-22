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


def publishToTeamPPA(team_name=None, distroseries_name=None,
                     sourcepackage_name=None, sourcepackage_version=None,
                     team_member_name=None, distribution_name=None,
                     binarypackage_version=None, publishing_status=None,
                     arch=None):
    """Publish a signed package in a team PPA.

    It defaults to publishing mozilla-firefox 0.9 signed by name16 in
    the ubuntu-team PPA for the 'hoary' distroseries.

    The team PPA must already be created.
    """
    if team_name is None:
        team_name = "ubuntu-team"
    if team_member_name is None:
        team_member_name = "name16"
    team = getUtility(IPersonSet).getByName(team_name)
    _publishToPPA(team.archive, team_member_name, distroseries_name,
                  sourcepackage_name, sourcepackage_version, distribution_name,
                  binarypackage_version, publishing_status, arch)

def publishToPPA(person_name, distroseries_name=None, sourcepackage_name=None,
                 sourcepackage_version=None, distribution_name=None,
                 binarypackage_version=None, publishing_status=None,
                 arch=None):
    person = getUtility(IPersonSet).getByName(person_name)
    _publishToPPA(person.archive, person_name, distroseries_name,
                  sourcepackage_name, sourcepackage_version,
                  distribution_name, binarypackage_version, publishing_status,
                  arch)

def _publishToPPA(archive, person_name, distroseries_name, sourcepackage_name,
                  sourcepackage_version, distribution_name,
                  binarypackage_version, publishing_status, arch):
    if distribution_name is None:
        distribution = archive.distribution
    else:
        distribution = getUtility(IDistributionSet)[distribution_name]
    if distroseries_name is None:
        distroseries_name = "hoary"
    if sourcepackage_name is None:
        sourcepackage_name = "mozilla-firefox"
    if sourcepackage_version is None:
        sourcepackage_version = "0.9"
    if publishing_status is None:
        publishing_status = PackagePublishingStatus.PENDING
    if arch is None:
        arch = "i386"

    sourcepackagename = getUtility(ISourcePackageNameSet)[sourcepackage_name]
    distroseries = distribution[distroseries_name]
    sourcepackagerelease = SourcePackageRelease.selectOneBy(
            sourcepackagenameID=sourcepackagename.id,
            version=sourcepackage_version)

    person = getUtility(IPersonSet).getByName(person_name)
    if person.gpgkeys:
        # XXX: oy, what a hack. I need to test with cprov and he doesn't
        # have a signing key in the database. -- kiko, 2007-10-25
        sourcepackagerelease.dscsigningkey = person.gpgkeys[0]
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
        archive=archive)

    # Only publish binaries if the callsite specified a version.
    if binarypackage_version:
        binarypackagename = getUtility(
            IBinaryPackageNameSet)[sourcepackage_name]
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
            archive=archive)
