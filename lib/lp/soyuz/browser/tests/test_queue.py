# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for QueueItemsView."""

__metaclass__ = type

import transaction
from zope.component import (
    getUtility,
    queryMultiAdapter,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.archiveuploader.tests import datadir
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import PackageUploadStatus
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestAcceptQueueUploads(TestCaseWithFactory):
    """Uploads for the partner archive can be accepted with the relevant
    permissions.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create two new uploads in the new state and a person with
        permission to upload to the partner archive."""
        super(TestAcceptQueueUploads, self).setUp()
        login('admin@canonical.com')
        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.prepareBreezyAutotest()
        distribution = self.test_publisher.distroseries.distribution
        self.main_archive = distribution.getArchiveByComponent('main')
        self.partner_archive = distribution.getArchiveByComponent('partner')

        # Get some sample changes file content for the new uploads.
        changes_file = open(
            datadir('suite/bar_1.0-1/bar_1.0-1_source.changes'))
        changes_file_content = changes_file.read()
        changes_file.close()

        self.partner_spr = self.test_publisher.getPubSource(
            sourcename='partner-upload', spr_only=True,
            component='partner', changes_file_content=changes_file_content,
            archive=self.partner_archive)
        self.partner_spr.package_upload.setNew()
        self.main_spr = self.test_publisher.getPubSource(
            sourcename='main-upload', spr_only=True,
            component='main', changes_file_content=changes_file_content)
        self.main_spr.package_upload.setNew()

        # Define the form that will be used to post to the view.
        self.form = {
            'queue_state': PackageUploadStatus.NEW.value,
            'Accept': 'Accept',
            }

        # Create a user with queue admin rights for main, and a separate
        # user with queue admin rights for partner (on the partner
        # archive).
        self.main_queue_admin = self.factory.makePerson(
            email='main-queue@example.org')
        getUtility(IArchivePermissionSet).newQueueAdmin(
            distribution.getArchiveByComponent('main'),
            self.main_queue_admin, self.main_spr.component)
        self.partner_queue_admin = self.factory.makePerson(
            email='partner-queue@example.org')
        getUtility(IArchivePermissionSet).newQueueAdmin(
            distribution.getArchiveByComponent('partner'),
            self.partner_queue_admin, self.partner_spr.component)

        # We need to commit to ensure the changes file exists in the
        # librarian.
        transaction.commit()
        logout()

    def setupQueueView(self, request):
        """A helper to create and setup the view for testing."""
        view = queryMultiAdapter(
            (self.test_publisher.distroseries, request), name="+queue")
        view.setupQueueList()
        view.performQueueAction()
        return view

    def test_main_admin_can_accept_main_upload(self):
        # A person with queue admin access for main
        # can accept uploads to the main archive.
        login('main-queue@example.org')
        self.assertTrue(
            self.main_archive.canAdministerQueue(
                self.main_queue_admin, self.main_spr.component))

        package_upload_id = self.main_spr.package_upload.id
        self.form['QUEUE_ID'] = [package_upload_id]
        request = LaunchpadTestRequest(form=self.form)
        request.method = 'POST'
        self.setupQueueView(request)

        self.assertEquals(
            'DONE',
            getUtility(IPackageUploadSet).get(package_upload_id).status.name)

    def test_main_admin_cannot_accept_partner_upload(self):
        # A person with queue admin access for main cannot necessarily
        # accept uploads to partner.
        login('main-queue@example.org')
        self.assertFalse(
            self.partner_archive.canAdministerQueue(
                self.main_queue_admin, self.partner_spr.component))

        package_upload_id = self.partner_spr.package_upload.id
        self.form['QUEUE_ID'] = [package_upload_id]
        request = LaunchpadTestRequest(form=self.form)
        request.method = 'POST'
        view = self.setupQueueView(request)

        self.assertEquals(
            "FAILED: partner-upload (You have no rights to accept "
            "component(s) 'partner')",
            view.request.response.notifications[0].message)
        self.assertEquals(
            'NEW',
            getUtility(IPackageUploadSet).get(package_upload_id).status.name)

    def test_admin_can_accept_partner_upload(self):
        # An admin can always accept packages, even for the
        # partner archive (note, this is *not* an archive admin).
        login('admin@canonical.com')

        package_upload_id = self.partner_spr.package_upload.id
        self.form['QUEUE_ID'] = [package_upload_id]
        request = LaunchpadTestRequest(form=self.form)
        request.method = 'POST'
        self.setupQueueView(request)

        self.assertEquals(
            'DONE',
            getUtility(IPackageUploadSet).get(package_upload_id).status.name)

    def test_partner_admin_can_accept_partner_upload(self):
        # A person with queue admin access for partner
        # can accept uploads to the partner archive.
        login('partner-queue@example.org')
        self.assertTrue(
            self.partner_archive.canAdministerQueue(
                self.partner_queue_admin, self.partner_spr.component))

        package_upload_id = self.partner_spr.package_upload.id
        self.form['QUEUE_ID'] = [package_upload_id]
        request = LaunchpadTestRequest(form=self.form)
        request.method = 'POST'
        self.setupQueueView(request)

        self.assertEquals(
            'DONE',
            getUtility(IPackageUploadSet).get(package_upload_id).status.name)

    def test_partner_admin_cannot_accept_main_upload(self):
        # A person with queue admin access for partner cannot necessarily
        # accept uploads to main.
        login('partner-queue@example.org')
        self.assertFalse(
            self.main_archive.canAdministerQueue(
                self.partner_queue_admin, self.main_spr.component))

        package_upload_id = self.main_spr.package_upload.id
        self.form['QUEUE_ID'] = [package_upload_id]
        request = LaunchpadTestRequest(form=self.form)
        request.method = 'POST'
        view = self.setupQueueView(request)

        self.assertEquals(
            "FAILED: main-upload (You have no rights to accept "
            "component(s) 'main')",
            view.request.response.notifications[0].message)
        self.assertEquals(
            'NEW',
            getUtility(IPackageUploadSet).get(package_upload_id).status.name)


class TestQueueItemsView(TestCaseWithFactory):
    """Unit tests for `QueueItemsView`."""

    layer = LaunchpadFunctionalLayer

    def makeView(self, distroseries, user, form):
        return create_initialized_view(
            distroseries, name='+queue', principal=user)

    def makeCopyJobUpload(self, distroseries, component):
        job = self.factory.makePlainPackageCopyJob(
            target_distroseries=distroseries)
        job.addSourceOverride(SourceOverride(
            self.factory.makeSourcePackageName().name,
            component=component, section=self.factory.makeSection()))
        naked_job = removeSecurityProxy(job).context
        return self.factory.makePackageUpload(
            distroseries=distroseries, package_copy_job=naked_job)

    def test_copy_upload_does_not_break_rendering(self):
        # The presence of a PackageUpload with a PackageCopyJob does not
        # break rendering of the page.
        # XXX JeroenVermeulen 2011-06-13 bug=394645: the current reason
        # why this doesn't break is that the view uses getQueueItems,
        # which won't return PackageUploads with copy jobs.  This test
        # may start breaking once the view uses getPackageUploads.
        distroseries = self.factory.makeDistroSeries()
        component = self.factory.makeComponent()
        upload = self.makeCopyJobUpload(distroseries, component=component)
        queue_admin = self.factory.makeArchiveAdmin(distroseries.main_archive)
        form = {
            'queue_state': PackageUploadStatus.NEW.value,
            'Accept': 'Accept',
            'QUEUE_ID': [upload.id],
            }
        with person_logged_in(queue_admin):
            view = self.makeView(distroseries, queue_admin, form)
            view()
