# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0231

"""Unit tests for worker.py."""

__metaclass__ = type

import gc
from StringIO import StringIO
import unittest

import bzrlib.branch
from bzrlib.branch import (
    BranchReferenceFormat,
    BzrBranchFormat7,
    )
from bzrlib.bzrdir import (
    BzrDir,
    BzrDirMetaFormat1,
    )
from bzrlib.errors import (
    IncompatibleRepositories,
    NotBranchError,
    NotStacked,
    )
from bzrlib.repofmt.pack_repo import RepositoryFormatKnitPack1
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import (
    TestCaseInTempDir,
    TestCaseWithTransport,
    )
from bzrlib.transport import get_transport

from lp.code.enums import BranchType
from lp.codehosting.puller.tests import (
    AcceptAnythingPolicy,
    BlacklistPolicy,
    FixedHttpServer,
    PullerWorkerMixin,
    WhitelistPolicy,
    )
from lp.codehosting.puller.worker import (
    BranchLoopError,
    BranchMirrorer,
    BranchReferenceForbidden,
    install_worker_ui_factory,
    PullerWorkerProtocol,
    WORKER_ACTIVITY_NETWORK,
    )
from lp.codehosting.vfs.branchfs import (
    BadUrl,
    BadUrlLaunchpad,
    BadUrlScheme,
    BadUrlSsh,
    BranchPolicy,
    ImportedBranchPolicy,
    MirroredBranchPolicy,
    )
from lp.testing import TestCase
from lp.testing.factory import (
    LaunchpadObjectFactory,
    ObjectFactory,
    )


def get_netstrings(line):
    """Parse `line` as a sequence of netstrings.

    :return: A list of strings.
    """
    strings = []
    while len(line) > 0:
        colon_index = line.find(':')
        length = int(line[:colon_index])
        strings.append(line[colon_index+1:colon_index+1+length])
        assert ',' == line[colon_index+1+length], (
            'Expected %r == %r' % (',', line[colon_index+1+length]))
        line = line[colon_index+length+2:]
    return strings


class PrearrangedStackedBranchPolicy(AcceptAnythingPolicy):
    """A branch policy that returns a pre-configurable stack-on URL."""

    def __init__(self, stack_on_url):
        AcceptAnythingPolicy.__init__(self)
        self.stack_on_url = stack_on_url

    def getStackedOnURLForDestinationBranch(self, source_branch,
                                            destination_url):
        return self.stack_on_url


