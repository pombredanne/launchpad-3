# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Unit tests for worker.py."""

__metaclass__ = type


import httplib
import os
import re
import shutil
import socket
from StringIO import StringIO
import tempfile
import unittest
import urllib2

import bzrlib.branch
from bzrlib import bzrdir
from bzrlib.branch import BranchReferenceFormat
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import (
    TestCaseInTempDir, TestCaseWithMemoryTransport, TestCaseWithTransport)
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)
from bzrlib.transport import get_transport
from bzrlib.weave import Weave
from bzrlib.errors import (
    BzrError, UnsupportedFormatError, UnknownFormatError, ParamikoNotPresent,
    NotBranchError)

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.puller.worker import (
    PullerWorker, BadUrlSsh, BadUrlLaunchpad, BranchReferenceLoopError,
    BranchReferenceForbidden, BranchReferenceValueError,
    get_canonical_url_for_branch_name, install_worker_progress_factory,
    PullerWorkerProtocol)
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.launchpad.database import Branch
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.uri import URI
from canonical.testing import LaunchpadScriptLayer, reset_logging


class StubbedPullerWorkerProtocol(PullerWorkerProtocol):

    def __init__(self):
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


class PullerWorkerMixin:
    """Mixin for tests that want to make PullerWorker objects."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        self._home = os.environ.get('HOME', None)
        os.environ.update({'HOME': self.test_dir})

    def tearDown(self):
        if self._home is not None:
            os.environ['HOME'] = self._home
        shutil.rmtree(self.test_dir)

    def makePullerWorker(self, src_dir=None, dest_dir=None, branch_type=None,
                         protocol=None):
        """Anonymous creation method for PullerWorker."""
        if src_dir is None:
            src_dir = os.path.join(self.test_dir, 'source_dir')
        if dest_dir is None:
            dest_dir = os.path.join(self.test_dir, 'dest_dir')
        if protocol is None:
            protocol = PullerWorkerProtocol(StringIO())
        return PullerWorker(
            src_dir, dest_dir, branch_id=1, unique_name='foo/bar/baz',
            branch_type=branch_type, protocol=protocol)


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
            protocol=self.protocol)
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
        self.protocol.calls = []
        return str(mirrorFailed[2])

    def runMirrorAndAssertErrorStartsWith(self, expected_error):
        """Run mirror and check that we receive exactly one error, the str() of
        which starts with `expected_error`.
        """
        error = self.runMirrorAndGetError()
        if not error.startswith(expected_error):
            self.fail('Expected "%s" but got "%s"' % (expected_error, error))

    def runMirrorAndAssertErrorEquals(self, expected_error):
        """Run mirror and check that we receive exactly one error, the str() of
        which is equal to `expected_error`.
        """
        error = self.runMirrorAndGetError()
        self.assertEqual(error, expected_error)


class TestPullerWorker(unittest.TestCase, PullerWorkerMixin):
    """Test the mirroring functionality of PullerWorker."""

    test_dir = None

    def setUp(self):
        PullerWorkerMixin.setUp(self)

    def tearDown(self):
        PullerWorkerMixin.tearDown(self)

    def testMirrorActuallyMirrors(self):
        # Check that mirror() will mirror the Bazaar branch.
        to_mirror = self.makePullerWorker()
        tree = create_branch_with_one_revision(to_mirror.source)
        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            tree.last_revision(), mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # Check that we can mirror an empty branch, and that the
        # last_mirrored_id for an empty branch can be distinguished from an
        # unmirrored branch.
        to_mirror = self.makePullerWorker()

        # Create an empty source branch.
        os.makedirs(to_mirror.source)
        tree = bzrdir.BzrDir.create_branch_and_repo(to_mirror.source)

        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(NULL_REVISION, mirrored_branch.last_revision())


class TestPullerWorkerFormats(TestCaseWithRepository, PullerWorkerMixin):

    def setUp(self):
        TestCaseWithRepository.setUp(self)

    def tearDown(self):
        TestCaseWithRepository.tearDown(self)
        reset_logging()

    def testMirrorKnitAsKnit(self):
        # Create a source branch in knit format, and check that the mirror is in
        # knit format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
        self._testMirrorFormat()

    def testMirrorMetaweaveAsMetaweave(self):
        # Create a source branch in metaweave format, and check that the mirror
        # is in metaweave format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat7()
        self._testMirrorFormat()

    def testMirrorWeaveAsWeave(self):
        # Create a source branch in weave format, and check that the mirror is
        # in weave format.
        self.bzrdir_format = bzrdir.BzrDirFormat6()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat6()
        self._testMirrorFormat()

    def testSourceFormatChange(self):
        # Create and mirror a branch in weave format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat7()
        self._createSourceBranch()
        self._mirror()

        # Change the branch to knit format.
        shutil.rmtree('src-branch')
        self.repository_format = bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
        self._createSourceBranch()

        # Mirror again.  The mirrored branch should now be in knit format.
        mirrored_branch = self._mirror()
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())

    def _createSourceBranch(self):
        os.mkdir('src-branch')
        tree = self.make_branch_and_tree('src-branch')
        self.local_branch = tree.branch
        self.build_tree(['foo'], transport=get_transport('./src-branch'))
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')
        return tree

    def _mirror(self):
        # Mirror src-branch to dest-branch
        source_url = os.path.abspath('src-branch')
        to_mirror = self.makePullerWorker(src_dir=source_url)
        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        return mirrored_branch

    def _testMirrorFormat(self):
        tree = self._createSourceBranch()

        mirrored_branch = self._mirror()
        self.assertEqual(tree.last_revision(),
                         mirrored_branch.last_revision())

        # Assert that the mirrored branch is in source's format
        # XXX AndrewBennetts 2006-05-18: comparing format objects is ugly.
        # See bug 45277.
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())
        self.assertEqual(
            self.bzrdir_format.get_format_description(),
            mirrored_branch.bzrdir._format.get_format_description())


class TestPullerWorker_SourceProblems(TestCaseWithTransport,
                                      PullerWorkerMixin):

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        PullerWorkerMixin.setUp(self)

    def tearDown(self):
        PullerWorkerMixin.tearDown(self)
        TestCaseWithTransport.tearDown(self)
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
        tree.branch.repository.weave_store._put_weave(
            "myid", Weave(weave_name="myid"),
            tree.branch.repository.get_transaction())
        source_url = os.path.abspath('missingrevision')
        my_branch = self.makePullerWorker(
            src_dir=source_url, dest_dir="non-existent-destination",
            protocol=StubbedPullerWorkerProtocol())
        my_branch.mirror()
        self.assertMirrorFailed(my_branch, 'No such file')


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
        reference_url = self.createBranchReference('http://example.com/branch')
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


class TestCanTraverseReferences(unittest.TestCase, PullerWorkerMixin):
    """Unit tests for PullerWorker._canTraverseReferences."""

    def setUp(self):
        PullerWorkerMixin.setUp(self)

    def tearDown(self):
        PullerWorkerMixin.setUp(self)

    def makeBranch(self, branch_type):
        """Helper to create a PullerWorker with a specified branch_type."""
        return self.makePullerWorker(branch_type=branch_type)

    def testTrueForMirrored(self):
        """We can traverse branch references when pulling mirror branches."""
        mirror_branch = self.makeBranch(BranchType.MIRRORED)
        self.assertEqual(mirror_branch._canTraverseReferences(), True)

    def testFalseForImported(self):
        """We cannot traverse branch references when pulling import branches.
        """
        import_branch = self.makeBranch(BranchType.IMPORTED)
        self.assertEqual(import_branch._canTraverseReferences(), False)

    def testFalseForHosted(self):
        """We cannot traverse branch references when pulling hosted branches.
        """
        hosted_branch = self.makeBranch(BranchType.HOSTED)
        self.assertEqual(hosted_branch._canTraverseReferences(), False)

    def testErrorForOtherRemote(self):
        """We do not pull REMOTE branches. If the branch type is REMOTE, an
        AssertionError is raised.
        """
        remote_branch = self.makeBranch(BranchType.REMOTE)
        self.assertRaises(AssertionError, remote_branch._canTraverseReferences)

    def testErrorForBogusType(self):
        """If the branch type is a bogus value, AssertionError is raised.
        """
        bogus_branch = self.makeBranch(None)
        self.assertRaises(AssertionError, bogus_branch._canTraverseReferences)


class TestCheckBranchReference(unittest.TestCase):
    """Unit tests for PullerWorker._checkBranchReference."""

    class StubbedPullerWorker(PullerWorker):
        """Partially stubbed PullerWorker for checkBranchReference unit tests.
        """

        def _getBranchReference(self, url):
            self.testcase.get_branch_reference_calls.append(url)
            return self.testcase.reference_values[url]

        def _canTraverseReferences(self):
            assert self.testcase.can_traverse_references is not None
            return self.testcase.can_traverse_references

    def setUp(self):
        self.branch = TestCheckBranchReference.StubbedPullerWorker(
            'foo', 'bar', 1, 'owner/product/foo', None, None)
        self.branch.testcase = self
        self.get_branch_reference_calls = []
        self.reference_values = {}
        self.can_traverse_references = None

    def setUpReferences(self, locations):
        """Set up the stubbed PullerWorker to model a chain of references.

        Branch references can point to other branch references, forming a chain
        of locations. If the chain ends in a real branch, then the last
        location is None. If the final branch reference is a circular
        reference, or a branch reference that cannot be opened, the last
        location is not None.

        :param locations: sequence of branch location URL strings.
        """
        self.branch.source = locations[0]
        for i in range(len(locations) - 1):
            self.reference_values[locations[i]] = locations[i+1]

    def assertGetBranchReferenceCallsEqual(self, calls):
        """Assert that _getBranchReference was called a given number of times
        and for the given urls.
        """
        self.assertEqual(self.get_branch_reference_calls, calls)

    def testNotReference(self):
        """_checkBranchReference does not raise if the source url does not
        point to a branch reference.
        """
        self.can_traverse_references = False
        self.setUpReferences(['file:///local/branch', None])
        self.branch._checkBranchReference() # This must not raise.
        self.assertGetBranchReferenceCallsEqual(['file:///local/branch'])

    def testBranchReferenceForbidden(self):
        """_checkBranchReference raises BranchReferenceForbidden if
        _canTraverseReferences is false and the source url points to a branch
        reference.
        """
        self.can_traverse_references = False
        self.setUpReferences(
            ['file:///local/branch', 'http://example.com/branch'])
        self.assertRaises(
            BranchReferenceForbidden, self.branch._checkBranchReference)
        self.assertGetBranchReferenceCallsEqual(['file:///local/branch'])

    def testAllowedReference(self):
        """_checkBranchReference does not raise if _canTraverseReferences is
        true and the source URL points to a branch reference to a remote
        location.
        """
        self.can_traverse_references = True
        self.setUpReferences([
            'http://example.com/reference',
            'http://example.com/branch',
            None])
        self.branch._checkBranchReference() # This must not raise.
        self.assertGetBranchReferenceCallsEqual([
            'http://example.com/reference', 'http://example.com/branch'])

    def testFileReference(self):
        """_checkBranchReference raises BranchReferenceValueError if
        _canTraverseReferences is true and the source url points to a 'file'
        branch reference.
        """
        self.can_traverse_references = True
        self.setUpReferences([
            'http://example.com/reference',
            'file://local/branch'])
        self.assertRaises(
            BranchReferenceValueError, self.branch._checkBranchReference)
        self.assertGetBranchReferenceCallsEqual([
            'http://example.com/reference'])

    def testSelfReferencingBranch(self):
        """_checkBranchReference raises BranchReferenceLoopError if
        _canTraverseReferences is true and the source url points to a
        self-referencing branch."""
        self.can_traverse_references = True
        self.setUpReferences([
            'http://example.com/reference',
            'http://example.com/reference'])
        self.assertRaises(
            BranchReferenceLoopError, self.branch._checkBranchReference)
        self.assertGetBranchReferenceCallsEqual([
            'http://example.com/reference'])

    def testBranchReferenceLoop(self):
        """_checkBranchReference raises BranchReferenceLoopError if
        _canTraverseReferences is true and the source url points to a loop of
        branch references."""
        self.can_traverse_references = True
        self.setUpReferences([
            'http://example.com/reference-1',
            'http://example.com/reference-2',
            'http://example.com/reference-1'])
        self.assertRaises(
            BranchReferenceLoopError, self.branch._checkBranchReference)
        self.assertGetBranchReferenceCallsEqual([
            'http://example.com/reference-1',
            'http://example.com/reference-2'])


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
        """The not-a-branch error message for import branch should not disclose
        the internal URL. Since there is no user-visible URL to blame, we do
        not display any URL at all.
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
            raise URI("This is not a URL")
        self.branch._checkBranchReference = stubCheckBranchReference
        self.runMirrorAndAssertErrorEquals(
            '"This is not a URL" is not a valid URI')

    def testBzrErrorHandling(self):
        def stubOpenSourceBranch():
            raise BzrError('A generic bzr error')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A generic bzr error'
        self.runMirrorAndAssertErrorEquals(expected_msg)


