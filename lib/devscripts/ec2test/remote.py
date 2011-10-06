#!/usr/bin/env python
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run tests in a daemon.

 * `EC2Runner` handles the daemonization and instance shutdown.

 * `Request` knows everything about the test request we're handling (e.g.
   "test merging foo-bar-bug-12345 into db-devel").

 * `LaunchpadTester` knows how to actually run the tests and gather the
   results. It uses `SummaryResult` to do so.

 * `WebTestLogger` knows how to display the results to the user, and is given
   the responsibility of handling the results that `LaunchpadTester` gathers.
"""

__metatype__ = type

import datetime
from email import MIMEMultipart, MIMEText
from email.mime.application import MIMEApplication
import errno
import gzip
import optparse
import os
import pickle
from StringIO import StringIO
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import unittest
from xml.sax.saxutils import escape

import bzrlib.branch
import bzrlib.config
from bzrlib.email_message import EmailMessage
import bzrlib.errors
from bzrlib.smtp_connection import SMTPConnection
import bzrlib.workingtree
import simplejson
import subunit
from testtools import MultiTestResult

# We need to be able to unpickle objects from bzr-pqm, so make sure we
# can import it.
bzrlib.plugin.load_plugins()


class NonZeroExitCode(Exception):
    """Raised when the child process exits with a non-zero exit code."""

    def __init__(self, retcode):
        super(NonZeroExitCode, self).__init__(
            'Test process died with exit code %r, but no tests failed.'
            % (retcode,))


class SummaryResult(unittest.TestResult):
    """Test result object used to generate the summary."""

    double_line = '=' * 70
    single_line = '-' * 70

    def __init__(self, output_stream):
        super(SummaryResult, self).__init__()
        self.stream = output_stream

    def _formatError(self, flavor, test, error):
        return '\n'.join(
            [self.double_line,
             '%s: %s' % (flavor, test),
             self.single_line,
             error,
             ''])

    def addError(self, test, error):
        super(SummaryResult, self).addError(test, error)
        self.stream.write(
            self._formatError(
                'ERROR', test, self._exc_info_to_string(error, test)))

    def addFailure(self, test, error):
        super(SummaryResult, self).addFailure(test, error)
        self.stream.write(
            self._formatError(
                'FAILURE', test, self._exc_info_to_string(error, test)))

    def stopTest(self, test):
        super(SummaryResult, self).stopTest(test)
        # At the very least, we should be sure that a test's output has been
        # completely displayed once it has stopped.
        self.stream.flush()


class FailureUpdateResult(unittest.TestResult):

    def __init__(self, logger):
        super(FailureUpdateResult, self).__init__()
        self._logger = logger

    def addError(self, *args, **kwargs):
        super(FailureUpdateResult, self).addError(*args, **kwargs)
        self._logger.got_failure()

    def addFailure(self, *args, **kwargs):
        super(FailureUpdateResult, self).addFailure(*args, **kwargs)
        self._logger.got_failure()


class EC2Runner:
    """Runs generic code in an EC2 instance.

    Handles daemonization, instance shutdown, and email in the case of
    catastrophic failure.
    """

    # XXX: JonathanLange 2010-08-17: EC2Runner needs tests.

    # The number of seconds we give this script to clean itself up, and for
    # 'ec2 test --postmortem' to grab control if needed.  If we don't give
    # --postmortem enough time to log in via SSH and take control, then this
    # server will begin to shutdown on its own.
    #
    # (FWIW, "grab control" means sending SIGTERM to this script's process id,
    # thus preventing fail-safe shutdown.)
    SHUTDOWN_DELAY = 60

    def __init__(self, daemonize, pid_filename, shutdown_when_done,
                 smtp_connection=None, emails=None):
        """Make an EC2Runner.

        :param daemonize: Whether or not we will daemonize.
        :param pid_filename: The filename to store the pid in.
        :param shutdown_when_done: Whether or not to shut down when the tests
            are done.
        :param smtp_connection: The `SMTPConnection` to use to send email.
        :param emails: The email address(es) to send catastrophic failure
            messages to. If not provided, the error disappears into the ether.
        """
        self._should_daemonize = daemonize
        self._pid_filename = pid_filename
        self._shutdown_when_done = shutdown_when_done
        if smtp_connection is None:
            config = bzrlib.config.GlobalConfig()
            smtp_connection = SMTPConnection(config)
        self._smtp_connection = smtp_connection
        self._emails = emails
        self._daemonized = False

    def _daemonize(self):
        """Turn the testrunner into a forked daemon process."""
        # This also writes our pidfile to disk to a specific location.  The
        # ec2test.py --postmortem command will look there to find our PID,
        # in order to control this process.
        daemonize(self._pid_filename)
        self._daemonized = True

    def _shutdown_instance(self):
        """Shut down this EC2 instance."""
        # Make sure our process is daemonized, and has therefore disconnected
        # the controlling terminal.  This also disconnects the ec2test.py SSH
        # connection, thus signalling ec2test.py that it may now try to take
        # control of the server.
        if not self._daemonized:
            # We only want to do this if we haven't already been daemonized.
            # Nesting daemons is bad.
            self._daemonize()

        time.sleep(self.SHUTDOWN_DELAY)

        # Cancel the running shutdown.
        subprocess.call(['sudo', 'shutdown', '-c'])

        # We'll only get here if --postmortem didn't kill us.  This is our
        # fail-safe shutdown, in case the user got disconnected or suffered
        # some other mishap that would prevent them from shutting down this
        # server on their own.
        subprocess.call(['sudo', 'shutdown', '-P', 'now'])

    def run(self, name, function, *args, **kwargs):
        try:
            if self._should_daemonize:
                print 'Starting %s daemon...' % (name,)
                self._daemonize()

            return function(*args, **kwargs)
        except:
            config = bzrlib.config.GlobalConfig()
            # Handle exceptions thrown by the test() or daemonize() methods.
            if self._emails:
                msg = EmailMessage(
                    from_address=config.username(),
                    to_address=self._emails,
                    subject='%s FAILED' % (name,),
                    body=traceback.format_exc())
                self._smtp_connection.send_email(msg)
            raise
        finally:
            # When everything is over, if we've been ask to shut down, then
            # make sure we're daemonized, then shutdown.  Otherwise, if we're
            # daemonized, just clean up the pidfile.
            if self._shutdown_when_done:
                self._shutdown_instance()
            elif self._daemonized:
                # It would be nice to clean up after ourselves, since we won't
                # be shutting down.
                remove_pidfile(self._pid_filename)
            else:
                # We're not a daemon, and we're not shutting down.  The user
                # most likely started this script manually, from a shell
                # running on the instance itself.
                pass


class LaunchpadTester:
    """Runs Launchpad tests and gathers their results in a useful way."""

    def __init__(self, logger, test_directory, test_options=()):
        """Construct a TestOnMergeRunner.

        :param logger: The WebTestLogger to log to.
        :param test_directory: The directory to run the tests in. We expect
            this directory to have a fully-functional checkout of Launchpad
            and its dependent branches.
        :param test_options: A sequence of options to pass to the test runner.
        """
        self._logger = logger
        self._test_directory = test_directory
        self._test_options = ' '.join(test_options)

    def build_test_command(self):
        """Return the command that will execute the test suite.

        Should return a list of command options suitable for submission to
        subprocess.call()

        Subclasses must provide their own implementation of this method.
        """
        command = ['make', 'check']
        if self._test_options:
            command.append('TESTOPTS="%s"' % self._test_options)
        return command

    def _spawn_test_process(self):
        """Actually run the tests.

        :return: A `subprocess.Popen` object for the test run.
        """
        call = self.build_test_command()
        self._logger.write_line("Running %s" % (call,))
        # bufsize=0 means do not buffer any of the output. We want to
        # display the test output as soon as it is generated.
        return subprocess.Popen(
            call, bufsize=0,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=self._test_directory)

    def test(self):
        """Run the tests, log the results.

        Signals the ec2test process and cleans up the logs once all the tests
        have completed.  If necessary, submits the branch to PQM, and mails
        the user the test results.
        """
        self._logger.prepare()
        try:
            popen = self._spawn_test_process()
            result = self._gather_test_output(popen.stdout, self._logger)
            retcode = popen.wait()
            # The process could have an error not indicated by an actual test
            # result nor by a raised exception
            if result.wasSuccessful() and retcode:
                raise NonZeroExitCode(retcode)
        except:
            self._logger.error_in_testrunner(sys.exc_info())
        else:
            self._logger.got_result(result)

    def _gather_test_output(self, input_stream, logger):
        """Write the testrunner output to the logs."""
        summary_stream = logger.get_summary_stream()
        summary_result = SummaryResult(summary_stream)
        result = MultiTestResult(
            summary_result,
            FailureUpdateResult(logger))
        subunit_server = subunit.TestProtocolServer(result, summary_stream)
        for line in input_stream:
            subunit_server.lineReceived(line)
            logger.got_line(line)
            summary_stream.flush()
        return summary_result


# XXX: Publish a JSON file that includes the relevant details from this
# request.
class Request:
    """A request to have a branch tested and maybe landed."""

    def __init__(self, branch_url, revno, local_branch_path, sourcecode_path,
                 emails=None, pqm_message=None, smtp_connection=None):
        """Construct a `Request`.

        :param branch_url: The public URL to the Launchpad branch we are
            testing.
        :param revno: The revision number of the branch we are testing.
        :param local_branch_path: A local path to the Launchpad branch we are
            testing.  This must be a branch of Launchpad with a working tree.
        :param sourcecode_path: A local path to the sourcecode dependencies
            directory (normally '$local_branch_path/sourcecode'). This must
            contain up-to-date copies of all of Launchpad's sourcecode
            dependencies.
        :param emails: A list of emails to send the results to. If not
            provided, no emails are sent.
        :param pqm_message: The message to submit to PQM. If not provided, we
            don't submit to PQM.
        :param smtp_connection: The `SMTPConnection` to use to send email.
        """
        self._branch_url = branch_url
        self._revno = revno
        self._local_branch_path = local_branch_path
        self._sourcecode_path = sourcecode_path
        self._emails = emails
        self._pqm_message = pqm_message
        # Used for figuring out how to send emails.
        self._bzr_config = bzrlib.config.GlobalConfig()
        if smtp_connection is None:
            smtp_connection = SMTPConnection(self._bzr_config)
        self._smtp_connection = smtp_connection

    def _send_email(self, message):
        """Actually send 'message'."""
        self._smtp_connection.send_email(message)

    def _format_test_list(self, header, tests):
        if not tests:
            return []
        tests = ['  ' + test.id() for test, error in tests]
        return [header, '-' * len(header)] + tests + ['']

    def format_result(self, result, start_time, end_time):
        duration = end_time - start_time
        output = [
            'Tests started at approximately %s' % start_time,
            ]
        source = self.get_source_details()
        if source:
            output.append('Source: %s r%s' % source)
        target = self.get_target_details()
        if target:
            output.append('Target: %s r%s' % target)
        output.extend([
            '',
            '%s tests run in %s, %s failures, %s errors' % (
                result.testsRun, duration, len(result.failures),
                len(result.errors)),
            '',
            ])

        bad_tests = (
            self._format_test_list('Failing tests', result.failures) +
            self._format_test_list('Tests with errors', result.errors))
        output.extend(bad_tests)

        if bad_tests:
            full_error_stream = StringIO()
            copy_result = SummaryResult(full_error_stream)
            for test, error in result.failures:
                full_error_stream.write(
                    copy_result._formatError('FAILURE', test, error))
            for test, error in result.errors:
                full_error_stream.write(
                    copy_result._formatError('ERROR', test, error))
            output.append(full_error_stream.getvalue())

        subject = self._get_pqm_subject()
        if subject:
            if result.wasSuccessful():
                output.append('SUBMITTED TO PQM:')
            else:
                output.append('**NOT** submitted to PQM:')
            output.extend([subject, ''])
        output.extend(['(See the attached file for the complete log)', ''])
        return '\n'.join(output)

    def get_target_details(self):
        """Return (branch_url, revno) for trunk."""
        branch = bzrlib.branch.Branch.open(self._local_branch_path)
        return branch.get_parent().encode('utf-8'), branch.revno()

    def get_source_details(self):
        """Return (branch_url, revno) for the branch we're merging in.

        If we're not merging in a branch, but instead just testing a trunk,
        then return None.
        """
        tree = bzrlib.workingtree.WorkingTree.open(self._local_branch_path)
        parent_ids = tree.get_parent_ids()
        if len(parent_ids) < 2:
            return None
        return self._branch_url.encode('utf-8'), self._revno

    def _last_segment(self, url):
        """Return the last segment of a URL."""
        return url.strip('/').split('/')[-1]

    def get_nick(self):
        """Get the nick of the branch we are testing."""
        details = self.get_source_details()
        if not details:
            details = self.get_target_details()
        url, revno = details
        return self._last_segment(url)

    def get_revno(self):
        """Get the revno of the branch we are testing."""
        if self._revno is not None:
            return self._revno
        return bzrlib.branch.Branch.open(self._local_branch_path).revno()

    def get_merge_description(self):
        """Get a description of the merge request.

        If we're merging a branch, return '$SOURCE_NICK => $TARGET_NICK', if
        we're just running tests for a trunk branch without merging return
        '$TRUNK_NICK'.
        """
        source = self.get_source_details()
        if not source:
            return '%s r%s' % (self.get_nick(), self.get_revno())
        target = self.get_target_details()
        return '%s => %s' % (
            self._last_segment(source[0]), self._last_segment(target[0]))

    def get_summary_commit(self):
        """Get a message summarizing the change from the commit log.

        Returns the last commit message of the merged branch, or None.
        """
        # XXX: JonathanLange 2010-08-17: I don't actually know why we are
        # using this commit message as a summary message. It's used in the
        # test logs and the EC2 hosted web page.
        branch = bzrlib.branch.Branch.open(self._local_branch_path)
        tree = bzrlib.workingtree.WorkingTree.open(self._local_branch_path)
        parent_ids = tree.get_parent_ids()
        if len(parent_ids) == 1:
            return None
        summary = (
            branch.repository.get_revision(parent_ids[1]).get_summary())
        return summary.encode('utf-8')

    def _build_report_email(self, successful, body_text, full_log_gz):
        """Build a MIME email summarizing the test results.

        :param successful: True for pass, False for failure.
        :param body_text: The body of the email to send to the requesters.
        :param full_log_gz: A gzip of the full log.
        """
        message = MIMEMultipart.MIMEMultipart()
        message['To'] = ', '.join(self._emails)
        message['From'] = self._bzr_config.username()
        if successful:
            status = 'SUCCESS'
        else:
            status = 'FAILURE'
        subject = 'Test results: %s: %s' % (
            self.get_merge_description(), status)
        message['Subject'] = subject

        # Make the body.
        body = MIMEText.MIMEText(body_text, 'plain', 'utf8')
        body['Content-Disposition'] = 'inline'
        message.attach(body)

        # Attach the gzipped log.
        zipped_log = MIMEApplication(full_log_gz, 'x-gzip')
        zipped_log.add_header(
            'Content-Disposition', 'attachment',
            filename='%s-r%s.subunit.gz' % (
                self.get_nick(), self.get_revno()))
        message.attach(zipped_log)
        return message

    def send_report_email(self, successful, body_text, full_log_gz):
        """Send an email summarizing the test results.

        :param successful: True for pass, False for failure.
        :param body_text: The body of the email to send to the requesters.
        :param full_log_gz: A gzip of the full log.
        """
        message = self._build_report_email(successful, body_text, full_log_gz)
        self._send_email(message)

    def iter_dependency_branches(self):
        """Iterate through the Bazaar branches we depend on."""
        for name in sorted(os.listdir(self._sourcecode_path)):
            path = os.path.join(self._sourcecode_path, name)
            if os.path.isdir(path):
                try:
                    branch = bzrlib.branch.Branch.open(path)
                except bzrlib.errors.NotBranchError:
                    continue
                yield name, branch.get_parent(), branch.revno()

    def _get_pqm_subject(self):
        if not self._pqm_message:
            return
        return self._pqm_message.get('Subject')

    def submit_to_pqm(self, successful):
        """Submit this request to PQM, if successful & configured to do so."""
        subject = self._get_pqm_subject()
        if subject and successful:
            self._send_email(self._pqm_message)
        return subject

    @property
    def wants_email(self):
        """Do the requesters want emails sent to them?"""
        return bool(self._emails)


class WebTestLogger:
    """Logs test output to disk and a simple web page.

    :ivar successful: Whether the logger has received only successful input up
        until now.
    """

    def __init__(self, full_log_filename, summary_filename, index_filename,
                 request, echo_to_stdout):
        """Construct a WebTestLogger.

        Because this writes an HTML file with links to the summary and full
        logs, you should construct this object with
        `WebTestLogger.make_in_directory`, which guarantees that the files
        are available in the correct locations.

        :param full_log_filename: Path to a file that will have the full
            log output written to it. The file will be overwritten.
        :param summary_file: Path to a file that will have a human-readable
            summary written to it. The file will be overwritten.
        :param index_file: Path to a file that will have an HTML page
            written to it. The file will be overwritten.
        :param request: A `Request` object representing the thing that's being
            tested.
        :param echo_to_stdout: Whether or not we should echo output to stdout.
        """
        self._full_log_filename = full_log_filename
        self._summary_filename = summary_filename
        self._index_filename = index_filename
        self._info_json = os.path.join(
            os.path.dirname(index_filename), 'info.json')
        self._request = request
        self._echo_to_stdout = echo_to_stdout
        # Actually set by prepare(), but setting to a dummy value to make
        # testing easier.
        self._start_time = datetime.datetime.utcnow()
        self.successful = True

    @classmethod
    def make_in_directory(cls, www_dir, request, echo_to_stdout):
        """Make a logger that logs to specific files in `www_dir`.

        :param www_dir: The directory in which to log the files:
            current_test.log, summary.log and index.html. These files
            will be overwritten.
        :param request: A `Request` object representing the thing that's being
            tested.
        :param echo_to_stdout: Whether or not we should echo output to stdout.
        """
        files = [
            os.path.join(www_dir, 'current_test.log'),
            os.path.join(www_dir, 'summary.log'),
            os.path.join(www_dir, 'index.html')]
        files.extend([request, echo_to_stdout])
        return cls(*files)

    def error_in_testrunner(self, exc_info):
        """Called when there is a catastrophic error in the test runner."""
        exc_type, exc_value, exc_tb = exc_info
        # XXX: JonathanLange 2010-08-17: This should probably log to the full
        # log as well.
        summary = self.get_summary_stream()
        summary.write('\n\nERROR IN TESTRUNNER\n\n')
        traceback.print_exception(exc_type, exc_value, exc_tb, file=summary)
        summary.flush()
        if self._request.wants_email:
            self._write_to_filename(
                self._summary_filename,
                '\n(See the attached file for the complete log)\n')
            summary = self.get_summary_contents()
            full_log_gz = gzip_data(self.get_full_log_contents())
            self._request.send_report_email(False, summary, full_log_gz)

    def get_index_contents(self):
        """Return the contents of the index.html page."""
        return self._get_contents(self._index_filename)

    def get_full_log_contents(self):
        """Return the contents of the complete log."""
        return self._get_contents(self._full_log_filename)

    def get_summary_contents(self):
        """Return the contents of the summary log."""
        return self._get_contents(self._summary_filename)

    def get_summary_stream(self):
        """Return a stream that, when written to, writes to the summary."""
        return open(self._summary_filename, 'a')

    def got_line(self, line):
        """Called when we get a line of output from our child processes."""
        self._write_to_filename(self._full_log_filename, line)
        if self._echo_to_stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

    def _get_contents(self, filename):
        """Get the full contents of 'filename'."""
        try:
            return open(filename, 'r').read()
        except IOError, e:
            if e.errno == errno.ENOENT:
                return ''

    def got_failure(self):
        """Called when we receive word that a test has failed."""
        self.successful = False
        self._dump_json()

    def got_result(self, result):
        """The tests are done and the results are known."""
        self._end_time = datetime.datetime.utcnow()
        successful = result.wasSuccessful()
        self._handle_pqm_submission(successful)
        if self._request.wants_email:
            email_text = self._request.format_result(
                result, self._start_time, self._end_time)
            full_log_gz = gzip_data(self.get_full_log_contents())
            self._request.send_report_email(successful, email_text, full_log_gz)

    def _handle_pqm_submission(self, successful):
        subject = self._request.submit_to_pqm(successful)
        if not subject:
            return
        self.write_line('')
        self.write_line('')
        if successful:
            self.write_line('SUBMITTED TO PQM:')
        else:
            self.write_line('**NOT** submitted to PQM:')
        self.write_line(subject)

    def _write_to_filename(self, filename, msg):
        fd = open(filename, 'a')
        fd.write(msg)
        fd.flush()
        fd.close()

    def _write(self, msg):
        """Write to the summary and full log file."""
        self._write_to_filename(self._full_log_filename, msg)
        self._write_to_filename(self._summary_filename, msg)

    def write_line(self, msg):
        """Write to the summary and full log file with a newline."""
        self._write(msg + '\n')

    def _dump_json(self):
        fd = open(self._info_json, 'w')
        simplejson.dump(
            {'description': self._request.get_merge_description(),
             'failed-yet': not self.successful,
             }, fd)
        fd.close()

    def prepare(self):
        """Prepares the log files on disk.

        Writes three log files: the raw output log, the filtered "summary"
        log file, and a HTML index page summarizing the test run paramters.
        """
        self._dump_json()
        # XXX: JonathanLange 2010-07-18: Mostly untested.
        log = self.write_line

        # Clear the existing index file.
        index = open(self._index_filename, 'w')
        index.truncate(0)
        index.close()

        def add_to_html(html):
            return self._write_to_filename(
                self._index_filename, textwrap.dedent(html))

        self._start_time = datetime.datetime.utcnow()
        msg = 'Tests started at approximately %(now)s UTC' % {
            'now': self._start_time.strftime('%a, %d %b %Y %H:%M:%S')}
        add_to_html('''\
            <html>
              <head>
                <title>Testing</title>
              </head>
              <body>
                <h1>Testing</h1>
                <p>%s</p>
                <ul>
                  <li><a href="summary.log">Summary results</a></li>
                  <li><a href="current_test.log">Full results</a></li>
                </ul>
            ''' % (msg,))
        log(msg)

        add_to_html('''\
            <h2>Branches Tested</h2>
            ''')

        # Describe the trunk branch.
        trunk, trunk_revno = self._request.get_target_details()
        msg = '%s, revision %d\n' % (trunk, trunk_revno)
        add_to_html('''\
            <p><strong>%s</strong></p>
            ''' % (escape(msg),))
        log(msg)

        branch_details = self._request.get_source_details()
        if not branch_details:
            add_to_html('<p>(no merged branch)</p>\n')
            log('(no merged branch)')
        else:
            branch_name, branch_revno = branch_details
            data = {'name': branch_name,
                    'revno': branch_revno,
                    'commit': self._request.get_summary_commit()}
            msg = ('%(name)s, revision %(revno)d '
                   '(commit message: %(commit)s)\n' % data)
            add_to_html('''\
               <p>Merged with<br />%(msg)s</p>
               ''' % {'msg': escape(msg)})
            log("Merged with")
            log(msg)

        add_to_html('<dl>\n')
        log('\nDEPENDENCY BRANCHES USED\n')
        for name, branch, revno in self._request.iter_dependency_branches():
            data = {'name': name, 'branch': branch, 'revno': revno}
            log(
                '- %(name)s\n    %(branch)s\n    %(revno)d\n' % data)
            escaped_data = {'name': escape(name),
                            'branch': escape(branch),
                            'revno': revno}
            add_to_html('''\
                <dt>%(name)s</dt>
                  <dd>%(branch)s</dd>
                  <dd>%(revno)s</dd>
                ''' % escaped_data)
        add_to_html('''\
                </dl>
              </body>
            </html>''')
        log('\n\nTEST RESULTS FOLLOW\n\n')


def daemonize(pid_filename):
    # this seems like the sort of thing that ought to be in the
    # standard library :-/
    pid = os.fork()
    if (pid == 0): # Child 1
        os.setsid()
        pid = os.fork()
        if (pid == 0): # Child 2, the daemon.
            pass # lookie, we're ready to do work in the daemon
        else:
            os._exit(0)
    else: # Parent
        # Make sure the pidfile is written before we exit, so that people
        # who've chosen to daemonize can quickly rectify their mistake.  Since
        # the daemon might terminate itself very, very quickly, we cannot poll
        # for the existence of the pidfile. Instead, we just sleep for a
        # reasonable amount of time.
        time.sleep(1)
        os._exit(0)

    # write a pidfile ASAP
    write_pidfile(pid_filename)

   # Iterate through and close all file descriptors.
    import resource
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    assert maxfd != resource.RLIM_INFINITY
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:
            # we assume fd was closed
            pass
    os.open(os.devnull, os.O_RDWR) # this will be 0
    os.dup2(0, 1)
    os.dup2(0, 2)


def gunzip_data(data):
    """Decompress 'data'.

    :param data: The gzip data to decompress.
    :return: The decompressed data.
    """
    fd, path = tempfile.mkstemp()
    os.write(fd, data)
    os.close(fd)
    try:
        return gzip.open(path, 'r').read()
    finally:
        os.unlink(path)


def gzip_data(data):
    """Compress 'data'.

    :param data: The data to compress.
    :return: The gzip-compressed data.
    """
    fd, path = tempfile.mkstemp()
    os.close(fd)
    gz = gzip.open(path, 'wb')
    gz.writelines(data)
    gz.close()
    try:
        return open(path).read()
    finally:
        os.unlink(path)


def write_pidfile(pid_filename):
    """Write a pidfile for the current process."""
    pid_file = open(pid_filename, "w")
    pid_file.write(str(os.getpid()))
    pid_file.close()


def remove_pidfile(pid_filename):
    if os.path.exists(pid_filename):
        os.remove(pid_filename)


def parse_options(argv):
    """Make an `optparse.OptionParser` for running the tests remotely.
    """
    parser = optparse.OptionParser(
        usage="%prog [options] [-- test options]",
        description=("Build and run tests for an instance."))
    parser.add_option(
        '-e', '--email', action='append', dest='email', default=None,
        help=('Email address to which results should be mailed.  Defaults to '
              'the email address from `bzr whoami`. May be supplied multiple '
              'times. `bzr whoami` will be used as the From: address.'))
    parser.add_option(
        '-s', '--submit-pqm-message', dest='pqm_message', default=None,
        help=('A base64-encoded pickle (string) of a pqm message '
              '(bzrib.plugins.pqm.pqm_submit.PQMEmailMessage) to submit if '
              'the test run is successful.'))
    parser.add_option(
        '--daemon', dest='daemon', default=False,
        action='store_true', help=('Run test in background as daemon.'))
    parser.add_option(
        '--debug', dest='debug', default=False,
        action='store_true',
        help=('Drop to pdb trace as soon as possible.'))
    parser.add_option(
        '--shutdown', dest='shutdown', default=False,
        action='store_true',
        help=('Terminate (shutdown) instance after completion.'))
    parser.add_option(
        '--public-branch', dest='public_branch', default=None,
        help=('The URL of the public branch being tested.'))
    parser.add_option(
        '--public-branch-revno', dest='public_branch_revno',
        type="int", default=None,
        help=('The revision number of the public branch being tested.'))

    return parser.parse_args(argv)


def main(argv):
    options, args = parse_options(argv)

    if options.debug:
        import pdb; pdb.set_trace()
    if options.pqm_message is not None:
        pqm_message = pickle.loads(
            options.pqm_message.decode('string-escape').decode('base64'))
    else:
        pqm_message = None

    # Locations for Launchpad. These are actually defined by the configuration
    # of the EC2 image that we use.
    LAUNCHPAD_DIR = '/var/launchpad'
    TEST_DIR = os.path.join(LAUNCHPAD_DIR, 'test')
    SOURCECODE_DIR = os.path.join(TEST_DIR, 'sourcecode')

    pid_filename = os.path.join(LAUNCHPAD_DIR, 'ec2test-remote.pid')

    smtp_connection = SMTPConnection(bzrlib.config.GlobalConfig())

    request = Request(
        options.public_branch, options.public_branch_revno, TEST_DIR,
        SOURCECODE_DIR, options.email, pqm_message, smtp_connection)
    # Only write to stdout if we are running as the foreground process.
    echo_to_stdout = not options.daemon
    logger = WebTestLogger.make_in_directory(
        '/var/www', request, echo_to_stdout)

    runner = EC2Runner(
        options.daemon, pid_filename, options.shutdown,
        smtp_connection, options.email)

    tester = LaunchpadTester(logger, TEST_DIR, test_options=args[1:])
    runner.run("Test runner", tester.test)


if __name__ == '__main__':
    main(sys.argv)