class TestPullerWorker(TestCaseWithTransport, PullerWorkerMixin):
    """Test the mirroring functionality of PullerWorker."""

    def test_mirror_opener_with_stacked_on_url(self):
        # A PullerWorker for a mirrored branch gets a MirroredBranchPolicy as
        # the policy of its branch_mirrorer. The default stacked-on URL is
        # passed through.
        url = '/~foo/bar/baz'
        worker = self.makePullerWorker(
            branch_type=BranchType.MIRRORED, default_stacked_on_url=url)
        policy = worker.branch_mirrorer.policy
        self.assertIsInstance(policy, MirroredBranchPolicy)
        self.assertEqual(url, policy.stacked_on_url)

    def test_mirror_opener_without_stacked_on_url(self):
        # A PullerWorker for a mirrored branch get a MirroredBranchPolicy as
        # the policy of its mirrorer. If a default stacked-on URL is not
        # specified (indicated by an empty string), then the stacked_on_url is
        # None.
        worker = self.makePullerWorker(
            branch_type=BranchType.MIRRORED, default_stacked_on_url='')
        policy = worker.branch_mirrorer.policy
        self.assertIsInstance(policy, MirroredBranchPolicy)
        self.assertIs(None, policy.stacked_on_url)

    def testImportedOpener(self):
        # A PullerWorker for an imported branch gets a ImportedBranchPolicy as
        # the policy of its branch_mirrorer.
        worker = self.makePullerWorker(branch_type=BranchType.IMPORTED)
        self.assertIsInstance(
            worker.branch_mirrorer.policy, ImportedBranchPolicy)

    def testMirrorActuallyMirrors(self):
        # Check that mirror() will mirror the Bazaar branch.
        source_tree = self.make_branch_and_tree('source-branch')
        to_mirror = self.makePullerWorker(
            source_tree.branch.base, self.get_url('dest'))
        source_tree.commit('commit message')
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_tree.last_revision(), mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # We can mirror an empty branch.
        source_branch = self.make_branch('source-branch')
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('dest'))
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(NULL_REVISION, mirrored_branch.last_revision())

    def testCanMirrorWhenDestDirExists(self):
        # We can mirror a branch even if the destination exists, and contains
        # data but is not a branch.
        source_tree = self.make_branch_and_tree('source-branch')
        to_mirror = self.makePullerWorker(
            source_tree.branch.base, self.get_url('destdir'))
        source_tree.commit('commit message')
        # Make the directory.
        dest = get_transport(to_mirror.dest)
        dest.create_prefix()
        dest.mkdir('.bzr')
        # 'dest' is not a branch.
        self.assertRaises(
            NotBranchError, bzrlib.branch.Branch.open, to_mirror.dest)
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_tree.last_revision(), mirrored_branch.last_revision())

    def testHttpTransportStillThere(self):
        # We tweak the http:// transport in the worker. Make sure that it's
        # still available after mirroring.
        http = get_transport('http://example.com')
        source_branch = self.make_branch('source-branch')
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('destdir'))
        to_mirror.mirrorWithoutChecks()
        new_http = get_transport('http://example.com')
        self.assertEqual(get_transport('http://example.com').base, http.base)
        self.assertEqual(new_http.__class__, http.__class__)

    def test_defaultStackedOnBranchDoesNotForceStacking(self):
        # If the policy supplies a stacked on URL but the source branch does
        # not support stacking, the destination branch does not support
        # stacking.
        stack_on = self.make_branch('default-stack-on')
        source_branch = self.make_branch('source-branch', format='pack-0.92')
        self.assertFalse(source_branch._format.supports_stacking())
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('destdir'),
            policy=PrearrangedStackedBranchPolicy(stack_on.base))
        to_mirror.mirrorWithoutChecks()
        dest = bzrlib.branch.Branch.open(self.get_url('destdir'))
        self.assertFalse(dest._format.supports_stacking())

    def test_defaultStackedOnBranchIncompatibleMirrorsOK(self):
        # If the policy supplies a stacked on URL for a branch which is
        # incompatible with the branch we're mirroring, the mirroring
        # completes successfully and the destination branch is not stacked.
        stack_on = self.make_branch('default-stack-on', format='2a')
        source_branch = self.make_branch('source-branch', format='1.9')
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('destdir'),
            policy=PrearrangedStackedBranchPolicy(stack_on.base))
        to_mirror.mirrorWithoutChecks()
        dest = bzrlib.branch.Branch.open(self.get_url('destdir'))
        self.assertRaises(NotStacked, dest.get_stacked_on_url)

    def testCanMirrorWithIncompatibleRepos(self):
        # If the destination branch cannot be opened because its repository is
        # not compatible with that of the branch it is stacked on, we delete
        # the destination branch and start again.
        self.get_transport('dest').ensure_base()
        # Make a branch to stack on in 1.6 format
        self.make_branch('dest/stacked-on', format='1.6')
        # Make a branch stacked on this.
        stacked_branch = self.make_branch('dest/stacked', format='1.6')
        stacked_branch.set_stacked_on_url(self.get_url('dest/stacked-on'))
        # Delete the stacked-on branch and replace it with a 2a format branch.
        self.get_transport('dest').delete_tree('stacked-on')
        self.make_branch('dest/stacked-on', format='2a')
        # Check our setup: trying to open the stacked branch raises
        # IncompatibleRepositories.
        self.assertRaises(
            IncompatibleRepositories,
            bzrlib.branch.Branch.open, 'dest/stacked')
        source_branch = self.make_branch(
            'source-branch', format='2a')
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('dest/stacked'))
        # The branch can be mirrored without errors and the destionation
        # location is upgraded to match the source format.
        to_mirror.mirrorWithoutChecks()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(
            source_branch.repository._format,
            mirrored_branch.repository._format)

    def getStackedOnUrlFromNetStringOutput(self, netstring_output):
        netstrings = get_netstrings(netstring_output)
        branchChanged_index = netstrings.index('branchChanged')
        return netstrings[branchChanged_index + 2]

    def testSendsStackedInfo(self):
        # When the puller worker stacks a branch, it reports the stacked on
        # URL to the master.
        base_branch = self.make_branch('base_branch', format='1.9')
        stacked_branch = self.make_branch('stacked-branch', format='1.9')
        protocol_output = StringIO()
        to_mirror = self.makePullerWorker(
            stacked_branch.base, self.get_url('destdir'),
            protocol=PullerWorkerProtocol(protocol_output),
            policy=PrearrangedStackedBranchPolicy(base_branch.base))
        to_mirror.mirror()
        stacked_on_url = self.getStackedOnUrlFromNetStringOutput(
            protocol_output.getvalue())
        self.assertEqual(base_branch.base, stacked_on_url)

    def testDoesntSendStackedInfoUnstackableFormat(self):
        # Mirroring an unstackable branch sends '' as the stacked-on location
        # to the master.
        source_branch = self.make_branch('source-branch', format='pack-0.92')
        protocol_output = StringIO()
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('destdir'),
            protocol=PullerWorkerProtocol(protocol_output))
        to_mirror.mirror()
        stacked_on_url = self.getStackedOnUrlFromNetStringOutput(
            protocol_output.getvalue())
        self.assertEqual('', stacked_on_url)

    def testDoesntSendStackedInfoNotStacked(self):
        # Mirroring a non-stacked branch sends '' as the stacked-on location
        # to the master.
        source_branch = self.make_branch('source-branch', format='1.9')
        protocol_output = StringIO()
        to_mirror = self.makePullerWorker(
            source_branch.base, self.get_url('destdir'),
            protocol=PullerWorkerProtocol(protocol_output))
        to_mirror.mirror()
        stacked_on_url = self.getStackedOnUrlFromNetStringOutput(
            protocol_output.getvalue())
        self.assertEqual('', stacked_on_url)


