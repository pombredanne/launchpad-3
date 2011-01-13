# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug subscription filter browser code."""

__metaclass__ = type

from functools import partial
from urlparse import urlparse

from lazr.restfulclient.errors import BadRequest
from lxml import html
from storm.exceptions import LostObjectError
from testtools.matchers import StartsWith
import transaction

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.publisher import BugsLayer
from lp.registry.browser.structuralsubscription import (
    StructuralSubscriptionNavigation,
    )
from lp.testing import (
    login_person,
    normalize_whitespace,
    person_logged_in,
    TestCaseWithFactory,
    ws_object,
    )
from lp.testing.views import create_initialized_view


class TestBugSubscriptionFilterBase:

    def setUp(self):
        super(TestBugSubscriptionFilterBase, self).setUp()
        self.owner = self.factory.makePerson(name=u"foo")
        self.structure = self.factory.makeProduct(
            owner=self.owner, name=u"bar")
        with person_logged_in(self.owner):
            self.subscription = self.structure.addBugSubscription(
                self.owner, self.owner)
            self.subscription_filter = self.subscription.newBugFilter()


class TestBugSubscriptionFilterNavigation(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_canonical_url(self):
        url = urlparse(canonical_url(self.subscription_filter))
        self.assertThat(url.hostname, StartsWith("bugs."))
        self.assertEqual(
            "/bar/+subscription/foo/+filter/%d" % (
                self.subscription_filter.id),
            url.path)

    def test_navigation(self):
        request = LaunchpadTestRequest()
        request.setTraversalStack([unicode(self.subscription_filter.id)])
        navigation = StructuralSubscriptionNavigation(
            self.subscription, request)
        view = navigation.publishTraverse(request, '+filter')
        self.assertIsNot(None, view)


class TestBugSubscriptionFilterAPI(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = AppServerLayer

    def test_visible_attributes(self):
        # Bug subscription filters are not private objects. All attributes are
        # visible to everyone.
        transaction.commit()
        # Create a service for a new person.
        service = self.factory.makeLaunchpadService()
        get_ws_object = partial(ws_object, service)
        ws_subscription = get_ws_object(self.subscription)
        ws_subscription_filter = get_ws_object(self.subscription_filter)
        self.assertEqual(
            ws_subscription.self_link,
            ws_subscription_filter.structural_subscription_link)
        self.assertEqual(
            self.subscription_filter.find_all_tags,
            ws_subscription_filter.find_all_tags)
        self.assertEqual(
            self.subscription_filter.description,
            ws_subscription_filter.description)
        self.assertEqual(
            list(self.subscription_filter.statuses),
            ws_subscription_filter.statuses)
        self.assertEqual(
            list(self.subscription_filter.importances),
            ws_subscription_filter.importances)
        self.assertEqual(
            list(self.subscription_filter.tags),
            ws_subscription_filter.tags)

    def test_structural_subscription_cannot_be_modified(self):
        # Bug filters cannot be moved from one structural subscription to
        # another. In other words, the structural_subscription field is
        # read-only.
        user = self.factory.makePerson(name=u"baz")
        with person_logged_in(self.owner):
            user_subscription = self.structure.addBugSubscription(user, user)
        transaction.commit()
        # Create a service for the structure owner.
        service = self.factory.makeLaunchpadService(self.owner)
        get_ws_object = partial(ws_object, service)
        ws_user_subscription = get_ws_object(user_subscription)
        ws_subscription_filter = get_ws_object(self.subscription_filter)
        ws_subscription_filter.structural_subscription = ws_user_subscription
        error = self.assertRaises(BadRequest, ws_subscription_filter.lp_save)
        self.assertEqual(400, error.response.status)
        self.assertEqual(
            self.subscription,
            self.subscription_filter.structural_subscription)


class TestBugSubscriptionFilterAPIModifications(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestBugSubscriptionFilterAPIModifications, self).setUp()
        transaction.commit()
        self.service = self.factory.makeLaunchpadService(self.owner)
        self.ws_subscription_filter = ws_object(
            self.service, self.subscription_filter)

    def test_modify_tags_fields(self):
        # Two tags-related fields - find_all_tags and tags - can be
        # modified. The other two tags-related fields - include_any_tags and
        # exclude_any_tags - are not exported because the tags field provides
        # a more intuitive way to update them (from the perspective of an API
        # consumer).
        self.assertFalse(self.subscription_filter.find_all_tags)
        self.assertFalse(self.subscription_filter.include_any_tags)
        self.assertFalse(self.subscription_filter.exclude_any_tags)
        self.assertEqual(set(), self.subscription_filter.tags)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.find_all_tags = True
        self.ws_subscription_filter.tags = ["foo", "-bar", "*", "-*"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertTrue(self.subscription_filter.find_all_tags)
        self.assertTrue(self.subscription_filter.include_any_tags)
        self.assertTrue(self.subscription_filter.exclude_any_tags)
        self.assertEqual(
            set(["*", "-*", "foo", "-bar"]),
            self.subscription_filter.tags)

    def test_modify_description(self):
        # The description can be modified.
        self.assertEqual(
            None, self.subscription_filter.description)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.description = u"It's late."
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            u"It's late.", self.subscription_filter.description)

    def test_modify_statuses(self):
        # The statuses field can be modified.
        self.assertEqual(set(), self.subscription_filter.statuses)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.statuses = ["New", "Triaged"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            set([BugTaskStatus.NEW, BugTaskStatus.TRIAGED]),
            self.subscription_filter.statuses)

    def test_modify_importances(self):
        # The importances field can be modified.
        self.assertEqual(set(), self.subscription_filter.importances)

        # Modify, save, and start a new transaction.
        self.ws_subscription_filter.importances = ["Low", "High"]
        self.ws_subscription_filter.lp_save()
        transaction.begin()

        # Updated state.
        self.assertEqual(
            set([BugTaskImportance.LOW, BugTaskImportance.HIGH]),
            self.subscription_filter.importances)

    def test_delete(self):
        # Subscription filters can be deleted.
        self.ws_subscription_filter.lp_delete()
        transaction.begin()
        self.assertRaises(
            LostObjectError, getattr, self.subscription_filter,
            "find_all_tags")


class TestBugSubscriptionFilterView(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterView, self).setUp()
        self.view = create_initialized_view(
            self.subscription_filter, "+definition")

    def test_description(self):
        # If the description is not set then the empty string is returned.
        self.assertEqual(u"", self.view.description)
        # If the description is just whitespace then the empty string is
        # returned.
        with person_logged_in(self.owner):
            self.subscription_filter.description = u"  "
        self.assertEqual(u"", self.view.description)
        # If the description is set it is returned.
        with person_logged_in(self.owner):
            self.subscription_filter.description = u"Foo"
        self.assertEqual(u"Foo", self.view.description)
        # Leading and trailing whitespace is trimmed.
        with person_logged_in(self.owner):
            self.subscription_filter.description = u"  Foo\t  "
        self.assertEqual(u"Foo", self.view.description)

    def test_conditions_with_nothing_set(self):
        # If nothing is set the conditions list is empty.
        self.assertEqual([], self.view.conditions)

    def test_conditions_for_statuses(self):
        # If no statuses have been specified nothing is returned.
        self.assertEqual([], self.view.conditions)
        # If set, a description of the statuses is returned.
        with person_logged_in(self.owner):
            self.subscription_filter.statuses = [
                BugTaskStatus.NEW,
                BugTaskStatus.CONFIRMED,
                BugTaskStatus.TRIAGED,
                ]
        self.assertEqual(
            [u"the status is New, Confirmed, or Triaged"],
            self.view.conditions)

    def test_conditions_for_importances(self):
        # If no importances have been specified nothing is returned.
        self.assertEqual([], self.view.conditions)
        # If set, a description of the importances is returned.
        with person_logged_in(self.owner):
            self.subscription_filter.importances = [
                BugTaskImportance.LOW,
                BugTaskImportance.MEDIUM,
                BugTaskImportance.HIGH,
                ]
        self.assertEqual(
            [u"the importance is High, Medium, or Low"],
             self.view.conditions)

    def test_conditions_for_tags(self):
        # If no tags have been specified nothing is returned.
        self.assertEqual([], self.view.conditions)
        # If set, a description of the tags is returned.
        with person_logged_in(self.owner):
            self.subscription_filter.tags = [u"foo", u"bar", u"*"]
        self.assertEqual(
            [u"the bug is tagged with *, bar, or foo"],
            self.view.conditions)
        # If find_all_tags is set, the conjunction changes.
        with person_logged_in(self.owner):
            self.subscription_filter.find_all_tags = True
        self.assertEqual(
            [u"the bug is tagged with *, bar, and foo"],
            self.view.conditions)

    def assertRender(self, dt_content=None, dd_content=None):
        root = html.fromstring(self.view.render())
        if dt_content is not None:
            self.assertEqual(
                dt_content, normalize_whitespace(
                    root.find("dt").text_content()))
        if dd_content is not None:
            self.assertEqual(
                dd_content, normalize_whitespace(
                    root.find("dd").text_content()))

    def test_render_with_no_description_and_no_conditions(self):
        # If no description and no conditions are set, the rendered
        # description is very simple, and there's a short message describing
        # the absense of conditions.
        self.assertRender(
            u"This filter does not allow mail through.",
            u"There are no filter conditions! (edit)")

    def test_render_with_no_description_and_conditions(self):
        # If conditions are set but no description, the rendered description
        # is very simple, and the conditions are described.
        with person_logged_in(self.owner):
            self.subscription_filter.statuses = [
                BugTaskStatus.NEW,
                BugTaskStatus.CONFIRMED,
                BugTaskStatus.TRIAGED,
                ]
            self.subscription_filter.importances = [
                BugTaskImportance.LOW,
                BugTaskImportance.MEDIUM,
                BugTaskImportance.HIGH,
                ]
            self.subscription_filter.tags = [u"foo", u"bar"]
        self.assertRender(
            u"This filter allows mail through when:",
            u" and ".join(self.view.conditions) + u" (edit)")

    def test_render_with_description_and_no_conditions(self):
        # If a description is set it appears in the content of the dt tag,
        # surrounded by "curly" quotes.
        with person_logged_in(self.owner):
            self.subscription_filter.description = u"The Wait"
        self.assertRender(
            u"\u201cThe Wait\u201d does not allow mail through.",
            u"There are no filter conditions! (edit)")

    def test_render_with_description_and_conditions(self):
        # If a description is set it appears in the content of the dt tag,
        # surrounded by "curly" quotes.
        with person_logged_in(self.owner):
            self.subscription_filter.description = u"The Wait"
            self.subscription_filter.tags = [u"foo"]
        self.assertRender(
            u"\u201cThe Wait\u201d allows mail through when:",
            u" and ".join(self.view.conditions) + u" (edit)")


class TestBugSubscriptionFilterEditView(
    TestBugSubscriptionFilterBase, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_view_properties(self):
        # The cancel url and next url will both point to the user's structural
        # subscription overview page.
        login_person(self.owner)
        view = create_initialized_view(
            self.subscription_filter, name="+edit",
            layer=BugsLayer, principal=self.owner)
        self.assertEqual([], view.errors)
        path = "/~%s/+structural-subscriptions" % self.owner.name
        self.assertEqual(path, urlparse(view.cancel_url).path)
        self.assertEqual(path, urlparse(view.next_url).path)

    def test_edit(self):
        # The filter can be updated by using the update action.
        form = {
            "field.description": "New description",
            "field.statuses": ["NEW", "INCOMPLETE"],
            "field.importances": ["LOW", "MEDIUM"],
            "field.tags": u"foo bar",
            "field.find_all_tags": "on",
            "field.actions.update": "Update",
            }
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.subscription_filter, name="+edit",
                form=form, layer=BugsLayer, principal=self.owner)
            self.assertEqual([], view.errors)
        # The subscription filter has been updated.
        self.assertEqual(
            u"New description",
            self.subscription_filter.description)
        self.assertEqual(
            frozenset([BugTaskStatus.NEW, BugTaskStatus.INCOMPLETE]),
            self.subscription_filter.statuses)
        self.assertEqual(
            frozenset([BugTaskImportance.LOW, BugTaskImportance.MEDIUM]),
            self.subscription_filter.importances)
        self.assertEqual(
            frozenset([u"foo", u"bar"]),
            self.subscription_filter.tags)
        self.assertTrue(
            self.subscription_filter.find_all_tags)


class TestBugSubscriptionFilterCreateView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterCreateView, self).setUp()
        self.owner = self.factory.makePerson(name=u"foo")
        self.structure = self.factory.makeProduct(
            owner=self.owner, name=u"bar")
        with person_logged_in(self.owner):
            self.subscription = self.structure.addBugSubscription(
                self.owner, self.owner)

    def test_view_properties(self):
        # The cancel url and next url will both point to the user's structural
        # subscription overview page.
        login_person(self.owner)
        view = create_initialized_view(
            self.subscription, name="+new-filter",
            layer=BugsLayer, principal=self.owner)
        self.assertEqual([], view.errors)
        path = "/~%s/+structural-subscriptions" % self.owner.name
        self.assertEqual(path, urlparse(view.cancel_url).path)
        self.assertEqual(path, urlparse(view.next_url).path)

    def test_create(self):
        # New filters can be created with +new-filter.
        self.assertEqual([], list(self.subscription.bug_filters))
        form = {
            "field.description": "New description",
            "field.statuses": ["NEW", "INCOMPLETE"],
            "field.importances": ["LOW", "MEDIUM"],
            "field.tags": u"foo bar",
            "field.find_all_tags": "on",
            "field.actions.create": "Create",
            }
        with person_logged_in(self.owner):
            view = create_initialized_view(
                self.subscription, name="+new-filter",
                form=form, layer=BugsLayer, principal=self.owner)
            self.assertEqual([], view.errors)
        # The subscription filter has been created.
        subscription_filter = self.subscription.bug_filters.one()
        self.assertEqual(
            u"New description",
            subscription_filter.description)
        self.assertEqual(
            frozenset([BugTaskStatus.NEW, BugTaskStatus.INCOMPLETE]),
            subscription_filter.statuses)
        self.assertEqual(
            frozenset([BugTaskImportance.LOW, BugTaskImportance.MEDIUM]),
            subscription_filter.importances)
        self.assertEqual(
            frozenset([u"foo", u"bar"]),
            subscription_filter.tags)
        self.assertTrue(
            subscription_filter.find_all_tags)
