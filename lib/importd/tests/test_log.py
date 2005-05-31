from twisted.trial import unittest
from twisted.python import log

class LogCounter(object):
    """count how many messages pass through"""
    def __init__(self):
        self.messages=0
    def log(self, d):
        self.messages+=1

class TestAdaptor(unittest.TestCase):
    """test logging to log adapter"""
    def setUp(self):
        """we need to see where the msgs go"""
        self.counter=LogCounter()
        log.addObserver(self.counter.log)
    def tearDown(self):
        log.removeObserver(self.counter.log)
    def testTrial(self):
        """does the adapter catch messages"""
        import logging
        from importd import LoggingLogAdaptor
        adaptor=LoggingLogAdaptor(log)
        logger=logging.Logger("test")
        logger.addHandler(adaptor)
        logger.info("test")
        logger.removeHandler(adaptor)
        self.assertEqual(self.counter.messages, 1)
