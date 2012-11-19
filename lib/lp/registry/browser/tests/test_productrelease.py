# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductRelease pages."""

__metaclass__ = type


from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class ProductReleaseAddDownloadFileViewTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_add_file(self):
        release = self.factory.makeProductRelease()
        maintainer = release.milestone.product.owner
        upload = self.factory.makeFakeFileUpload(filename='pting.tar.gz')
        form = {
            'field.description': 'App 0.1 tarball',
            'field.contenttype': 'CODETARBALL',
            'field.filecontent': upload,
            'field.actions.add': 'Upload',
            }
        with person_logged_in(maintainer):
            view = create_initialized_view(
                release, '+adddownloadfile', form=form)
        self.assertEqual([], view.errors)
        notifications = [
            nm.message for nm in view.request.response.notifications]
        self.assertEqual(
            ["Your file 'pting.tar.gz' has been uploaded."], notifications)

    def test_add_file_duplicate(self):
        release = self.factory.makeProductRelease()
        maintainer = release.milestone.product.owner
        release_file = self.factory.makeProductReleaseFile(release=release)
        file_name = release_file.libraryfile.filename
        upload = self.factory.makeFakeFileUpload(filename=file_name)
        form = {
            'field.description': 'App 0.1 tarball',
            'field.contenttype': 'CODETARBALL',
            'field.filecontent': upload,
            'field.actions.add': 'Upload',
            }
        with person_logged_in(maintainer):
            view = create_initialized_view(
                release, '+adddownloadfile', form=form)
        self.assertEqual(
            ["The file '%s' is already uploaded." % file_name], view.errors)
