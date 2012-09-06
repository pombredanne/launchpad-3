# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Specification."""

__metaclass__ = type


from zope.component import (
    getUtility,
    queryAdapter,
    )
from zope.security.checker import (
    CheckerPublic,
    getChecker,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.interfaces.security import IAuthorization
from lp.blueprints.enums import (
    NewSpecificationDefinitionStatus,
    SpecificationDefinitionStatus,
    SpecificationGoalStatus,
    )
from lp.blueprints.errors import TargetAlreadyHasSpecification
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.registry.enums import (
    PRIVATE_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.security import (
    AdminSpecification,
    EditSpecificationByRelatedPeople,
    EditWhiteboardSpecification,
    ViewSpecification,
    )
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.interaction import ANONYMOUS
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class SpecificationTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_target_driver_has_edit_rights(self):
        """Drivers of a blueprint's target can edit that blueprint."""
        product = self.factory.makeProduct()
        driver = self.factory.makePerson()
        removeSecurityProxy(product).driver = driver
        specification = self.factory.makeSpecification(product=product)
        login_person(driver)
        self.assertTrue(check_permission('launchpad.Edit', specification))

    def test_auto_accept_of_goal_for_drivers(self):
        """Drivers of a series accept the goal when they propose."""
        product = self.factory.makeProduct()
        proposer = self.factory.makePerson()
        productseries = self.factory.makeProductSeries(product=product)
        removeSecurityProxy(productseries).driver = proposer
        specification = self.factory.makeSpecification(product=product)
        specification.proposeGoal(productseries, proposer)
        self.assertEqual(
            SpecificationGoalStatus.ACCEPTED, specification.goalstatus)

    def test_goal_not_accepted_for_non_drivers(self):
        """People who aren't drivers don't have their proposals approved."""
        product = self.factory.makeProduct()
        proposer = self.factory.makePerson()
        productseries = self.factory.makeProductSeries(product=product)
        specification = self.factory.makeSpecification(product=product)
        specification.proposeGoal(productseries, proposer)
        self.assertEqual(
            SpecificationGoalStatus.PROPOSED, specification.goalstatus)

    def test_retarget_existing_specification(self):
        """An error is raised if the name is already taken."""
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        specification1 = self.factory.makeSpecification(
            product=product1, name="foo")
        self.factory.makeSpecification(product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification,
            removeSecurityProxy(specification1).retarget, product2)

    def test_retarget_is_protected(self):
        specification = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        self.assertRaises(
            Unauthorized, getattr, specification, 'retarget')

    def test_validate_move_existing_specification(self):
        """An error is raised by validateMove if the name is already taken."""
        product1 = self.factory.makeProduct()
        product2 = self.factory.makeProduct()
        specification1 = self.factory.makeSpecification(
            product=product1, name="foo")
        self.factory.makeSpecification(
            product=product2, name="foo")
        self.assertRaises(
            TargetAlreadyHasSpecification, specification1.validateMove,
            product2)

    def test_setTarget(self):
        product = self.factory.makeProduct()
        specification = self.factory.makeSpecification(product=product)
        self.assertEqual(product, specification.target)
        self.assertIs(None, specification.distribution)

        distribution = self.factory.makeDistribution()
        removeSecurityProxy(specification).setTarget(distribution)

        self.assertEqual(distribution, specification.target)
        self.assertEqual(distribution, specification.distribution)
        self.assertIs(None, specification.product)

    def test_setTarget_is_protected(self):
        specification = self.factory.makeSpecification(
            product=self.factory.makeProduct())
        self.assertRaises(
            Unauthorized, getattr, specification, 'setTarget')

    def check_permissions(self, expected_permissions, used_permissions,
                             type_):
        expected = set(expected_permissions.keys())
        self.assertEqual(
            expected, set(used_permissions.values()),
            'Unexpected %s permissions' % type_)
        for permission in expected_permissions:
            attribute_names = set(
                name for name, value in used_permissions.items()
                if value == permission)
            self.assertEqual(
                expected_permissions[permission], attribute_names,
                'Unexpected set of attributes with %s permission %s:\n'
                'Defined but not expected: %s\n'
                'Expected but not defined: %s'
                % (
                    type_, permission,
                    attribute_names - expected_permissions[permission],
                    expected_permissions[permission] - attribute_names))

    def test_get_permissions(self):
        expected_get_permissions = {
            CheckerPublic: set((
                'id', 'information_type', 'private', 'userCanView')),
            'launchpad.LimitedView': set((
                'acceptBy', 'all_blocked', 'all_deps', 'approver',
                'approverID', 'assignee', 'assigneeID', 'blocked_specs',
                'bug_links', 'bugs', 'completer', 'createDependency',
                'date_completed', 'date_goal_decided', 'date_goal_proposed',
                'date_started', 'datecreated', 'declineBy',
                'definition_status', 'dependencies', 'direction_approved',
                'distribution', 'distroseries', 'drafter', 'drafterID',
                'getBranchLink', 'getDelta', 'getAllowedInformationTypes',
                'getLinkedBugTasks', 'getSprintSpecification',
                'getSubscriptionByName', 'goal', 'goal_decider',
                'goal_proposer', 'goalstatus', 'has_accepted_goal',
                'implementation_status', 'informational', 'isSubscribed',
                'is_blocked', 'is_complete', 'is_incomplete', 'is_started',
                'lifecycle_status', 'linkBranch', 'linkSprint',
                'linked_branches', 'man_days', 'milestone', 'name',
                'notificationRecipientAddresses', 'owner', 'priority',
                'product', 'productseries', 'proposeGoal', 'removeDependency',
                'specurl', 'sprint_links', 'sprints', 'starter', 'subscribe',
                'subscribers', 'subscription', 'subscriptions', 'summary',
                'superseded_by', 'target', 'title', 'unlinkBranch',
                'unlinkSprint', 'unsubscribe', 'updateLifecycleStatus',
                'validateMove', 'whiteboard', 'work_items',
                'workitems_text')),
            'launchpad.Edit': set((
                'newWorkItem', 'retarget', 'setDefinitionStatus',
                'setImplementationStatus', 'setTarget',
                'transitionToInformationType', 'updateWorkItems')),
            'launchpad.AnyAllowedPerson': set((
                'unlinkBug', 'linkBug', 'setWorkItems')),
            }
        specification = self.factory.makeSpecification()
        checker = getChecker(specification)
        self.check_permissions(
            expected_get_permissions, checker.get_permissions, 'get')

    def test_set_permissions(self):
        expected_get_permissions = {
            'launchpad.Admin': set(('direction_approved', 'priority')),
            'launchpad.AnyAllowedPerson': set(('whiteboard', )),
            'launchpad.Edit': set((
                'approver', 'assignee', 'definition_status', 'distribution',
                'drafter', 'implementation_status', 'information_type',
                'man_days', 'milestone', 'name', 'product', 'specurl',
                'summary', 'superseded_by', 'title')),
            }
        specification = self.factory.makeSpecification()
        checker = getChecker(specification)
        self.check_permissions(
            expected_get_permissions, checker.set_permissions, 'set')

    def test_security_adapters(self):
        expected_adapters = {
            CheckerPublic: None,
            'launchpad.Admin': AdminSpecification,
            'launchpad.AnyAllowedPerson': EditWhiteboardSpecification,
            'launchpad.Edit': EditSpecificationByRelatedPeople,
            'launchpad.LimitedView': ViewSpecification,
            }
        specification = self.factory.makeSpecification()
        for permission in expected_adapters:
            adapter = queryAdapter(specification, IAuthorization, permission)
            expected_class = expected_adapters[permission]
            if expected_class is None:
                self.assertIsNone(
                    adapter, 'No security adapter for %s' % permission)
            else:
                self.assertTrue(
                    isinstance(adapter, expected_class),
                    'Invalid adapter for %s: %s' % (permission, adapter))

    def read_access_to_ISpecificationView(self, user, specification,
                                          error_expected):
        # Access an attribute whose interface is defined in
        # ISPecificationView.
        with person_logged_in(user):
            if error_expected:
                self.assertRaises(
                    Unauthorized, getattr, specification, 'name')
            else:
                # Just try to access an attribute. No execption should be
                # raised.
                specification.name

    def write_access_to_ISpecificationView(self, user, specification,
                                           error_expected, attribute, value):
        # Access an attribute whose interface is defined in
        # ISPecificationView.
        with person_logged_in(user):
            if error_expected:
                self.assertRaises(
                    Unauthorized, setattr, specification, attribute, value)
            else:
                # Just try to change an attribute. No execption should be
                # raised.
                setattr(specification, attribute, value)

    def test_anon_read_access(self):
        # Anonymous users have access to public specifications...
        specification = self.factory.makeSpecification()
        for information_type in PUBLIC_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.read_access_to_ISpecificationView(
                ANONYMOUS, specification, error_expected=False)
        # ...but not to private specifications.
        for information_type in PRIVATE_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.read_access_to_ISpecificationView(
                ANONYMOUS, specification, error_expected=True)

    def test_anon_write_access(self):
        # Anonymous users do not have write access to specifications.
        specification = self.factory.makeSpecification()
        for information_type in (PUBLIC_INFORMATION_TYPES +
                                 PRIVATE_INFORMATION_TYPES):
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.write_access_to_ISpecificationView(
                ANONYMOUS, specification, error_expected=True,
                attribute='whiteboard', value='foo')
            self.write_access_to_ISpecificationView(
                ANONYMOUS, specification, error_expected=True,
                attribute='name', value='foo')

    def test_ordinary_user_read_access(self):
        # Oridnary users have access to public specifications...
        specification = self.factory.makeSpecification()
        user = self.factory.makePerson()
        for information_type in PUBLIC_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.read_access_to_ISpecificationView(
                user, specification, error_expected=False)
        # ...but not to private specifications.
        for information_type in PRIVATE_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.read_access_to_ISpecificationView(
                user, specification, error_expected=True)

    def test_ordinary_user_write_access(self):
        # Oridnary users can change the whiteborad of public specifications.
        # They cannot change other attributes.
        specification = self.factory.makeSpecification()
        user = self.factory.makePerson()
        for information_type in PUBLIC_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.write_access_to_ISpecificationView(
                user, specification, error_expected=False,
                attribute='whiteboard', value='foo')
            self.write_access_to_ISpecificationView(
                user, specification, error_expected=True,
                attribute='name', value='foo')
        # The cannot change any attribute of private specifcations.
        for information_type in PRIVATE_INFORMATION_TYPES:
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.write_access_to_ISpecificationView(
                user, specification, error_expected=True,
                attribute='whiteboard', value='foo')
            self.write_access_to_ISpecificationView(
                user, specification, error_expected=True,
                attribute='name', value='foo')

    def test_special_user_read_access(self):
        # Users with special privileges can aceess the attributes
        # of public and private specifcations.
        specification = self.factory.makeSpecification()
        for information_type in (PUBLIC_INFORMATION_TYPES +
                                 PRIVATE_INFORMATION_TYPES):
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.read_access_to_ISpecificationView(
                specification.owner, specification, error_expected=False)

    def test_special_user_write_access(self):
        # Users with special privileges can change the attributes
        # of public and private specifcations.
        specification = self.factory.makeSpecification()
        for information_type in (PUBLIC_INFORMATION_TYPES +
                                 PRIVATE_INFORMATION_TYPES):
            with person_logged_in(specification.owner):
                specification.information_type = information_type
            self.write_access_to_ISpecificationView(
                specification.owner, specification, error_expected=False,
                attribute='whiteboard', value='foo')
            self.write_access_to_ISpecificationView(
                specification.owner, specification, error_expected=False,
                attribute='name', value='foo')


class TestSpecificationSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSpecificationSet, self).setUp()
        self.specification_set = getUtility(ISpecificationSet)
        self.new_names = NewSpecificationDefinitionStatus.items.mapping.keys()

    def test_new_with_open_definition_status_creates_specification(self):
        # Calling new() with an open definition status will create
        # a specification.
        self.assertTrue(
            SpecificationDefinitionStatus.NEW.name in self.new_names)
        product = self.factory.makeProduct()
        spec = self.specification_set.new(
            name='plane', title='Place', specurl='http://eg.org/plane',
            summary='summary', owner=product.owner, product=product,
            definition_status=SpecificationDefinitionStatus.NEW)
        self.assertEqual(
            SpecificationDefinitionStatus.NEW, spec.definition_status)

    def test_new_with_closed_definition_status_raises_error(self):
        # Calling new() with a obsolete or superseded definition status
        # raises an error.
        self.assertTrue(
            SpecificationDefinitionStatus.OBSOLETE.name not in self.new_names)
        product = self.factory.makeProduct()
        args = dict(
            name='plane', title='Place', specurl='http://eg.org/plane',
            summary='summary', owner=product.owner, product=product,
            definition_status=SpecificationDefinitionStatus.OBSOLETE)
        self.assertRaises(
            AssertionError, self.specification_set.new, **args)
