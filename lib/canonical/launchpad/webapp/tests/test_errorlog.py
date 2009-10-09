# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for error logging & OOPS reporting."""

__metaclass__ = type

import datetime
import logging
import os
import shutil
import StringIO
import sys
import tempfile
from textwrap import dedent
import traceback
import unittest

import pytz

from zope.app.publication.tests.test_zopepublication import (
    UnauthenticatedPrincipal)
from zope.interface import directlyProvides
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.security.interfaces import Unauthorized
from zope.testing.loggingsupport import InstalledHandler

from canonical.config import config
from canonical.testing import reset_logging
from canonical.launchpad import versioninfo
from canonical.launchpad.layers import WebServiceLayer
from canonical.launchpad.webapp.errorlog import (
    ErrorReport, ErrorReportingUtility, OopsLoggingHandler, ScriptRequest,
    _is_sensitive)
from canonical.launchpad.webapp.interfaces import TranslationUnavailable
from lazr.restful.declarations import webservice_error
from lp.services.osutils import remove_tree
from lp.testing import TestCase


UTC = pytz.timezone('UTC')


class ArbitraryException(Exception):
    """Used to test handling of exceptions in OOPS reports."""


class TestErrorReport(unittest.TestCase):

    def tearDown(self):
        reset_logging()

    def test___init__(self):
        """Test ErrorReport.__init__()"""
        entry = ErrorReport('id', 'exc-type', 'exc-value', 'timestamp',
                            'pageid', 'traceback-text', 'username', 'url', 42,
                            [('name1', 'value1'), ('name2', 'value2'),
                             ('name1', 'value3')],
                            [(1, 5, 'store_a', 'SELECT 1'),
                             (5, 10, 'store_b', 'SELECT 2')],
                            False)
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
        self.assertEqual(entry.informational, False)
        self.assertEqual(len(entry.req_vars), 3)
        self.assertEqual(entry.req_vars[0], ('name1', 'value1'))
        self.assertEqual(entry.req_vars[1], ('name2', 'value2'))
        self.assertEqual(entry.req_vars[2], ('name1', 'value3'))
        self.assertEqual(len(entry.db_statements), 2)
        self.assertEqual(
            entry.db_statements[0],
            (1, 5, 'store_a', 'SELECT 1'))
        self.assertEqual(
            entry.db_statements[1],
            (5, 10, 'store_b', 'SELECT 2'))

    def test_write(self):
        """Test ErrorReport.write()"""
        entry = ErrorReport('OOPS-A0001', 'NotFound', 'error message',
                            datetime.datetime(2005, 04, 01, 00, 00, 00,
                                              tzinfo=UTC),
                            'IFoo:+foo-template',
                            'traceback-text', 'Sample User',
                            'http://localhost:9000/foo', 42,
                            [('HTTP_USER_AGENT', 'Mozilla/5.0'),
                             ('HTTP_REFERER', 'http://localhost:9000/'),
                             ('name=foo', 'hello\nworld')],
                            [(1, 5, 'store_a', 'SELECT 1'),
                             (5, 10,'store_b', 'SELECT\n2')], False)
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
            Informational: False

            HTTP_USER_AGENT=Mozilla/5.0
            HTTP_REFERER=http://localhost:9000/
            name%%3Dfoo=hello%%0Aworld

            00001-00005@store_a SELECT 1
            00005-00010@store_b SELECT 2

            traceback-text""" % (versioninfo.branch_nick, versioninfo.revno)))

    def test_read(self):
        """Test ErrorReport.read()."""
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

            00001-00005@store_a SELECT 1
            00005-00010@store_b SELECT 2

            traceback-text"""))
        entry = ErrorReport.read(fp)
        self.assertEqual(entry.id, 'OOPS-A0001')
        self.assertEqual(entry.type, 'NotFound')
        self.assertEqual(entry.value, 'error message')
        self.assertEqual(entry.time, datetime.datetime(2005, 4, 1))
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
        self.assertEqual(
            entry.db_statements[0],
            (1, 5, 'store_a', 'SELECT 1'))
        self.assertEqual(
            entry.db_statements[1],
            (5, 10, 'store_b', 'SELECT 2'))


    def test_read_no_store_id(self):
        """Test ErrorReport.read() for old logs with no store_id."""
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
        self.assertEqual(entry.time, datetime.datetime(2005, 4, 1))
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
        self.assertEqual(entry.db_statements[0], (1, 5, None, 'SELECT 1'))
        self.assertEqual(entry.db_statements[1], (5, 10, None, 'SELECT 2'))


