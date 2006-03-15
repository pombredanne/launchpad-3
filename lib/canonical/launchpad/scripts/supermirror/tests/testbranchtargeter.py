import unittest

from branchtargeter import branchtarget
from configuration import config

class TestConfig(unittest.TestCase):
    
    def testcalculate0(self):
        self.assertEquals("00/00/00", branchtargeter(0))

    def testcalculate1(self):
        self.assertEquals("00/00/01", branchtarget(1))

    def testcalculatebirthday(self):
        self.assertEquals("00/01/3d/78", branchtarget(81272))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
