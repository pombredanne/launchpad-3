# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View tests for ProductRelease pages."""

__metaclass__ = type


from lp.app.enums import InformationType
from lp.services.webapp.escaping import html_escape
from lp.services.webapp import canonical_url
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


class NonPublicProductReleaseViewTestCase(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def test_proprietary_add_milestone(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(name='fnord',
            owner=owner, information_type=InformationType.PROPRIETARY)
        milestone = self.factory.makeMilestone(product=product)
        with person_logged_in(owner):
            browser = self.getViewBrowser(
                milestone, view_name="+addrelease", user=owner)
            msg = 'Fnord is PROPRIETARY. It cannot have any releases.'
            self.assertTrue(html_escape(msg) in browser.contents)

    def test_proprietary_add_series(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(name='fnord',
            owner=owner, information_type=InformationType.PROPRIETARY)
        series = self.factory.makeProductSeries(product=product, name='bnord')
        with person_logged_in(owner):
            browser = self.getViewBrowser(
                series, view_name="+addrelease", user=owner)
            msg = ('The bnord series of Fnord is PROPRIETARY.'
                   ' It cannot have any releases.')
            self.assertTrue(html_escape(msg) in browser.contents)

    def test_embargoed_add_milestone(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(name='fnord',
            owner=owner, information_type=InformationType.EMBARGOED)
        milestone = self.factory.makeMilestone(product=product)
        with person_logged_in(owner):
            view = create_initialized_view(milestone, name="+addrelease")
            notifications = [
                nm.message for nm in view.request.response.notifications]
            self.assertEqual(
                [html_escape("Any releases added for Fnord will be PUBLIC.")],
                notifications)

    def test_embargoed_add_series(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(name='fnord',
            owner=owner, information_type=InformationType.EMBARGOED)
        series = self.factory.makeProductSeries(product=product, name='bnord')
        with person_logged_in(owner):
            view = create_initialized_view(series, name="+addrelease")
            notifications = [
                nm.message for nm in view.request.response.notifications]
            self.assertEqual(
                [html_escape("Any releases added for bnord will be PUBLIC.")],
                notifications)

class ProductReleaseAddDownloadFileViewTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def makeForm(self, file_name):
        upload = self.factory.makeFakeFileUpload(filename=file_name)
        form = {
            'field.description': 'App 0.1 tarball',
            'field.contenttype': 'CODETARBALL',
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
