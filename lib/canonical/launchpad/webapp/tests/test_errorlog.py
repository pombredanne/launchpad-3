# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import os
import datetime
import pytz
import unittest
import shutil
import StringIO
from textwrap import dedent
from zope.testing.loggingsupport import InstalledHandler

from canonical.config import config
from canonical.testing import reset_logging

UTC = pytz.timezone('UTC')

class TestErrorReport(unittest.TestCase):
    def tearDown(self):
        reset_logging()

    def test_import(self):
        from canonical.launchpad.webapp.errorlog import (
            ErrorReport, ErrorReportingUtility)

    def test___init__(self):
        """Test ErrorReport.__init__()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        entry = ErrorReport('id', 'exc-type', 'exc-value', 'timestamp',
                            'traceback-text', 'username', 'url', 42,
                            [('name1', 'value1'), ('name2', 'value2'),
                             ('name1', 'value3'),
                             ('field.password', 'secret1'),
                             ('PassWd2', 'secret2')],
                            [(1, 5, 'SELECT 1'),
                             (5, 10, 'SELECT 2')])
        self.assertEqual(entry.id, 'id')
        self.assertEqual(entry.type, 'exc-type')
        self.assertEqual(entry.value, 'exc-value')
        self.assertEqual(entry.time, 'timestamp')
        self.assertEqual(entry.tb_text, 'traceback-text')
        self.assertEqual(entry.username, 'username')
        self.assertEqual(entry.url, 'url')
        self.assertEqual(entry.duration, 42)
        self.assertEqual(len(entry.req_vars), 5)
        self.assertEqual(entry.req_vars[0], ('name1', 'value1'))
        self.assertEqual(entry.req_vars[1], ('name2', 'value2'))
        self.assertEqual(entry.req_vars[2], ('name1', 'value3'))
        self.assertEqual(entry.req_vars[3], ('field.password', '<hidden>'))
        self.assertEqual(entry.req_vars[4], ('PassWd2', '<hidden>'))
        self.assertEqual(len(entry.db_statements), 2)
        self.assertEqual(entry.db_statements[0], (1, 5, 'SELECT 1'))
        self.assertEqual(entry.db_statements[1], (5, 10, 'SELECT 2'))

    def test_write(self):
        """Test ErrorReport.write()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        entry = ErrorReport('OOPS-A0001', 'NotFound', 'error message',
                            datetime.datetime(2005, 04, 01, 00, 00, 00,
                                              tzinfo=UTC),
                            'traceback-text',
                            'Sample User', 'http://localhost:9000/foo', 42,
                            [('HTTP_USER_AGENT', 'Mozilla/5.0'),
                             ('HTTP_REFERER', 'http://localhost:9000/'),
                             ('name=foo', 'hello\nworld')],
                            [(1, 5, 'SELECT 1'),
                             (5, 10, 'SELECT\n2')])
        fp = StringIO.StringIO()
        entry.write(fp)
        self.assertEqual(fp.getvalue(), dedent("""\
            Oops-Id: OOPS-A0001
            Exception-Type: NotFound
            Exception-Value: error message
            Date: 2005-04-01T00:00:00+00:00
            User: Sample User
            URL: http://localhost:9000/foo
            Duration: 42
            
            HTTP_USER_AGENT=Mozilla/5.0
            HTTP_REFERER=http://localhost:9000/
            name%3Dfoo=hello%0Aworld
            
            00001-00005 SELECT 1
            00005-00010 SELECT 2

            traceback-text"""))

    def test_read(self):
        """Test ErrorReport.read()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        fp = StringIO.StringIO(dedent("""\
            Oops-Id: OOPS-A0001
            Exception-Type: NotFound
            Exception-Value: error message
            Date: 2005-04-01T00:00:00+00:00
            User: Sample User
            URL: http://localhost:9000/foo
            Duration: 42
            
            HTTP_USER_AGENT=Mozilla/5.0
            HTTP_REFERER=http://localhost:9000/
            name%3Dfoo=hello%0Aworld

            00001-00005 SELECT 1
            00005-00010 SELECT 2

            traceback-text"""))
        entry = ErrorReport.read(fp)
        self.assertEqual(entry.id, 'OOPS-A0001')
        self.assertEqual(entry.type, 'NotFound')
        self.assertEqual(entry.value, 'error message')
        # XXX 20051130: jamesh
        # this should probably convert back to a datetime
        self.assertEqual(entry.time, '2005-04-01T00:00:00+00:00')
        self.assertEqual(entry.tb_text, 'traceback-text')
        self.assertEqual(entry.username, 'Sample User')
        self.assertEqual(entry.url, 'http://localhost:9000/foo')
        self.assertEqual(entry.duration, 42)
        self.assertEqual(len(entry.req_vars), 3)
        self.assertEqual(entry.req_vars[0], ('HTTP_USER_AGENT', 'Mozilla/5.0'))
        self.assertEqual(entry.req_vars[1], ('HTTP_REFERER',
                                             'http://localhost:9000/'))
        self.assertEqual(entry.req_vars[2], ('name=foo', 'hello\nworld'))
        self.assertEqual(len(entry.db_statements), 2)
        self.assertEqual(entry.db_statements[0], (1, 5, 'SELECT 1'))
        self.assertEqual(entry.db_statements[1], (5, 10, 'SELECT 2'))


class TestErrorReportingUtility(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(config.launchpad.errorreports.errordir,
                      ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(config.launchpad.errorreports.errordir,
                      ignore_errors=True)
        reset_logging()

    def test_newOopsId(self):
        """Test ErrorReportingUtility.newOopsId()"""
        from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
        utility = ErrorReportingUtility()

        # first oops of the day
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-91T1')
        self.assertEqual(filename, '/var/tmp/lperr.test/2006-04-01/01800.T1')
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(utility.lasterrordate, '2006-04-01')

        # second oops of the day
        now = datetime.datetime(2006, 04, 01, 12, 00, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-91T2')
        self.assertEqual(filename, '/var/tmp/lperr.test/2006-04-01/43200.T2')
        self.assertEqual(utility.lastid, 2)
        self.assertEqual(utility.lasterrordate, '2006-04-01')

        # first oops of following day
        now = datetime.datetime(2006, 04, 02, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-92T1')
        self.assertEqual(filename, '/var/tmp/lperr.test/2006-04-02/01800.T1')
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(utility.lasterrordate, '2006-04-02')

        # another oops with a naiive datetime
        now = datetime.datetime(2006, 04, 02, 00, 30, 00)
        self.assertRaises(ValueError, utility.newOopsId, now)

    def test_findLastOopsId(self):
        """Test ErrorReportingUtility._findLastOopsId()"""
        from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
        utility = ErrorReportingUtility()

        self.assertEqual(config.launchpad.errorreports.oops_prefix, 'T')

        errordir = utility.errordir()
        # write some files
        open(os.path.join(errordir, '12343.T1'), 'w').close()
        open(os.path.join(errordir, '12342.T2'), 'w').close()
        open(os.path.join(errordir, '12345.T3'), 'w').close()
        open(os.path.join(errordir, '1234567.T0010'), 'w').close()
        open(os.path.join(errordir, '12346.A42'), 'w').close()
        open(os.path.join(errordir, '12346.B100'), 'w').close()

        self.assertEqual(utility._findLastOopsId(errordir), 10)

    def test_raising(self):
        """Test ErrorReportingUtility.raising() with no request"""
        from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise Exception('xyz')
        except:
            utility.raising(sys.exc_info(), now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: Exception\n')
        self.assertEqual(lines[2], 'Exception-Value: xyz\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'User: None\n')
        self.assertEqual(lines[5], 'URL: None\n')
        self.assertEqual(lines[6], 'Duration: -1\n')
        self.assertEqual(lines[7], '\n')

        # no request vars
        self.assertEqual(lines[8], '\n')

        # no database statements
        self.assertEqual(lines[9], '\n')

        # traceback
        self.assertEqual(lines[10], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise Exception(\'xyz\')
        self.assertEqual(lines[13], 'Exception: xyz\n')

    def test_raising_with_request(self):
        """Test ErrorReportingUtility.raising() with a request"""
        from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        class FakeRequest:
            URL = 'http://localhost:9000/foo'
            class principal:
                id = 42
                title = u'title'
                # non ASCII description
                description = u'description |\N{BLACK SQUARE}|'

                @staticmethod
                def getLogin():
                    return u'Login'

            oopsid = None

            def items(self):
                return [('name2', 'value2'), ('name1', 'value1'),
                        ('name1', 'value3 \xa7'),
                        (u'\N{BLACK SQUARE}', u'value4')]

        request = FakeRequest()

        try:
            raise Exception('xyz\nabc')
        except:
            utility.raising(sys.exc_info(), request, now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: Exception\n')
        self.assertEqual(lines[2], 'Exception-Value: xyz abc\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'User: Login, 42, title, description |\\u25a0|\n')
        self.assertEqual(lines[5], 'URL: http://localhost:9000/foo\n')
        self.assertEqual(lines[6], 'Duration: -1\n')
        self.assertEqual(lines[7], '\n')

        # request vars
        self.assertEqual(lines[8], '\\u25a0=value4\n')    # non-ASCII request var
        self.assertEqual(lines[9], 'name1=value1\n')
        self.assertEqual(lines[10], 'name1=value3 \\xa7\n')
        self.assertEqual(lines[11], 'name2=value2\n')
        self.assertEqual(lines[12], '\n')

        # no database statements
        self.assertEqual(lines[13], '\n')

        # traceback
        self.assertEqual(lines[14], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise Exception(\'xyz\')
        self.assertEqual(lines[17], 'Exception: xyz\n')

        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, 'OOPS-91T1')

    def test_raising_for_script(self):
        """Test ErrorReportingUtility.raising with a ScriptRequest."""
        from canonical.launchpad.webapp.errorlog import (
            ErrorReportingUtility, ScriptRequest)
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise Exception('xyz\nabc')
        except:
            # Do not test escaping of request vars here, it is already tested
            # in test_raising_with_request.
            request = ScriptRequest([
                ('name2', 'value2'), ('name1', 'value1'), ('name1', 'value3')],
                URL='https://launchpad.net/example')
            utility.raising(sys.exc_info(), request, now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: Exception\n')
        self.assertEqual(lines[2], 'Exception-Value: xyz abc\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'User: None\n')
        self.assertEqual(lines[5], 'URL: https://launchpad.net/example\n')
        self.assertEqual(lines[6], 'Duration: -1\n')
        self.assertEqual(lines[7], '\n')

        # request vars
        self.assertEqual(lines[8], 'name1=value1\n')
        self.assertEqual(lines[9], 'name1=value3\n')
        self.assertEqual(lines[10], 'name2=value2\n')
        self.assertEqual(lines[11], '\n')

        # no database statements
        self.assertEqual(lines[12], '\n')

        # traceback
        self.assertEqual(lines[13], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise Exception(\'xyz\')
        self.assertEqual(lines[16], 'Exception: xyz\n')

        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, 'OOPS-91T1')


    def test_raising_with_unprintable_exception(self):
        """Test ErrorReportingUtility.raising() with an unprintable exception"""
        from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 01, 01, 00, 30, 00, tzinfo=UTC)

        class UnprintableException(Exception):
            def __str__(self):
                raise RuntimeError('arrgh')

        log = InstalledHandler('SiteError')
        try:
            raise UnprintableException()
        except:
            utility.raising(sys.exc_info(), now=now)
        log.uninstall()

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-1T1\n')
        self.assertEqual(lines[1], 'Exception-Type: UnprintableException\n')
        self.assertEqual(lines[2], 'Exception-Value: <unprintable instance object>\n')
        self.assertEqual(lines[3], 'Date: 2006-01-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'User: None\n')
        self.assertEqual(lines[5], 'URL: None\n')
        self.assertEqual(lines[6], 'Duration: -1\n')
        self.assertEqual(lines[7], '\n')

        # no request vars
        self.assertEqual(lines[8], '\n')

        # no database statements
        self.assertEqual(lines[9], '\n')

        # traceback
        self.assertEqual(lines[10], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise UnprintableException()
        self.assertEqual(lines[13], 'UnprintableException: <unprintable instance object>\n')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestErrorReport))
    suite.addTest(unittest.makeSuite(TestErrorReportingUtility))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
