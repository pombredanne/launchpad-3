# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductRelease pages."""

__metaclass__ = type


from lp.app.enums import InformationType
from lp.services.webapp.escaping import html_escape
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class ProductReleaseAddDownloadFileViewTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def makeForm(self, file_name, file_release_type='CODETARBALL'):
        upload = self.factory.makeFakeFileUpload(filename=file_name)
        form = {
            'field.description': 'App 0.1 tarball',
            'field.contenttype': file_release_type,
            'field.filecontent': upload,
            'field.actions.add': 'Upload',
            }
        return form

    def test_add_file(self):
        release = self.factory.makeProductRelease()
        maintainer = release.milestone.product.owner
        form = self.makeForm('pting.tar.gz')
        with person_logged_in(maintainer):
            view = create_initialized_view(
                release, '+adddownloadfile', form=form)
        self.assertEqual([], view.errors)
        notifications = [
            nm.message for nm in view.request.response.notifications]
        self.assertEqual(
            [html_escape("Your file 'pting.tar.gz' has been uploaded.")],
            notifications)

    def test_add_file_duplicate(self):
        release = self.factory.makeProductRelease()
        maintainer = release.milestone.product.owner
        release_file = self.factory.makeProductReleaseFile(release=release)
        file_name = release_file.libraryfile.filename
        form = self.makeForm(file_name)
        with person_logged_in(maintainer):
            view = create_initialized_view(
                release, '+adddownloadfile', form=form)
        self.assertEqual(
            [html_escape("The file '%s' is already uploaded." % file_name)],
            view.errors)

    def test_refuses_proprietary_products(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(
            owner=owner, information_type=InformationType.PROPRIETARY)
        with person_logged_in(owner):
            release = self.factory.makeProductRelease(product=product)
            form = self.makeForm('something.tar.gz')
            view = create_initialized_view(
                release, '+adddownloadfile', form=form)
        self.assertEqual(
            ['Only public projects can have download files.'], view.errors)

    def assertFileHasMimeType(self, file_release_type, expected_mimetype):
        """Assert that a release file is stored with a specific mimetype.

        :param file_release_type: A string specifying the type of the release
            file. Must be one of: CODETARBALL, README, RELEASENOTES,
            CHANGELOG, INSTALLER.
        :param expected_mimetype: The mimetype string you expect the file to
            have.

        """
        release = self.factory.makeProductRelease()
        maintainer = release.milestone.product.owner
        form = self.makeForm('foo', file_release_type)
        with person_logged_in(maintainer):
            create_initialized_view(release, '+adddownloadfile', form=form)
        self.assertEqual(1, release.files.count())
        self.assertEqual(
            expected_mimetype,
            release.files[0].libraryfile.mimetype
        )

    def test_tarballs_and_installers_are_octet_stream(self):
        self.assertFileHasMimeType('CODETARBALL', "application/octet-stream")
        self.assertFileHasMimeType('INSTALLER', "application/octet-stream")

    def test_readme_files_are_text_plain(self):
        self.assertFileHasMimeType('README', "text/plain")
        self.assertFileHasMimeType('CHANGELOG', "text/plain")
        self.assertFileHasMimeType('RELEASENOTES', "text/plain")
