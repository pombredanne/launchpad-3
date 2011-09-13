# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

from datetime import datetime, timedelta
import doctest
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import gzip
from itertools import izip
import os
from StringIO import StringIO
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

import simplejson

from bzrlib.config import GlobalConfig
from bzrlib.tests import TestCaseWithTransport

from testtools import TestCase, TestResult
from testtools.content import Content
from testtools.content_type import ContentType
from testtools.matchers import DocTestMatches

from devscripts.ec2test.remote import (
    EC2Runner,
    FailureUpdateResult,
    gunzip_data,
    gzip_data,
    LaunchpadTester,
    remove_pidfile,
    Request,
    SummaryResult,
    WebTestLogger,
    write_pidfile,
    )


class LoggingSMTPConnection(object):
    """An SMTPConnection double that logs sent email."""

    def __init__(self, log):
        self._log = log

    def send_email(self, message):
        self._log.append(message)


class RequestHelpers:

    def patch(self, obj, name, value):
        orig = getattr(obj, name)
        setattr(obj, name, value)
        self.addCleanup(setattr, obj, name, orig)
        return orig

    def make_trunk(self, parent_url='http://example.com/bzr/trunk'):
        """Make a trunk branch suitable for use with `Request`.

        `Request` expects to be given a path to a working tree that has a
        branch with a configured parent URL, so this helper returns such a
        working tree.
        """
        nick = parent_url.strip('/').split('/')[-1]
        tree = self.make_branch_and_tree(nick)
        tree.branch.set_parent(parent_url)
        return tree

    def make_request(self, branch_url=None, revno=None,
                     trunk=None, sourcecode_path=None,
                     emails=None, pqm_message=None, emails_sent=None):
        """Make a request to test, specifying only things we care about.

        Note that the returned request object will not ever send email, but
        will instead append "sent" emails to the list provided here as
        'emails_sent'.
        """
        if trunk is None:
            trunk = self.make_trunk()
        if sourcecode_path is None:
            sourcecode_path = self.make_sourcecode(
                [('a', 'http://example.com/bzr/a', 2),
                 ('b', 'http://example.com/bzr/b', 3),
                 ('c', 'http://example.com/bzr/c', 5)])
        if emails_sent is None:
            emails_sent = []
        smtp_connection = LoggingSMTPConnection(emails_sent)
        request = Request(
            branch_url, revno, trunk.basedir, sourcecode_path, emails,
            pqm_message, smtp_connection)
        return request

    def make_sourcecode(self, branches):
        """Make a sourcecode directory with sample branches.

        :param branches: A list of (name, parent_url, revno) tuples.
        :return: The path to the sourcecode directory.
        """
        self.build_tree(['sourcecode/'])
        for name, parent_url, revno in branches:
            tree = self.make_branch_and_tree('sourcecode/%s' % (name,))
            tree.branch.set_parent(parent_url)
            for i in range(revno):
                tree.commit(message=str(i))
        return 'sourcecode/'

    def make_tester(self, logger=None, test_directory=None, test_options=()):
        if not logger:
            logger = self.make_logger()
        return LaunchpadTester(logger, test_directory, test_options)

    def make_logger(self, request=None, echo_to_stdout=False):
        if request is None:
            request = self.make_request()
        return WebTestLogger(
            'full.log', 'summary.log', 'index.html', request, echo_to_stdout)


class TestSummaryResult(TestCase):
    """Tests for `SummaryResult`."""

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_formatError(self):
        # SummaryResult._formatError() combines the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        result = SummaryResult(None)
        output = result._formatError('FOO', 'test', 'error')
        expected = '%s\nFOO: test\n%s\nerror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, output)

    def test_addError(self):
        # SummaryResult.addError doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'ERROR', test, result._exc_info_to_string(error, test))
        result.addError(test, error)
        self.assertEqual(expected, stream.getvalue())

    def test_addFailure_does_not_write_immediately(self):
        # SummaryResult.addFailure doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'FAILURE', test, result._exc_info_to_string(error, test))
        result.addFailure(test, error)
        self.assertEqual(expected, stream.getvalue())

    def test_stopTest_flushes_stream(self):
        # SummaryResult.stopTest() flushes the stream.
        stream = StringIO()
        flush_calls = []
        stream.flush = lambda: flush_calls.append(None)
        result = SummaryResult(stream)
        result.stopTest(self)
        self.assertEqual(1, len(flush_calls))


