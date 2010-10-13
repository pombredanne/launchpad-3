# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Code of Conduct views."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.model.codeofconduct import SignedCodeOfConduct
from lp.testing import (
    login_celebrity,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class SignCodeOfConductTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(SignCodeOfConductTestCase, self).setUp()
        user = self.factory.makePerson()
        gpg_key = self.factory.makeGPGKey(user)
        self.signed_coc = self.sign_coc(user, gpg_key)
        self.admin = login_celebrity('admin')

    def sign_coc(self, user, gpg_key):
        """Return a SignedCodeOfConduct using dummy text."""
        signed_coc = SignedCodeOfConduct(
            owner=user, signingkey=gpg_key,
            signedcode="Dummy CoC signed text.", active=True)
        return signed_coc

    def verify_common_view_properties(self, view):
        self.assertEqual(['admincomment'], view.field_names)
        self.assertEqual(
            view.page_title, view.label)
        url = 'http://launchpad.dev/codeofconduct/console/%d' % (
            self.signed_coc.id)
        self.assertEqual(url, view.next_url)
        self.assertEqual(url, view.cancel_url)

    def verify_admincomment_required(self, action_name, view_name):
        # Empty comments are not permitted for any state change.
        form = {
            'field.admincomment': '',
            'field.actions.change': action_name,
            }
        view = create_initialized_view(
            self.signed_coc, name=view_name, form=form,
            principal=self.admin)
        self.assertEqual(1, len(view.errors))
        self.assertEqual('admincomment', view.errors[0].field_name)


class TestSignedCodeOfConductActiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = False
        view = create_initialized_view(self.signed_coc, name="+activate")
        self.assertEqual(
            'Activate code of conduct signature', view.label)
        self.assertTrue(view.state)
        self.verify_common_view_properties(view)

    def test_activate(self):
        self.signed_coc.active = False
        form = {
            'field.admincomment': 'The user is sorry.',
            'field.actions.change': 'Activate',
            }
        view = create_initialized_view(
            self.signed_coc, name="+activate", form=form,
            principal=self.admin)
        self.assertEqual([], view.errors)
        self.assertTrue(self.signed_coc.active)
        self.assertEqual(self.admin, self.signed_coc.recipient)
        self.assertEqual(
            'The user is sorry.', self.signed_coc.admincomment)

    def test_admincomment_required(self):
        self.verify_admincomment_required('Activate', '+activate')


class TestSignedCodeOfConductDeactiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = True
        view = create_initialized_view(self.signed_coc, name="+deactivate")
        self.assertEqual(
            'Deactivate code of conduct signature', view.label)
        self.assertFalse(view.state)
        self.verify_common_view_properties(view)

    def test_deactivate(self):
        self.signed_coc.active = True
        form = {
            'field.admincomment': 'The user is bad.',
            'field.actions.change': 'Deactivate',
            }
        view = create_initialized_view(
            self.signed_coc, name="+deactivate", form=form,
            principal=self.admin)
        self.assertEqual([], view.errors)
        self.assertFalse(self.signed_coc.active)
        self.assertEqual(
            'The user is bad.', self.signed_coc.admincomment)

    def test_admincomment_required(self):
        self.verify_admincomment_required('Deactivate', '+deactivate')