class TestBranchMirrorerCheckAndFollowBranchReference(TestCase):
    """Unit tests for `BranchMirrorer.checkAndFollowBranchReference`."""

    class StubbedBranchMirrorer(BranchMirrorer):
        """BranchMirrorer that provides canned answers.

        We implement the methods we need to to be able to control all the
        inputs to the `BranchMirrorer.checkSource` method, which is what is
        being tested in this class.
        """

        def __init__(self, references, policy):
            parent_cls = TestBranchMirrorerCheckAndFollowBranchReference
            super(parent_cls.StubbedBranchMirrorer, self).__init__(policy)
            self._reference_values = {}
            for i in range(len(references) - 1):
                self._reference_values[references[i]] = references[i+1]
            self.follow_reference_calls = []

        def followReference(self, url):
            self.follow_reference_calls.append(url)
            return self._reference_values[url]

    def makeBranchMirrorer(self, should_follow_references, references,
                         unsafe_urls=None):
        policy = BlacklistPolicy(should_follow_references, unsafe_urls)
        opener = self.StubbedBranchMirrorer(references, policy)
        return opener

    def testCheckInitialURL(self):
        # checkSource rejects all URLs that are not allowed.
        opener = self.makeBranchMirrorer(None, [], set(['a']))
        self.assertRaises(BadUrl, opener.checkAndFollowBranchReference, 'a')

    def testNotReference(self):
        # When branch references are forbidden, checkAndFollowBranchReference
        # does not raise on non-references.
        opener = self.makeBranchMirrorer(False, ['a', None])
        self.assertEquals('a', opener.checkAndFollowBranchReference('a'))
        self.assertEquals(['a'], opener.follow_reference_calls)

    def testBranchReferenceForbidden(self):
        # checkAndFollowBranchReference raises BranchReferenceForbidden if
        # branch references are forbidden and the source URL points to a
        # branch reference.
        opener = self.makeBranchMirrorer(False, ['a', 'b'])
        self.assertRaises(
            BranchReferenceForbidden,
            opener.checkAndFollowBranchReference, 'a')
        self.assertEquals(['a'], opener.follow_reference_calls)

    def testAllowedReference(self):
        # checkAndFollowBranchReference does not raise if following references
        # is allowed and the source URL points to a branch reference to a
        # permitted location.
        opener = self.makeBranchMirrorer(True, ['a', 'b', None])
        self.assertEquals('b', opener.checkAndFollowBranchReference('a'))
        self.assertEquals(['a', 'b'], opener.follow_reference_calls)

    def testCheckReferencedURLs(self):
        # checkAndFollowBranchReference checks if the URL a reference points
        # to is safe.
        opener = self.makeBranchMirrorer(
            True, ['a', 'b', None], unsafe_urls=set('b'))
        self.assertRaises(BadUrl, opener.checkAndFollowBranchReference, 'a')
        self.assertEquals(['a'], opener.follow_reference_calls)

    def testSelfReferencingBranch(self):
        # checkAndFollowBranchReference raises BranchReferenceLoopError if
        # following references is allowed and the source url points to a
        # self-referencing branch reference.
        opener = self.makeBranchMirrorer(True, ['a', 'a'])
        self.assertRaises(
            BranchLoopError, opener.checkAndFollowBranchReference, 'a')
        self.assertEquals(['a'], opener.follow_reference_calls)

    def testBranchReferenceLoop(self):
        # checkAndFollowBranchReference raises BranchReferenceLoopError if
        # following references is allowed and the source url points to a loop
        # of branch references.
        references = ['a', 'b', 'a']
        opener = self.makeBranchMirrorer(True, references)
        self.assertRaises(
            BranchLoopError, opener.checkAndFollowBranchReference, 'a')
        self.assertEquals(['a', 'b'], opener.follow_reference_calls)


