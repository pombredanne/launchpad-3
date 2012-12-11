# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test projectmilestone tag views."""

__metaclass__ = type

from lp.registry.model.milestonetag import ProjectGroupMilestoneTag
from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_view

class TestProjectMilestoneTagView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_projectgroup_milestone(self):
        # The projectgroup milestone index page loads without errors.
        group = self.factory.makeProject()
        #product = self.factory.makeProduct(project=group)
        #milestone = self.factory.makeMilestone(product=product)
        #project_milestone = group.all_milestones[0]
        #view = create_view(project_milestone, name="+index")
        url = canonical_url(group) + "/+tags/fab/+index"
        browser = self.getUserBrowser(url=url)
        self.assertTrue('fab' in browser.contents)
