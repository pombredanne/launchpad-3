# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions/classes for Soyuz tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

__all__ = [
    'Base64KeyMatches',
    'SoyuzTestHelper',
    ]

import base64

from testtools.matchers import (
    Equals,
    Matcher,
    )
from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.gpg.interfaces import IGPGHandler
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.publishing import SourcePackagePublishingHistory
from lp.testing.sampledata import (
    BUILDD_ADMIN_USERNAME,
    UBUNTU_DISTRIBUTION_NAME,
    )


class SoyuzTestHelper:
    """Helper class to support easier tests in Soyuz component."""

    def __init__(self):
        self.ubuntu = getUtility(IDistributionSet)[UBUNTU_DISTRIBUTION_NAME]
        self.cprov_archive = getUtility(
            IPersonSet).getByName(BUILDD_ADMIN_USERNAME).archive

    @property
    def sample_publishing_data(self):
        """Return a list of triples as (status, archive, pocket).

        Returns the following triples (in this order):

         1. ubuntu/PRIMARY, PENDING, RELEASE;
         2. ubuntu/PRIMARY, PUBLISHED, RELEASE;
         3. ubuntu/PRIMARY, PENDING, UPDATES;
         4. ubuntu/PRIMARY, PUBLISHED, PROPOSED;
         5. ubuntu/cprov PPA, PENDING, RELEASE;
         6. ubuntu/cprov PPA, PUBLISHED, RELEASE;
         7. ubuntu/cprov PPA, PENDING, UPDATES;
         8. ubuntu/cprov PPA, PUBLISHED, PROPOSED;
        """
        return [
            (PackagePublishingStatus.PENDING, self.ubuntu.main_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PUBLISHED, self.ubuntu.main_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PENDING, self.ubuntu.main_archive,
             PackagePublishingPocket.UPDATES),
            (PackagePublishingStatus.PUBLISHED, self.ubuntu.main_archive,
             PackagePublishingPocket.PROPOSED),
            (PackagePublishingStatus.PENDING, self.cprov_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PUBLISHED, self.cprov_archive,
             PackagePublishingPocket.RELEASE),
            (PackagePublishingStatus.PENDING, self.cprov_archive,
             PackagePublishingPocket.UPDATES),
            (PackagePublishingStatus.PUBLISHED, self.cprov_archive,
             PackagePublishingPocket.PROPOSED),
            ]

    def createPublishingForDistroSeries(self, sourcepackagerelease,
                                        distroseries):
        """Return a list of `SourcePackagePublishingHistory`.

        The publishing records are created according to the given
        `SourcePackageRelease` and `DistroSeries` for all
        (status, archive, pocket) returned from `sample_publishing_data`.
        """
        sample_pub = []
        for status, archive, pocket in self.sample_publishing_data:
            pub = SourcePackagePublishingHistory(
                sourcepackagerelease=sourcepackagerelease,
                sourcepackagename=sourcepackagerelease.sourcepackagename,
                distroseries=distroseries,
                component=sourcepackagerelease.component,
                section=sourcepackagerelease.section,
                status=status,
                archive=archive,
                pocket=pocket)
            # Flush the object changes into DB do guarantee stable database
            # ID order as expected in the callsites.
            sample_pub.append(pub)
        return sample_pub

    def checkPubList(self, expected, given):
        """Check if the given publication list matches the expected one.

        Return True if the lists matches, otherwise False.
        """
        return [p.id for p in expected] == [r.id for r in given]


class Base64KeyMatches(Matcher):
    """Matches if base64-encoded key material has a given fingerprint."""

    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    def match(self, encoded_key):
        key = base64.b64decode(encoded_key)
        return Equals(self.fingerprint).match(
            getUtility(IGPGHandler).importPublicKey(key).fingerprint)

    def __str__(self):
        return "Base64KeyMatches(%s)" % self.fingerprint
