from importd.tests import testutil
from importd.tests import (
    test_Job, test_bzrmanager,
    test_cvsstrategy, test_jobstrategy, test_sanity, test_svnstrategy)


def test_suite():
    """return the packages tests"""
    result = testutil.TestSuite()
    result.addTest(test_Job.test_suite())
    result.addTest(test_sanity.test_suite())
    result.addTest(test_bzrmanager.test_suite())
    result.addTest(test_jobstrategy.test_suite())
    result.addTest(test_cvsstrategy.test_suite())
    result.addTest(test_svnstrategy.test_suite())
    return result

