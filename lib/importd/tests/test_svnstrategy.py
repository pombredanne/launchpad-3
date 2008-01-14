# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for SVNStrategy."""

__metaclass__ = type

import os
import re

from bzrlib.branch import Branch
import cscvs.bzr
import cscvs.ProgressPrinter
from cscvs.ProgressPrinter import ProgressPrinterHelper

from importd import JobStrategy
from importd.tests.helpers import SimpleJobHelper, JobTestCase
from importd.tests import testutil



class SvnJobHelper(SimpleJobHelper):
    """Job factory for SVNStrategy test cases."""

    def setUp(self):
        SimpleJobHelper.setUp(self)
        self.svn_repo_path = self.sandbox.join('svnrepo')

    def makeJob(self):
        """Create a job for SVNStrategy to use.

        This job contains just enough information to perform a svn import and a
        svn sync.
        """
        job = SimpleJobHelper.makeJob(self)
        job.repository = 'file://' + self.svn_repo_path + '/trunk'
        job.autotest = False
        return job


class SvnRepositoryHelper:
    """Helper to create a svn repository to import."""

    def __init__(self, sandbox, job_helper):
        self.sandbox = sandbox
        self.job_helper = job_helper
        self.svn_repo = None
        self.svn_tree = None

    def setUp(self):
        self.svn_tree_path = self.sandbox.join('svntree')

    def tearDown(self):
        pass

    def setUpSvnImport(self):
        """Setup a SVN repository to test importing.

        First create two files in a different branch, then copy the branch into
        the branch to import, then modify one file. This will create a branch
        with two revisions to import, that does not start at revision 1, and
        with a revision that has a different number of changes than files.

        Starting on a revision different than 1 allows us to test that we use
        cscvs correctly to handle this situation (which cannot arise with CVS
        imports), and different number of changes and files allows us to test
        that we properly do incremental imports.
        """
        self._createRepository()
        self._checkoutWholeRepository()
        self._makeRevisionOne()
        self._makeRevisionTwo()
        self._makeRevisionThree()

    def setUpSvnSync(self):
        """Augment the SVN repository to test syncing.

        Just modify a single file in the imported branch. That will allow to
        test that syncing actually records new changes in the repository.
        """
        self._makeRevisionFour()

    def _createRepository(self):
        """Create a svn repository at self.job_helper.svn_repo_path."""
        svn_repo_path = self.job_helper.svn_repo_path
        logger = testutil.makeSilentLogger()

        # XXX DavidAllouche 2007-05-07: 
        # Scoped import of svn_oo to work around segfault
        # on importing svn on ia64.
        import svn_oo

        self.svn_repo = svn_oo.Repository.Create(svn_repo_path, logger)

    def _checkoutWholeRepository(self):
        """Check out the root of self.svn_repo at self.svn_tree_path."""
        # XXX DavidAllouche 2007-05-07: 
        # Scoped import of svn_oo to work around segfault
        # on importing svn on ia64.
        import svn_oo
        from svn_oo.util import pysvnClient

        # XXX David Allouche 2006-11-03:
        # svn_oo does not allow to checkout the whole repository, so we
        # need to use lower-level bindings here.
        client = pysvnClient()
        svn_repo_path = self.job_helper.svn_repo_path
        client.checkout('file://' + svn_repo_path, self.svn_tree_path)
        self.svn_tree = svn_oo.WorkingTree(self.svn_tree_path)

    def _makeRevisionOne(self):
        """Make the first revision. It creates two files in /branch."""
        os.mkdir(self._abspath('branch'))
        self._writeSourceFile('branch/foo', 'initial foo')
        self._writeSourceFile('branch/bar', 'initial bar')
        for relpath in ['branch', 'branch/foo', 'branch/bar']:
            self.svn_tree.add(relpath)
        self.svn_tree.commit('create branch/foo and branch/bar')

    def _makeRevisionTwo(self):
        """Make the second revision. It creates the branch we will import."""
        # XXX DavidAllouche 2007-05-07:
        # Scoped import of svn_oo to work around segfault
        # on importing svn on ia64.
        from svn_oo.util import pysvnClient

        # XXX David Allouche 2006-11-03:
        # svn_oo does not support copy. We need to use lower-level
        # bindings.
        client = pysvnClient()
        client.copy(self._abspath('branch'), self._abspath('trunk'))
        self.svn_tree.commit('create trunk')

    def _makeRevisionThree(self):
        """Make the third revision. It modifies one imported file."""
        self._writeSourceFile('trunk/foo', 'modified foo')
        self.svn_tree.commit('modify trunk/foo')

    def _makeRevisionFour(self):
        """Make the fourth revision. It modifies another imported file."""
        self._writeSourceFile('trunk/bar', 'modified bar')
        self.svn_tree.commit('modify trunk/bar')

    def _writeSourceFile(self, relpath, data):
        """Write data at the relative path relpath in self.svn_tree_path."""
        source_file = open(self._abspath(relpath), 'w')
        try:
            source_file.write(data)
        finally:
            source_file.close()

    def _abspath(self, relpath):
        """Produce an absolute path from a relative path in the checkout."""
        return os.path.join(self.svn_tree_path, relpath)


