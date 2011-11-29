# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions/classes to be used when testing Personal Package Archives.
"""

__metaclass__ = type

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.soyuz.enums import (
    PackagePublishingPriority,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.testing.sampledata import (
    HOARY_DISTROSERIES_NAME,
    I386_ARCHITECTURE_NAME,
    MAIN_COMPONENT_NAME,
    UBUNTU_DEVELOPER_ADMIN_NAME,
    UBUNTU_UPLOAD_TEAM_NAME,
    WARTY_ONLY_SOURCEPACKAGENAME,
    WARTY_ONLY_SOURCEPACKAGEVERSION,
    )


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
        team_name = UBUNTU_UPLOAD_TEAM_NAME
    if team_member_name is None:
        team_member_name = UBUNTU_DEVELOPER_ADMIN_NAME
    team = getUtility(IPersonSet).getByName(team_name)
    _publishToPPA(
        team.archive, team_member_name, distroseries_name,
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
        distroseries_name = HOARY_DISTROSERIES_NAME
    if sourcepackage_name is None:
        sourcepackage_name = WARTY_ONLY_SOURCEPACKAGENAME
    if sourcepackage_version is None:
        sourcepackage_version = WARTY_ONLY_SOURCEPACKAGEVERSION
    if publishing_status is None:
        publishing_status = PackagePublishingStatus.PENDING
    if arch is None:
        arch = I386_ARCHITECTURE_NAME

    sourcepackagename = getUtility(ISourcePackageNameSet)[sourcepackage_name]
    distroseries = distribution[distroseries_name]
    sourcepackagerelease = SourcePackageRelease.selectOneBy(
            sourcepackagenameID=sourcepackagename.id,
            version=sourcepackage_version)

    person = getUtility(IPersonSet).getByName(person_name)
    if person.gpg_keys:
        # XXX: kiko 2007-10-25: oy, what a hack. I need to test with cprov
        # and he doesn't have a signing key in the database
        sourcepackagerelease.dscsigningkey = person.gpg_keys[0]
    main_component = getUtility(IComponentSet)[MAIN_COMPONENT_NAME]
    SourcePackagePublishingHistory(
        distroseries=distroseries,
        sourcepackagerelease=sourcepackagerelease,
        sourcepackagename=sourcepackagename,
        component=main_component,
        section=sourcepackagerelease.section,
        status=publishing_status,
        datecreated=UTC_NOW,
        pocket=PackagePublishingPocket.RELEASE,
        archive=archive)

    # Only publish binaries if the callsite specified a version.
    if binarypackage_version:
        binarypackagename = getUtility(
            IBinaryPackageNameSet)[sourcepackage_name]
        binarypackagerelease = BinaryPackageRelease.selectOneBy(
            binarypackagenameID=binarypackagename.id,
            version=binarypackage_version)
        distroarchseries = distroseries[arch]
        BinaryPackagePublishingHistory(
            binarypackagerelease=binarypackagerelease,
            binarypackagename=binarypackagename,
            distroarchseries=distroarchseries,
            component=main_component,
            section=sourcepackagerelease.section,
            priority=PackagePublishingPriority.STANDARD,
            status=publishing_status,
            datecreated=UTC_NOW,
            pocket=PackagePublishingPocket.RELEASE,
            archive=archive)
