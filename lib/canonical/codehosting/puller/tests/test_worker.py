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
    BadUrlFile, BadUrlLaunchpad, BadUrlSsh, BranchReferenceForbidden,
    BranchReferenceLoopError, MirroredURLChecker, PullerWorkerProtocol,
    URLChecker, get_canonical_url_for_branch_name, install_worker_ui_factory)
from canonical.launchpad.database import Branch
from canonical.launchpad.testing import LaunchpadObjectFactory
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



class TestURLCheckerCheckSource(unittest.TestCase):
    """Unit tests for `URLChecker.checkSource`."""

    class StubbedURLChecker(URLChecker):
        """URLChecker that provides canned answers."""

        def __init__(self, should_follow_references, references):
            self._should_follow_references = should_follow_references
            self._reference_values = {}
            for i in range(len(references) - 1):
                self._reference_values[references[i]] = references[i+1]
            self.follow_reference_calls = []

        def followReference(self, url):
            self.follow_reference_calls.append(url)
            return self._reference_values[url]

        def shouldFollowReferences(self):
            return self._should_follow_references

        def checkOneURL(self, url):
            pass

    def testNotReference(self):
        # checkSource does not raise if the source url does not point to a
        # branch reference, even if branch references are forbidden.
        references = ['file:///local/branch', None]
        checker = self.StubbedURLChecker(False, references)
        # This must not raise.
        checker.checkSource(references[0])
        self.assertEquals(references[:1], checker.follow_reference_calls)

    def testBranchReferenceForbidden(self):
        # checkSource raises BranchReferenceForbidden if branch references are
        # forbidden and the source URL points to a branch reference.
        references = ['file:///local/branch', 'http://example.com/branch']
        checker = self.StubbedURLChecker(False, references)
        self.assertRaises(
            BranchReferenceForbidden, checker.checkSource, references[0])
        self.assertEquals(references[:1], checker.follow_reference_calls)

    def testAllowedReference(self):
        # checkSource does not raise if following references is allowed and
        # the source URL points to a branch reference to a remote location.
        references = [
            'http://example.com/reference',
            'http://example.com/branch',
            None,
            ]
        checker = self.StubbedURLChecker(True, references)
        # This must not raise.
        checker.checkSource(references[0])
        self.assertEquals(references[:2], checker.follow_reference_calls)

    def testSelfReferencingBranch(self):
        # checkSource raises BranchReferenceLoopError if following references
        # is allowed and the source url points to a self-referencing branch
        # reference.
        references = [
            'http://example.com/reference',
            'http://example.com/reference',
            ]
        checker = self.StubbedURLChecker(True, references)
        self.assertRaises(
            BranchReferenceLoopError, checker.checkSource, references[0])
        self.assertEquals(references[:1], checker.follow_reference_calls)

    def testBranchReferenceLoop(self):
        # checkSource raises BranchReferenceLoopError if following references
        # is allowed and the source url points to a loop of branch references.
        references = [
            'http://example.com/reference-1',
            'http://example.com/reference-2',
            'http://example.com/reference-1',
            ]
        checker = self.StubbedURLChecker(True, references)
        self.assertRaises(
            BranchReferenceLoopError, checker.checkSource, references[0])
        self.assertEquals(references[:2], checker.follow_reference_calls)


class TestMirroredURLChecker(unittest.TestCase):
    """Tests specific to `MirroredURLChecker`."""

    def setUp(self):
        self.factory = LaunchpadObjectFactory()

    def testNoFileURL(self):
        checker = MirroredURLChecker()
        self.assertRaises(
            BadUrlFile, checker.checkOneURL,
            self.factory.getUniqueURL(scheme='file'))

    def testNoSSHURL(self):
        checker = MirroredURLChecker()
        self.assertRaises(
            BadUrlSsh, checker.checkOneURL,
            self.factory.getUniqueURL(scheme='bzr+ssh'))

    def testNoSftpURL(self):
        checker = MirroredURLChecker()
        self.assertRaises(
            BadUrlSsh, checker.checkOneURL,
            self.factory.getUniqueURL(scheme='sftp'))

    def testNoLaunchpadURL(self):
        checker = MirroredURLChecker()
        self.assertRaises(
            BadUrlLaunchpad, checker.checkOneURL,
            self.factory.getUniqueURL(host='bazaar.launchpad.dev'))


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
        # Empty the test output and error buffers.
        self.output.truncate(0)
        self.assertEqual('', self.output.getvalue())

    def test_nothingSentOnConstruction(self):
        # The protocol sends nothing until it receives an event.
        self.assertSentNetstrings([])

    def test_startMirror(self):
        # Calling startMirroring sends 'startMirroring' as a netstring.
        self.protocol.startMirroring(self.branch_to_mirror)
        self.assertSentNetstrings(['startMirroring', '0'])

    def test_mirrorSucceeded(self):
        # Calling 'mirrorSucceeded' sends the revno and 'mirrorSucceeded'.
        self.protocol.startMirroring(self.branch_to_mirror)
        self.resetBuffers()
        self.protocol.mirrorSucceeded(self.branch_to_mirror, 1234)
        self.assertSentNetstrings(['mirrorSucceeded', '1', '1234'])

    def test_mirrorFailed(self):
        # Calling 'mirrorFailed' sends the error message.
        self.protocol.startMirroring(self.branch_to_mirror)
        self.resetBuffers()
        self.protocol.mirrorFailed(
            self.branch_to_mirror, 'Error Message', 'OOPS')
        self.assertSentNetstrings(
            ['mirrorFailed', '2', 'Error Message', 'OOPS'])

    def test_progressMade(self):
        # Calling 'progressMade' sends an arbitrary string indicating
        # progress.
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
