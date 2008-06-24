# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Unit tests for worker.py."""

__metaclass__ = type

import os
import shutil
from StringIO import StringIO
import tempfile
import unittest

import bzrlib.branch
from bzrlib import bzrdir
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestCaseWithTransport
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)
from bzrlib.transport import get_transport

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
        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_tree.last_revision(), mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # Check that we can mirror an empty branch, and that the
        # last_mirrored_id for an empty branch can be distinguished from an
        # unmirrored branch.
        source_branch = self.make_branch('source-branch')
        to_mirror = self.makePullerWorker(source_branch.base)
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
        # Create a source branch in knit format, and check that the mirror is
        # in knit format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = \
            bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
        self._testMirrorFormat()

    def testMirrorMetaweaveAsMetaweave(self):
        # Create a source branch in metaweave format, and check that the
        # mirror is in metaweave format.
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
        self.repository_format = \
            bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
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


class TestCanTraverseReferences(unittest.TestCase, PullerWorkerMixin):
    """Unit tests for PullerWorker._canTraverseReferences."""

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
        self.assertRaises(
            AssertionError, remote_branch._canTraverseReferences)

    def testErrorForBogusType(self):
        """If the branch type is a bogus value, AssertionError is raised.
        """
        bogus_branch = self.makeBranch(None)
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


class TestWorkerProtocol(unittest.TestCase, PullerWorkerMixin):
    """Tests for the client-side implementation of the protocol used to
    communicate to the master process.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output = StringIO()
        self.protocol = PullerWorkerProtocol(self.output)
        self.branch_to_mirror = self.makePullerWorker()

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