class TestErrorReportingUtility(unittest.TestCase):
    def setUp(self):
        # ErrorReportingUtility reads the global config to get the
        # current error directory.
        test_data = dedent("""
            [error_reports]
            copy_to_zlog: true
            error_dir: %s
            """ % tempfile.mkdtemp())
        config.push('test_data', test_data)
        shutil.rmtree(config.error_reports.error_dir, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(config.error_reports.error_dir, ignore_errors=True)
        config.pop('test_data')
        reset_logging()

    def test_configure(self):
        """Test ErrorReportingUtility.setConfigSection()."""
        utility = ErrorReportingUtility()
        # The ErrorReportingUtility uses the config.error_reports section
        # by default.
        self.assertEqual(config.error_reports.oops_prefix, utility.prefix)
        self.assertEqual(config.error_reports.error_dir, utility.error_dir)
        self.assertEqual(
            config.error_reports.copy_to_zlog, utility.copy_to_zlog)
        # Some external processes may use another config section to
        # provide the error log configuration.
        utility.configure(section_name='branchscanner')
        self.assertEqual(config.branchscanner.oops_prefix, utility.prefix)
        self.assertEqual(config.branchscanner.error_dir, utility.error_dir)
        self.assertEqual(
            config.branchscanner.copy_to_zlog, utility.copy_to_zlog)

        # The default error section can be restored.
        utility.configure()
        self.assertEqual(config.error_reports.oops_prefix, utility.prefix)
        self.assertEqual(config.error_reports.error_dir, utility.error_dir)
        self.assertEqual(
            config.error_reports.copy_to_zlog, utility.copy_to_zlog)

    def test_setOopsToken(self):
        """Test ErrorReportingUtility.setOopsToken()."""
        utility = ErrorReportingUtility()
        default_prefix = config.error_reports.oops_prefix
        self.assertEqual('T', default_prefix)
        self.assertEqual('T', utility.prefix)

        # Some scripts will append a string token to the prefix.
        utility.setOopsToken('CW')
        self.assertEqual('TCW', utility.prefix)

        # Some scripts run multiple processes and append a string number
        # to the prefix.
        utility.setOopsToken('1')
        self.assertEqual('T1', utility.prefix)

    def test_newOopsId(self):
        """Test ErrorReportingUtility.newOopsId()"""
        utility = ErrorReportingUtility()

        errordir = config.error_reports.error_dir

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

        # The oops_prefix honours setOopsToken().
        utility.setOopsToken('XXX')
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(oopsid, 'OOPS-92TXXX2')

        # Another oops with a native datetime.
        now = datetime.datetime(2006, 04, 02, 00, 30, 00)
        self.assertRaises(ValueError, utility.newOopsId, now)

    def test_changeErrorDir(self):
        """Test changing the error dir using the global config."""
        utility = ErrorReportingUtility()
        errordir = utility.error_dir

        # First an oops in the original error directory.
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        oopsid, filename = utility.newOopsId(now)
        self.assertEqual(utility.lastid, 1)
        self.assertEqual(
            utility.lasterrordir, os.path.join(errordir, '2006-04-01'))

        # ErrorReportingUtility uses the error_dir attribute to
        # get the current error directory.
        new_errordir = tempfile.mkdtemp()
        utility.error_dir = new_errordir

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
        self.assertEqual(lines[10], 'Informational: False\n')
        self.assertEqual(lines[11], '\n')

        # no request vars
        self.assertEqual(lines[12], '\n')

        # no database statements
        self.assertEqual(lines[13], '\n')

        # traceback
        self.assertEqual(lines[14], 'Traceback (most recent call last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        self.assertEqual(lines[17], 'ArbitraryException: xyz\n')

    def test_raising_with_request(self):
        """Test ErrorReportingUtility.raising() with a request"""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

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
        self.assertEqual(lines.pop(0), 'Informational: False\n')
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
        self.assertEqual(lines.pop(0), 'Traceback (most recent call last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        lines.pop(0)
        lines.pop(0)
        self.assertEqual(lines.pop(0), 'ArbitraryException: xyz\n')

        # verify that the oopsid was set on the request
        self.assertEqual(request.oopsid, 'OOPS-91T1')
        self.assertEqual(request.oops.id, 'OOPS-91T1')

    def test_raising_with_xmlrpc_request(self):
        # Test ErrorReportingUtility.raising() with an XML-RPC request.
        request = TestRequest()
        directlyProvides(request, IXMLRPCRequest)
        request.getPositionalArguments = lambda: (1, 2)
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        try:
            raise ArbitraryException('xyz\nabc')
        except ArbitraryException:
            utility.raising(sys.exc_info(), request, now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.assertTrue(os.path.exists(errorfile))
        lines = open(errorfile, 'r').readlines()
        self.assertEqual(lines[16], 'xmlrpc args=(1, 2)\n')

    def test_raising_with_webservice_request(self):
        # Test ErrorReportingUtility.raising() with a WebServiceRequest
        # request. Only some exceptions result in OOPSes.
        request = TestRequest()
        directlyProvides(request, WebServiceLayer)
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        # Exceptions that don't use webservice_error result in OOPSes.
        try:
            raise ArbitraryException('xyz\nabc')
        except ArbitraryException:
            utility.raising(sys.exc_info(), request, now=now)
            self.assertNotEqual(request.oopsid, None)

        # Exceptions with a webservice_error in the 500 range result
        # in OOPSes.
        class InternalServerError(Exception):
            webservice_error(500)
        try:
            raise InternalServerError("")
        except InternalServerError:
            utility.raising(sys.exc_info(), request, now=now)
            self.assertNotEqual(request.oopsid, None)

        # Exceptions with any other webservice_error do not result
        # in OOPSes.
        class BadDataError(Exception):
            webservice_error(400)
        try:
            raise BadDataError("")
        except BadDataError:
            utility.raising(sys.exc_info(), request, now=now)
            self.assertEqual(request.oopsid, None)

    def test_raising_for_script(self):
        """Test ErrorReportingUtility.raising with a ScriptRequest."""
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
        self.assertEqual(lines[10], 'Informational: False\n')
        self.assertEqual(lines[11], '\n')

        # request vars
        self.assertEqual(lines[12], 'name1=value1\n')
        self.assertEqual(lines[13], 'name1=value3\n')
        self.assertEqual(lines[14], 'name2=value2\n')
        self.assertEqual(lines[15], '\n')

        # no database statements
        self.assertEqual(lines[16], '\n')

        # traceback
        self.assertEqual(lines[17], 'Traceback (most recent call last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        self.assertEqual(lines[20], 'ArbitraryException: xyz\n')

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
        self.assertEqual(lines[10], 'Informational: False\n')
        self.assertEqual(lines[11], '\n')

        # no request vars
        self.assertEqual(lines[12], '\n')

        # no database statements
        self.assertEqual(lines[13], '\n')

        # traceback
        self.assertEqual(lines[14], 'Traceback (most recent call last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise UnprintableException()
        self.assertEqual(
            lines[17], 'UnprintableException: <unprintable instance object>\n'
            )

    def test_raising_unauthorized_without_request(self):
        """Unauthorized exceptions are logged when there's no request."""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        try:
            raise Unauthorized('xyz')
        except Unauthorized:
            utility.raising(sys.exc_info(), now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.failUnless(os.path.exists(errorfile))

    def test_raising_unauthorized_without_principal(self):
        """Unauthorized exceptions are logged when the request has no
        principal."""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        request = ScriptRequest([('name2', 'value2')])
        try:
            raise Unauthorized('xyz')
        except Unauthorized:
            utility.raising(sys.exc_info(), request, now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.failUnless(os.path.exists(errorfile))

    def test_raising_unauthorized_with_unauthenticated_principal(self):
        """Unauthorized exceptions are not logged when the request has an
        unauthenticated principal."""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        request = TestRequestWithUnauthenticatedPrincipal()
        try:
            raise Unauthorized('xyz')
        except Unauthorized:
            utility.raising(sys.exc_info(), request, now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.failIf(os.path.exists(errorfile))

    def test_raising_unauthorized_with_authenticated_principal(self):
        """Unauthorized exceptions are logged when the request has an
        authenticated principal."""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)
        request = TestRequestWithPrincipal()
        try:
            raise Unauthorized('xyz')
        except Unauthorized:
            utility.raising(sys.exc_info(), request, now=now)
        errorfile = os.path.join(utility.errordir(now), '01800.T1')
        self.failUnless(os.path.exists(errorfile))

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
        self.assertEqual(lines[10], 'Informational: False\n')
        self.assertEqual(lines[11], '\n')

        # no request vars
        self.assertEqual(lines[12], '\n')

        # no database statements
        self.assertEqual(lines[13], '\n')

        # traceback
        self.assertEqual(''.join(lines[14:18]), exc_tb)

    def test_handling(self):
        """Test ErrorReportingUtility.handling()."""
        utility = ErrorReportingUtility()
        now = datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC)

        try:
            raise ArbitraryException('xyz')
        except ArbitraryException:
            utility.handling(sys.exc_info(), now=now)

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
        self.assertEqual(lines[10], 'Informational: True\n')
        self.assertEqual(lines[11], '\n')

        # no request vars
        self.assertEqual(lines[12], '\n')

        # no database statements
        self.assertEqual(lines[13], '\n')

        # traceback
        self.assertEqual(lines[14], 'Traceback (most recent call last):\n')
        #  Module canonical.launchpad.webapp.ftests.test_errorlog, ...
        #    raise ArbitraryException(\'xyz\')
        self.assertEqual(lines[17], 'ArbitraryException: xyz\n')


class TestSensitiveRequestVariables(unittest.TestCase):
    """Test request variables that should not end up in the stored OOPS.

    The _is_sensitive() method will return True for any variable name that
    should not be included in the OOPS.
    """

    def test_oauth_signature_is_sensitive(self):
        """The OAuth signature can be in the body of a POST request, but if
        that happens we don't want it to be included in the OOPS, so we need
        to mark it as sensitive.
        """
        request = TestRequest(
            environ={'SERVER_URL': 'http://api.launchpad.dev'},
            form={'oauth_signature': '&BTXPJ6pQTvh49r9p'})
        self.failUnless(_is_sensitive(request, 'oauth_signature'))


class TestRequestWithUnauthenticatedPrincipal(TestRequest):
    principal = UnauthenticatedPrincipal(42)


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


class TestOopsLoggingHandler(TestCase):
    """Tests for a Python logging handler that logs OOPSes."""

    def assertOopsMatches(self, report, exc_type, exc_value):
        """Assert that 'report' is an OOPS of a particular exception.

        :param report: An `IErrorReport`.
        :param exc_type: The string of an exception type.
        :param exc_value: The string of an exception value.
        """
        self.assertEqual(exc_type, report.type)
        self.assertEqual(exc_value, report.value)
        self.assertTrue(
            report.tb_text.startswith('Traceback (most recent call last):\n'),
            report.tb_text)
        self.assertEqual('', report.pageid)
        self.assertEqual('None', report.username)
        self.assertEqual('None', report.url)
        self.assertEqual([], report.req_vars)
        self.assertEqual([], report.db_statements)

    def setUp(self):
        TestCase.setUp(self)
        self.logger = logging.getLogger(self.factory.getUniqueString())
        self.error_utility = ErrorReportingUtility()
        self.error_utility.error_dir = tempfile.mkdtemp()
        self.logger.addHandler(
            OopsLoggingHandler(error_utility=self.error_utility))
        self.addCleanup(remove_tree, self.error_utility.error_dir)

    def test_exception_records_oops(self):
        # When OopsLoggingHandler is a handler for a logger, any exceptions
        # logged will have OOPS reports generated for them.
        error_message = self.factory.getUniqueString()
        try:
            ignored = 1/0
        except ZeroDivisionError:
            self.logger.exception(error_message)
        oops_report = self.error_utility.getLastOopsReport()
        self.assertOopsMatches(
            oops_report, 'ZeroDivisionError',
            'integer division or modulo by zero')

    def test_warning_does_nothing(self):
        # Logging a warning doesn't generate an OOPS.
        self.logger.warning("Cheeseburger")
        self.assertIs(None, self.error_utility.getLastOopsReport())

    def test_error_does_nothing(self):
        # Logging an error without an exception does nothing.
        self.logger.error("Delicious ponies")
        self.assertIs(None, self.error_utility.getLastOopsReport())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
