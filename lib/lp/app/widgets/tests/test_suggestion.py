# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )

from pytz import utc
from zope.schema import Choice
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.widgets.suggestion import TargetBranchWidget
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


def make_target_branch_widget(branch):
    """Given a branch, return a widget for selecting where to land it."""
    choice = Choice(vocabulary='Branch').bind(branch)
    request = LaunchpadTestRequest()
    return TargetBranchWidget(choice, None, request)


class TestTargetBranchWidget(TestCaseWithFactory):
    """Test the TargetBranchWidget class."""

    layer = DatabaseFunctionalLayer

    def test_stale_target(self):
        """Targets for proposals older than 90 days are not considered."""
        bmp = self.factory.makeBranchMergeProposal()
        target = bmp.target_branch
        source = self.factory.makeBranchTargetBranch(target.target)
        with person_logged_in(bmp.registrant):
            widget = make_target_branch_widget(source)
            self.assertIn(target, widget.suggestion_vocab)
            stale_date = datetime.now(utc) - timedelta(days=91)
            removeSecurityProxy(bmp).date_created = stale_date
            widget = make_target_branch_widget(source)
        self.assertNotIn(target, widget.suggestion_vocab)