class TestFailureUpdateResult(TestCaseWithTransport, RequestHelpers):

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_addError_is_unsuccessful(self):
        logger = self.make_logger()
        result = FailureUpdateResult(logger)
        result.addError(self, self.makeException())
        self.assertEqual(False, logger.successful)

    def test_addFailure_is_unsuccessful(self):
        logger = self.make_logger()
        result = FailureUpdateResult(logger)
        result.addFailure(self, self.makeException(AssertionError))
        self.assertEqual(False, logger.successful)


class FakePopen:
    """Fake Popen object so we don't have to spawn processes in tests."""

    def __init__(self, output, exit_status):
        self.stdout = StringIO(output)
        self._exit_status = exit_status

    def wait(self):
        return self._exit_status


class TestLaunchpadTester(TestCaseWithTransport, RequestHelpers):

    def test_build_test_command_no_options(self):
        # The LaunchpadTester runs "make check" if given no options.
        tester = self.make_tester()
        command = tester.build_test_command()
        self.assertEqual(['make', 'check'], command)

    def test_build_test_command_options(self):
        # The LaunchpadTester runs 'make check TESTOPTIONS="<options>"' if
        # given options.
        tester = self.make_tester(test_options=('-vvv', '--subunit'))
        command = tester.build_test_command()
        self.assertEqual(
            ['make', 'check', 'TESTOPTS="-vvv --subunit"'], command)

    def test_spawn_test_process(self):
        # _spawn_test_process uses subprocess.Popen to run the command
        # returned by build_test_command. stdout & stderr are piped together,
        # the cwd is the test directory specified in the constructor, and the
        # bufsize is zore, meaning "don't buffer".
        popen_calls = []
        self.patch(
            subprocess, 'Popen',
            lambda *args, **kwargs: popen_calls.append((args, kwargs)))
        tester = self.make_tester(test_directory='test-directory')
        tester._spawn_test_process()
        self.assertEqual(
            [((tester.build_test_command(),),
              {'bufsize': 0,
               'stdout': subprocess.PIPE,
               'stderr': subprocess.STDOUT,
               'cwd': 'test-directory'})], popen_calls)

    def test_running_test(self):
        # LaunchpadTester.test() runs the test command, and then calls
        # got_result with the result.  This test is more of a smoke test to
        # make sure that everything integrates well.
        message = {'Subject': "One Crowded Hour"}
        log = []
        request = self.make_request(pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        tester = self.make_tester(logger=logger)
        output = "test output\n"
        tester._spawn_test_process = lambda: FakePopen(output, 0)
        tester.test()
        # Message being sent implies got_result thought it got a success.
        self.assertEqual([message], log)

    def test_failing_test(self):
        # If LaunchpadTester gets a failing test, then it records that on the
        # logger.
        logger = self.make_logger()
        tester = self.make_tester(logger=logger)
        output = "test: foo\nerror: foo\n"
        tester._spawn_test_process = lambda: FakePopen(output, 0)
        tester.test()
        self.assertEqual(False, logger.successful)

    def test_error_in_testrunner(self):
        # Any exception is raised within LaunchpadTester.test() is an error in
        # the testrunner. When we detect these, we do three things:
        #   1. Log the error to the logger using error_in_testrunner
        #   2. Call got_result with a False value, indicating test suite
        #      failure.
        #   3. Re-raise the error. In the script, this triggers an email.
        message = {'Subject': "One Crowded Hour"}
        log = []
        request = self.make_request(pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        tester = self.make_tester(logger=logger)
        # Break the test runner deliberately. In production, this is more
        # likely to be a system error than a programming error.
        tester._spawn_test_process = lambda: 1/0
        tester.test()
        # Message not being sent implies got_result thought it got a failure.
        self.assertEqual([], log)
        self.assertIn("ERROR IN TESTRUNNER", logger.get_summary_contents())
        self.assertIn("ZeroDivisionError", logger.get_summary_contents())

    def test_nonzero_exit_code(self):
        message = {'Subject': "One Crowded Hour"}
        log = []
        request = self.make_request(pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        tester = self.make_tester(logger=logger)
        output = "test output\n"
        tester._spawn_test_process = lambda: FakePopen(output, 10)
        tester.test()
        # Message not being sent implies got_result thought it got a failure.
        self.assertEqual([], log)

    def test_gather_test_output(self):
        # LaunchpadTester._gather_test_output() summarises the output
        # stream as a TestResult.
        logger = self.make_logger()
        tester = self.make_tester(logger=logger)
        result = tester._gather_test_output(
            ['test: test_failure', 'failure: test_failure',
             'test: test_success', 'successful: test_success'],
            logger)
        self.assertEquals(2, result.testsRun)
        self.assertEquals(1, len(result.failures))


class TestPidfileHelpers(TestCase):
    """Tests for `write_pidfile` and `remove_pidfile`."""

    def test_write_pidfile(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.unlink, path)
        os.close(fd)
        write_pidfile(path)
        self.assertEqual(os.getpid(), int(open(path, 'r').read()))

    def test_remove_pidfile(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        write_pidfile(path)
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))

    def test_remove_nonexistent_pidfile(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, 'doesntexist')
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))


