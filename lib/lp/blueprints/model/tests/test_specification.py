# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for blueprints here."""

__metaclass__ = type

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from testtools.matchers import (
    Equals,
    MatchesStructure,
    )
from testtools.testcase import ExpectedException
import transaction
from zope.event import notify
from zope.interface import providedBy
from zope.security.interfaces import Unauthorized

from lp.app.validators import LaunchpadValidationError
from lp.blueprints.interfaces.specification import ISpecification
from lp.blueprints.interfaces.specificationworkitem import (
    SpecificationWorkItemStatus,
    )
from lp.blueprints.model.specificationworkitem import SpecificationWorkItem
from lp.registry.enums import InformationType
from lp.registry.errors import CannotChangeInformationType
from lp.registry.model.milestone import Milestone
from lp.services.mail import stub
from lp.services.webapp import canonical_url
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSpecificationDependencies(TestCaseWithFactory):
    """Test the methods for getting the dependencies for blueprints."""

    layer = DatabaseFunctionalLayer

    def test_no_deps(self):
        blueprint = self.factory.makeBlueprint()
        self.assertThat(list(blueprint.dependencies), Equals([]))
        self.assertThat(list(blueprint.all_deps), Equals([]))
        self.assertThat(list(blueprint.blocked_specs), Equals([]))
        self.assertThat(list(blueprint.all_blocked), Equals([]))

    def test_single_dependency(self):
        do_first = self.factory.makeBlueprint()
        do_next = self.factory.makeBlueprint()
        do_next.createDependency(do_first)
        self.assertThat(list(do_first.blocked_specs), Equals([do_next]))
        self.assertThat(list(do_first.all_blocked), Equals([do_next]))
        self.assertThat(list(do_next.dependencies), Equals([do_first]))
        self.assertThat(list(do_next.all_deps), Equals([do_first]))

    def test_linear_dependency(self):
        do_first = self.factory.makeBlueprint()
        do_next = self.factory.makeBlueprint()
        do_next.createDependency(do_first)
        do_last = self.factory.makeBlueprint()
        do_last.createDependency(do_next)
        self.assertThat(sorted(do_first.blocked_specs), Equals([do_next]))
        self.assertThat(
            sorted(do_first.all_blocked),
            Equals(sorted([do_next, do_last])))
        self.assertThat(sorted(do_last.dependencies), Equals([do_next]))
        self.assertThat(
            sorted(do_last.all_deps),
            Equals(sorted([do_first, do_next])))

    def test_diamond_dependency(self):
        #             do_first
        #            /        \
        #    do_next_lhs    do_next_rhs
        #            \        /
        #             do_last
        do_first = self.factory.makeBlueprint()
        do_next_lhs = self.factory.makeBlueprint()
        do_next_lhs.createDependency(do_first)
        do_next_rhs = self.factory.makeBlueprint()
        do_next_rhs.createDependency(do_first)
        do_last = self.factory.makeBlueprint()
        do_last.createDependency(do_next_lhs)
        do_last.createDependency(do_next_rhs)
        self.assertThat(
            sorted(do_first.blocked_specs),
            Equals(sorted([do_next_lhs, do_next_rhs])))
        self.assertThat(
            sorted(do_first.all_blocked),
            Equals(sorted([do_next_lhs, do_next_rhs, do_last])))
        self.assertThat(
            sorted(do_last.dependencies),
            Equals(sorted([do_next_lhs, do_next_rhs])))
        self.assertThat(
            sorted(do_last.all_deps),
            Equals(sorted([do_first, do_next_lhs, do_next_rhs])))


