import httplib
import os
import re
import socket
import tempfile
import urllib2
import unittest

import bzrlib
from bzrlib.branch import BranchReferenceFormat
from bzrlib import bzrdir
from bzrlib.errors import (
    BzrError, UnsupportedFormatError, UnknownFormatError, ParamikoNotPresent,
    NotBranchError)
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.weave import Weave

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.puller.tests import PullerWorkerMixin
from canonical.codehosting.puller.worker import (
    BadUrlSsh,
    BadUrlLaunchpad,
    BranchReferenceLoopError,
    PullerWorker,
    PullerWorkerProtocol)
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp.uri import InvalidURIError
from canonical.testing import reset_logging


class StubbedPullerWorkerProtocol(PullerWorkerProtocol):

    def __init__(self):
        # We are deliberately not calling PullerWorkerProtocol.__init__:
        # pylint: disable-msg=W0231
        self.calls = []

    def startMirroring(self, branch_to_mirror):
        self.calls.append(('startMirroring', branch_to_mirror))

    def mirrorSucceeded(self, branch_to_mirror, last_revision):
        self.calls.append(
            ('mirrorSucceeded', branch_to_mirror, last_revision))

    def mirrorFailed(self, branch_to_mirror, message, oops_id):
        self.calls.append(
            ('mirrorFailed', branch_to_mirror, message, oops_id))


class StubbedPullerWorker(PullerWorker):
    """Partially stubbed subclass of PullerWorker, for unit tests."""

    enable_checkBranchReference = False
    enable_checkSourceUrl = True

    def _checkSourceUrl(self):
        if self.enable_checkSourceUrl:
            PullerWorker._checkSourceUrl(self)

    def _checkBranchReference(self):
        if self.enable_checkBranchReference:
            PullerWorker._checkBranchReference(self)

    def _openSourceBranch(self):
        self.testcase.open_call_count += 1

    def _mirrorToDestBranch(self):
        pass


class ErrorHandlingTestCase(unittest.TestCase):
    """Base class to test PullerWorker error reporting."""

    def setUp(self):
        unittest.TestCase.setUp(self)
        self._errorHandlingSetUp()

    def _errorHandlingSetUp(self):
        """Setup code that is specific to ErrorHandlingTestCase.

        This is needed because TestReferenceMirroring uses a diamond-shaped
        class hierarchy and we do not want to end up calling unittest.TestCase
        twice.
        """
        self.protocol = StubbedPullerWorkerProtocol()
        self.branch = StubbedPullerWorker(
            src='foo', dest='bar', branch_id=1,
            unique_name='owner/product/foo', branch_type=None,
            protocol=self.protocol, oops_prefix='TOKEN')
        self.open_call_count = 0
        self.branch.testcase = self

    def runMirrorAndGetError(self):
        """Run mirror, check that we receive exactly one error, and return its
        str().
        """
        self.branch.mirror()
        self.assertEqual(
            2, len(self.protocol.calls),
            "Expected startMirroring and mirrorFailed, got: %r"
            % (self.protocol.calls,))
        startMirroring, mirrorFailed = self.protocol.calls
        self.assertEqual(('startMirroring', self.branch), startMirroring)
        self.assertEqual(('mirrorFailed', self.branch), mirrorFailed[:2])
        self.assert_('TOKEN' in mirrorFailed[3])
        self.protocol.calls = []
        return str(mirrorFailed[2])

    def runMirrorAndAssertErrorStartsWith(self, expected_error):
        """Run mirror and check that we receive exactly one error, the str()
        of which starts with `expected_error`.
        """
        error = self.runMirrorAndGetError()
        if not error.startswith(expected_error):
            self.fail('Expected "%s" but got "%s"' % (expected_error, error))

    def runMirrorAndAssertErrorEquals(self, expected_error):
        """Run mirror and check that we receive exactly one error, the str()
        of which is equal to `expected_error`.
        """
        error = self.runMirrorAndGetError()
        self.assertEqual(error, expected_error)


