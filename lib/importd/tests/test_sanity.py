# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test sanity checks in importd.

We do some simple sanity checks on imports to avoid putting excessive
load on the servers we are connecting to. These checks are only
performed on the initial import, because the system guarantees that
syncs are only run on published imports and once a vcs import is
published, its details can only be changed by a privileged operator.

SVN repositories are typically laid out as:

    product/
         branches/
         tags/
         trunk/

Less often, they are laid out as:

    trunk/
         productA/
         productB/
         ...
    branches/
         ...

In the first example, if a client attempts to fetch svn://repo/product
(e.g. to import it to bzr), the server will send them the full text of
every single branch and tag, which is much larger than the actual size
of the repository.
"""

__metaclass__ = type

from importd.tests import testutil, helpers
from importd.JobStrategy import SVNStrategy, ImportSanityError


class CheckSanityCalled(Exception):
    """Raised to indicate that the _checkSanity method was called."""

class SanityIsOverriddenCalled(Exception):
    """Raised to indicate that _sanityIsOverridden was called."""


class SvnSanityTestCase(helpers.JobTestCase):
    """Base class for Subversion sanity tests."""

    def setUp(self):
        helpers.JobTestCase.setUp(self)
        self.logger = testutil.makeSilentLogger()

    def makeTestingSvnJob(self, svn_url):
        """Create a job with svn details, to test svn sanity checking."""
        job = self.job_helper.makeJob()
        job.repository = svn_url
        return job

    def makeTestingSvnStrategy(self, svn_url):
        """Create a a SVNStrategy to test sanity checking.

        Fulfills the role of the Import and sync entry point methods in setting
        up a SVNStrategy instance usable for unit-testing internal methods.
        """
        job = self.makeTestingSvnJob(svn_url)
        job.autotest = True # Sanity check is only enabled on autotest.
        strategy = SVNStrategy()
        strategy.job = job
        strategy.aJob = job
        strategy.dir = '.'
        strategy.logger = self.logger
        return strategy


class TestSvnSanity(SvnSanityTestCase):
    """Test sanity checks of SVN job strategy."""

    def testImportCallsCheckSanity(self):
        # SvnStrategy.Import calls _checkSanity before trying the import.
        strategy = SVNStrategy()
        def check_sanity():
            raise CheckSanityCalled()
        strategy._checkSanity = check_sanity
        # Since the job does not have the information necessary to perform an
        # import, CheckSanityCalled is only raised if _checkSanity is called
        # before doing anything.
        invalid_url = None
        job = self.makeTestingSvnJob(invalid_url)
        self.assertRaises(CheckSanityCalled,
            strategy.Import, job, '.', self.logger)

    def testCheckSanityCallsSanityIsOverridden(self):
        # SvnStrategy._checkSanity calls SvnStrategy._sanityIsOverridden
        #
        # Use an obviously invalid svn url, so SanityIsOverriddenCalled is only
        # raised if _sanityIsOverridden is called early on.
        invalid_url = None
        strategy = self.makeTestingSvnStrategy(invalid_url)
        def sanity_is_overridden():
            raise SanityIsOverriddenCalled()
        strategy._sanityIsOverridden = sanity_is_overridden
        self.assertRaises(SanityIsOverriddenCalled, strategy._checkSanity)

    def testSanityIsOverriddenFalse(self):
        # SvnStrategy._sanityIsOverridden returns false for an URL not in the
        # exception list
        not_whitelisted_url = 'svn://example.com/bogus'
        strategy = self.makeTestingSvnStrategy(not_whitelisted_url)
        self.assertFalse(not_whitelisted_url in strategy._svn_url_whitelist)
        self.assertFalse(strategy._sanityIsOverridden())

    def testSanityIsOverriddenIfNotAutotest(self):
        # SvnStrategy._sanityIsOverridden returns true if the job is not run on
        # autotest.
        not_whitelisted_url = 'svn://example.com/bogus'
        strategy = self.makeTestingSvnStrategy(not_whitelisted_url)
        strategy.job.autotest = False
        self.assertFalse(not_whitelisted_url in strategy._svn_url_whitelist)
        self.assertTrue(strategy._sanityIsOverridden())

    def testSanityIsOverriddenTrue(self):
        # SvnStrategy._sanityIsOverridden returns true for an URL in the
        # exception list
        unsafe_url = 'svn://example.com/bogus'
        strategy = self.makeTestingSvnStrategy(unsafe_url)
        strategy._svn_url_whitelist.add(unsafe_url)
        self.assertTrue(strategy._sanityIsOverridden())

    def testCheckSanityNoTrunk(self):
        # SvnStrategy._checkSanity raises for URL w/o trunk
        unsafe_url = 'svn://example.com/bogus'
        strategy = self.makeTestingSvnStrategy(unsafe_url)
        self.assertRaises(ImportSanityError, strategy._checkSanity)

    def testCheckSanityUrlIncludesTrunk(self):
        # SvnStrategy._checkSanity does not raise for URL including '/trunk/'
        good_url = 'svn://example.com/trunk/foo'
        strategy = self.makeTestingSvnStrategy(good_url)
        strategy._checkSanity() # test that it does not raise

    def testCheckSanityUrlEndswithTrunk(self):
        # SvnStrategy._checkSanity does not raise for URL ending in '/trunk'
        good_url = 'svn://example.com/foo/trunk'
        strategy = self.makeTestingSvnStrategy(good_url)
        strategy._checkSanity() # test that it does not raise

    def testCheckSanityUrlsEndswithSlash(self):
        # SvnStrategy._checkSanity raises for URL with a trailing slash
        url_slash = 'svn://example.com/foo/trunk/'
        strategy = self.makeTestingSvnStrategy(url_slash)
        self.assertRaises(ImportSanityError, strategy._checkSanity)

    def testCheckSanityCanBeOverridden(self):
        # SvnStrategy._checkSanity does not raise for a bad URL if
        # _sanityIsOverriddenReturns is true.
        unsafe_url = 'svn://example.com/bogus'
        strategy = self.makeTestingSvnStrategy(unsafe_url)
        def sanity_is_overridden():
            return True
        strategy._sanityIsOverridden = sanity_is_overridden
        strategy._checkSanity() # test that it does not raise



testutil.register(__name__)
