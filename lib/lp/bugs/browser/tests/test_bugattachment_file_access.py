# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import re
from urlparse import (
    parse_qs,
    urlparse,
    )

import transaction
from zope.component import (
    getMultiAdapter,
    getUtility,
    )
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized
from zope.security.management import endInteraction

from canonical.launchpad.browser.librarian import (
    SafeStreamOrRedirectLibraryFileAliasView,
    StreamOrRedirectLibraryFileAliasView,
    )
from canonical.launchpad.interfaces.librarian import (
    ILibraryFileAliasWithParent,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import RedirectionView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lazr.restfulclient.errors import Unauthorized as RestfulUnauthorized
from lp.bugs.browser.bugattachment import BugAttachmentFileNavigation
import lp.services.features
from lp.services.features.flags import NullFeatureController
from lp.testing import (
    launchpadlib_for,
    launchpadlib_for_anonymous,
    login_person,
    TestCaseWithFactory,
    ws_object,
    )


class TestAccessToBugAttachmentFiles(TestCaseWithFactory):
    """Tests of traversal to and access of files of bug attachments."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestAccessToBugAttachmentFiles, self).setUp()
        self.bug_owner = self.factory.makePerson()
        getUtility(ILaunchBag).clear()
        login_person(self.bug_owner)
        self.bug = self.factory.makeBug(owner=self.bug_owner)
        self.bugattachment = self.factory.makeBugAttachment(
            bug=self.bug, filename='foo.txt', data='file content')

    def test_traversal_to_lfa_of_bug_attachment(self):
        # Traversing to the URL provided by a ProxiedLibraryFileAlias of a
        # bug attachament returns a StreamOrRedirectLibraryFileAliasView.
        request = LaunchpadTestRequest()
        request.setTraversalStack(['foo.txt'])
        navigation = BugAttachmentFileNavigation(
            self.bugattachment, request)
        view = navigation.publishTraverse(request, '+files')
        self.assertIsInstance(view, StreamOrRedirectLibraryFileAliasView)

    def test_traversal_to_lfa_of_bug_attachment_wrong_filename(self):
        # If the filename provided in the URL does not match the
        # filename of the LibraryFileAlias, a NotFound error is raised.
        request = LaunchpadTestRequest()
        request.setTraversalStack(['nonsense'])
        navigation = BugAttachmentFileNavigation(self.bugattachment, request)
        self.assertRaises(
            NotFound, navigation.publishTraverse, request, '+files')

    def test_access_to_unrestricted_file(self):
        # Requests of unrestricted files are redirected to Librarian URLs.
        request = LaunchpadTestRequest()
        request.setTraversalStack(['foo.txt'])
        navigation = BugAttachmentFileNavigation(
            self.bugattachment, request)
        view = navigation.publishTraverse(request, '+files')
        next_view, traversal_path = view.browserDefault(request)
        self.assertIsInstance(next_view, RedirectionView)
        mo = re.match(
            '^http://localhost:58000/\d+/foo.txt$', next_view.target)
        self.assertIsNot(None, mo)

    def test_access_to_restricted_file(self):
        # Requests of restricted files are handled by ProxiedLibraryFileAlias
        # until we enable the publicrestrictedlibrarian (at which point
        # this test should check the view like
        # test_access_to_unrestricted_file.
        lfa_with_parent = getMultiAdapter(
            (self.bugattachment.libraryfile, self.bugattachment),
            ILibraryFileAliasWithParent)
        lfa_with_parent.restricted = True
        self.bug.setPrivate(True, self.bug_owner)
        transaction.commit()
        request = LaunchpadTestRequest()
        request.setTraversalStack(['foo.txt'])
        navigation = BugAttachmentFileNavigation(self.bugattachment, request)
        view = navigation.publishTraverse(request, '+files')
        # XXX Ensure the feature will be off - everything is off with
        # NullFeatureController. bug=631884
        lp.services.features.per_thread.features = NullFeatureController()
        self.addCleanup(
            setattr, lp.services.features.per_thread, 'features', None)
        next_view, traversal_path = view.browserDefault(request)
        self.assertEqual(view, next_view)
        file_ = next_view()
        file_.seek(0)
        self.assertEqual('file content', file_.read())

    def test_access_to_restricted_file_unauthorized(self):
        # If a user cannot access the bug attachment itself, he can neither
        # access the restricted Librarian file.
        lfa_with_parent = getMultiAdapter(
            (self.bugattachment.libraryfile, self.bugattachment),
            ILibraryFileAliasWithParent)
        lfa_with_parent.restricted = True
        self.bug.setPrivate(True, self.bug_owner)
        transaction.commit()
        user = self.factory.makePerson()
        login_person(user)
        self.assertRaises(Unauthorized, getattr, self.bugattachment, 'title')
        request = LaunchpadTestRequest()
        request.setTraversalStack(['foo.txt'])
        navigation = BugAttachmentFileNavigation(self.bugattachment, request)
        self.assertRaises(
            Unauthorized, navigation.publishTraverse, request, '+files')

    def test_content_disposition_of_restricted_file(self):
        # The content of restricted Librarian files for bug attachments
        # is served by instances of SafeStreamOrRedirectLibraryFileAliasView
        # which set the content disposition header of the HTTP response for
        # to "attachment".
        lfa_with_parent = getMultiAdapter(
            (self.bugattachment.libraryfile, self.bugattachment),
            ILibraryFileAliasWithParent)
        lfa_with_parent.restricted = True
        self.bug.setPrivate(True, self.bug_owner)
        transaction.commit()
        request = LaunchpadTestRequest()
        request.setTraversalStack(['foo.txt'])
        navigation = BugAttachmentFileNavigation(self.bugattachment, request)
        view = navigation.publishTraverse(request, '+files')
        # XXX Ensure the feature will be off - everything is off with
        # NullFeatureController. bug=631884
        lp.services.features.per_thread.features = NullFeatureController()
        self.addCleanup(
            setattr, lp.services.features.per_thread, 'features', None)
        next_view, traversal_path = view.browserDefault(request)
        self.assertIsInstance(
            next_view, SafeStreamOrRedirectLibraryFileAliasView)
        next_view()
        self.assertEqual(
            'attachment', request.response.getHeader('Content-Disposition'))


class TestWebserviceAccessToBugAttachmentFiles(TestCaseWithFactory):
    """Tests access to bug attachments via the webservice."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestWebserviceAccessToBugAttachmentFiles, self).setUp()
        self.bug_owner = self.factory.makePerson()
        getUtility(ILaunchBag).clear()
        login_person(self.bug_owner)
        self.bug = self.factory.makeBug(owner=self.bug_owner)
        self.bugattachment = self.factory.makeBugAttachment(
            bug=self.bug, filename='foo.txt', data='file content')

    def test_anon_access_to_public_bug_attachment(self):
        # Attachments of public bugs can be accessed by anonymous users.
        #
        # Need to endInteraction() because launchpadlib_for_anonymous() will
        # setup a new one.
        endInteraction()
        launchpad = launchpadlib_for_anonymous('test', version='devel')
        ws_bug = ws_object(launchpad, self.bug)
        ws_bugattachment = ws_bug.attachments[0]
        self.assertEqual(
            'file content', ws_bugattachment.data.open().read())

    def test_user_access_to_private_bug_attachment(self):
        # Users having access to private bugs can also read attachments
        # of these bugs.
        self.bug.setPrivate(True, self.bug_owner)
        other_user = self.factory.makePerson()
        launchpad = launchpadlib_for('test', self.bug_owner, version='devel')
        ws_bug = ws_object(launchpad, self.bug)
        ws_bugattachment = ws_bug.attachments[0]

        # The attachment contains a link to a HostedBytes resource;
        # accessing this link results normally in a redirect to a
        # Librarian URL.  We cannot simply access these Librarian URLS
        # for restricted Librarian files because the host name used in
        # the URLs is different for each file, and our test envireonment
        # does not support wildcard DNS. So let's disable the redirection
        # mechanism in our client's HTTP connection and inspect the
        # the Librarian URL.
        launchpad._browser._connection.follow_redirects = False
        response, content = launchpad._browser.get(
            ws_bugattachment.data._wadl_resource._url, return_response=True)
        self.assertEqual(303, response.status)
        parsed_url = urlparse(response['location'])
        self.assertEqual('https', parsed_url.scheme)
        mo = re.search(
            r'^i\d+\.restricted\.localhost:58000$', parsed_url.netloc)
        self.assertIsNot(None, mo)
        mo = re.search(r'^/\d+/foo\.txt$', parsed_url.path)
        self.assertIsNot(None, mo)
        params = parse_qs(parsed_url.query)
        self.assertEqual(['token'], params.keys())

        # If a user which cannot access the private bug itself tries to
        # to access the attachemnt, an Unauthorized error is raised.
        other_launchpad = launchpadlib_for(
            'test_unauthenticated', other_user, version='devel')
        self.assertRaises(
            RestfulUnauthorized, other_launchpad._browser.get,
            ws_bugattachment.data._wadl_resource._url)
