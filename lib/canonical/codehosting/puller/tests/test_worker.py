# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Unit tests for worker.py."""

__metaclass__ = type

from StringIO import StringIO
import unittest

import bzrlib.branch
from bzrlib.errors import NotBranchError
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestCaseInTempDir, TestCaseWithTransport
from bzrlib.transport import get_transport

from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.puller.tests import PullerWorkerMixin
from canonical.codehosting.puller.worker import (
    PullerWorker, BranchReferenceLoopError,
    BranchReferenceForbidden, BranchReferenceValueError,
    get_canonical_url_for_branch_name, install_worker_ui_factory,
    PullerWorkerProtocol)
from canonical.launchpad.database import Branch
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp import canonical_url
from canonical.testing import LaunchpadScriptLayer, reset_logging


class TestPullerWorker(TestCaseWithTransport, PullerWorkerMixin):
    """Test the mirroring functionality of PullerWorker."""

    def testMirrorActuallyMirrors(self):
        # Check that mirror() will mirror the Bazaar branch.
        source_tree = self.make_branch_and_tree('source-branch')
        to_mirror = self.makePullerWorker(source_tree.branch.base)
        source_tree.commit('commit message')
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_tree.last_revision(), mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # We can mirror an empty branch.
        source_branch = self.make_branch('source-branch')
        to_mirror = self.makePullerWorker(source_branch.base)
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(NULL_REVISION, mirrored_branch.last_revision())

    def testCanMirrorWhenDestDirExists(self):
        # We can mirror a branch even if the destination exists, and contains
        # data but is not a branch.
        source_tree = self.make_branch_and_tree('source-branch')
        to_mirror = self.makePullerWorker(source_tree.branch.base)
        source_tree.commit('commit message')
        # Make the directory.
        dest = get_transport(to_mirror.dest)
        ensure_base(dest)
        dest.mkdir('.bzr')
        # 'dest' is not a branch.
        self.assertRaises(
            NotBranchError, bzrlib.branch.Branch.open, to_mirror.dest)
        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_tree.last_revision(), mirrored_branch.last_revision())

    def testHttpTransportStillThere(self):
        # We tweak the http:// transport in the worker. Make sure that it's
        # still available after mirroring.
        http = get_transport('http://example.com')
        source_branch = self.make_branch('source-branch')
        to_mirror = self.makePullerWorker(source_branch.base)
        to_mirror.mirror()
        new_http = get_transport('http://example.com')
        self.assertEqual(get_transport('http://example.com').base, http.base)
        self.assertEqual(new_http.__class__, http.__class__)


