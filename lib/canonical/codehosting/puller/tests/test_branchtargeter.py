import unittest

from canonical.codehosting.puller.branchtargeter import branchtarget


class TestBranchTargeter(unittest.TestCase):

    def testcalculate0(self):
        self.assertEquals("00/00/00/00", branchtarget(0))

    def testcalculate1(self):
        self.assertEquals("00/00/00/01", branchtarget(1))

    def testcalculatebirthday(self):
        self.assertEquals("00/01/3d/78", branchtarget(81272))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
