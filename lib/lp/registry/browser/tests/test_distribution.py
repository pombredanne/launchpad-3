# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Distribution page."""

__metaclass__ = type

import soupmatchers
from testtools.matchers import (
    MatchesAny,
    Not,
    )

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.series import SeriesStatus
from lp.testing import (
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestDistributionPage(TestCaseWithFactory):
    """A TestCase for the distribution index page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionPage, self).setUp()
        self.distro = self.factory.makeDistribution(
            name="distro", displayname=u'distro')
        self.simple_user = self.factory.makePerson()

    def test_distributionpage_addseries_link(self):
        # An admin sees the +addseries link.
        self.admin = login_celebrity('admin')
        view = create_initialized_view(
            self.distro, '+index', principal=self.admin)
        series_matches = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'),
            soupmatchers.Tag(
                'Active series and milestones widget', 'h2',
                text='Active series and milestones'),
            )
        self.assertThat(view.render(), series_matches)

    def test_distributionpage_addseries_link_noadmin(self):
        # A non-admin does not see the +addseries link nor the series
        # header (since there is no series yet).
        login_person(self.simple_user)
        view = create_initialized_view(
            self.distro, '+index', principal=self.simple_user)
        add_series_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'))
        series_header_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Active series and milestones widget', 'h2',
                text='Active series and milestones'))
        self.assertThat(
            view.render(),
            Not(MatchesAny(add_series_match, series_header_match)))

    def test_distributionpage_series_list_noadmin(self):
        # A non-admin does see the series list when there is a series.
        series = self.factory.makeDistroSeries(distribution=self.distro,
            status=SeriesStatus.CURRENT)
        login_person(self.simple_user)
        view = create_initialized_view(
            self.distro, '+index', principal=self.simple_user)
        add_series_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'))
        series_header_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Active series and milestones widget', 'h2',
                text='Active series and milestones'))
        self.assertThat(view.render(), series_header_match)
        self.assertThat(view.render(), Not(add_series_match))