class TestWorkerProtocol(unittest.TestCase, PullerWorkerMixin):
    """Tests for the client-side implementation of the protocol used to
    communicate to the master process.
    """

    def setUp(self):
        PullerWorkerMixin.setUp(self)
        self.test_dir = tempfile.mkdtemp()
        self.output = StringIO()
        self.protocol = PullerWorkerProtocol(self.output)
        self.branch_to_mirror = self.makePullerWorker()

    def tearDown(self):
        PullerWorkerMixin.tearDown(self)

    def assertSentNetstrings(self, expected_netstrings):
        """Assert that the protocol sent the given netstrings (in order)."""
        observed_netstrings = self.getNetstrings(self.output.getvalue())
        self.assertEqual(expected_netstrings, observed_netstrings)

    def getNetstrings(self, line):
        """Return the sequence of strings that are the netstrings that make up
        'line'.
        """
        strings = []
        while len(line) > 0:
            colon_index = line.find(':')
            length = int(line[:colon_index])
            strings.append(line[colon_index+1:colon_index+1+length])
            self.assertEqual(',', line[colon_index+1+length])
            line = line[colon_index+length+2:]
        return strings

    def resetBuffers(self):
        """Empty the test output and error buffers."""
        self.output.truncate(0)
        self.assertEqual('', self.output.getvalue())

    def test_nothingSentOnConstruction(self):
        """The protocol sends nothing until it receives an event."""
        self.assertSentNetstrings([])

    def test_startMirror(self):
        """Calling startMirroring sends 'startMirroring' as a netstring."""
        self.protocol.startMirroring(self.branch_to_mirror)
        self.assertSentNetstrings(['startMirroring', '0'])

    def test_mirrorSucceeded(self):
        """Calling 'mirrorSucceeded' sends the revno and 'mirrorSucceeded'."""
        self.protocol.startMirroring(self.branch_to_mirror)
        self.resetBuffers()
        self.protocol.mirrorSucceeded(self.branch_to_mirror, 1234)
        self.assertSentNetstrings(['mirrorSucceeded', '1', '1234'])

    def test_mirrorFailed(self):
        """Calling 'mirrorFailed' sends the error message."""
        self.protocol.startMirroring(self.branch_to_mirror)
        self.resetBuffers()
        self.protocol.mirrorFailed(
            self.branch_to_mirror, 'Error Message', 'OOPS')
        self.assertSentNetstrings(
            ['mirrorFailed', '2', 'Error Message', 'OOPS'])

    def test_progressMade(self):
        """Calling 'progressMade' sends an arbitrary string indicating
        progress.
        """
        self.protocol.progressMade()
        self.assertSentNetstrings(['progressMade', '0'])


