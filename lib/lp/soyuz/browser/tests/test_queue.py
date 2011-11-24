# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for QueueItemsView."""

__metaclass__ = type

import cgi
from lxml import html
import transaction
from zope.component import (
    getUtility,
    queryMultiAdapter,
    )

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.archiveuploader.tests import datadir
from lp.soyuz.browser.queue import CompletePackageUpload
from lp.soyuz.enums import PackageUploadStatus
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    login,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL
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

    def makeView(self, distroseries, user):
        """Create a queue view."""
        return create_initialized_view(
            distroseries, name='+queue', principal=user)

    def test_view_renders_source_upload(self):
        login(ADMIN_EMAIL)
        upload = self.factory.makeSourcePackageUpload()
        queue_admin = self.factory.makeArchiveAdmin(
            upload.distroseries.main_archive)
        with person_logged_in(queue_admin):
            view = self.makeView(upload.distroseries, queue_admin)
            html_text = view()
        self.assertIn(upload.package_name, html_text)

    def test_view_renders_build_upload(self):
        login(ADMIN_EMAIL)
        upload = self.factory.makeBuildPackageUpload()
        queue_admin = self.factory.makeArchiveAdmin(
            upload.distroseries.main_archive)
        with person_logged_in(queue_admin):
            view = self.makeView(upload.distroseries, queue_admin)
            html_text = view()
        self.assertIn(upload.package_name, html_text)

    def test_view_renders_copy_upload(self):
        login(ADMIN_EMAIL)
        upload = self.factory.makeCopyJobPackageUpload()
        queue_admin = self.factory.makeArchiveAdmin(
            upload.distroseries.main_archive)
        with person_logged_in(queue_admin):
            view = self.makeView(upload.distroseries, queue_admin)
            html_text = view()
        self.assertIn(upload.package_name, html_text)
        # The details section states the sync's origin and requester.
        self.assertIn(
            upload.package_copy_job.source_archive.displayname, html_text)
        self.assertIn(
            upload.package_copy_job.job.requester.displayname, html_text)


