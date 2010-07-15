# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer
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

    def initialize_admin_view(self, private=True):
        """Initialize the admin view to set the privacy.."""
        method = 'POST'
        form = {
            'field.enabled': 'on',
            'field.actions.save': 'Save',
            }
        if private is True:
            form['field.private'] = 'on'
            form['field.buildd_secret'] = 'test'
        else:
            form['field.private'] = 'off'
            form['field.buildd_secret'] = ''

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
        view = self.initialize_admin_view(private=True)
        self.assertEqual(0, len(view.errors))
        self.assertTrue(view.context.private)

    def test_set_public_without_packages(self):
        # If a ppa does not have packages published, it is possible to
        # update the private attribute.
        self.make_ppa_private(self.ppa)
        self.assertTrue(self.ppa.private)

        view = self.initialize_admin_view(private=False)
        self.assertEqual(0, len(view.errors))
        self.assertFalse(view.context.private)

    def test_set_private_with_packages(self):
        # A PPA that does have packages cannot be privatised.
        self.publish_to_ppa(self.ppa)
        view = self.initialize_admin_view(private=True)
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

        view = self.initialize_admin_view(private=False)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'This archive already has published sources. '
            'It is not possible to switch the privacy.',
            view.errors[0])
