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
from lp.testing.views import create_view


class SignCodeOfConductTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(SignCodeOfConductTestCase, self).setUp()
        user = self.factory.makePerson()
        gpg_key = self.factory.makeGPGKey(user)
        self.signed_coc = self.signCoC(user, gpg_key)
        self.admin = login_celebrity('admin')

    def signCoC(self, user, gpg_key):
        """Return a SignedCodeOfConduct using dummy text."""
        signed_coc = SignedCodeOfConduct(
            owner=user, signingkey=gpg_key,
            signedcode="Dummy CoC signed text.", active=True)
        return signed_coc


class TestSignedCodeOfConductActiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = False
        view = create_view(self.signed_coc, name="+activate")
        self.assertEqual(['admincomment'], view.fieldNames)
        self.assertEqual(
            'Activate code of conduct signature', view.label)
        self.assertEqual(
            'http://launchpad.dev/'
            'codeofconduct/console/%d' % self.signed_coc.id,
            view.next_url)

    def test_activate(self):
        self.signed_coc.active = False
        form = {
            'field.admincomment': 'The user is sorry.',
            'UPDATE_SUBMIT': 'Change',
            }
        view = create_view(
            self.signed_coc, name="+activate", form=form,
            principal=self.admin)
        view.update()
        self.assertTrue(self.signed_coc.active)
        self.assertEqual(
            'The user is sorry.', self.signed_coc.admincomment)


class TestSignedCodeOfConductDeactiveView(SignCodeOfConductTestCase):

    def test_view_properties(self):
        self.signed_coc.active = True
        view = create_view(self.signed_coc, name="+deactivate")
        self.assertEqual(
            'Deactivate code of conduct signature', view.label)
        self.assertEqual(['admincomment'], view.fieldNames)
        self.assertEqual(
            'http://launchpad.dev/'
            'codeofconduct/console/%d' % self.signed_coc.id,
            view.next_url)

    def test_deactivate(self):
        self.signed_coc.active = True
        form = {
            'field.admincomment': 'The user is bad.',
            'UPDATE_SUBMIT': 'Change',
            }
        view = create_view(
            self.signed_coc, name="+deactivate", form=form,
            principal=self.admin)
        view.update()
        self.assertFalse(self.signed_coc.active)
        self.assertEqual(
            'The user is bad.', self.signed_coc.admincomment)
