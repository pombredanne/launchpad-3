import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

class DummyRequestWithoutQueryString(object):
    def __init__(self):
        self.URL = "http://www.example.com/foo"
        self.environment = {}
        self.environment['QUERY_STRING'] = ""

class DummyRequestWithQueryString(object):
    def __init__(self):
        self.URL = "http://www.example.com/foo"
        self.environment = {}
        self.environment['QUERY_STRING'] = "fnorb=bar"

class DummyRequestWithQueryStringAfterNext(object):
    def __init__(self):
        self.URL = "http://www.example.com/foo"
        self.environment = {}
        self.environment['QUERY_STRING'] = "fnorb=bar&batch_start=3&batch_end=6"

def test_suite():
    suite = unittest.TestSuite((
        DocFileSuite(
        "batch_navigation.txt", globs = {
            "request_with_qs" : DummyRequestWithQueryString(),
            "request_with_qs_after_next" : DummyRequestWithQueryStringAfterNext(),
            "request_without_qs" : DummyRequestWithoutQueryString()}),))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest = "test_suite")
