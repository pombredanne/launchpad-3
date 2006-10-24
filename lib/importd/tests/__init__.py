from importd.tests import testutil
from importd.tests import (
    test_bzrmanager, test_cvsstrategy, test_Job, test_safety)


def test_suite():
    """return the packages tests"""
    result = testutil.TestSuite()
    result.addTest(test_Job.test_suite())
    result.addTest(test_safety.test_suite())
    result.addTest(test_bzrmanager.test_suite())
    result.addTest(test_cvsstrategy.test_suite())
    return result