class TestBadUrl(ErrorHandlingTestCase):
    """Test that PullerWorker does not try mirroring from bad URLs.

    Bad URLs use schemes like sftp or bzr+ssh that usually require
    authentication, and hostnames in the launchpad.net domains.

    That prevents errorspam produced by ssh when it cannot connect and saves
    timing out when trying to connect to chinstrap, sodium (always using a
    ssh-based scheme) or launchpad.net.

    That also allows us to display a more informative error message to the
    user.
    """

    def testBadUrlSftp(self):
        # If the scheme of the source url is sftp, _openSourceBranch raises
        # BadUrlSsh.
        self.branch.source = 'sftp://example.com/foo'
        self.assertRaises(BadUrlSsh, self.branch._checkSourceUrl)

    def testBadUrlBzrSsh(self):
        # If the scheme of the source url is bzr+ssh, _openSourceBracnh raises
        # BadUrlSsh.
        self.branch.source = 'bzr+ssh://example.com/foo'
        self.assertRaises(BadUrlSsh, self.branch._checkSourceUrl)

    def testBadUrlBzrSshCaught(self):
        # The exception raised if the scheme of the source url is sftp or
        # bzr+ssh is caught and an informative error message is displayed to
        # the user.
        expected_msg = "Launchpad cannot mirror branches from SFTP "
        self.branch.source = 'sftp://example.com/foo'
        self.runMirrorAndAssertErrorStartsWith(expected_msg)
        self.branch.source = 'bzr+ssh://example.com/foo'
        self.runMirrorAndAssertErrorStartsWith(expected_msg)

    def testBadUrlLaunchpadDomain(self):
        # If the host of the source branch is in the launchpad.net domain,
        # _openSourceBranch raises BadUrlLaunchpad.
        self.branch.source = 'http://bazaar.launchpad.dev/foo'
        self.assertRaises(BadUrlLaunchpad, self.branch._checkSourceUrl)
        self.branch.source = 'sftp://bazaar.launchpad.dev/bar'
        self.assertRaises(BadUrlLaunchpad, self.branch._checkSourceUrl)
        self.branch.source = 'http://launchpad.dev/baz'
        self.assertRaises(BadUrlLaunchpad, self.branch._checkSourceUrl)

    def testBadUrlLaunchpadCaught(self):
        # The exception raised if the host of the source url is launchpad.net
        # or a host in this domain is caught, and an informative error message
        # is displayed to the user.
        expected_msg = "Launchpad does not mirror branches from Launchpad."
        self.branch.source = 'http://bazaar.launchpad.dev/foo'
        self.runMirrorAndAssertErrorEquals(expected_msg)
        self.branch.source = 'http://launchpad.dev/foo'
        self.runMirrorAndAssertErrorEquals(expected_msg)


class TestReferenceMirroring(TestCaseWithTransport, ErrorHandlingTestCase):
    """Feature tests for mirroring of branch references."""

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        ErrorHandlingTestCase._errorHandlingSetUp(self)
        self.branch.enable_checkBranchReference = True

    def tearDown(self):
        TestCaseWithTransport.tearDown(self)
        reset_logging()

    def testCreateBranchReference(self):
        """Test that our createBranchReference helper works correctly."""
        # First create a bzrdir with a branch and repository.
        t = get_transport(self.get_url('.'))
        t.mkdir('repo')
        dir = bzrdir.BzrDir.create(self.get_url('repo'))
        dir.create_repository()
        target_branch = dir.create_branch()

        # Then create a pure branch reference using our custom helper.
        reference_url = self.createBranchReference(self.get_url('repo'))

        # Open the branch reference and check that the result is indeed the
        # branch we wanted it to point at.
        opened_branch = bzrlib.branch.Branch.open(reference_url)
        self.assertEqual(opened_branch.base, target_branch.base)

    def createBranchReference(self, url):
        """Create a pure branch reference that points to the specified URL.

        :param path: relative path to the branch reference.
        :param url: target of the branch reference.
        :return: file url to the created pure branch reference.
        """
        # XXX DavidAllouche 2007-09-12
        # We do this manually because the bzrlib API does not support creating
        # a branch reference without opening it. See bug 139109.
        t = get_transport(self.get_url('.'))
        t.mkdir('reference')
        a_bzrdir = bzrdir.BzrDir.create(self.get_url('reference'))
        branch_reference_format = BranchReferenceFormat()
        branch_transport = a_bzrdir.get_branch_transport(
            branch_reference_format)
        branch_transport.put_bytes('location', url)
        branch_transport.put_bytes(
            'format', branch_reference_format.get_format_string())
        return a_bzrdir.root_transport.base

    def testGetBranchReferenceValue(self):
        """PullerWorker._getBranchReference gives the reference value for
        a branch reference.
        """
        reference_value = 'http://example.com/branch'
        reference_url = self.createBranchReference(reference_value)
        self.branch.source = reference_url
        self.assertEqual(
            self.branch._getBranchReference(reference_url), reference_value)

    def testGetBranchReferenceNone(self):
        """PullerWorker._getBranchReference gives None for a normal branch.
        """
        self.make_branch('repo')
        branch_url = self.get_url('repo')
        self.assertIs(
            self.branch._getBranchReference(branch_url), None)

    def testHostedBranchReference(self):
        """A branch reference for a hosted branch must cause an error."""
        reference_url = self.createBranchReference(
            'http://example.com/branch')
        self.branch.branch_type = BranchType.HOSTED
        self.branch.source = reference_url
        expected_msg = (
            "Branch references are not allowed for branches of type Hosted.")
        error = self.runMirrorAndAssertErrorEquals(expected_msg)
        self.assertEqual(self.open_call_count, 0)

    def testMirrorLocalBranchReference(self):
        """A file:// branch reference for a mirror branch must cause an error.
        """
        reference_url = self.createBranchReference('file:///sauces/sikrit')
        self.branch.branch_type = BranchType.MIRRORED
        self.branch.source = reference_url
        expected_msg = ("Bad branch reference value: file:///sauces/sikrit")
        self.runMirrorAndAssertErrorEquals(expected_msg)
        self.assertEqual(self.open_call_count, 0)


