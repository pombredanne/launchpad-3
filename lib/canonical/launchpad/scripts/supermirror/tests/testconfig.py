import unittest


from configuration import config
class TestConfig(unittest.TestCase):
    
    def testInit(self):
        if not config.masterlockattempts == 20 :
            raise RuntimeError

    def testLoad(self):
        config.variables['masterlockattempts'] = 30
        config.load()
        if not config.masterlockattempts == 20:
            raise RuntimeError



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
