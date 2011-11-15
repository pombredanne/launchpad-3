# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for security contact views."""

__metaclass__ = type

from zope.app.form.interfaces import ConversionError

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestSecurityContactEditView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSecurityContactEditView, self).setUp()
        self.owner = self.factory.makePerson(
            name='splat', displayname='<splat />')
        self.product = self.factory.makeProduct(
            name="boing", displayname='<boing />', owner=self.owner)
        self.team = self.factory.makeTeam(
            name='thud', owner=self.owner,
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        login_person(self.owner)

    def _makeForm(self, person):
        if person is None:
            name = ''
        else:
            name = person.name
        return {
            'field.security_contact': name,
            'field.actions.change': 'Change',
            }

    def test_view_attributes(self):
        self.product.displayname = 'Boing'
        view = create_initialized_view(
            self.product, name='+securitycontact')
        label = 'Edit Boing security contact'
        self.assertEqual(label, view.label)
        self.assertEqual(label, view.page_title)
        fields = ['security_contact']
        self.assertEqual(fields, view.field_names)
        self.assertEqual('http://launchpad.dev/boing', view.next_url)
        self.assertEqual('http://launchpad.dev/boing', view.cancel_url)

    def test_owner_appoint_self_from_none(self):
        # This also verifies that displaynames are escaped.
        form = self._makeForm(self.owner)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.security_contact, self.owner)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = (
            'Successfully changed the security contact to &lt;splat /&gt;.')
        self.assertEqual(expected, notifications.pop().message)

    def test_owner_appoint_self_from_another(self):
        self.product.security_contact = self.team
        form = self._makeForm(self.owner)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.owner, self.product.security_contact)

    def test_owner_appoint_none(self):
        self.product.security_contact = self.owner
        form = self._makeForm(None)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.security_contact, None)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = ('Successfully removed the security contact.')
        self.assertEqual(expected, notifications.pop().message)

    def test_owner_appoint_his_team(self):
        form = self._makeForm(self.team)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(self.product.security_contact, self.team)
        notifications = view.request.response.notifications
        self.assertEqual(1, len(notifications))
        expected = ('Successfully changed the security contact to Thud.')
        self.assertEqual(expected, notifications.pop().message)

    def test_owner_cannot_appoint_another_team(self):
        team = self.factory.makeTeam(
            name='smack', displayname='<smack />',
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        form = self._makeForm(team)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual(1, len(view.errors))
        expected = (
            'You cannot set &lt;smack /&gt; as the security contact for '
            '&lt;boing /&gt; because you are not an administrator of that '
            'team.<br />If you believe that &lt;smack /&gt; should be the '
            'security contact for &lt;boing /&gt;, notify one of the '
            '<a href="http://launchpad.dev/~smack/+members">&lt;smack /&gt; '
            'administrators</a>.')
        self.assertEqual(expected, view.errors.pop())

    def test_owner_cannot_appoint_a_nonvalid_user(self):
        form = self._makeForm(None)
        form['field.security_contact'] = 'fnord'
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual(2, len(view.errors))
        expected = (
            'You must choose a valid person or team to be the '
            'security contact for &lt;boing /&gt;.')
        self.assertEqual(expected, view.errors.pop())
        self.assertTrue(isinstance(view.errors.pop(), ConversionError))

    def test_owner_cannot_appoint_another_user(self):
        another_user = self.factory.makePerson()
        form = self._makeForm(another_user)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual(1, len(view.errors))
        expected = (
            'You cannot set another person as the security contact for '
            '&lt;boing /&gt;.')
        self.assertEqual(expected, view.errors.pop())

    def test_admin_appoint_another_user(self):
        another_user = self.factory.makePerson()
        login('admin@canonical.com')
        form = self._makeForm(another_user)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(another_user, self.product.security_contact)

    def test_admin_appoint_another_team(self):
        another_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        login('admin@canonical.com')
        form = self._makeForm(another_team)
        view = create_initialized_view(
            self.product, name='+securitycontact', form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(another_team, self.product.security_contact)