class TestBranchMirrorerStacking(TestCaseWithTransport):

    def makeBranchMirrorer(self, allowed_urls):
        policy = WhitelistPolicy(True, allowed_urls, True)
        return BranchMirrorer(policy)

    def makeBranch(self, path, branch_format, repository_format):
        """Make a Bazaar branch at 'path' with the given formats."""
        bzrdir_format = BzrDirMetaFormat1()
        bzrdir_format.set_branch_format(branch_format)
        bzrdir = self.make_bzrdir(path, format=bzrdir_format)
        repository_format.initialize(bzrdir)
        return bzrdir.create_branch()

    def testAllowedURL(self):
        # checkSource does not raise an exception for branches stacked on
        # branches with allowed URLs.
        stacked_on_branch = self.make_branch('base-branch', format='1.6')
        stacked_branch = self.make_branch('stacked-branch', format='1.6')
        stacked_branch.set_stacked_on_url(stacked_on_branch.base)
        opener = self.makeBranchMirrorer(
            [stacked_branch.base, stacked_on_branch.base])
        # This doesn't raise an exception.
        opener.open(stacked_branch.base)

    def testUnstackableRepository(self):
        # checkSource treats branches with UnstackableRepositoryFormats as
        # being not stacked.
        branch = self.makeBranch(
            'unstacked', BzrBranchFormat7(), RepositoryFormatKnitPack1())
        opener = self.makeBranchMirrorer([branch.base])
        # This doesn't raise an exception.
        opener.open(branch.base)

    def testAllowedRelativeURL(self):
        # checkSource passes on absolute urls to checkOneURL, even if the
        # value of stacked_on_location in the config is set to a relative URL.
        stacked_on_branch = self.make_branch('base-branch', format='1.6')
        stacked_branch = self.make_branch('stacked-branch', format='1.6')
        stacked_branch.set_stacked_on_url('../base-branch')
        opener = self.makeBranchMirrorer(
            [stacked_branch.base, stacked_on_branch.base])
        # Note that stacked_on_branch.base is not '../base-branch', it's an
        # absolute URL.
        self.assertNotEqual('../base-branch', stacked_on_branch.base)
        # This doesn't raise an exception.
        opener.open(stacked_branch.base)

    def testAllowedRelativeNested(self):
        # Relative URLs are resolved relative to the stacked branch.
        self.get_transport().mkdir('subdir')
        a = self.make_branch('subdir/a', format='1.6')
        b = self.make_branch('b', format='1.6')
        b.set_stacked_on_url('../subdir/a')
        c = self.make_branch('subdir/c', format='1.6')
        c.set_stacked_on_url('../../b')
        opener = self.makeBranchMirrorer([c.base, b.base, a.base])
        # This doesn't raise an exception.
        opener.open(c.base)

    def testForbiddenURL(self):
        # checkSource raises a BadUrl exception if a branch is stacked on a
        # branch with a forbidden URL.
        stacked_on_branch = self.make_branch('base-branch', format='1.6')
        stacked_branch = self.make_branch('stacked-branch', format='1.6')
        stacked_branch.set_stacked_on_url(stacked_on_branch.base)
        opener = self.makeBranchMirrorer([stacked_branch.base])
        self.assertRaises(BadUrl, opener.open, stacked_branch.base)

    def testForbiddenURLNested(self):
        # checkSource raises a BadUrl exception if a branch is stacked on a
        # branch that is in turn stacked on a branch with a forbidden URL.
        a = self.make_branch('a', format='1.6')
        b = self.make_branch('b', format='1.6')
        b.set_stacked_on_url(a.base)
        c = self.make_branch('c', format='1.6')
        c.set_stacked_on_url(b.base)
        opener = self.makeBranchMirrorer([c.base, b.base])
        self.assertRaises(BadUrl, opener.open, c.base)

    def testSelfStackedBranch(self):
        # checkSource raises StackingLoopError if a branch is stacked on
        # itself. This avoids infinite recursion errors.
        a = self.make_branch('a', format='1.6')
        # Bazaar 1.17 and up make it harder to create branches like this.
        # It's still worth testing that we don't blow up in the face of them,
        # so we grovel around a bit to create one anyway.
        a.get_config().set_user_option('stacked_on_location', a.base)
        opener = self.makeBranchMirrorer([a.base])
        self.assertRaises(BranchLoopError, opener.open, a.base)

    def testLoopStackedBranch(self):
        # checkSource raises StackingLoopError if a branch is stacked in such
        # a way so that it is ultimately stacked on itself. e.g. a stacked on
        # b stacked on a.
        a = self.make_branch('a', format='1.6')
        b = self.make_branch('b', format='1.6')
        a.set_stacked_on_url(b.base)
        b.set_stacked_on_url(a.base)
        opener = self.makeBranchMirrorer([a.base, b.base])
        self.assertRaises(BranchLoopError, opener.open, a.base)
        self.assertRaises(BranchLoopError, opener.open, b.base)


