from importd.tests import testutil
from importd.tests import test_Job
from importd.tests import test_archivemanager
from importd.tests import test_cvsstrategy
from importd.tests import test_baz2bzr

def test_suite():
    """return the packages tests"""
    result = testutil.TestSuite()
    result.addTest(test_Job.test_suite())
    result.addTest(test_archivemanager.test_suite())
    result.addTest(test_cvsstrategy.test_suite())
    result.addTest(test_baz2bzr.test_suite())
    return result