class TestErrorHandling(ErrorHandlingTestCase):

    def setUp(self):
        ErrorHandlingTestCase.setUp(self)
        self.branch.enable_checkSourceUrl = False

    def testHTTPError(self):
        def stubOpenSourceBranch():
            raise urllib2.HTTPError(
                'http://something', httplib.UNAUTHORIZED,
                'Authorization Required', 'some headers',
                open(tempfile.mkstemp()[1]))
        self.branch._openSourceBranch = stubOpenSourceBranch
        self.runMirrorAndAssertErrorEquals("Authentication required.")

    def testSocketErrorHandling(self):
        def stubOpenSourceBranch():
            raise socket.error('foo')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A socket error occurred:'
        self.runMirrorAndAssertErrorStartsWith(expected_msg)

    def testUnsupportedFormatErrorHandling(self):
        def stubOpenSourceBranch():
            raise UnsupportedFormatError('Bazaar-NG branch, format 0.0.4')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'Launchpad does not support branches '
        self.runMirrorAndAssertErrorStartsWith(expected_msg)

    def testUnknownFormatError(self):
        def stubOpenSourceBranch():
            raise UnknownFormatError(format='Bad format')
        self.branch._openSourceBranch = stubOpenSourceBranch
        self.runMirrorAndAssertErrorStartsWith('Unknown branch format: ')

    def testParamikoNotPresent(self):
        def stubOpenSourceBranch():
            raise ParamikoNotPresent('No module named paramiko')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'Launchpad cannot mirror branches from SFTP '
        self.runMirrorAndAssertErrorStartsWith(expected_msg)

    def testNotBranchErrorMirrored(self):
        """Should receive a user-friendly message we are asked to mirror a
        non-branch.
        """
        def stubOpenSourceBranch():
            raise NotBranchError('http://example.com/not-branch')
        self.branch._openSourceBranch = stubOpenSourceBranch
        self.branch.branch_type = BranchType.MIRRORED
        expected_msg = 'Not a branch: "http://example.com/not-branch".'
        self.runMirrorAndAssertErrorEquals(expected_msg)

    def testNotBranchErrorHosted(self):
        """The not-a-branch error message should *not* include the Branch id
        from the database. Instead, the path should be translated to a
        user-visible location.
        """
        split_id = branch_id_to_path(self.branch.branch_id)
        def stubOpenSourceBranch():
            raise NotBranchError('/srv/sm-ng/push-branches/%s/.bzr/branch/'
                                 % split_id)
        self.branch._openSourceBranch = stubOpenSourceBranch
        self.branch.branch_type = BranchType.HOSTED
        expected_msg = 'Not a branch: "sftp://bazaar.launchpad.net/~%s".' % (
            self.branch.unique_name,)
        self.runMirrorAndAssertErrorEquals(expected_msg)

    def testNotBranchErrorImported(self):
        """The not-a-branch error message for import branch should not
        disclose the internal URL. Since there is no user-visible URL to
        blame, we do not display any URL at all.
        """
        def stubOpenSourceBranch():
            raise NotBranchError('http://canonical.example.com/internal/url')
        self.branch._openSourceBranch = stubOpenSourceBranch
        self.branch.branch_type = BranchType.IMPORTED
        self.runMirrorAndAssertErrorEquals('Not a branch.')

    def testBranchReferenceLoopError(self):
        """BranchReferenceLoopError exceptions are caught."""
        def stubCheckBranchReference():
            raise BranchReferenceLoopError()
        self.branch._checkBranchReference = stubCheckBranchReference
        self.runMirrorAndAssertErrorEquals("Circular branch reference.")

    def testInvalidURIError(self):
        """When a branch reference contains an invalid URL, an InvalidURIError
        is raised. The worker catches this and reports it to the scheduler.
        """
        def stubCheckBranchReference():
            raise InvalidURIError("This is not a URL")
        self.branch._checkBranchReference = stubCheckBranchReference
        self.runMirrorAndAssertErrorEquals("This is not a URL")

    def testBzrErrorHandling(self):
        def stubOpenSourceBranch():
            raise BzrError('A generic bzr error')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A generic bzr error'
        self.runMirrorAndAssertErrorEquals(expected_msg)