class TestCanonicalUrl(unittest.TestCase):
    """Test cases for rendering the canonical url of a branch."""

    layer = LaunchpadScriptLayer

    def testCanonicalUrlConsistent(self):
        # worker.get_canonical_url_for_branch_name is consistent with
        # webapp.canonical_url, if the provided unique_name is correct.
        branch = Branch.get(15)
        # Check that the unique_name used in this test is consistent with the
        # sample data. This is an invariant of the test, so use a plain assert.
        unique_name = 'name12/gnome-terminal/main'
        assert branch.unique_name == '~' + unique_name
        # Now check that our implementation of canonical_url is consistent with
        # the canonical one.
        self.assertEqual(
            canonical_url(branch),
            get_canonical_url_for_branch_name(unique_name))


class TestWorkerProgressReporting(TestCaseWithMemoryTransport):
    """Tests for the WorkerProgressBar progress reporting mechanism."""

    class StubProtocol:
        """A stub for PullerWorkerProtocol that just defines progressMade."""
        def __init__(self):
            self.call_count = 0
        def progressMade(self):
            self.call_count += 1

    def setUp(self):
        TestCaseWithMemoryTransport.setUp(self)
        self.saved_factory = bzrlib.ui.ui_factory

    def tearDown(self):
        TestCaseWithMemoryTransport.tearDown(self)
        bzrlib.ui.ui_factory = self.saved_factory
        reset_logging()

    def test_simple(self):
        # Even the simplest of pulls should call progressMade at least once.
        p = self.StubProtocol()
        install_worker_progress_factory(p)
        b1 = self.make_branch('some-branch')
        b2 = self.make_branch('some-other-branch')
        b1.pull(b2)
        self.assertPositive(p.call_count)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
