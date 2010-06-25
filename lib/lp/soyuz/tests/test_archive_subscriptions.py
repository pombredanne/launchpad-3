# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive features."""

from datetime import date, datetime, timedelta
import pytz
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import PersonVisibility
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.archive import (IArchiveSet, ArchivePurpose,
    ArchiveStatus, CannotSwitchPrivacy, InvalidPocketForPartnerArchive,
    InvalidPocketForPPA)
from lp.services.worlddata.interfaces.country import ICountrySet
from lp.soyuz.interfaces.archivearch import IArchiveArchSet
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.interfaces.binarypackagerelease import BinaryPackageFormat
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagerelease import (
    BinaryPackageReleaseDownloadCount)
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import login_person, TestCaseWithFactory


class TestArchiveSubscriptions(TestCaseWithFactory):
    """Edge-case tests for private PPA subscribers.

    See also lib/lp/soyuz/stories/ppa/xx-private-ppa-subscription-stories.txt
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a test archive."""
        super(TestArchiveSubscriptions, self).setUp()
        self.private_team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        self.archive = self.factory.makeArchive(
            private=True, owner=self.private_team)
        self.subscriber = self.factory.makePerson()

    def test_subscriber_can_access_private_team_ppa(self):
        # As per bug 597783, we need to make sure a subscriber can see
        # a private team's PPA after they have been given a subscription.
        login_person(self.archive.owner)
        self.archive.newSubscription(
            self.subscriber, registrant=self.archive.owner)

        login_person(self.subscriber)
        token = self.archive.newAuthToken(self.subscriber, token="test")
        self.assertEqual(token.token, "test")

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