class TestSpecificationSubscriptionSort(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_subscribers(self):
        # Subscriptions are sorted by subscriber's displayname without regard
        # to case
        spec = self.factory.makeBlueprint()
        bob = self.factory.makePerson(name='zbob', displayname='Bob')
        ced = self.factory.makePerson(name='xed', displayname='ced')
        dave = self.factory.makePerson(name='wdave', displayname='Dave')
        spec.subscribe(bob, bob, True)
        spec.subscribe(ced, bob, True)
        spec.subscribe(dave, bob, True)
        sorted_subscriptions = [bob.displayname, ced.displayname,
            dave.displayname]
        people = [sub.person.displayname for sub in spec.subscriptions]
        self.assertEqual(sorted_subscriptions, people)


class TestSpecificationValidation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_specurl_validation_duplicate(self):
        existing = self.factory.makeSpecification(
            specurl=u'http://ubuntu.com')
        spec = self.factory.makeSpecification()
        url = canonical_url(existing)
        field = ISpecification['specurl'].bind(spec)
        e = self.assertRaises(LaunchpadValidationError, field.validate,
            u'http://ubuntu.com')
        self.assertEqual(
            '%s is already registered by <a href="%s">%s</a>.'
            % (u'http://ubuntu.com', url, existing.title), str(e))

    def test_specurl_validation_valid(self):
        spec = self.factory.makeSpecification()
        field = ISpecification['specurl'].bind(spec)
        field.validate(u'http://example.com/nigelb')

    def test_specurl_validation_escape(self):
        existing = self.factory.makeSpecification(
                specurl=u'http://ubuntu.com/foo',
                title='<script>alert("foo");</script>')
        cleaned_title = '&lt;script&gt;alert("foo");&lt;/script&gt;'
        spec = self.factory.makeSpecification()
        url = canonical_url(existing)
        field = ISpecification['specurl'].bind(spec)
        e = self.assertRaises(LaunchpadValidationError, field.validate,
            u'http://ubuntu.com/foo')
        self.assertEqual(
            '%s is already registered by <a href="%s">%s</a>.'
            % (u'http://ubuntu.com/foo', url, cleaned_title), str(e))


class TestSpecificationWorkItemsNotifications(TestCaseWithFactory):
    """ Test the notification related to SpecificationWorkItems on
    ISpecification."""

    layer = DatabaseFunctionalLayer

    def test_workitems_added_notification_message(self):
        """ Test that we get a notification for setting work items on a new
        specification."""
        stub.test_emails = []
        spec = self.factory.makeSpecification()
        old_spec = Snapshot(spec, providing=providedBy(spec))
        status = SpecificationWorkItemStatus.TODO
        new_work_item = {
            'title': u'A work item',
            'status': status,
            'assignee': None,
            'milestone': None,
            'sequence': 0
        }

        login_person(spec.owner)
        spec.updateWorkItems([new_work_item])
        # In production this notification is fired by lazr.restful for changes
        # in the specification form and notify(ObjectModifiedEvent(...)) for
        # changes in the +workitems form. We need to do it ourselves in this
        # test.
        notify(ObjectModifiedEvent(
            spec, old_spec, edited_fields=['workitems_text']))
        transaction.commit()

        self.assertEqual(1, len(stub.test_emails))
        rationale = 'Work items set to:\nWork items:\n%s: %s' % (
            new_work_item['title'],
            new_work_item['status'].name)
        [email] = stub.test_emails
        # Actual message is part 2 of the e-mail.
        msg = email[2]
        self.assertIn(rationale, msg)

    def test_workitems_deleted_notification_message(self):
        """ Test that we get a notification for deleting a work item."""
        stub.test_emails = []
        wi = self.factory.makeSpecificationWorkItem()
        spec = wi.specification
        old_spec = Snapshot(spec, providing=providedBy(spec))
        login_person(spec.owner)
        spec.updateWorkItems([])
        # In production this notification is fired by lazr.restful, but we
        # need to do it ourselves in this test.
        notify(ObjectModifiedEvent(
            spec, old_spec, edited_fields=['workitems_text']))
        transaction.commit()

        self.assertEqual(1, len(stub.test_emails))
        rationale = '- %s: %s' % (wi.title, wi.status.name)
        [email] = stub.test_emails
        # Actual message is part 2 of the e-mail.
        msg = email[2]
        self.assertIn(rationale, msg)

    def test_workitems_changed_notification_message(self):
        """ Test that we get a notification about a work item status change.
        This will be in the form of a line added and one deleted."""
        spec = self.factory.makeSpecification()
        original_status = SpecificationWorkItemStatus.TODO
        new_status = SpecificationWorkItemStatus.DONE
        original_work_item = {
            'title': u'The same work item',
            'status': original_status,
            'assignee': None,
            'milestone': None,
            'sequence': 0
        }
        new_work_item = {
            'title': u'The same work item',
            'status': new_status,
            'assignee': None,
            'milestone': None,
            'sequence': 0
        }
        login_person(spec.owner)
        spec.updateWorkItems([original_work_item])
        old_spec = Snapshot(spec, providing=providedBy(spec))

        stub.test_emails = []
        spec.updateWorkItems([new_work_item])
        # In production this notification is fired by lazr.restful, but we
        # need to do it ourselves in this test.
        notify(ObjectModifiedEvent(
            spec, old_spec, edited_fields=['workitems_text']))
        transaction.commit()

        self.assertEqual(1, len(stub.test_emails))
        rationale_removed = '- %s: %s' % (
            original_work_item['title'], original_work_item['status'].name)
        rationale_added = '+ %s: %s' % (
            new_work_item['title'], new_work_item['status'].name)
        [email] = stub.test_emails
        # Actual message is part 2 of the e-mail.
        msg = email[2]
        self.assertIn(rationale_removed, msg)
        self.assertIn(rationale_added, msg)


class TestSpecificationWorkItems(TestCaseWithFactory):
    """Test the Workitem-related methods of ISpecification."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSpecificationWorkItems, self).setUp()
        self.wi_header = self.factory.makeMilestone(
            name='none-milestone-as-header')

    def assertWorkItemsTextContains(self, spec, items):
        expected_lines = []
        for item in items:
            if isinstance(item, SpecificationWorkItem):
                line = ''
                if item.assignee is not None:
                    line = "[%s] " % item.assignee.name
                expected_lines.append(u"%s%s: %s" % (line, item.title,
                                                    item.status.name))
            else:
                self.assertIsInstance(item, Milestone)
                if expected_lines != []:
                    expected_lines.append(u"")
                if item == self.wi_header:
                    expected_lines.append(u"Work items:")
                else:
                    expected_lines.append(u"Work items for %s:" % item.name)
        expected = "\n".join(expected_lines)
        self.assertEqual(expected, spec.workitems_text)

    def test_anonymous_newworkitem_not_allowed(self):
        spec = self.factory.makeSpecification()
        login(ANONYMOUS)
        self.assertRaises(Unauthorized, getattr, spec, 'newWorkItem')

    def test_owner_newworkitem_allowed(self):
        spec = self.factory.makeSpecification()
        login_person(spec.owner)
        work_item = spec.newWorkItem(title=u'new-work-item', sequence=0)
        self.assertIsInstance(work_item, SpecificationWorkItem)

    def test_newworkitem_uses_passed_arguments(self):
        title = u'new-work-item'
        spec = self.factory.makeSpecification()
        assignee = self.factory.makePerson()
        milestone = self.factory.makeMilestone(product=spec.product)
        status = SpecificationWorkItemStatus.DONE
        login_person(spec.owner)
        work_item = spec.newWorkItem(
            title=title, assignee=assignee, milestone=milestone,
            status=status, sequence=0)
        self.assertEqual(spec, work_item.specification)
        self.assertEqual(assignee, work_item.assignee)
        self.assertEqual(status, work_item.status)
        self.assertEqual(title, work_item.title)
        self.assertEqual(milestone, work_item.milestone)

    def test_workitems_text_no_workitems(self):
        spec = self.factory.makeSpecification()
        self.assertEqual('', spec.workitems_text)

    def test_workitems_text_deleted_workitem(self):
        work_item = self.factory.makeSpecificationWorkItem(deleted=True)
        self.assertEqual('', work_item.specification.workitems_text)

    def test_workitems_text_single_workitem(self):
        work_item = self.factory.makeSpecificationWorkItem()
        self.assertWorkItemsTextContains(work_item.specification,
                                         [self.wi_header, work_item])

    def test_workitems_text_multi_workitems_all_statuses(self):
        spec = self.factory.makeSpecification()
        work_item1 = self.factory.makeSpecificationWorkItem(specification=spec,
            status=SpecificationWorkItemStatus.TODO)
        work_item2 = self.factory.makeSpecificationWorkItem(specification=spec,
            status=SpecificationWorkItemStatus.DONE)
        work_item3 = self.factory.makeSpecificationWorkItem(specification=spec,
            status=SpecificationWorkItemStatus.POSTPONED)
        work_item4 = self.factory.makeSpecificationWorkItem(specification=spec,
            status=SpecificationWorkItemStatus.INPROGRESS)
        work_item5 = self.factory.makeSpecificationWorkItem(specification=spec,
            status=SpecificationWorkItemStatus.BLOCKED)
        work_items = [self.wi_header, work_item1, work_item2, work_item3,
                      work_item4, work_item5]
        self.assertWorkItemsTextContains(spec, work_items)

    def test_workitems_text_with_milestone(self):
        spec = self.factory.makeSpecification()
        milestone = self.factory.makeMilestone(product=spec.product)
        login_person(spec.owner)
        work_item = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'new-work-item',
            status=SpecificationWorkItemStatus.TODO,
            milestone=milestone)
        items = [milestone, work_item]
        self.assertWorkItemsTextContains(spec, items)

    def test_workitems_text_with_implicit_and_explicit_milestone(self):
        spec = self.factory.makeSpecification()
        milestone = self.factory.makeMilestone(product=spec.product)
        login_person(spec.owner)
        work_item1 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with default milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=None)
        work_item2 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with set milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=milestone)
        items = [self.wi_header, work_item1, milestone, work_item2]
        self.assertWorkItemsTextContains(spec, items)

    def test_workitems_text_with_implicit_and_explicit_milestone_reverse(self):
        spec = self.factory.makeSpecification()
        milestone = self.factory.makeMilestone(product=spec.product)
        login_person(spec.owner)
        work_item1 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with set milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=milestone)
        work_item2 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with default milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=None)
        items = [milestone, work_item1, self.wi_header, work_item2]
        self.assertWorkItemsTextContains(spec, items)

    def test_workitems_text_with_different_milestones(self):
        spec = self.factory.makeSpecification()
        milestone1 = self.factory.makeMilestone(product=spec.product)
        milestone2 = self.factory.makeMilestone(product=spec.product)
        login_person(spec.owner)
        work_item1 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with first milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=milestone1)
        work_item2 = self.factory.makeSpecificationWorkItem(specification=spec,
            title=u'Work item with second milestone',
            status=SpecificationWorkItemStatus.TODO,
            milestone=milestone2)
        items = [milestone1, work_item1, milestone2, work_item2]
        self.assertWorkItemsTextContains(spec, items)

    def test_workitems_text_with_assignee(self):
        assignee = self.factory.makePerson()
        work_item = self.factory.makeSpecificationWorkItem(assignee=assignee)
        self.assertWorkItemsTextContains(
            work_item.specification, [self.wi_header, work_item])

    def test_work_items_property(self):
        spec = self.factory.makeSpecification()
        wi1 = self.factory.makeSpecificationWorkItem(
            specification=spec, sequence=2)
        wi2 = self.factory.makeSpecificationWorkItem(
            specification=spec, sequence=1)
        # This work item won't be included in the results of spec.work_items
        # because it is deleted.
        self.factory.makeSpecificationWorkItem(
            specification=spec, sequence=3, deleted=True)
        # This work item belongs to a different spec so it won't be returned
        # by spec.work_items.
        self.factory.makeSpecificationWorkItem()
        self.assertEqual([wi2, wi1], list(spec.work_items))

    def test_updateWorkItems_no_existing_items(self):
        """When there are no existing work items, updateWorkItems will create
        a new entry for every element in the list given to it.
        """
        spec = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        milestone = self.factory.makeMilestone(product=spec.product)
        work_item1_data = dict(
            title=u'Foo Bar', status=SpecificationWorkItemStatus.DONE,
            assignee=spec.owner, milestone=None)
        work_item2_data = dict(
            title=u'Bar Foo', status=SpecificationWorkItemStatus.TODO,
            assignee=None, milestone=milestone)

        # We start with no work items.
        self.assertEquals([], list(spec.work_items))

        login_person(spec.owner)
        spec.updateWorkItems([work_item1_data, work_item2_data])

        # And after calling updateWorkItems() we have 2 work items.
        self.assertEqual(2, spec.work_items.count())

        # The data dicts we pass to updateWorkItems() have no sequence because
        # that's taken from their position on the list, so we update our data
        # dicts with the sequence we expect our work items to have.
        work_item1_data['sequence'] = 0
        work_item2_data['sequence'] = 1

        # Assert that the work items ultimately inserted in the DB are exactly
        # what we expect them to be.
        created_wi1, created_wi2 = list(spec.work_items)
        self.assertThat(
            created_wi1, MatchesStructure.byEquality(**work_item1_data))
        self.assertThat(
            created_wi2, MatchesStructure.byEquality(**work_item2_data))

    def test_updateWorkItems_merges_with_existing_ones(self):
        spec = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        login_person(spec.owner)
        # Create two work-items in our database.
        wi1_data = self._createWorkItemAndReturnDataDict(spec)
        wi2_data = self._createWorkItemAndReturnDataDict(spec)
        self.assertEqual(2, spec.work_items.count())

        # These are the work items we'll be inserting.
        new_wi1_data = dict(
            title=u'Some Title', status=SpecificationWorkItemStatus.TODO,
            assignee=None, milestone=None)
        new_wi2_data = dict(
            title=u'Other title', status=SpecificationWorkItemStatus.TODO,
            assignee=None, milestone=None)

        # We want to insert the two work items above in the first and third
        # positions respectively, so the existing ones to be moved around
        # (e.g. have their sequence updated).
        work_items = [new_wi1_data, wi1_data, new_wi2_data, wi2_data]
        spec.updateWorkItems(work_items)

        # Update our data dicts with the sequences we expect the work items in
        # our DB to have.
        new_wi1_data['sequence'] = 0
        wi1_data['sequence'] = 1
        new_wi2_data['sequence'] = 2
        wi2_data['sequence'] = 3

        self.assertEqual(4, spec.work_items.count())
        for data, obj in zip(work_items, list(spec.work_items)):
            self.assertThat(obj, MatchesStructure.byEquality(**data))

    def _dup_work_items_set_up(self):
        spec = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        login_person(spec.owner)
        # Create two work-items in our database.
        wi1_data = self._createWorkItemAndReturnDataDict(spec)
        wi2_data = self._createWorkItemAndReturnDataDict(spec)

        # Create a duplicate and a near duplicate, insert into DB.
        new_wi1_data = wi2_data.copy()
        new_wi2_data = new_wi1_data.copy()
        new_wi2_data['status'] = SpecificationWorkItemStatus.DONE
        work_items = [new_wi1_data, wi1_data, new_wi2_data, wi2_data]
        spec.updateWorkItems(work_items)

        # Update our data dicts with the sequences to match data in DB
        new_wi1_data['sequence'] = 0
        wi1_data['sequence'] = 1
        new_wi2_data['sequence'] = 2
        wi2_data['sequence'] = 3

        self.assertEqual(4, spec.work_items.count())
        for data, obj in zip(work_items, list(spec.work_items)):
            self.assertThat(obj, MatchesStructure.byEquality(**data))

        return spec, work_items

    def test_add_duplicate_work_item(self):
        spec, work_items = self._dup_work_items_set_up()

        # Test that we can insert another duplicate work item.
        new_wi3_data = work_items[0].copy()
        new_wi3_data['sequence'] = 4
        work_items.append(new_wi3_data)
        spec.updateWorkItems(work_items)

        self.assertEqual(5, spec.work_items.count())
        for data, obj in zip(work_items, list(spec.work_items)):
            self.assertThat(obj, MatchesStructure.byEquality(**data))

    def test_delete_duplicate_work_item(self):
        spec, work_items = self._dup_work_items_set_up()

        # Delete a duplicate work item
        work_items.pop()
        spec.updateWorkItems(work_items)

        self.assertEqual(3, spec.work_items.count())
        for data, obj in zip(work_items, list(spec.work_items)):
            self.assertThat(obj, MatchesStructure.byEquality(**data))

    def test_updateWorkItems_updates_existing_ones(self):
        spec = self.factory.makeSpecification()
        login_person(spec.owner)
        # Create a work-item in our database.
        wi_data = self._createWorkItemAndReturnDataDict(spec)
        self.assertEqual(1, spec.work_items.count())

        # This time we're only changing the existing work item; we'll change
        # its assignee and status.
        wi_data.update(dict(status=SpecificationWorkItemStatus.DONE,
                            assignee=spec.owner))
        spec.updateWorkItems([wi_data])

        self.assertEqual(1, spec.work_items.count())
        self.assertThat(
            spec.work_items[0], MatchesStructure.byEquality(**wi_data))

    def test_updateWorkItems_deletes_all_if_given_empty_list(self):
        work_item = self.factory.makeSpecificationWorkItem()
        spec = work_item.specification
        self.assertEqual(1, spec.work_items.count())
        spec.updateWorkItems([])
        self.assertEqual(0, spec.work_items.count())

    def test_updateWorkItems_marks_removed_ones_as_deleted(self):
        spec = self.factory.makeSpecification()
        self._createWorkItemAndReturnDataDict(spec)
        wi2_data = self._createWorkItemAndReturnDataDict(spec)
        self.assertEqual(2, spec.work_items.count())
        login_person(spec.owner)

        # We have two work items in the DB but now we want to update them to
        # keep just the second one. The first will be deleted and the sequence
        # of the second will be changed.
        spec.updateWorkItems([wi2_data])
        self.assertEqual(1, spec.work_items.count())
        wi2_data['sequence'] = 0
        self.assertThat(
            spec.work_items[0], MatchesStructure.byEquality(**wi2_data))

    def _createWorkItemAndReturnDataDict(self, spec):
        """Create a new work item for the given spec using the next available
        sequence number.

        Return a dict with the title, status, assignee, milestone and sequence
        attributes of the spec.
        """
        if spec.work_items.count() == 0:
            sequence = 0
        else:
            sequence = max(wi.sequence for wi in spec.work_items) + 1
        wi = self.factory.makeSpecificationWorkItem(
            specification=spec, sequence=sequence)
        return dict(
            title=wi.title, status=wi.status, assignee=wi.assignee,
            milestone=wi.milestone, sequence=sequence)


class TestSpecificationInformationType(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_transitionToInformationType(self):
        """Ensure transitionToInformationType works."""
        spec = self.factory.makeSpecification()
        self.assertEqual(InformationType.PUBLIC, spec.information_type)
        with person_logged_in(spec.owner):
            result = spec.transitionToInformationType(
                InformationType.EMBARGOED, spec.owner)
            self.assertEqual(InformationType.EMBARGOED, spec.information_type)
        self.assertTrue(result)

    def test_transitionToInformationType_no_change(self):
        """Return False on no change."""
        spec = self.factory.makeSpecification()
        with person_logged_in(spec.owner):
            result = spec.transitionToInformationType(InformationType.PUBLIC,
                                                      spec.owner)
        self.assertFalse(result)

    def test_transitionToInformationType_forbidden(self):
        """Raise if specified type is not supported."""
        spec = self.factory.makeSpecification()
        with person_logged_in(spec.owner):
            with ExpectedException(CannotChangeInformationType, '.*'):
                spec.transitionToInformationType(None, spec.owner)
