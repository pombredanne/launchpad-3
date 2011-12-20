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


class MilestoneTagTest(TestCaseWithFactory):
    """Test cases for setting and retrieving milestone tags."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(MilestoneTagTest, self).setUp()
        self.milestone = self.factory.makeMilestone()
        self.person = self.milestone.target.owner
        self.tags = [u'tag2', u'tag1', u'tag3']

    def test_no_tags(self):
        # Ensure a newly created milestone does not have associated tags.
        self.assertEquals([], list(self.milestone.getTags()))

    def test_tags_setting_and_retrieval(self):
        # Ensure tags are correctly saved and retrieved from the db.
        with person_logged_in(self.person):
            self.milestone.setTags(self.tags, self.person)
        self.assertEqual(sorted(self.tags), list(self.milestone.getTags()))

    def test_tags_override(self):
        # Ensure you can override tags already associated with the milestone.
        with person_logged_in(self.person):
            self.milestone.setTags(self.tags, self.person)
            new_tags = [u'tag2', u'tag4', u'tag3']
            self.milestone.setTags(new_tags, self.person)
        self.assertEqual(sorted(new_tags), list(self.milestone.getTags()))

    def test_tags_deletion(self):
        # Ensure passing an empty sequence of tags deletes them all.
        with person_logged_in(self.person):
            self.milestone.setTags(self.tags, self.person)
            self.milestone.setTags([], self.person)
        self.assertEquals([], list(self.milestone.getTags()))


class ProjectGroupMilestoneTagTest(TestCaseWithFactory):
    """Test cases for retrieving bugtasks for a milestonetag."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProjectGroupMilestoneTagTest, self).setUp()
        self.owner = self.factory.makePerson()
        self.project_group = self.factory.makeProject(owner=self.owner)
        self.product = self.factory.makeProduct(
            name="product1",
            owner=self.owner,
            project=self.project_group)
        self.milestone = self.factory.makeMilestone(product=self.product)

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

    # Add a test similar to TestProjectExcludeConjoinedMasterSearch in
    # lp.bugs.tests.test_bugsearch_conjoined.

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

    def test_bugtasks_for_untagged_milestone(self):
        # Ensure that bugtasks for a project group are retrieved
        # only if associated with milestones having specified tags.
        tagname = u'tag1'
        new_milestone = self.factory.makeMilestone(product=self.product)
        with person_logged_in(self.owner):
            self.milestone.setTags([tagname], self.owner)
            bugtasks = self._create_bugtasks(5, self.milestone)
            self._create_bugtasks(3, new_milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=[tagname])
            self.assertContentEqual(
                bugtasks,
                milestonetag.bugtasks(self.owner))

    def test_bugtasks_multiple_tags(self):
        # Ensure that, in presence of multiple tags, only bugtasks
        # for milestones associated with all the tags are retrieved.
        tagnames = (u'tag1', u'tag2')
        new_milestone = self.factory.makeMilestone(product=self.product)
        with person_logged_in(self.owner):
            self.milestone.setTags(tagnames, self.owner)
            new_milestone.setTags(tagnames[:1], self.owner)
            bugtasks = self._create_bugtasks(5, self.milestone)
            self._create_bugtasks(3, new_milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=tagnames)
            self.assertContentEqual(
                bugtasks,
                milestonetag.bugtasks(self.owner))

    def test_specification_retrieval(self):
        # Ensure that all specifications on a milestone can be retrieved.
        tagname = u'tag1'
        with person_logged_in(self.owner):
            self.milestone.setTags([tagname], self.owner)
            specifications = self._create_specifications(5, self.milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=[tagname])
            self.assertContentEqual(
                specifications,
                milestonetag.specifications)

    def test_specifications_for_untagged_milestone(self):
        # Ensure that specifications for a project group are retrieved
        # only if associated with milestones having specified tags.
        tagname = u'tag1'
        new_milestone = self.factory.makeMilestone(product=self.product)
        with person_logged_in(self.owner):
            self.milestone.setTags([tagname], self.owner)
            specifications = self._create_specifications(5, self.milestone)
            self._create_specifications(3, new_milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=[tagname])
            self.assertContentEqual(
                specifications,
                milestonetag.specifications)

    def test_specifications_multiple_tags(self):
        # Ensure that, in presence of multiple tags, only specifications
        # for milestones associated with all the tags are retrieved.
        tagnames = (u'tag1', u'tag2')
        new_milestone = self.factory.makeMilestone(product=self.product)
        with person_logged_in(self.owner):
            self.milestone.setTags(tagnames, self.owner)
            new_milestone.setTags(tagnames[:1], self.owner)
            specifications = self._create_specifications(5, self.milestone)
            self._create_specifications(3, new_milestone)
            milestonetag = ProjectGroupMilestoneTag(
                target=self.project_group, tags=tagnames)
            self.assertContentEqual(
                specifications,
                milestonetag.specifications)