class TestPullerWorker_SourceProblems(TestCaseWithTransport,
                                      PullerWorkerMixin):

    def tearDown(self):
        super(TestPullerWorker_SourceProblems, self).tearDown()
        reset_logging()

    def assertMirrorFailed(self, puller_worker, message_substring):
        """Assert that puller_worker failed, and that message_substring is in
        the message.

        'puller_worker' must use a StubbedPullerWorkerProtocol.
        """
        protocol = puller_worker.protocol
        self.assertEqual(
            2, len(protocol.calls),
            "Expected startMirroring and mirrorFailed, got: %r"
            % (protocol.calls,))
        startMirroring, mirrorFailed = protocol.calls
        self.assertEqual(('startMirroring', puller_worker), startMirroring)
        self.assertEqual(('mirrorFailed', puller_worker), mirrorFailed[:2])
        self.assertContainsRe(
            str(mirrorFailed[2]), re.escape(message_substring))

    def testUnopenableSourceDoesNotCreateMirror(self):
        non_existent_source = os.path.abspath('nonsensedir')
        dest_dir = 'dest-dir'
        my_branch = self.makePullerWorker(
            src_dir=non_existent_source, dest_dir=dest_dir)
        my_branch.mirror()
        self.failIf(os.path.exists(dest_dir), 'dest-dir should not exist')

    def testMissingSourceWhines(self):
        non_existent_source = os.path.abspath('nonsensedir')
        my_branch = self.makePullerWorker(
            src_dir=non_existent_source, dest_dir="non-existent-destination",
            protocol=StubbedPullerWorkerProtocol())
        my_branch.mirror()
        self.assertMirrorFailed(my_branch, 'Not a branch')

    def testMissingFileRevisionData(self):
        self.build_tree(['missingrevision/',
                         'missingrevision/afile'])
        tree = self.make_branch_and_tree('missingrevision', format='dirstate')
        tree.add(['afile'], ['myid'])
        tree.commit('start')
        # Now we have a good branch with a file called afile and id myid we
        # need to figure out the actual path for the weave.. or deliberately
        # corrupt it. like this.

        # XXX: JonathanLange 2007-10-11: _put_weave is an internal function
        # that we probably shouldn't be using. TODO: Ask author of this test
        # to better explain which particular repository corruption we are
        # trying to reproduce here.
        tree.lock_write()
        self.addCleanup(tree.unlock)
        tree.branch.repository.weave_store._put_weave(
            "myid", Weave(weave_name="myid"),
            tree.branch.repository.get_transaction())
        source_url = os.path.abspath('missingrevision')
        my_branch = self.makePullerWorker(
            src_dir=source_url, dest_dir="non-existent-destination",
            protocol=StubbedPullerWorkerProtocol())
        my_branch.mirror()
        self.assertMirrorFailed(my_branch, 'No such file')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
