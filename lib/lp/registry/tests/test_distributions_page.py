# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Distributions page."""

__metaclass__ = type

from lazr.lifecycle.snapshot import Snapshot
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.errors import NoSuchDistroSeries
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.tests.test_distroseries import (
    TestDistroSeriesCurrentSourceReleases,
    )
from lp.services.propertycache import get_property_cache
from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease,
    )
from lp.testing import TestCaseWithFactory
from lp.testing import login_person
from lp.testing.views import create_initialized_view

import soupmatchers

from zope.component import getUtility


class TestDistributionsPage(TestCaseWithFactory):
    """A TestCase for the distributions page."""
    
    layer = DatabaseFunctionalLayer

    def test_distributions_page_add_distro(self):
        """ Verify that an admin sees the +add link."""
        distributionset = getUtility(IDistributionSet)
        admin = getUtility(IPersonSet).getByEmail(
                    'admin@canonical.com')
        login_person(admin)
        view = create_initialized_view(distributionset, '+index',
            principal=admin)
        add_distro_matches = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a distro', 'a',
                attrs={'href':
                    canonical_url(distributionset, view_name='+index')},
                text='Register a distribution'),
            )
        self.assertThat(view.render(), add_distro_matches)



