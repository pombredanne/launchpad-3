import soupmatchers

from lp.testing import BrowserTestCase
from lp.testing.layers import DatabaseFunctionalLayer

class TestCodeSummaryView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_meaningful_branch_name(self):
        """The displayed branch name should include the unique name."""
        branch = self.factory.makeProductBranch()
        series = self.factory.makeProductSeries(branch=branch)
        tag = soupmatchers.Tag('series-branch', 'a',
                               attrs={'id': 'series-branch'},
                               text='lp:' + branch.unique_name)
        browser = self.getViewBrowser(series)
        self.assertThat(browser.contents, soupmatchers.HTMLContains(tag))