class TestCompletePackageUpload(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def makeCompletePackageUpload(self, upload=None, build_upload_files=None,
                                  source_upload_files=None,
                                  package_sets=None):
        if upload is None:
            upload = self.factory.makeSourcePackageUpload()
        if build_upload_files is None:
            build_upload_files = {}
        if source_upload_files is None:
            source_upload_files = {}
        if package_sets is None:
            package_sets = {}
        return CompletePackageUpload(
            upload, build_upload_files, source_upload_files, package_sets)

    def mapPackageSets(self, upload, package_sets=None):
        if package_sets is None:
            package_sets = [self.factory.makePackageset(
                distroseries=upload.distroseries)]
        spn = upload.sourcepackagerelease.sourcepackagename
        return {spn.id: package_sets}

    def test_display_package_sets_returns_source_upload_packagesets(self):
        upload = self.factory.makeSourcePackageUpload()
        package_sets = self.mapPackageSets(upload)
        complete_upload = self.makeCompletePackageUpload(
            upload, package_sets=package_sets)
        self.assertEqual(
            package_sets.values()[0][0].name,
            complete_upload.display_package_sets)

    def test_display_package_sets_returns_empty_for_other_upload(self):
        upload = self.factory.makeBuildPackageUpload()
        complete_upload = self.makeCompletePackageUpload(
            upload, package_sets=self.mapPackageSets(upload))
        self.assertEqual("", complete_upload.display_package_sets)

    def test_display_package_sets_sorts_by_name(self):
        complete_upload = self.makeCompletePackageUpload()
        distroseries = complete_upload.distroseries
        complete_upload.package_sets = [
            self.factory.makePackageset(distroseries=distroseries, name=name)
            for name in [u'ccc', u'aaa', u'bbb']]
        self.assertEqual("aaa bbb ccc", complete_upload.display_package_sets)

    def test_display_component_returns_source_upload_component_name(self):
        upload = self.factory.makeSourcePackageUpload()
        complete_upload = self.makeCompletePackageUpload(upload)
        self.assertEqual(
            upload.sourcepackagerelease.component.name.lower(),
            complete_upload.display_component)

    def test_display_component_returns_copy_job_upload_component_name(self):
        copy_job_upload = self.factory.makeCopyJobPackageUpload()
        complete_upload = self.makeCompletePackageUpload(copy_job_upload)
        self.assertEqual(
            copy_job_upload.component_name.lower(),
            complete_upload.display_component)

    def test_display_component_returns_empty_for_other_upload(self):
        complete_upload = self.makeCompletePackageUpload(
            self.factory.makeBuildPackageUpload())
        self.assertEqual('', complete_upload.display_component)

    def test_display_section_returns_source_upload_section_name(self):
        upload = self.factory.makeSourcePackageUpload()
        complete_upload = self.makeCompletePackageUpload(upload)
        self.assertEqual(
            upload.sourcepackagerelease.section.name.lower(),
            complete_upload.display_section)

    def test_display_section_returns_copy_job_upload_section_name(self):
        copy_job_upload = self.factory.makeCopyJobPackageUpload()
        complete_upload = self.makeCompletePackageUpload(copy_job_upload)
        self.assertEqual(
            copy_job_upload.section_name.lower(),
            complete_upload.display_section)

    def test_display_section_returns_empty_for_other_upload(self):
        complete_upload = self.makeCompletePackageUpload(
            self.factory.makeBuildPackageUpload())
        self.assertEqual('', complete_upload.display_section)

    def test_display_priority_returns_source_upload_priority(self):
        upload = self.factory.makeSourcePackageUpload()
        complete_upload = self.makeCompletePackageUpload(upload)
        self.assertEqual(
            upload.sourcepackagerelease.urgency.name.lower(),
            complete_upload.display_priority)

    def test_display_priority_returns_empty_for_other_upload(self):
        complete_upload = self.makeCompletePackageUpload(
            self.factory.makeBuildPackageUpload())
        self.assertEqual('', complete_upload.display_priority)

    def test_composeIcon_produces_image_tag(self):
        alt = self.factory.getUniqueString()
        icon = self.factory.getUniqueString() + ".png"
        title = self.factory.getUniqueString()
        html_text = self.makeCompletePackageUpload().composeIcon(
            alt, icon, title)
        img = html.fromstring(html_text)
        self.assertEqual("img", img.tag)
        self.assertEqual("[%s]" % alt, img.get("alt"))
        self.assertEqual("/@@/" + icon, img.get("src"))
        self.assertEqual(title, img.get("title"))

    def test_composeIcon_title_defaults_to_alt_text(self):
        alt = self.factory.getUniqueString()
        icon = self.factory.getUniqueString() + ".png"
        html_text = self.makeCompletePackageUpload().composeIcon(alt, icon)
        img = html.fromstring(html_text)
        self.assertEqual(alt, img.get("title"))

    def test_composeIcon_escapes_alt_and_title(self):
        alt = 'alt"&'
        icon = self.factory.getUniqueString() + ".png"
        title = 'title"&'
        html_text = self.makeCompletePackageUpload().composeIcon(
            alt, icon, title)
        img = html.fromstring(html_text)
        self.assertEqual("[%s]" % alt, img.get("alt"))
        self.assertEqual(title, img.get("title"))

    def test_composeIconList_produces_icons(self):
        icons = self.makeCompletePackageUpload().composeIconList()
        self.assertNotEqual([], icons)
        self.assertEqual('img', html.fromstring(icons[0]).tag)

    def test_composeIconList_produces_icons_conditionally(self):
        complete_upload = self.makeCompletePackageUpload()
        base_count = len(complete_upload.composeIconList())
        complete_upload.contains_build = True
        new_count = len(complete_upload.composeIconList())
        self.assertEqual(base_count + 1, new_count)

    def test_composeNameAndChangesLink_does_not_link_if_no_changes_file(self):
        upload = self.factory.makeCopyJobPackageUpload()
        complete_upload = self.makeCompletePackageUpload(upload)
        self.assertEqual(
            complete_upload.displayname,
            complete_upload.composeNameAndChangesLink())

    def test_composeNameAndChangesLink_links_to_changes_file(self):
        complete_upload = self.makeCompletePackageUpload()
        link = html.fromstring(complete_upload.composeNameAndChangesLink())
        self.assertEqual(
            complete_upload.changesfile.http_url, link.get("href"))

    def test_composeNameAndChangesLink_escapes_nonlinked_display_name(self):
        filename = 'name"&name'
        upload = self.factory.makeCustomPackageUpload(filename=filename)
        # Stop nameAndChangesLink from producing a link.
        upload.changesfile = None
        complete_upload = self.makeCompletePackageUpload(upload)
        self.assertIn(
            cgi.escape(filename), complete_upload.composeNameAndChangesLink())

    def test_composeNameAndChangesLink_escapes_name_in_link(self):
        filename = 'name"&name'
        upload = self.factory.makeCustomPackageUpload(filename=filename)
        complete_upload = self.makeCompletePackageUpload(upload)
        link = html.fromstring(complete_upload.composeNameAndChangesLink())
        self.assertIn(filename, link.get("title"))
        self.assertEqual(filename, link.text)

    def test_icons_and_name_composes_icons_and_link_and_archs(self):
        complete_upload = self.makeCompletePackageUpload()
        icons_and_name = html.fromstring(complete_upload.icons_and_name)
        self.assertNotEqual(None, icons_and_name.find("img"))
        self.assertNotEqual(None, icons_and_name.find("a"))
        self.assertIn(
            complete_upload.displayarchs, ' '.join(icons_and_name.itertext()))
