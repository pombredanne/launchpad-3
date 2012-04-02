# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from textwrap import dedent

from testtools.matchers import MatchesStructure

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.blueprints.workitemmigration import (
    extractWorkItemsFromWhiteboard,
    WorkItemParseError,
    WorkitemParser,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class FakeSpecification(object):
    assignee = None


class TestWorkItemParser(TestCase):

    def test_parse_line_basic(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: TODO")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_line_with_assignee(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "[salgado] A single work item: TODO")
        self.assertEqual(
            ["salgado", "A single work item",
             SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_line_with_missing_closing_bracket_for_assignee(self):
        parser = WorkitemParser(FakeSpecification())
        self.assertRaises(
            WorkItemParseError, parser.parse_blueprint_workitem,
            "[salgado A single work item: TODO")

    def test_parse_line_without_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.TODO],
            [assignee, description, status])

    def test_parse_line_with_invalid_status(self):
        parser = WorkitemParser(FakeSpecification())
        self.assertRaises(
            WorkItemParseError, parser.parse_blueprint_workitem,
            "A single work item: FOO")

    def test_parse_line_without_description(self):
        parser = WorkitemParser(FakeSpecification())
        self.assertRaises(
            WorkItemParseError, parser.parse_blueprint_workitem,
            " : TODO")

    def test_parse_line_with_completed_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: Completed")
        self.assertEqual(
            [None, "A single work item", SpecificationWorkItemStatus.DONE],
            [assignee, description, status])

    def test_parse_line_with_inprogress_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: INPROGRESS")
        self.assertEqual(
            [None, "A single work item",
             SpecificationWorkItemStatus.INPROGRESS],
            [assignee, description, status])

    def test_parse_line_with_postpone_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: POSTPONE")
        self.assertEqual(
            [None, "A single work item",
             SpecificationWorkItemStatus.POSTPONED],
            [assignee, description, status])

    def test_parse_line_with_drop_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: DROP")
        self.assertEqual(
            [None, "A single work item",
             SpecificationWorkItemStatus.POSTPONED],
            [assignee, description, status])

    def test_parse_line_with_dropped_status(self):
        parser = WorkitemParser(FakeSpecification())
        assignee, description, status = parser.parse_blueprint_workitem(
            "A single work item: DROPPED")
        self.assertEqual(
            [None, "A single work item",
             SpecificationWorkItemStatus.POSTPONED],
            [assignee, description, status])

    def test_parse_empty_line(self):
        parser = WorkitemParser(FakeSpecification())
        self.assertRaises(
            AssertionError, parser.parse_blueprint_workitem, "")


class TestSpecificationWorkItemExtractionFromWhiteboard(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_None_whiteboard(self):
        spec = self.factory.makeSpecification(whiteboard=None)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual([], work_items)

    def test_empty_whiteboard(self):
        spec = self.factory.makeSpecification(whiteboard='')
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual([], work_items)

    def test_single_work_item(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item", milestone=None,
            status=SpecificationWorkItemStatus.TODO, specification=spec))

    def test_multiple_work_items(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO
            Another work item: DONE
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(2, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item", milestone=None,
            status=SpecificationWorkItemStatus.TODO, specification=spec))
        self.assertThat(work_items[1], MatchesStructure.byEquality(
            assignee=None, title="Another work item", milestone=None,
            status=SpecificationWorkItemStatus.DONE, specification=spec))

    def test_work_item_with_assignee(self):
        person = self.factory.makePerson()
        whiteboard = dedent("""
            Work items:
            [%s] A single work item: TODO
            """ % person.name)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=person, title="A single work item", milestone=None,
            status=SpecificationWorkItemStatus.TODO, specification=spec))

    def test_work_item_with_nonexistent_assignee(self):
        whiteboard = dedent("""
            Work items:
            [nonexistentperson] A single work item: TODO""")
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        self.assertRaises(ValueError, extractWorkItemsFromWhiteboard, spec)

    def test_work_item_with_milestone(self):
        milestone = self.factory.makeMilestone()
        whiteboard = dedent("""
            Work items for %s:
            A single work item: TODO
            """ % milestone.name)
        spec = self.factory.makeSpecification(
            whiteboard=whiteboard, product=milestone.product)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item", milestone=milestone,
            status=SpecificationWorkItemStatus.TODO, specification=spec))

    def test_work_item_with_inactive_milestone(self):
        milestone = self.factory.makeMilestone(active=False)
        whiteboard = dedent("""
            Work items for %s:
            A single work item: TODO
            """ % milestone.name)
        spec = self.factory.makeSpecification(
            whiteboard=whiteboard, product=milestone.product)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item", milestone=milestone,
            status=SpecificationWorkItemStatus.TODO, specification=spec))

    def test_work_item_with_unknown_milestone(self):
        whiteboard = dedent("""
            Work items for foo:
            A single work item: TODO
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        self.assertRaises(
            WorkItemParseError, extractWorkItemsFromWhiteboard, spec)

    def test_blank_line_signals_end_of_work_item_block(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO

            Some random notes about this BP.
              * This is what was discussed during UDS
              * Oh, yeah, we need to do that too
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item",
            status=SpecificationWorkItemStatus.TODO, specification=spec))

    def test_whiteboard_with_all_possible_sections(self):
        whiteboard = dedent("""
            Work items:
            A single work item: TODO

            Meta:
            Headline: Foo bar
            Acceptance: Baz foo

            Complexity:
            [user1] milestone1: 10
            """)
        spec = self.factory.makeSpecification(whiteboard=whiteboard)
        work_items = extractWorkItemsFromWhiteboard(spec)
        self.assertEqual(1, len(work_items))
        self.assertThat(work_items[0], MatchesStructure.byEquality(
            assignee=None, title="A single work item", milestone=None,
            status=SpecificationWorkItemStatus.TODO, specification=spec))

        # Now assert that the work items were removed from the whiteboard.
        self.assertEqual(dedent("""
            Meta:
            Headline: Foo bar
            Acceptance: Baz foo

            Complexity:
            [user1] milestone1: 10""").strip(), spec.whiteboard.strip())