class TestGzip(TestCase):
    """Tests for gzip helpers."""

    def test_gzip_data(self):
        data = 'foobarbaz\n'
        compressed = gzip_data(data)
        fd, path = tempfile.mkstemp()
        os.write(fd, compressed)
        os.close(fd)
        self.assertEqual(data, gzip.open(path, 'r').read())

    def test_gunzip_data(self):
        data = 'foobarbaz\n'
        compressed = gzip_data(data)
        self.assertEqual(data, gunzip_data(compressed))


class TestRequest(TestCaseWithTransport, RequestHelpers):
    """Tests for `Request`."""

    def test_doesnt_want_email(self):
        # If no email addresses were provided, then the user does not want to
        # receive email.
        req = self.make_request()
        self.assertEqual(False, req.wants_email)

    def test_wants_email(self):
        # If some email addresses were provided, then the user wants to
        # receive email.
        req = self.make_request(emails=['foo@example.com'])
        self.assertEqual(True, req.wants_email)

    def test_get_target_details(self):
        parent = 'http://example.com/bzr/branch'
        tree = self.make_trunk(parent)
        req = self.make_request(trunk=tree)
        self.assertEqual(
            (parent, tree.branch.revno()), req.get_target_details())

    def test_get_revno_target_only(self):
        # If there's only a target branch, then the revno is the revno of that
        # branch.
        parent = 'http://example.com/bzr/branch'
        tree = self.make_trunk(parent)
        req = self.make_request(trunk=tree)
        self.assertEqual(tree.branch.revno(), req.get_revno())

    def test_get_revno_source_and_target(self):
        # If we're merging in a branch, then the revno is the revno of the
        # branch we're merging in.
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual(42, req.get_revno())

    def test_get_source_details_no_commits(self):
        req = self.make_request(trunk=self.make_trunk())
        self.assertEqual(None, req.get_source_details())

    def test_get_source_details_no_merge(self):
        tree = self.make_trunk()
        tree.commit(message='foo')
        req = self.make_request(trunk=tree)
        self.assertEqual(None, req.get_source_details())

    def test_get_source_details_merge(self):
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual(
            ('https://example.com/bzr/thing', 42), req.get_source_details())

    def test_get_nick_trunk_only(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel')
        req = self.make_request(trunk=tree)
        self.assertEqual('db-devel', req.get_nick())

    def test_get_nick_merge(self):
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual('thing', req.get_nick())

    def test_get_merge_description_trunk_only(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel')
        req = self.make_request(trunk=tree)
        self.assertEqual(
            'db-devel r%s' % req.get_revno(), req.get_merge_description())

    def test_get_merge_description_merge(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel/')
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual('thing => db-devel', req.get_merge_description())

    def test_get_summary_commit(self):
        # The summary commit message is the last commit message of the branch
        # we're merging in.
        trunk = self.make_trunk()
        trunk.commit(message="a starting point")
        thing_bzrdir = trunk.branch.bzrdir.sprout('thing')
        thing = thing_bzrdir.open_workingtree()
        thing.commit(message="a new thing")
        trunk.merge_from_branch(thing.branch)
        req = self.make_request(
            branch_url='https://example.com/bzr/thing',
            revno=thing.branch.revno(),
            trunk=trunk)
        self.assertEqual("a new thing", req.get_summary_commit())

    def test_iter_dependency_branches(self):
        # iter_dependency_branches yields a list of branches in the sourcecode
        # directory, along with their parent URLs and their revnos.
        sourcecode_branches = [
            ('b', 'http://example.com/parent-b', 3),
            ('a', 'http://example.com/parent-a', 2),
            ('c', 'http://example.com/parent-c', 5),
            ]
        sourcecode_path = self.make_sourcecode(sourcecode_branches)
        self.build_tree(
            ['%s/not-a-branch/' % sourcecode_path,
             '%s/just-a-file' % sourcecode_path])
        req = self.make_request(sourcecode_path=sourcecode_path)
        branches = list(req.iter_dependency_branches())
        self.assertEqual(sorted(sourcecode_branches), branches)

    def test_submit_to_pqm_no_message(self):
        # If there's no PQM message, then 'submit_to_pqm' returns None.
        req = self.make_request(pqm_message=None)
        subject = req.submit_to_pqm(successful=True)
        self.assertIs(None, subject)

    def test_submit_to_pqm_no_message_doesnt_send(self):
        # If there's no PQM message, then 'submit_to_pqm' returns None.
        log = []
        req = self.make_request(pqm_message=None, emails_sent=log)
        req.submit_to_pqm(successful=True)
        self.assertEqual([], log)

    def test_submit_to_pqm_unsuccessful(self):
        # submit_to_pqm returns the subject of the PQM mail even if it's
        # handling a failed test run.
        message = {'Subject': 'My PQM message'}
        req = self.make_request(pqm_message=message)
        subject = req.submit_to_pqm(successful=False)
        self.assertIs(message.get('Subject'), subject)

    def test_submit_to_pqm_unsuccessful_no_email(self):
        # submit_to_pqm doesn't send any email if the run was unsuccessful.
        message = {'Subject': 'My PQM message'}
        log = []
        req = self.make_request(pqm_message=message, emails_sent=log)
        req.submit_to_pqm(successful=False)
        self.assertEqual([], log)

    def test_submit_to_pqm_successful(self):
        # submit_to_pqm returns the subject of the PQM mail.
        message = {'Subject': 'My PQM message'}
        log = []
        req = self.make_request(pqm_message=message, emails_sent=log)
        subject = req.submit_to_pqm(successful=True)
        self.assertIs(message.get('Subject'), subject)
        self.assertEqual([message], log)

    def test_report_email_subject_success(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(True, 'foo', 'gobbledygook')
        self.assertEqual(
            'Test results: %s: SUCCESS' % req.get_merge_description(),
            email['Subject'])

    def test_report_email_subject_failure(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(False, 'foo', 'gobbledygook')
        self.assertEqual(
            'Test results: %s: FAILURE' % req.get_merge_description(),
            email['Subject'])

    def test_report_email_recipients(self):
        req = self.make_request(emails=['foo@example.com', 'bar@example.com'])
        email = req._build_report_email(False, 'foo', 'gobbledygook')
        self.assertEqual('foo@example.com, bar@example.com', email['To'])

    def test_report_email_sender(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(False, 'foo', 'gobbledygook')
        self.assertEqual(GlobalConfig().username(), email['From'])

    def test_report_email_body(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(False, 'foo', 'gobbledygook')
        [body, attachment] = email.get_payload()
        self.assertIsInstance(body, MIMEText)
        self.assertEqual('inline', body['Content-Disposition'])
        self.assertIn(
            body['Content-Type'],
            ['text/plain; charset="utf-8"', 'text/plain; charset="utf8"'])
        self.assertEqual("foo", body.get_payload(decode=True))

    def test_report_email_attachment(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(False, "foo", "gobbledygook")
        [body, attachment] = email.get_payload()
        self.assertIsInstance(attachment, MIMEApplication)
        self.assertEqual('application/x-gzip', attachment['Content-Type'])
        self.assertEqual(
            'attachment; filename="%s-r%s.subunit.gz"' % (
                req.get_nick(), req.get_revno()),
            attachment['Content-Disposition'])
        self.assertEqual(
            "gobbledygook", attachment.get_payload(decode=True))

    def test_send_report_email_sends_email(self):
        log = []
        req = self.make_request(emails=['foo@example.com'], emails_sent=log)
        expected = req._build_report_email(False, "foo", "gobbledygook")
        req.send_report_email(False, "foo", "gobbledygook")
        [observed] = log
        # The standard library sucks. None of the MIME objects have __eq__
        # implementations.
        for expected_part, observed_part in izip(
            expected.walk(), observed.walk()):
            self.assertEqual(type(expected_part), type(observed_part))
            self.assertEqual(expected_part.items(), observed_part.items())
            self.assertEqual(
                expected_part.is_multipart(), observed_part.is_multipart())
            if not expected_part.is_multipart():
                self.assertEqual(
                    expected_part.get_payload(), observed_part.get_payload())

    def test_format_result_success(self):

        class SomeTest(TestCase):

            def test_a(self):
                pass

            def test_b(self):
                pass

            def test_c(self):
                pass

        test = unittest.TestSuite(map(SomeTest, ['test_' + x for x in 'abc']))
        result = TestResult()
        test.run(result)
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        source_branch, source_revno = req.get_source_details()
        target_branch, target_revno = req.get_target_details()
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=1)
        data = {
            'source_branch': source_branch,
            'source_revno': source_revno,
            'target_branch': target_branch,
            'target_revno': target_revno,
            'start_time': str(start_time),
            'duration': str(end_time - start_time),
            'num_tests': result.testsRun,
            'num_failures': len(result.failures),
            'num_errors': len(result.errors),
            }
        result_text = req.format_result(result, start_time, end_time)
        self.assertThat(
            result_text, DocTestMatches("""\
Tests started at approximately %(start_time)s
Source: %(source_branch)s r%(source_revno)s
Target: %(target_branch)s r%(target_revno)s
<BLANKLINE>
%(num_tests)s tests run in %(duration)s, %(num_failures)s failures, \
%(num_errors)s errors
<BLANKLINE>
(See the attached file for the complete log)
""" % data, doctest.REPORT_NDIFF | doctest.ELLIPSIS))

    def test_format_result_with_errors(self):

        class SomeTest(TestCase):

            def test_ok(self):
                pass

            def test_fail(self):
                self.fail("oh no")

            def test_error(self):
                1/0

        fail_test = SomeTest('test_fail')
        error_test = SomeTest('test_error')
        test = unittest.TestSuite(
            [fail_test, error_test, SomeTest('test_ok')])
        result = TestResult()
        test.run(result)
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        source_branch, source_revno = req.get_source_details()
        target_branch, target_revno = req.get_target_details()
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=1)
        data = {
            'source_branch': source_branch,
            'source_revno': source_revno,
            'target_branch': target_branch,
            'target_revno': target_revno,
            'start_time': str(start_time),
            'duration': str(end_time - start_time),
            'fail_id': fail_test.id(),
            'error_id': error_test.id(),
            'num_tests': result.testsRun,
            'num_failures': len(result.failures),
            'num_errors': len(result.errors),
            }
        result_text = req.format_result(result, start_time, end_time)
        self.assertThat(
            result_text, DocTestMatches("""\
Tests started at approximately %(start_time)s
Source: %(source_branch)s r%(source_revno)s
Target: %(target_branch)s r%(target_revno)s
<BLANKLINE>
%(num_tests)s tests run in %(duration)s, %(num_failures)s failures, \
%(num_errors)s errors
<BLANKLINE>
Failing tests
-------------
  %(fail_id)s
<BLANKLINE>
Tests with errors
-----------------
  %(error_id)s
<BLANKLINE>
======================================================================
FAILURE: test_fail...
----------------------------------------------------------------------
Traceback (most recent call last):
...
<BLANKLINE>
======================================================================
ERROR: test_error...
----------------------------------------------------------------------
Traceback (most recent call last):
...
<BLANKLINE>
<BLANKLINE>
(See the attached file for the complete log)
""" % data, doctest.REPORT_NDIFF | doctest.ELLIPSIS))


class TestWebTestLogger(TestCaseWithTransport, RequestHelpers):

    def test_make_in_directory(self):
        # WebTestLogger.make_in_directory constructs a logger that writes to a
        # bunch of specific files in a directory.
        self.build_tree(['www/'])
        request = self.make_request()
        logger = WebTestLogger.make_in_directory('www', request, False)
        # A method on logger that writes to _everything_.
        logger.prepare()
        self.assertEqual(
            logger.get_summary_contents(), open('www/summary.log').read())
        self.assertEqual(
            logger.get_full_log_contents(),
            open('www/current_test.log').read())
        self.assertEqual(
            logger.get_index_contents(), open('www/index.html').read())

    def test_initial_full_log(self):
        # Initially, the full log has nothing in it.
        logger = self.make_logger()
        self.assertEqual('', logger.get_full_log_contents())

    def test_initial_summary_contents(self):
        # Initially, the summary log has nothing in it.
        logger = self.make_logger()
        self.assertEqual('', logger.get_summary_contents())

    def test_initial_json(self):
        self.build_tree(['www/'])
        request = self.make_request()
        logger = WebTestLogger.make_in_directory('www', request, False)
        logger.prepare()
        self.assertEqual(
            {'description': request.get_merge_description(),
             'failed-yet': False,
             },
            simplejson.loads(open('www/info.json').read()))

    def test_initial_success(self):
        # The Logger initially thinks it is successful because there have been
        # no failures yet.
        logger = self.make_logger()
        self.assertEqual(True, logger.successful)

    def test_got_failure_changes_success(self):
        # Logger.got_failure() tells the logger it is no longer successful.
        logger = self.make_logger()
        logger.got_failure()
        self.assertEqual(False, logger.successful)

    def test_got_failure_updates_json(self):
        # Logger.got_failure() updates JSON so that interested parties can
        # determine that it is unsuccessful.
        self.build_tree(['www/'])
        request = self.make_request()
        logger = WebTestLogger.make_in_directory('www', request, False)
        logger.prepare()
        logger.got_failure()
        self.assertEqual(
            {'description': request.get_merge_description(),
             'failed-yet': True,
             },
            simplejson.loads(open('www/info.json').read()))

    def test_got_line_no_echo(self):
        # got_line forwards the line to the full log, but does not forward to
        # stdout if echo_to_stdout is False.
        stdout = StringIO()
        self.patch(sys, 'stdout', stdout)
        logger = self.make_logger(echo_to_stdout=False)
        logger.got_line("output from script\n")
        self.assertEqual(
            "output from script\n", logger.get_full_log_contents())
        self.assertEqual("", stdout.getvalue())

    def test_got_line_echo(self):
        # got_line forwards the line to the full log, and to stdout if
        # echo_to_stdout is True.
        stdout = StringIO()
        self.patch(sys, 'stdout', stdout)
        logger = self.make_logger(echo_to_stdout=True)
        logger.got_line("output from script\n")
        self.assertEqual(
            "output from script\n", logger.get_full_log_contents())
        self.assertEqual("output from script\n", stdout.getvalue())

    def test_write_line(self):
        # write_line writes a line to both the full log and the summary log.
        logger = self.make_logger()
        logger.write_line('foo')
        self.assertEqual('foo\n', logger.get_full_log_contents())
        self.assertEqual('foo\n', logger.get_summary_contents())

    def test_error_in_testrunner_logs_to_summary(self):
        # error_in_testrunner logs the traceback to the summary log in a very
        # prominent way.
        try:
            1/0
        except ZeroDivisionError:
            exc_info = sys.exc_info()
        stack = ''.join(traceback.format_exception(*exc_info))
        logger = self.make_logger()
        logger.error_in_testrunner(exc_info)
        self.assertEqual(
            "\n\nERROR IN TESTRUNNER\n\n%s" % (stack,),
            logger.get_summary_contents())

    def test_error_in_testrunner_sends_email(self):
        # If email addresses are configurd, error_in_testrunner emails them
        # with the failure and the full log.
        try:
            1/0
        except ZeroDivisionError:
            exc_info = sys.exc_info()
        log = []
        request = self.make_request(
            emails=['foo@example.com'], emails_sent=log)
        logger = self.make_logger(request=request)
        logger.error_in_testrunner(exc_info)
        [email] = log
        self.assertEqual(
            'Test results: %s: FAILURE' % request.get_merge_description(),
            email['Subject'])
        [body, attachment] = email.get_payload()
        self.assertIsInstance(body, MIMEText)
        self.assertEqual('inline', body['Content-Disposition'])
        self.assertIn(
            body['Content-Type'],
            ['text/plain; charset="utf-8"', 'text/plain; charset="utf8"'])
        self.assertEqual(
            logger.get_summary_contents(), body.get_payload(decode=True))
        self.assertIsInstance(attachment, MIMEApplication)
        self.assertEqual('application/x-gzip', attachment['Content-Type'])
        self.assertEqual(
            'attachment;',
            attachment['Content-Disposition'][:len('attachment;')])
        self.assertEqual(
            logger.get_full_log_contents(),
            gunzip_data(attachment.get_payload().decode('base64')))


class TestEC2Runner(TestCaseWithTransport, RequestHelpers):

    def make_ec2runner(self, emails=None, email_log=None):
        if email_log is None:
            email_log = []
        smtp_connection = LoggingSMTPConnection(email_log)
        return EC2Runner(
            False, "who-cares.pid", False, smtp_connection, emails=emails)

    def test_run(self):
        # EC2Runner.run() runs the given function, passing through whatever
        # arguments and keyword arguments it has been given.
        calls = []
        runner = self.make_ec2runner()

        def function(*args, **kwargs):
            calls.append((args, kwargs))
        runner.run("boring test method", function, "foo", "bar", baz="qux")
        self.assertEqual([(("foo", "bar"), {'baz': 'qux'})], calls)

    def test_email_on_failure_no_emails(self):
        # If no emails are specified, then no email is sent on failure.
        log = []
        runner = self.make_ec2runner(email_log=log)
        self.assertRaises(
            ZeroDivisionError, runner.run, "failing method", lambda: 1/0)
        self.assertEqual([], log)

    def test_email_on_failure_some_emails(self):
        # If emails *are* specified, then an email is sent on failure.
        log = []
        runner = self.make_ec2runner(
            email_log=log, emails=["foo@example.com"])
        self.assertRaises(
            ZeroDivisionError, runner.run, "failing method", lambda: 1/0)
        # XXX: Expect this to fail. Fix the test to be more correct.
        [message] = log
        self.assertEqual('failing method FAILED', message['Subject'])
        self.assertEqual('foo@example.com', message['To'])
        self.assertIn('ZeroDivisionError', str(message))

    def test_email_with_launchpad_tester_failure(self):
        # LaunchpadTester sends email on catastrophic failure.
        email_log = []
        to_emails = ['foo@example.com']
        request = self.make_request(emails=to_emails, emails_sent=email_log)
        logger = self.make_logger(request=request)
        tester = self.make_tester(logger=logger)
        # Deliberately break 'tester'.  A likely failure in production is not
        # being able to spawn the child process.
        tester._spawn_test_process = lambda: 1/0
        runner = self.make_ec2runner(emails=to_emails, email_log=email_log)
        runner.run("launchpad tester", tester.test)
        # The primary thing we care about is that email *was* sent.
        self.assertNotEqual([], email_log)
        [tester_msg] = email_log
        self.assertEqual('foo@example.com', tester_msg['To'])
        self.assertIn(
            'ZeroDivisionError',
            tester_msg.get_payload()[0].get_payload(decode=True))


class TestDaemonizationInteraction(TestCaseWithTransport, RequestHelpers):

    script_file = 'remote_daemonization_test.py'

    def run_script(self, script_file, pidfile, directory, logfile):
        path = os.path.join(os.path.dirname(__file__), script_file)
        popen = subprocess.Popen(
            [sys.executable, path, pidfile, directory, logfile],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = popen.communicate()
        self.assertEqual((0, '', ''), (popen.returncode, stdout, stderr))
        # Make sure the daemon is finished doing its thing.
        while os.path.exists(pidfile):
            time.sleep(0.01)
        # If anything was written to 'logfile' while the script was running,
        # we want it to appear in our test errors.  This way, stack traces in
        # the script are visible to us as test runners.
        if os.path.exists(logfile):
            content_type = ContentType("text", "plain", {"charset": "utf8"})
            content = Content(content_type, open(logfile).read)
            self.addDetail('logfile', content)

    def test_daemonization(self):
        # Daemonizing something can do funny things to its behavior. This test
        # runs a script that's very similar to remote.py but only does
        # "logger.prepare".
        pidfile = "%s.pid" % self.id()
        directory = 'www'
        logfile = "%s.log" % self.id()
        self.run_script(self.script_file, pidfile, directory, logfile)
        # Check that the output from the daemonized version matches the output
        # from a normal version. Only checking one of the files, since this is
        # more of a smoke test than a correctness test.
        logger = self.make_logger()
        logger.prepare()
        expected_summary = logger.get_summary_contents()
        observed_summary = open(os.path.join(directory, 'summary.log')).read()
        # The first line contains a timestamp, so we ignore it.
        self.assertEqual(
            expected_summary.splitlines()[1:],
            observed_summary.splitlines()[1:])


class TestResultHandling(TestCaseWithTransport, RequestHelpers):
    """Tests for how we handle the result at the end of the test suite."""

    def get_body_text(self, email):
        return email.get_payload()[0].get_payload(decode=True)

    def make_empty_result(self):
        return TestResult()

    def make_successful_result(self):
        result = self.make_empty_result()
        result.startTest(self)
        result.stopTest(self)
        return result

    def make_failing_result(self):
        result = self.make_empty_result()
        result.startTest(self)
        try:
            1/0
        except ZeroDivisionError:
            result.addError(self, sys.exc_info())
        result.stopTest(self)
        return result

    def test_success_no_emails(self):
        log = []
        request = self.make_request(emails=[], emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_successful_result())
        self.assertEqual([], log)

    def test_failure_no_emails(self):
        log = []
        request = self.make_request(emails=[], emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_failing_result())
        self.assertEqual([], log)

    def test_submits_to_pqm_on_success(self):
        log = []
        message = {'Subject': 'foo'}
        request = self.make_request(
            emails=[], pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_successful_result())
        self.assertEqual([message], log)

    def test_records_pqm_submission_in_email(self):
        log = []
        message = {'Subject': 'foo'}
        request = self.make_request(
            emails=['foo@example.com'], pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_successful_result())
        [pqm_message, user_message] = log
        self.assertEqual(message, pqm_message)
        self.assertIn(
            'SUBMITTED TO PQM:\n%s' % (message['Subject'],),
            self.get_body_text(user_message))

    def test_doesnt_submit_to_pqm_on_failure(self):
        log = []
        message = {'Subject': 'foo'}
        request = self.make_request(
            emails=[], pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_failing_result())
        self.assertEqual([], log)

    def test_records_non_pqm_submission_in_email(self):
        log = []
        message = {'Subject': 'foo'}
        request = self.make_request(
            emails=['foo@example.com'], pqm_message=message, emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_failing_result())
        [user_message] = log
        self.assertIn(
            '**NOT** submitted to PQM:\n%s' % (message['Subject'],),
            self.get_body_text(user_message))

    def test_email_refers_to_attached_log(self):
        log = []
        request = self.make_request(
            emails=['foo@example.com'], emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_result(self.make_failing_result())
        [user_message] = log
        self.assertIn(
            '(See the attached file for the complete log)\n',
            self.get_body_text(user_message))

    def test_email_body_is_format_result(self):
        # The body of the email sent to the user is the summary file.
        log = []
        request = self.make_request(
            emails=['foo@example.com'], emails_sent=log)
        logger = self.make_logger(request=request)
        result = self.make_failing_result()
        logger.got_result(result)
        [user_message] = log
        self.assertEqual(
            request.format_result(
                result, logger._start_time, logger._end_time),
            self.get_body_text(user_message))

    def test_gzip_of_full_log_attached(self):
        # The full log is attached to the email.
        log = []
        request = self.make_request(
            emails=['foo@example.com'], emails_sent=log)
        logger = self.make_logger(request=request)
        logger.got_line("output from test process\n")
        logger.got_line("more output\n")
        logger.got_result(self.make_successful_result())
        [user_message] = log
        [body, attachment] = user_message.get_payload()
        self.assertEqual('application/x-gzip', attachment['Content-Type'])
        self.assertEqual(
            'attachment;',
            attachment['Content-Disposition'][:len('attachment;')])
        attachment_contents = attachment.get_payload().decode('base64')
        uncompressed = gunzip_data(attachment_contents)
        self.assertEqual(
            "output from test process\nmore output\n", uncompressed)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
