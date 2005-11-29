# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import datetime
import pytz
import unittest
import shutil
import StringIO

from canonical.config import config

class TestErrorReport(unittest.TestCase):
    def test_import(self):
        from canonical.launchpad.webapp.errorlog import ErrorReport

    def test_constructor(self):
        from canonical.launchpad.webapp.errorlog import ErrorReport

        entry = ErrorReport('id', 'exc-type', 'exc-value', 'timestamp',
                            'traceback-text', 'traceback-html', 'username',
                            'url', [('name1', 'value1'), ('name2', 'value2')])
        self.assertEqual(entry.id, 'id')
        self.assertEqual(entry.type, 'exc-type')
        self.assertEqual(entry.value, 'exc-value')
        self.assertEqual(entry.time, 'timestamp')
        self.assertEqual(entry.tb_text, 'traceback-text')
        self.assertEqual(entry.tb_html, 'traceback-html')
        self.assertEqual(entry.username, 'username')
        self.assertEqual(entry.url, 'url')
        self.assertEqual(len(entry.req_vars), 2)
        self.assertEqual(entry.req_vars[0], ('name1', 'value1'))
        self.assertEqual(entry.req_vars[1], ('name2', 'value2'))

    def test_write(self):
        from canonical.launchpad.webapp.errorlog import ErrorReport

        entry = ErrorReport('OOPS-A0001', 'NotFound', 'error message',
                            datetime.datetime(2005,04,01,00,00,00,
                                              tzinfo=pytz.timezone('UTC')),
                            'traceback-text', 'traceback-html',
                            'Sample User', 'http://localhost:9000/foo',
                            [('HTTP_USER_AGENT', 'Mozilla/5.0'),
                             ('HTTP_REFERER', 'http://localhost:9000/')])
        fp = StringIO.StringIO()
        entry.write(fp)
        self.assertEqual(fp.getvalue(),
                         'Oops-Id: OOPS-A0001\n'
                         'Exception-Type: NotFound\n'
                         'Exception-Value: error message\n'
                         'Date: 2005-04-01T00:00:00+00:00\n'
                         'User: Sample User\n'
                         'URL: http://localhost:9000/foo\n'
                         '\n'
                         'HTTP_USER_AGENT=Mozilla/5.0\n'
                         'HTTP_REFERER=http://localhost:9000/\n'
                         '\n'
                         'traceback-text')
        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestErrorReport))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
