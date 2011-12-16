# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestone related test helper."""

__metaclass__ = type

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    )
from lp.registry.model.milestonetag import ProjectGroupMilestoneTag
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class MilestoneTagBugTaskTest(TestCaseWithFactory):
    """Test cases for retrieving bugtasks for a milestonetag."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(MilestoneTagBugTaskTest, self).setUp()
        self.owner = self.factory.makePerson()
        self.project_group = self.factory.makeProject(owner=self.owner)
        self.product = self.factory.makeProduct(
            name="product1",
            owner=self.owner,
            project=self.project_group)
        self.milestone = self.factory.makeMilestone(
            product=self.product)

    def _create_bugtasks(self, num, milestone=None):
        bugtasks = []
        with person_logged_in(self.owner):
            for n in xrange(num):
                bugtask = self.factory.makeBugTask(
                    target=self.product,
                    owner=self.owner)
                if milestone:
                    bugtask.milestone = milestone
                bugtasks.append(bugtask)
        return bugtasks

    def test_bugtask_retrieve_single_milestone(self):
        # Ensure that all bugtasks on a single milestone can be retrieved.
        tagname = u'tag1'
        with person_logged_in(self.owner):
            self.milestone.setTags([tagname], self.owner)
            bugtasks = self._create_bugtasks(5, self.milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=[tagname])
            self.assertContentEqual(
                bugtasks,
                milestonetag.bugtasks(self.owner))


class MilestoneSpecificationTest(TestCaseWithFactory):
    """Test cases for retrieving specifications for a milestone."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(MilestoneSpecificationTest, self).setUp()
        self.owner = self.factory.makePerson()
        self.product = self.factory.makeProduct(name="product1")
        self.milestone = self.factory.makeMilestone(product=self.product)

    def _create_specifications(self, num, milestone=None):
        specifications = []
        with person_logged_in(self.owner):
            for n in xrange(num):
                specification = self.factory.makeSpecification(
                    product=self.product,
                    owner=self.owner,
                    milestone=milestone)
                specifications.append(specification)
        return specifications

    def test_specification_retrieval(self):
        # Ensure that all specifications on a milestone can be retrieved.
        specifications = self._create_specifications(5, self.milestone)
        self.assertContentEqual(
            specifications,
            self.milestone.specifications)
