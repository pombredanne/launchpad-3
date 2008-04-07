# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import os
import datetime
import pytz
import unittest
import shutil
import StringIO
from textwrap import dedent
import tempfile
import traceback

from zope.publisher.browser import TestRequest
from zope.security.interfaces import Unauthorized
from zope.testing.loggingsupport import InstalledHandler

from canonical.config import config
from canonical.testing import reset_logging
from canonical.launchpad import versioninfo
from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
from canonical.launchpad.webapp.interfaces import TranslationUnavailable


UTC = pytz.timezone('UTC')


class ArbitraryException(Exception):
    """Used to test handling of exceptions in OOPS reports."""


class TestErrorReport(unittest.TestCase):

    def tearDown(self):
        reset_logging()

    def test_import(self):
        from canonical.launchpad.webapp.errorlog import ErrorReport

    def test___init__(self):
        """Test ErrorReport.__init__()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        entry = ErrorReport('id', 'exc-type', 'exc-value', 'timestamp',
                            'pageid', 'traceback-text', 'username', 'url', 42,
                            [('name1', 'value1'), ('name2', 'value2'),
                             ('name1', 'value3')],
                            [(1, 5, 'SELECT 1'),
                             (5, 10, 'SELECT 2')])
        self.assertEqual(entry.id, 'id')
        self.assertEqual(entry.type, 'exc-type')
        self.assertEqual(entry.value, 'exc-value')
        self.assertEqual(entry.time, 'timestamp')
        self.assertEqual(entry.pageid, 'pageid')
        self.assertEqual(entry.branch_nick, versioninfo.branch_nick)
        self.assertEqual(entry.revno, versioninfo.revno)
        self.assertEqual(entry.username, 'username')
        self.assertEqual(entry.url, 'url')
        self.assertEqual(entry.duration, 42)
        self.assertEqual(len(entry.req_vars), 3)
        self.assertEqual(entry.req_vars[0], ('name1', 'value1'))
        self.assertEqual(entry.req_vars[1], ('name2', 'value2'))
        self.assertEqual(entry.req_vars[2], ('name1', 'value3'))
        self.assertEqual(len(entry.db_statements), 2)
        self.assertEqual(entry.db_statements[0], (1, 5, 'SELECT 1'))
        self.assertEqual(entry.db_statements[1], (5, 10, 'SELECT 2'))

    def test_write(self):
        """Test ErrorReport.write()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        entry = ErrorReport('OOPS-A0001', 'NotFound', 'error message',
                            datetime.datetime(2005, 04, 01, 00, 00, 00,
                                              tzinfo=UTC),
                            'IFoo:+foo-template',
                            'traceback-text', 'Sample User',
                            'http://localhost:9000/foo', 42,
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
            Page-Id: IFoo:+foo-template
            Branch: %s
            Revision: %s
            User: Sample User
            URL: http://localhost:9000/foo
            Duration: 42

            HTTP_USER_AGENT=Mozilla/5.0
            HTTP_REFERER=http://localhost:9000/
            name%%3Dfoo=hello%%0Aworld

            00001-00005 SELECT 1
            00005-00010 SELECT 2

            traceback-text""" % (versioninfo.branch_nick, versioninfo.revno)))

    def test_read(self):
        """Test ErrorReport.read()"""
        from canonical.launchpad.webapp.errorlog import ErrorReport
        fp = StringIO.StringIO(dedent("""\
            Oops-Id: OOPS-A0001
            Exception-Type: NotFound
            Exception-Value: error message
            Date: 2005-04-01T00:00:00+00:00
            Page-Id: IFoo:+foo-template
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
        # XXX jamesh 2005-11-30:
        # this should probably convert back to a datetime
        self.assertEqual(entry.time, '2005-04-01T00:00:00+00:00')
        self.assertEqual(entry.pageid, 'IFoo:+foo-template')
        self.assertEqual(entry.tb_text, 'traceback-text')
        self.assertEqual(entry.username, 'Sample User')
        self.assertEqual(entry.url, 'http://localhost:9000/foo')
        self.assertEqual(entry.duration, 42)
        self.assertEqual(len(entry.req_vars), 3)
        self.assertEqual(entry.req_vars[0], ('HTTP_USER_AGENT',
                                             'Mozilla/5.0'))
        self.assertEqual(entry.req_vars[1], ('HTTP_REFERER',
                                             'http://localhost:9000/'))
        self.assertEqual(entry.req_vars[2], ('name=foo', 'hello\nworld'))
        self.assertEqual(len(entry.db_statements), 2)
        self.assertEqual(entry.db_statements[0], (1, 5, 'SELECT 1'))
        self.assertEqual(entry.db_statements[1], (5, 10, 'SELECT 2'))


class TestErrorReportingUtility(unittest.TestCase):
    def setUp(self):
        # ErrorReportingUtility reads the global config to get the
        # current error directory.
        test_data = dedent("""
            [error_reports]
            copy_to_zlog: true
            errordir: %s
            """ % tempfile.mkdtemp())
        config.push('test_data', test_data)
        shutil.rmtree(config.error_reports.errordir, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(config.error_reports.errordir, ignore_errors=True)
        test_config_data = config.pop('test_data')
        reset_logging()

    def test_appendToOopsPrefix(self):
        """Test ErrorReportingUtility.appendToOopsPrefix()."""
        utility = ErrorReportingUtility()
        default_prefix = config.launchpad.errorreports.oops_prefix
        self.assertEqual('T', default_prefix)
        self.assertEqual('T', utility.prefix)

        # Some scripts will append a string token to the prefix.
        utility.appendToOopsPrefix('CW')
        self.assertEqual('TCW', utility.prefix)

        # Some scripts run multiple processes and append a string number
        # to the prefix.
        utility.appendToOopsPrefix('1')
        self.assertEqual('T1', utility.prefix)

    def test_newOopsId(self):
        """Test ErrorReportingUtility.newOopsId()"""
        utility = ErrorReportingUtility()

        errordir = config.error_reports.errordir

        # first oops of the day
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-91T1')
        self.assertEqual(filename,
                         os.path.join(errordir, '2006-04-01/01800.T1'))
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(
            utility.lasterrordir, os.path.join(errordir, '2006-04-01'))

        # second oops of the day
        now = datetime.datetime(2006, 04, 01, 12, 00, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-91T2')
        self.assertEqual(filename,
                         os.path.join(errordir, '2006-04-01/43200.T2'))
        self.assertEqual(utility.lastid, 2)
        self.assertEqual(
            utility.lasterrordir, os.path.join(errordir, '2006-04-01'))

        # first oops of following day
        now = datetime.datetime(2006, 04, 02, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-92T1')
        self.assertEqual(filename,
                         os.path.join(errordir, '2006-04-02/01800.T1'))
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(
            utility.lasterrordir, os.path.join(errordir, '2006-04-02'))

        # The oops_prefix honours appendToOopsPrefix().
        utility.appendToOopsPrefix('XXX')
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-92TXXX2')

        # Another oops with a native datetime.
        now = datetime.datetime(2006, 04, 02, 00, 30, 00)
        self.assertRaises(ValueError, utility.newOopsId, now)

    def test_changeErrorDir(self):
        """Test changing the error dir using the global config."""
        utility = ErrorReportingUtility()
        errordir = config.error_reports.errordir

        # First an oops in the original error directory.
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(
            utility.lasterrordir, os.path.join(errordir, '2006-04-01'))

        # ErrorReportingUtility reads the global config to get the
        # current error directory.
        new_errordir = tempfile.mkdtemp()
        errordir_data = dedent("""
            [error_reports]
            errordir: %s
            """ % new_errordir)
        config.push('errordir_data', errordir_data)

        # Now an oops on the same day, in the new directory.
        now = datetime.datetime(2006, 04, 01, 12, 00, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)

        # Since it's a new directory, with no previous oops reports, the
        # id is 1 again, rather than 2.
        self.assertEqual(oopsid, 'OOPS-91T1')
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(
            utility.lasterrordir, os.path.join(new_errordir, '2006-04-01'))

        shutil.rmtree(new_errordir, ignore_errors=True)
        config_data = config.pop('errordir_data')

    def test_findLastOopsId(self):
        """Test ErrorReportingUtility._findLastOopsId()"""
        utility = ErrorReportingUtility()

        self.assertEqual(config.error_reports.oops_prefix, 'T')

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
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise ArbitraryException('xyz')
        except ArbitraryException:
            utility.raising(sys.exc_info(), now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: ArbitraryException\n')
        self.assertEqual(lines[2], 'Exception-Value: xyz\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'Page-Id: \n')
        self.assertEqual(lines[5], 'Branch: %s\n' % versioninfo.branch_nick)
        self.assertEqual(lines[6], 'Revision: %s\n'% versioninfo.revno)
        self.assertEqual(lines[7], 'User: None\n')
        self.assertEqual(lines[8], 'URL: None\n')
        self.assertEqual(lines[9], 'Duration: -1\n')
        self.assertEqual(lines[10], '\n')

        # no request vars
        self.assertEqual(lines[11], '\n')

        # no database statements
        self.assertEqual(lines[12], '\n')

        # traceback
        self.assertEqual(lines[13], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        self.assertEqual(lines[16], 'ArbitraryException: xyz\n')

    def test_raising_with_request(self):
        """Test ErrorReportingUtility.raising() with a request"""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        class TestRequestWithPrincipal(TestRequest):
            def setInWSGIEnvironment(self, key, value):
                self._orig_env[key] = value

            class principal:
                id = 42
                title = u'title'
                # non ASCII description
                description = u'description |\N{BLACK SQUARE}|'

                @staticmethod
                def getLogin():
                    return u'Login'

        request = TestRequestWithPrincipal(
                environ={
                    'SERVER_URL': 'http://localhost:9000/foo',
                    'HTTP_COOKIE': 'lp=cookies_hidden_for_security_reasons',
                    'name1': 'value1',
                    },
                form={
                    'name1': 'value3 \xa7',
                    'name2': 'value2',
                    u'\N{BLACK SQUARE}': u'value4',
                    }
                )
        request.setInWSGIEnvironment('launchpad.pageid', 'IFoo:+foo-template')

        try:
            raise ArbitraryException('xyz\nabc')
        except ArbitraryException:
            utility.raising(sys.exc_info(), request, now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines.pop(0), 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines.pop(0), 'Exception-Type: ArbitraryException\n')
        self.assertEqual(lines.pop(0), 'Exception-Value: xyz abc\n')
        self.assertEqual(lines.pop(0), 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines.pop(0), 'Page-Id: IFoo:+foo-template\n')
        self.assertEqual(
            lines.pop(0), 'Branch: %s\n' % versioninfo.branch_nick)
        self.assertEqual(lines.pop(0), 'Revision: %s\n' % versioninfo.revno)
        self.assertEqual(
            lines.pop(0), 'User: Login, 42, title, description |\\u25a0|\n')
        self.assertEqual(lines.pop(0), 'URL: http://localhost:9000/foo\n')
        self.assertEqual(lines.pop(0), 'Duration: -1\n')
        self.assertEqual(lines.pop(0), '\n')

        # request vars
        self.assertEqual(lines.pop(0), 'CONTENT_LENGTH=0\n')
        self.assertEqual(
            lines.pop(0), 'GATEWAY_INTERFACE=TestFooInterface/1.0\n')
        self.assertEqual(lines.pop(0), 'HTTP_COOKIE=%3Chidden%3E\n')
        self.assertEqual(lines.pop(0), 'HTTP_HOST=127.0.0.1\n')
        self.assertEqual(
            lines.pop(0), 'SERVER_URL=http://localhost:9000/foo\n')

        # non-ASCII request var
        self.assertEqual(lines.pop(0), '\\u25a0=value4\n')
        self.assertEqual(lines.pop(0), 'lp=%3Chidden%3E\n')
        self.assertEqual(lines.pop(0), 'name1=value3 \\xa7\n')
        self.assertEqual(lines.pop(0), 'name2=value2\n')
        self.assertEqual(lines.pop(0), '\n')

        # no database statements
        self.assertEqual(lines.pop(0), '\n')

        # traceback
        self.assertEqual(lines.pop(0), 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        lines.pop(0)
        lines.pop(0)
        self.assertEqual(lines.pop(0), 'ArbitraryException: xyz\n')

        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, 'OOPS-91T1')

    def test_raising_for_script(self):
        """Test ErrorReportingUtility.raising with a ScriptRequest."""
        from canonical.launchpad.webapp.errorlog import ScriptRequest
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise ArbitraryException('xyz\nabc')
        except ArbitraryException:
            # Do not test escaping of request vars here, it is already tested
            # in test_raising_with_request.
            request = ScriptRequest([
                ('name2', 'value2'), ('name1', 'value1'),
                ('name1', 'value3')], URL='https://launchpad.net/example')
            utility.raising(sys.exc_info(), request, now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: ArbitraryException\n')
        self.assertEqual(lines[2], 'Exception-Value: xyz abc\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'Page-Id: \n')
        self.assertEqual(lines[5], 'Branch: %s\n' % versioninfo.branch_nick)
        self.assertEqual(lines[6], 'Revision: %s\n'% versioninfo.revno)
        self.assertEqual(lines[7], 'User: None\n')
        self.assertEqual(lines[8], 'URL: https://launchpad.net/example\n')
        self.assertEqual(lines[9], 'Duration: -1\n')
        self.assertEqual(lines[10], '\n')

        # request vars
        self.assertEqual(lines[11], 'name1=value1\n')
        self.assertEqual(lines[12], 'name1=value3\n')
        self.assertEqual(lines[13], 'name2=value2\n')
        self.assertEqual(lines[14], '\n')

        # no database statements
        self.assertEqual(lines[15], '\n')

        # traceback
        self.assertEqual(lines[16], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        self.assertEqual(lines[19], 'ArbitraryException: xyz\n')

        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, 'OOPS-91T1')


    def test_raising_with_unprintable_exception(self):
        # Test ErrorReportingUtility.raising() with an unprintable exception.
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 01, 01, 00, 30, 00, tzinfo=UTC)

        class UnprintableException(Exception):
            def __str__(self):
                raise RuntimeError('arrgh')

        log = InstalledHandler('SiteError')
        try:
            raise UnprintableException()
        except UnprintableException:
            utility.raising(sys.exc_info(), now=now)
        log.uninstall()

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-1T1\n')
        self.assertEqual(lines[1], 'Exception-Type: UnprintableException\n')
        self.assertEqual(
            lines[2], 'Exception-Value: <unprintable instance object>\n')
        self.assertEqual(lines[3], 'Date: 2006-01-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'Page-Id: \n')
        self.assertEqual(lines[5], 'Branch: %s\n' % versioninfo.branch_nick)
        self.assertEqual(lines[6], 'Revision: %s\n' % versioninfo.revno)
        self.assertEqual(lines[7], 'User: None\n')
        self.assertEqual(lines[8], 'URL: None\n')
        self.assertEqual(lines[9], 'Duration: -1\n')
        self.assertEqual(lines[10], '\n')

        # no request vars
        self.assertEqual(lines[11], '\n')

        # no database statements
        self.assertEqual(lines[12], '\n')

        # traceback
        self.assertEqual(lines[13], 'Traceback (innermost last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise UnprintableException()
        self.assertEqual(
            lines[16], 'UnprintableException: <unprintable instance object>\n'
            )

    def test_raising_unauthorized(self):
        """Test ErrorReportingUtility.raising() with an Unauthorized
        exception.

        An OOPS is not recorded when a Unauthorized exceptions is raised.
        """
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise Unauthorized('xyz')
        except Unauthorized:
            utility.raising(sys.exc_info(), now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertFalse(os.path.exists(errorfile))

    def test_raising_translation_unavailable(self):
        """Test ErrorReportingUtility.raising() with a TranslationUnavailable
        exception.

        An OOPS is not recorded when a TranslationUnavailable exception is
        raised.
        """
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise TranslationUnavailable('xyz')
        except TranslationUnavailable:
            utility.raising(sys.exc_info(), now=now)

        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertFalse(os.path.exists(errorfile))

    def test_raising_with_string_as_traceback(self):
        # ErrorReportingUtility.raising() can be called with a string in the
        # place of a traceback. This is useful when the original traceback
        # object is unavailable.
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise RuntimeError('hello')
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            # Turn the traceback into a string. When the traceback itself
            # cannot be passed to ErrorReportingUtility.raising, a string like
            # one generated by format_exc is sometimes passed instead.
            exc_tb = traceback.format_exc()

        utility.raising((exc_type, exc_value, exc_tb), now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')

        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()

        # the header
        self.assertEqual(lines[0], 'Oops-Id: OOPS-91T1\n')
        self.assertEqual(lines[1], 'Exception-Type: RuntimeError\n')
        self.assertEqual(lines[2], 'Exception-Value: hello\n')
        self.assertEqual(lines[3], 'Date: 2006-04-01T00:30:00+00:00\n')
        self.assertEqual(lines[4], 'Page-Id: \n')
        self.assertEqual(lines[5], 'Branch: %s\n' % versioninfo.branch_nick)
        self.assertEqual(lines[6], 'Revision: %s\n'% versioninfo.revno)
        self.assertEqual(lines[7], 'User: None\n')
        self.assertEqual(lines[8], 'URL: None\n')
        self.assertEqual(lines[9], 'Duration: -1\n')
        self.assertEqual(lines[10], '\n')

        # no request vars
        self.assertEqual(lines[11], '\n')

        # no database statements
        self.assertEqual(lines[12], '\n')

        # traceback
        self.assertEqual(''.join(lines[13:17]), exc_tb)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestErrorReport))
    suite.addTest(unittest.makeSuite(TestErrorReportingUtility))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