class TestReferenceMirroring(TestCaseWithTransport):
    """Feature tests for mirroring of branch references."""

    def createBranchReference(self, url):
        """Create a pure branch reference that points to the specified URL.

        :param url: target of the branch reference.
        :return: file url to the created pure branch reference.
        """
        # XXX DavidAllouche 2007-09-12 bug=139109:
        # We do this manually because the bzrlib API does not support creating
        # a branch reference without opening it.
        t = get_transport(self.get_url('.'))
        t.mkdir('reference')
        a_bzrdir = BzrDir.create(self.get_url('reference'))
        branch_reference_format = BranchReferenceFormat()
        branch_transport = a_bzrdir.get_branch_transport(
            branch_reference_format)
        branch_transport.put_bytes('location', url)
        branch_transport.put_bytes(
            'format', branch_reference_format.get_format_string())
        return a_bzrdir.root_transport.base

    def testCreateBranchReference(self):
        # createBranchReference creates a branch reference and returns a URL
        # that points to that branch reference.

        # First create a branch and a reference to that branch.
        target_branch = self.make_branch('repo')
        reference_url = self.createBranchReference(target_branch.base)

        # References are transparent, so we can't test much about them. The
        # least we can do is confirm that the reference URL isn't the branch
        # URL.
        self.assertNotEqual(reference_url, target_branch.base)

        # Open the branch reference and check that the result is indeed the
        # branch we wanted it to point at.
        opened_branch = bzrlib.branch.Branch.open(reference_url)
        self.assertEqual(opened_branch.base, target_branch.base)

    def testFollowReferenceValue(self):
        # BranchMirrorer.followReference gives the reference value for
        # a branch reference.
        opener = BranchMirrorer(BranchPolicy())
        reference_value = 'http://example.com/branch'
        reference_url = self.createBranchReference(reference_value)
        self.assertEqual(
            reference_value, opener.followReference(reference_url))

    def testFollowReferenceNone(self):
        # BranchMirrorer.followReference gives None for a normal branch.
        self.make_branch('repo')
        branch_url = self.get_url('repo')
        opener = BranchMirrorer(BranchPolicy())
        self.assertIs(None, opener.followReference(branch_url))