class TestCanTraverseReferences(TestCaseInTempDir, PullerWorkerMixin):
    """Unit tests for PullerWorker._canTraverseReferences."""

    def testTrueForMirrored(self):
        """We can traverse branch references when pulling mirror branches."""
        mirror_branch = self.makePullerWorker(branch_type=BranchType.MIRRORED)
        self.assertEqual(mirror_branch._canTraverseReferences(), True)

    def testFalseForImported(self):
        """We cannot traverse branch references when pulling import branches.
        """
        import_branch = self.makePullerWorker(branch_type=BranchType.IMPORTED)
        self.assertEqual(import_branch._canTraverseReferences(), False)

    def testFalseForHosted(self):
        """We cannot traverse branch references when pulling hosted branches.
        """
        hosted_branch = self.makePullerWorker(branch_type=BranchType.HOSTED)
        self.assertEqual(hosted_branch._canTraverseReferences(), False)

    def testErrorForOtherRemote(self):
        """We do not pull REMOTE branches. If the branch type is REMOTE, an
        AssertionError is raised.
        """
        remote_branch = self.makePullerWorker(branch_type=BranchType.REMOTE)
        self.assertRaises(
            AssertionError, remote_branch._canTraverseReferences)

    def testErrorForBogusType(self):
        """If the branch type is a bogus value, AssertionError is raised.
        """
        bogus_branch = self.makePullerWorker(branch_type=None)
        self.assertRaises(
            AssertionError, bogus_branch._canTraverseReferences)


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

        Branch references can point to other branch references, forming a
        chain of locations. If the chain ends in a real branch, then the last
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
        references = ['file:///local/branch', None]
        self.setUpReferences(references)
        self.branch._checkBranchReference(references[0]) # This must not raise.
        self.assertGetBranchReferenceCallsEqual(references[:1])

    def testBranchReferenceForbidden(self):
        """_checkBranchReference raises BranchReferenceForbidden if
        _canTraverseReferences is false and the source url points to a branch
        reference.
        """
        self.can_traverse_references = False
        references = ['file:///local/branch', 'http://example.com/branch']
        self.setUpReferences(references)
        self.assertRaises(
            BranchReferenceForbidden, self.branch._checkBranchReference,
            references[0])
        self.assertGetBranchReferenceCallsEqual(references[:1])

    def testAllowedReference(self):
        """_checkBranchReference does not raise if _canTraverseReferences is
        true and the source URL points to a branch reference to a remote
        location.
        """
        self.can_traverse_references = True
        references = [
            'http://example.com/reference',
            'http://example.com/branch',
            None,
            ]
        self.setUpReferences(references)
        self.branch._checkBranchReference(references[0]) # This must not raise.
        self.assertGetBranchReferenceCallsEqual(references[:2])

    def testFileReference(self):
        """_checkBranchReference raises BranchReferenceValueError if
        _canTraverseReferences is true and the source url points to a 'file'
        branch reference.
        """
        self.can_traverse_references = True
        references = [
            'http://example.com/reference',
            'file://local/branch',
            ]
        self.setUpReferences(references)
        self.assertRaises(
            BranchReferenceValueError, self.branch._checkBranchReference,
            references[0])
        self.assertGetBranchReferenceCallsEqual(references[:1])

    def testSelfReferencingBranch(self):
        """_checkBranchReference raises BranchReferenceLoopError if
        _canTraverseReferences is true and the source url points to a
        self-referencing branch."""
        self.can_traverse_references = True
        references = [
            'http://example.com/reference',
            'http://example.com/reference',
            ]
        self.setUpReferences(references)
        self.assertRaises(
            BranchReferenceLoopError, self.branch._checkBranchReference,
            references[0])
        self.assertGetBranchReferenceCallsEqual(references[:1])

    def testBranchReferenceLoop(self):
        """_checkBranchReference raises BranchReferenceLoopError if
        _canTraverseReferences is true and the source url points to a loop of
        branch references."""
        self.can_traverse_references = True
        references = [
            'http://example.com/reference-1',
            'http://example.com/reference-2',
            'http://example.com/reference-1',
            ]
        self.setUpReferences(references)
        self.assertRaises(
            BranchReferenceLoopError, self.branch._checkBranchReference,
            references[0])
        self.assertGetBranchReferenceCallsEqual([
            'http://example.com/reference-1',
            'http://example.com/reference-2'])


class TestWorkerProtocol(TestCaseInTempDir, PullerWorkerMixin):
    """Tests for the client-side implementation of the protocol used to
    communicate to the master process.
    """

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.output = StringIO()
        self.protocol = PullerWorkerProtocol(self.output)
        self.branch_to_mirror = self.makePullerWorker()

    def assertSentNetstrings(self, expected_netstrings):
        """Assert that the protocol sent the given netstrings (in order)."""
        observed_netstrings = self.getNetstrings(self.output.getvalue())
        self.assertEqual(expected_netstrings, observed_netstrings)

    def getNetstrings(self, line):
        """Parse `line` as a sequence of netstrings.

        :return: A list of strings.
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
        # sample data. This is an invariant of the test, so use a plain
        # assert.
        unique_name = 'name12/gnome-terminal/main'
        assert branch.unique_name == '~' + unique_name
        # Now check that our implementation of canonical_url is consistent
        # with the canonical one.
        self.assertEqual(
            canonical_url(branch),
            get_canonical_url_for_branch_name(unique_name))


class TestWorkerProgressReporting(TestCaseWithTransport):
    """Tests for the WorkerProgressBar progress reporting mechanism."""

    class StubProtocol:
        """A stub for PullerWorkerProtocol that just defines progressMade."""
        def __init__(self):
            self.call_count = 0
        def progressMade(self):
            self.call_count += 1

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self.saved_factory = bzrlib.ui.ui_factory

    def tearDown(self):
        TestCaseWithTransport.tearDown(self)
        bzrlib.ui.ui_factory = self.saved_factory
        reset_logging()

    def test_simple(self):
        # Even the simplest of pulls should call progressMade at least once.
        p = self.StubProtocol()
        install_worker_ui_factory(p)
        b1 = self.make_branch('some-branch')
        b2_tree = self.make_branch_and_tree('some-other-branch')
        b2 = b2_tree.branch
        b2_tree.commit('rev1', allow_pointless=True)
        b1.pull(b2)
        self.assertPositive(p.call_count)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