class SvnStrategyTestCase(JobTestCase):
    """Base class for SVNStrategy tests.

    Glues JobTestCase, SvnRepositoryHelper and ProgressPrinterHelper, and
    define some helper methods.
    """

    jobHelperType = SvnJobHelper

    def setUp(self):
        JobTestCase.setUp(self)
        self.svn_helper = SvnRepositoryHelper(self.sandbox, self.job_helper)
        self.svn_helper.setUp()
        self.progress_helper = ProgressPrinterHelper()
        self.progress_helper.setUp()

    def tearDown(self):
        self.svn_helper.tearDown()
        self.progress_helper.tearDown()
        JobTestCase.tearDown(self)

    def targetTree(self):
        """Cscvs working tree for the imported tree."""
        target_tree_path = self.targetTreePath()
        target_tree = cscvs.bzr.tree(target_tree_path)
        return target_tree

    def targetRevno(self):
        """Revision number of the bzr import tree."""
        target_tree_path = self.targetTreePath()
        revno = Branch.open(target_tree_path).revno()
        return revno

    def targetTreePath(self):
        """Path of the import target tree."""
        return self.sandbox.join('series-0000002a', 'bzrworking')

    def progressMessages(self, logger):
        """Extract progress messages from the collecting logger.

        We are only interested in the 'N changeset' and 'change' messages. The
        'N changeset' messages tell us when a svn revision is processed, and
        the 'change' messages when each discrete change from this revision is
        processed.
        """
        return [message for message in logger.messages if (
            re.match(r"N changeset \d+", message)
            or re.match(r"change \d+", message))]


class TestSvnStrategyImport(SvnStrategyTestCase):
    """Tests for SVNStrategy.Import"""

    def testSvnImport(self):
        # Feature test for an initial import from SVN.
        #
        # The first revision must be done with a full-tree import, the second
        # revision must be done with an incremental import. We check that the
        # second revision is incremental by counting the changes logged by
        # cscvs. We also use the cscvs logging to make sure that the first
        # revision is only processed once.
        #
        # The peculiarities of the svn_oo.RevisionRangeParser makes this
        # non-trivial, and this test reflects bugs that actually occured.
        self.svn_helper.setUpSvnImport()
        logger = testutil.makeCollectingLogger()
        job = self.job_helper.makeJob()
        job.working_root = self.sandbox.path
        cscvs.ProgressPrinter.set_interval(0) # log all progress messages
        # Actually run the import, now that we have all the required bits.
        strategy = JobStrategy.SVNStrategy()
        strategy.Import(job, self.sandbox.path, logger)
        # Check the progress messages.
        messages = self.progressMessages(logger)
        self.assertEqual(messages, [
            # The first revision on trunk is 2. It must be a full-tree import,
            # and contain two changes, one for each source node in the
            # revision: /trunk/foo and /trunk/bar.
            'N changeset 2', 'change 0', 'change 1',
            # The second revision on trunk is 3. It must be an incremental
            # import, and contain only one change, for the modification on
            # /trunk/foo.
            'N changeset 3', 'change 0'])
        # Check that import created the right number of bzr revisions.
        self.assertEqual(self.targetRevno(), 2)
        # Check the import result
        target_tree = self.targetTree()
        target_tree.lock_read()
        try:
            inventory = sorted(
                target_tree.iter_inventory(source=True, both=True))
        finally:
            target_tree.unlock()
        self.assertEqual(sorted(inventory), [u'bar', u'foo'])


class TestSvnStrategySync(SvnStrategyTestCase):
    """Tests for SVNStrategy.sync."""

    def testSvnSync(self):
        # Feature test for a sync from SVN.
        self.svn_helper.setUpSvnImport()
        logger = testutil.makeCollectingLogger()
        job = self.job_helper.makeJob()
        job.working_root = self.sandbox.path
        cscvs.ProgressPrinter.set_interval(0) # log all progress messages
        # Actually run the import, now that we have all the required bits.
        strategy = JobStrategy.SVNStrategy()
        strategy.Import(job, self.sandbox.path, logger)
        # If there is nothing new, a sync must produce no commit.
        logger = testutil.makeCollectingLogger()
        revno_before_sync = self.targetRevno()
        strategy = JobStrategy.SVNStrategy()
        strategy._getSyncTarget = self.stubGetSyncTarget
        strategy.sync(job, self.sandbox.path, logger)
        messages = self.progressMessages(logger)
        self.assertEqual(messages, []) # no change was reported
        self.assertEqual(self.targetRevno(), revno_before_sync)
        # If was a new commit, sync must produce a new revision.
        self.svn_helper.setUpSvnSync()
        logger = testutil.makeCollectingLogger()
        strategy = JobStrategy.SVNStrategy()
        strategy._getSyncTarget = self.stubGetSyncTarget
        strategy.sync(job, self.sandbox.path, logger)
        messages = self.progressMessages(logger)
        self.assertEqual(messages, ['N changeset 4', 'change 0'])
        self.assertEqual(self.targetRevno(), revno_before_sync + 1)

    def stubGetSyncTarget(self, working_dir):
        """Stub implementation of CSCVSStrategy._getSyncTarget.

        The full implementation needs database access. Supporting it would add
        much unecessary hair to the test.
        """
        bzrworking = os.path.join(working_dir, 'bzrworking')
        self.assertEqual(bzrworking, self.targetTreePath())
        return bzrworking


testutil.register(__name__)