class TestMirroredBranchPolicy(TestCase):
    """Tests specific to `MirroredBranchPolicy`."""

    def setUp(self):
        super(TestMirroredBranchPolicy, self).setUp()
        self.factory = LaunchpadObjectFactory()

    def testNoFileURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlScheme, policy.checkOneURL,
            self.factory.getUniqueURL(scheme='file'))

    def testNoUnknownSchemeURLs(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlScheme, policy.checkOneURL,
            self.factory.getUniqueURL(scheme='decorator+scheme'))

    def testNoSSHURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlSsh, policy.checkOneURL,
            self.factory.getUniqueURL(scheme='bzr+ssh'))

    def testNoSftpURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlSsh, policy.checkOneURL,
            self.factory.getUniqueURL(scheme='sftp'))

    def testNoLaunchpadURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlLaunchpad, policy.checkOneURL,
            self.factory.getUniqueURL(host='bazaar.launchpad.dev'))

    def testNoHTTPSLaunchpadURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlLaunchpad, policy.checkOneURL,
            self.factory.getUniqueURL(
                host='bazaar.launchpad.dev', scheme='https'))

    def testNoOtherHostLaunchpadURL(self):
        policy = MirroredBranchPolicy()
        self.assertRaises(
            BadUrlLaunchpad, policy.checkOneURL,
            self.factory.getUniqueURL(host='code.launchpad.dev'))

    def testLocalhost(self):
        self.pushConfig(
            'codehosting', blacklisted_hostnames='localhost,127.0.0.1')
        policy = MirroredBranchPolicy()
        localhost_url = self.factory.getUniqueURL(host='localhost')
        self.assertRaises(BadUrl, policy.checkOneURL, localhost_url)
        localhost_url = self.factory.getUniqueURL(host='127.0.0.1')
        self.assertRaises(BadUrl, policy.checkOneURL, localhost_url)

    def test_no_stacked_on_url(self):
        # By default, a MirroredBranchPolicy does not stack branches.
        policy = MirroredBranchPolicy()
        # This implementation of the method doesn't actually care about the
        # arguments.
        self.assertIs(
            None, policy.getStackedOnURLForDestinationBranch(None, None))

    def test_specified_stacked_on_url(self):
        # If a default stacked-on URL is specified, then the
        # MirroredBranchPolicy will tell branches to be stacked on that.
        stacked_on_url = '/foo'
        policy = MirroredBranchPolicy(stacked_on_url)
        destination_url = 'http://example.com/bar'
        self.assertEqual(
            '/foo',
            policy.getStackedOnURLForDestinationBranch(None, destination_url))

    def test_stacked_on_url_for_mirrored_branch(self):
        # If the default stacked-on URL is also the URL for the branch being
        # mirrored, then the stacked-on URL for destination branch is None.
        stacked_on_url = '/foo'
        policy = MirroredBranchPolicy(stacked_on_url)
        destination_url = 'http://example.com/foo'
        self.assertIs(
            None,
            policy.getStackedOnURLForDestinationBranch(None, destination_url))


