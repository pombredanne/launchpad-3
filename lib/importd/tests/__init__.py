from importd.tests import TestUtil
from importd.tests import test_Job
from importd.tests import test_taxi

def test_suite():
    """return the packages tests"""
    result = TestUtil.TestSuite()
    result.addTest(test_Job.test_suite())
    result.addTest(test_taxi.test_suite())
    return result

