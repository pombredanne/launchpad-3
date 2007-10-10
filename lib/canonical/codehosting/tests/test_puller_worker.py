# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for branchtomirror.py."""

__metaclass__ = type

import httplib
import logging
import os
import shutil
import socket
import tempfile
import unittest
import urllib2

import bzrlib.branch
from bzrlib import bzrdir
from bzrlib.branch import BranchReferenceFormat
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestCaseInTempDir, TestCaseWithTransport
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)
from bzrlib.transport import get_transport
from bzrlib.weave import Weave
from bzrlib.errors import (
    BzrError, UnsupportedFormatError, UnknownFormatError, ParamikoNotPresent,
    NotBranchError)

import transaction
from canonical.launchpad import database
from canonical.launchpad.database import Branch
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts.supermirror_rewritemap import split_branch_id
from canonical.launchpad.webapp import canonical_url
from canonical.codehosting.tests.helpers import create_branch
from canonical.codehosting.puller.branchtomirror import (
    BranchToMirror, BadUrlSsh, BadUrlLaunchpad, BranchReferenceLoopError,
    BranchReferenceForbidden, BranchReferenceValueError)
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.testing import LaunchpadFunctionalLayer, reset_logging
from canonical.testing import LaunchpadZopelessLayer


class StubbedBranchStatusClient(BranchStatusClient):
    """Partially stubbed subclass of BranchStatusClient, for unit tests."""

    def startMirroring(self, branch_id):
        pass


class StubbedBranchToMirror(BranchToMirror):
    """Partially stubbed subclass of BranchToMirror, for unit tests."""

    enable_checkBranchReference = False
    enable_checkSourceUrl = True

    def _checkSourceUrl(self):
        if self.enable_checkSourceUrl:
            BranchToMirror._checkSourceUrl(self)

    def _checkBranchReference(self):
        if self.enable_checkBranchReference:
            BranchToMirror._checkBranchReference(self)

    def _openSourceBranch(self):
        self.testcase.open_call_count += 1

    def _mirrorToDestBranch(self):
        pass

    def _mirrorSuccessful(self, logger):
        pass

    def _mirrorFailed(self, logger, error_msg):
        self.testcase.errors.append(error_msg)


class ErrorHandlingTestCase(unittest.TestCase):
    """Base class to test BranchToMirror error reporting."""

    def setUp(self):
        unittest.TestCase.setUp(self)
        self._errorHandlingSetUp()

    def _errorHandlingSetUp(self):
        """Setup code that is specific to ErrorHandlingTestCase.

        This is needed because TestReferenceMirroring uses a diamond-shaped
        class hierarchy and we do not want to end up calling unittest.TestCase
        twice.
        """
        client = StubbedBranchStatusClient()
        self.branch = StubbedBranchToMirror(
            src='foo', dest='bar', branch_status_client=client, branch_id=1,
            unique_name='owner/product/foo', branch_type=None)
        self.errors = []
        self.open_call_count = 0
        self.branch.testcase = self
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        self._errorHandlingTearDown()
        unittest.TestCase.tearDown(self)

    def _errorHandlingTearDown(self):
        """Teardown code that is specific to ErrorHandlingTestCase."""
        reset_logging()

    def runMirrorAndGetError(self):
        """Run mirror, check that we receive exactly one error, and return its
        str().
        """
        self.branch.mirror(logging.getLogger())
        self.assertEqual(len(self.errors), 1)
        error = str(self.errors[0])
        self.errors = []
        return error

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