class TestWorkerProtocol(TestCaseInTempDir, PullerWorkerMixin):
    """Tests for the client-side implementation of the protocol used to
    communicate to the master process.
    """

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.output = StringIO()
        self.protocol = PullerWorkerProtocol(self.output)
        self.factory = ObjectFactory()

    def assertSentNetstrings(self, expected_netstrings):
        """Assert that the protocol sent the given netstrings (in order)."""
        observed_netstrings = get_netstrings(self.output.getvalue())
        self.assertEqual(expected_netstrings, observed_netstrings)

    def resetBuffers(self):
        # Empty the test output and error buffers.
        self.output.truncate(0)
        self.assertEqual('', self.output.getvalue())

    def test_nothingSentOnConstruction(self):
        # The protocol sends nothing until it receives an event.
        self.branch_to_mirror = self.makePullerWorker(protocol=self.protocol)
        self.assertSentNetstrings([])

    def test_startMirror(self):
        # Calling startMirroring sends 'startMirroring' as a netstring.
        self.protocol.startMirroring()
        self.assertSentNetstrings(['startMirroring', '0'])

    def test_branchChanged(self):
        # Calling 'branchChanged' sends the arguments.
        arbitrary_args = [self.factory.getUniqueString() for x in range(6)]
        self.protocol.startMirroring()
        self.resetBuffers()
        self.protocol.branchChanged(*arbitrary_args)
        self.assertSentNetstrings(['branchChanged', '6'] + arbitrary_args)

    def test_mirrorFailed(self):
        # Calling 'mirrorFailed' sends the error message.
        self.protocol.startMirroring()
        self.resetBuffers()
        self.protocol.mirrorFailed('Error Message', 'OOPS')
        self.assertSentNetstrings(
            ['mirrorFailed', '2', 'Error Message', 'OOPS'])

    def test_progressMade(self):
        # Calling 'progressMade' sends an arbitrary string indicating
        # progress.
        self.protocol.progressMade('test')
        self.assertSentNetstrings(['progressMade', '0'])

    def test_log(self):
        # Calling 'log' sends 'log' as a netstring and its arguments, after
        # formatting as a string.
        self.protocol.log('logged %s', 'message')
        self.assertSentNetstrings(['log', '1', 'logged message'])


class TestWorkerProgressReporting(TestCaseWithTransport):
    """Tests for the progress reporting mechanism."""

    class StubProtocol:
        """A stub for PullerWorkerProtocol that just defines progressMade."""
        def __init__(self):
            self.calls = []
        def progressMade(self, type):
            self.calls.append(type)

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self.saved_factory = bzrlib.ui.ui_factory
        self.disable_directory_isolation()

    def tearDown(self):
        TestCaseWithTransport.tearDown(self)
        bzrlib.ui.ui_factory = self.saved_factory

    def getHttpServerForCwd(self):
        """Get an `HttpServer` instance that serves from '.'."""
        server = FixedHttpServer()
        server.start_server()
        self.addCleanup(server.stop_server)
        # The gc.collect allows the threads behind any HTTP requests to exit.
        self.addCleanup(gc.collect)
        return server

    def test_simple(self):
        # Even the simplest of pulls should call progressMade at least once.
        b1 = self.make_branch('some-branch')
        b2_tree = self.make_branch_and_tree('some-other-branch')
        b2_tree.commit('rev1', allow_pointless=True)

        p = self.StubProtocol()
        install_worker_ui_factory(p)
        b1.pull(b2_tree.branch)
        self.assertPositive(len(p.calls))

    def test_network(self):
        # Even the simplest of pulls over a transport that reports activity
        # (here, HTTP) should call progressMade with a type of 'activity'.
        b1 = self.make_branch('some-branch')
        b2_tree = self.make_branch_and_tree('some-other-branch')
        b2_tree.commit('rev1', allow_pointless=True)
        http_server = self.getHttpServerForCwd()

        p = self.StubProtocol()
        install_worker_ui_factory(p)
        b2_http = bzrlib.branch.Branch.open(
            http_server.get_url() + 'some-other-branch')
        b1.pull(b2_http)
        self.assertSubset([WORKER_ACTIVITY_NETWORK], p.calls)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
