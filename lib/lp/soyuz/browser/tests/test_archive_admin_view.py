# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.soyuz.browser.archive import ArchiveAdminView
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestArchivePrivacySwitchingView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create a ppa for the tests and login as an admin."""
        super(TestArchivePrivacySwitchingView, self).setUp()
        self.ppa = self.factory.makeArchive()
        # Login as an admin to ensure access to the view's context
        # object.
        login('admin@canonical.com')

    def initialize_admin_view(self, private=True, buildd_secret=''):
        """Initialize the admin view to set the privacy.."""
        method = 'POST'
        form = {
            'field.enabled': 'on',
            'field.actions.save': 'Save',
            }

        form['field.buildd_secret'] = buildd_secret
        if private is True:
            form['field.private'] = 'on'
        else:
            form['field.private'] = 'off'

        view = ArchiveAdminView(self.ppa, LaunchpadTestRequest(
            method=method, form=form))
        view.initialize()
        return view

    def make_ppa_private(self, ppa):
        """Helper method to privatise a ppa."""
        ppa.private = True
        ppa.buildd_secret = "secret"

    def publish_to_ppa(self, ppa):
        """Helper method to publish a package in a PPA."""
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        publisher.getPubSource(archive=ppa)

    def test_set_private_without_packages(self):
        # If a ppa does not have packages published, it is possible to
        # update the private attribute.
        view = self.initialize_admin_view(private=True, buildd_secret="test")
        self.assertEqual(0, len(view.errors))
        self.assertTrue(view.context.private)

    def test_set_public_without_packages(self):
        # If a ppa does not have packages published, it is possible to
        # update the private attribute.
        self.make_ppa_private(self.ppa)
        self.assertTrue(self.ppa.private)

        view = self.initialize_admin_view(private=False, buildd_secret='')
        self.assertEqual(0, len(view.errors))
        self.assertFalse(view.context.private)

    def test_set_private_without_buildd_secret(self):
        """If a PPA is marked private but no buildd secret is specified,
        one will be generated."""
        view = self.initialize_admin_view(private=True, buildd_secret='')
        self.assertEqual(0, len(view.errors))
        self.assertTrue(view.context.private)
        self.assertTrue(len(view.context.buildd_secret) > 4)

    def test_set_private_with_packages(self):
        # A PPA that does have packages cannot be privatised.
        self.publish_to_ppa(self.ppa)
        view = self.initialize_admin_view(private=True, buildd_secret="test")
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'This archive already has published sources. '
            'It is not possible to switch the privacy.',
            view.errors[0])

    def test_set_public_with_packages(self):
        # A PPA that does have (or had) packages published is presented
        # with a disabled 'private' field.
        self.make_ppa_private(self.ppa)
        self.assertTrue(self.ppa.private)
        self.publish_to_ppa(self.ppa)

        view = self.initialize_admin_view(private=False, buildd_secret='')
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'This archive already has published sources. '
            'It is not possible to switch the privacy.',
            view.errors[0])

    def test_can_leave_restricted_families_unchecked(self):
        # We should be able to leave restricted families unchecked and
        # still submit the form. (see bug 888083)
        self.factory.makeProcessorFamily(restricted=True)
        self.factory.makeProcessorFamily(restricted=True)
        form = {
            "field.enabled": "on",
            'field.private': 'off',
            "field.require_virtualized": "off",
            'field.enabled_restricted_families': [],
            'field.actions.save': 'Save',
            }

        view = ArchiveAdminView(
            self.ppa, LaunchpadTestRequest(method="POST", form=form))
        view.initialize()

        self.assertEqual(
           None, view.widget_errors.get('enabled_restricted_families'))

    def test_cannot_change_enabled_restricted_families(self):
        # If require_virtualized is False, enabled_restricted_families
        # cannot be changed.
        pf1 = self.factory.makeProcessorFamily(restricted=True)
        method = 'POST'
        form = {
            'field.enabled': 'on',
            'field.require_virtualized': '',
            'field.enabled_restricted_families': [pf1.name],
            'field.actions.save': 'Save',
            }

        view = ArchiveAdminView(self.ppa, LaunchpadTestRequest(
            method=method, form=form))
        view.initialize()

        error_msg = (
            u'Main archives can not be restricted to certain '
            'architectures unless they are set to build on '
            'virtualized builders.')
        self.assertEqual(
           error_msg,
           view.widget_errors.get('enabled_restricted_families'))
        self.assertEqual(
           error_msg,
           view.widget_errors.get('require_virtualized'))