class TestBranchToMirror(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        shutil.rmtree(self.testdir)
        self.authserver.tearDown()

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testMirror(self):
        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        client = BranchStatusClient()
        to_mirror = BranchToMirror(
            srcbranchdir, destbranchdir, client, branch_id=1, unique_name=None,
            branch_type=None)
        tree = create_branch(srcbranchdir)
        to_mirror.mirror(logging.getLogger())
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(tree.last_revision(),
                         mirrored_branch.last_revision())

        # make sure that the last mirrored revision is recorded
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(branch.last_mirrored_id,
                         mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # Check that we can mirror an empty branch, and that the
        # last_mirrored_id for an empty branch can be distinguished
        # from an unmirrored branch.

        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        client = BranchStatusClient()
        to_mirror = BranchToMirror(
            srcbranchdir, destbranchdir, client, branch_id=1, unique_name=None,
            branch_type=None)

        # create empty source branch
        os.makedirs(srcbranchdir)
        tree = bzrdir.BzrDir.create_standalone_workingtree(srcbranchdir)

        to_mirror.mirror(logging.getLogger())
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(NULL_REVISION, mirrored_branch.last_revision())

        # make sure that the last mirrored revision is recorded as a string
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertNotEqual(None, branch.last_mirrored_id)
        self.assertEqual(NULL_REVISION, branch.last_mirrored_id)


class TestBranchToMirrorFormats(TestCaseWithRepository):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBranchToMirrorFormats, self).setUp()
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        self.authserver.tearDown()
        super(TestBranchToMirrorFormats, self).tearDown()

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
        client = BranchStatusClient()
        source_url = os.path.abspath('src-branch')
        to_mirror = BranchToMirror(
            source_url, 'dest-branch', client, branch_id=1, unique_name=None,
            branch_type=None)
        to_mirror.mirror(logging.getLogger())
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


class TestBranchToMirror_SourceProblems(TestCaseInTempDir):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        self.authserver.tearDown()
        TestCaseInTempDir.tearDown(self)

    def testUnopenableSourceDoesNotCreateMirror(self):
        non_existent_source = os.path.abspath('nonsensedir')
        dest_dir = 'dest-dir'
        client = BranchStatusClient()
        mybranch = BranchToMirror(
            non_existent_source, dest_dir, client, branch_id=1,
            unique_name='foo/bar/baz', branch_type=None)
        mybranch.mirror(logging.getLogger())
        self.failIf(os.path.exists(dest_dir), 'dest-dir should not exist')

    def testMissingSourceWhines(self):
        non_existent_source = os.path.abspath('nonsensedir')
        client = BranchStatusClient()
        # ensure that we have no errors muddying up the test
        client.mirrorComplete(1, NULL_REVISION)
        mybranch = BranchToMirror(
            non_existent_source, "non-existent-destination",
            client, branch_id=1, unique_name='foo/bar/baz', branch_type=None)
        mybranch.mirror(logging.getLogger())
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(1, branch.mirror_failures)

    def testMissingFileRevisionData(self):
        self.build_tree(['missingrevision/',
                         'missingrevision/afile'])
        tree = bzrdir.BzrDir.create_standalone_workingtree(
            'missingrevision')
        tree.add(['afile'], ['myid'])
        tree.commit('start')
        # now we have a good branch with a file called afile and id myid we
        # need to figure out the actual path for the weave.. or deliberately
        # corrupt it. like this.

        # XXX: JonathanLange 2007-10-11: _put_weave is an internal function
        # that we probably shouldn't be using. TODO: Ask author of this test
        # to better explain which particular repository corruption we are
        # trying to reproduce here.
        tree.branch.repository.weave_store._put_weave(
            "myid", Weave(weave_name="myid"),
            tree.branch.repository.get_transaction())
        # now try mirroring this branch.
        client = BranchStatusClient()
        # clear the error status
        client.mirrorComplete(1, NULL_REVISION)
        source_url = os.path.abspath('missingrevision')
        mybranch = BranchToMirror(
            source_url, "non-existent-destination", client, branch_id=1,
            unique_name='foo/bar/baz', branch_type=None)
        mybranch.mirror(logging.getLogger())
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(1, branch.mirror_failures)


class TestBadUrl(ErrorHandlingTestCase):
    """Test that BranchToMirror does not try mirroring from bad URLs.

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
        # errorHandlingTearDown must be called after
        # TestCaseWithTransport.tearDown otherwise the latter fails
        # when trying to uninstall its log handlers.
        ErrorHandlingTestCase._errorHandlingTearDown(self)

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
        """BranchToMirror._getBranchReference gives the reference value for
        a branch reference.
        """
        reference_value = 'http://example.com/branch'
        reference_url = self.createBranchReference(reference_value)
        self.branch.source = reference_url
        self.assertEqual(
            self.branch._getBranchReference(reference_url), reference_value)

    def testGetBranchReferenceNone(self):
        """BranchToMirror._getBranchReference gives None for a normal branch.
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


class TestCanTraverseReferences(unittest.TestCase):
    """Unit tests for BranchToMirror._canTraverseReferences."""

    def setUp(self):
        self.client = BranchStatusClient()

    def makeBranch(self, branch_type):
        """Helper to create a BranchToMirror with a specified branch_type."""
        return BranchToMirror(
            src='foo', dest='bar', branch_status_client=self.client,
            branch_id=1, unique_name='owner/product/foo',
            branch_type=branch_type)

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
    """Unit tests for BranchToMirror._checkBranchReference."""

    class StubbedBranchToMirror(BranchToMirror):
        """Partially stubbed BranchToMirror."""

        def _getBranchReference(self, url):
            self.testcase.get_branch_reference_calls.append(url)
            return self.testcase.reference_values[url]

        def _canTraverseReferences(self):
            assert self.testcase.can_traverse_references is not None
            return self.testcase.can_traverse_references

    def setUp(self):
        client = BranchStatusClient()
        self.branch = TestCheckBranchReference.StubbedBranchToMirror(
            'foo', 'bar', client, 1, 'owner/product/foo', None)
        self.branch.testcase = self
        self.get_branch_reference_calls = []
        self.reference_values = {}
        self.can_traverse_references = None

    def setUpReferences(self, locations):
        """Set up the stubbed BranchToMirror to model a chain of references.

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
        split_id = split_branch_id(self.branch.branch_id)
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

    def testBzrErrorHandling(self):
        def stubOpenSourceBranch():
            raise BzrError('A generic bzr error')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A generic bzr error'
        self.runMirrorAndAssertErrorEquals(expected_msg)


class TestCanonicalUrl(unittest.TestCase):
    """Test cases for rendering the canonical url of a branch."""

    layer = LaunchpadZopelessLayer

    def testCanonicalUrlConsistent(self):
        # BranchToMirror._canonical_url is consistent with
        # webapp.canonical_url, if the provided unique_name is correct.
        branch = Branch.get(15)
        # Check that the unique_name used in this test is consistent with the
        # sample data. This is an invariant of the test, so use a plain assert.
        unique_name = 'name12/gnome-terminal/main'
        assert branch.unique_name == '~' + unique_name
        branch_to_mirror = BranchToMirror(
            src=None, dest=None, branch_status_client=None,
            branch_id=None, unique_name=unique_name, branch_type=None)
        # Now check that our implementation of canonical_url is consistent with
        # the canonical one.
        self.assertEqual(
            branch_to_mirror._canonical_url(), canonical_url(branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
