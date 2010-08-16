#!/usr/bin/env python
# Run tests in a daemon.
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metatype__ = type

import datetime
from email import MIMEMultipart, MIMEText
from email.mime.application import MIMEApplication
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
import bzrlib.email_message
import bzrlib.errors
import bzrlib.smtp_connection
import bzrlib.workingtree

import subunit


class SummaryResult(unittest.TestResult):
    """Test result object used to generate the summary."""

    double_line = '=' * 70
    single_line = '-' * 70

    def __init__(self, output_stream):
        super(SummaryResult, self).__init__()
        self.stream = output_stream
        self._buffered_results = StringIO()

    def _formatError(self, flavor, test, error):
        return '\n'.join(
            [self.double_line,
             '%s: %s' % (flavor, test),
             self.single_line,
             error,
             ''])

    def printError(self, flavor, test, error):
        """Print an error to the output stream."""
        self.stream.write(self._formatError(flavor, test, error))
        self.stream.flush()

    def addError(self, test, error):
        super(SummaryResult, self).addError(test, error)
        self._buffered_results.write(
            self._formatError(
                'ERROR', test, self._exc_info_to_string(error, test)))

    def addFailure(self, test, error):
        super(SummaryResult, self).addFailure(test, error)
        self._buffered_results.write(
            self._formatError(
                'FAILURE', test, self._exc_info_to_string(error, test)))

    def stopTestRun(self):
        # XXX: What we *actually* want is for a list of failing tests to be
        # written before the summary.
        self.stream.write(self._buffered_results.getvalue())


class FlagFallStream:
    """Wrapper around a stream that only starts forwarding after a flagfall.
    """

    def __init__(self, stream, flag):
        """Construct a `FlagFallStream` that wraps 'stream'.

        :param stream: A stream, a file-like object.
        :param flag: A string that needs to be written to this stream before
            we start forwarding the output.
        """
        self._stream = stream
        self._flag = flag
        self._flag_fallen = False

    def write(self, bytes):
        if self._flag_fallen:
            self._stream.write(bytes)
        else:
            index = bytes.find(self._flag)
            if index == -1:
                return
            else:
                self._stream.write(bytes[index:])
                self._flag_fallen = True

    def flush(self):
        self._stream.flush()


class EC2Runner:
    """Runs generic code in an EC2 instance.

    Handles daemonization, instance shutdown, and email in the case of
    catastrophic failure.
    """

    # The number of seconds we give this script to clean itself up, and for
    # 'ec2 test --postmortem' to grab control if needed.  If we don't give
    # --postmortem enough time to log in via SSH and take control, then this
    # server will begin to shutdown on its own.
    #
    # (FWIW, "grab control" means sending SIGTERM to this script's process id,
    # thus preventing fail-safe shutdown.)
    SHUTDOWN_DELAY = 60

    def __init__(self, daemonize, pid_filename, shutdown_when_done,
                 emails=None):
        """Make an EC2Runner.

        :param daemonize: Whether or not we will daemonize.
        :param pid_filename: The filename to store the pid in.
        :param shutdown_when_done: Whether or not to shut down when the tests
            are done.
        :param emails: The email address(es) to send catastrophic failure
            messages to. If not provided, the error disappears into the ether.
        """
        self._should_daemonize = daemonize
        self._pid_filename = pid_filename
        self._shutdown_when_done = shutdown_when_done
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
                bzrlib.email_message.EmailMessage.send(
                    config, config.username(),
                    self._emails, '%s FAILED' % (name,),
                    traceback.format_exc())
            raise
        finally:
            # When everything is over, if we've been ask to shut down, then
            # make sure we're daemonized, then shutdown.  Otherwise, if we're
            # daemonized, just clean up the pidfile.
            if self._should_shutdown:
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

    def __init__(self, logger, test_directory, test_options=None):
        """Construct a TestOnMergeRunner.

        :param logger: The WebTestLogger to log to.
        :param test_directory: The directory to run the tests in. We expect
            this directory to have a fully-functional checkout of Launchpad
            and its dependent branches.
        :param test_options: Options to pass to the test runner.
        """
        self.logger = logger
        self._test_directory = test_directory
        self._test_options = test_options

    def build_test_command(self):
        """Return the command that will execute the test suite.

        Should return a list of command options suitable for submission to
        subprocess.call()

        Subclasses must provide their own implementation of this method.
        """
        command = ['make', 'check', 'TESTOPTS=' + self._test_options]
        return command

    def test(self):
        """Run the tests, log the results.

        Signals the ec2test process and cleans up the logs once all the tests
        have completed.  If necessary, submits the branch to PQM, and mails
        the user the test results.
        """
        self.logger.prepare()

        call = self.build_test_command()

        try:
            popen = subprocess.Popen(
                call, bufsize=-1,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=self._testdirectory)

            self._gather_test_output(popen.stdout, self.logger)

            exit_status = popen.wait()

            self.logger.summary_file.write(
                '\n(See the attached file for the complete log)\n')
        except:
            self.logger.summary_file.write('\n\nERROR IN TESTRUNNER\n\n')
            traceback.print_exc(file=self.logger.summary_file)
            exit_status = 1
            raise
        finally:
            # It probably isn't safe to close the log files ourselves,
            # since someone else might try to write to them later.
            try:
                self.logger.got_result(
                    not exit_status, self.logger.summary_filename,
                    self.logger.out_filename)
            finally:
                self.logger.close_logs()

    def _gather_test_output(self, input_stream, logger):
        """Write the testrunner output to the logs."""
        result = SummaryResult(logger.summary_file)
        subunit_server = subunit.TestProtocolServer(
            result, logger.summary_file)
        for line in input_stream:
            subunit_server.lineReceived(line)
            logger.got_line(line)


class Request:
    """A request to have a branch tested and maybe landed."""

    def __init__(self, public_branch, public_branch_revno, test_directory,
                 sourcecode_dir, emails=None, pqm_message=None):
        self.public_branch = public_branch
        self.public_branch_revno = public_branch_revno
        self.test_directory = test_directory
        self.sourcecode_dir = sourcecode_dir
        self._emails = emails
        self._pqm_message = pqm_message

    def get_trunk_details(self):
        branch = bzrlib.branch.Branch.open_containing(self.test_directory)[0]
        return branch.get_parent().encode('utf-8'), branch.revno()

    def get_branch_details(self):
        tree = bzrlib.workingtree.WorkingTree.open(self.test_directory)
        parent_ids = tree.get_parent_ids()
        if len(parent_ids) == 1:
            return None
        return self.public_branch.encode('utf-8'), self.public_branch_revno

    def get_nick(self):
        """Get the nick of the branch we are testing."""
        details = self.get_branch_details()
        if not details:
            details = self.get_trunk_details()
        url, revno = details
        return url.strip('/').split('/')[-1]

    def get_merge_description(self):
        source = self.get_branch_details()
        if not source:
            return self.get_nick()
        target = self.get_trunk_details()
        return '%s => %s' % (source[0], target[0])

    def get_summary_commit(self):
        branch = bzrlib.branch.Branch.open_containing(self.test_directory)[0]
        tree = bzrlib.workingtree.WorkingTree.open(self.test_directory)
        parent_ids = tree.get_parent_ids()
        if len(parent_ids) == 1:
            return None
        summary = (
            branch.repository.get_revision(parent_ids[1]).get_summary())
        return summary.encode('utf-8')

    def send_email(self, result, body_text, full_log_gz, config):
        """Send an email summarizing the test results.

        :param result: True for pass, False for failure.
        :param body_text: The body of the email to send to the requesters.
        :param full_log_gz: A gzip of the full log.
        :param config: A Bazaar configuration object with SMTP details.
        """
        message = MIMEMultipart.MIMEMultipart()
        message['To'] = ', '.join(self._emails)
        message['From'] = config.username()
        subject = 'Test results: %s' % (result and 'FAILURE' or 'SUCCESS')
        message['Subject'] = subject

        # Make the body.
        body = MIMEText.MIMEText(body_text, 'plain', 'utf8')
        body['Content-Disposition'] = 'inline'
        message.attach(body)

        # Attach the gzipped log.
        zipped_log = MIMEApplication(full_log_gz, 'x-gzip')
        zipped_log.add_header(
            'Content-Disposition', 'attachment',
            filename='%s.log.gz' % self.get_nick())
        message.attach(zipped_log)

        bzrlib.smtp_connection.SMTPConnection(config).send_email(message)

    def iter_dependency_branches(self):
        """Iterate through the Bazaar branches we depend on."""
        for name in os.listdir(self.sourcecode_dir):
            path = os.path.join(self.sourcecode_dir, name)
            if os.path.isdir(path):
                try:
                    branch = bzrlib.branch.Branch.open_containing(path)[0]
                except bzrlib.errors.NotBranchError:
                    continue
                yield name, branch.get_parent(), branch.revno()

    def submit_to_pqm(self, successful, config):
        """Submit this request to PQM, if successful & configured to do so."""
        if not self._pqm_message:
            return
        subject = self._pqm_message.get('Subject')
        if successful:
            conn = bzrlib.smtp_connection.SMTPConnection(config)
            conn.send_email(self._pqm_message)
        return subject

    @property
    def wants_email(self):
        """Do the requesters want emails sent to them?"""
        return bool(self._emails)


class WebTestLogger:
    """Logs test output to disk and a simple web page."""

    def __init__(self, request, echo_to_stdout):
        """Construct a WebTestLogger.

        :param request: A `Request` object representing the thing that's being
            tested.
        :param echo_to_stdout: Whether or not we should echo output to stdout.
        """
        self._request = request
        self._echo_to_stdout = echo_to_stdout

        self.www_dir = os.path.join(os.path.sep, 'var', 'www')
        self.out_filename = os.path.join(self.www_dir, 'current_test.log')
        self.summary_filename = os.path.join(self.www_dir, 'summary.log')
        self.index_filename = os.path.join(self.www_dir, 'index.html')

        # We will set up the preliminary bits of the web-accessible log
        # files. "out" holds all stdout and stderr; "summary" holds filtered
        # output; and "index" holds an index page.
        self.out_file = None
        self.summary_file = None
        self.index_file = None

    def open_logs(self):
        """Open all of our log files for writing."""
        self.out_file = open(self.out_filename, 'w')
        self.summary_file = open(self.summary_filename, 'w')
        self.index_file = open(self.index_filename, 'w')

    def flush_logs(self):
        """Flush all of our log file buffers."""
        self.out_file.flush()
        self.summary_file.flush()
        self.index_file.flush()

    def close_logs(self):
        """Closes all of the open log file handles."""
        self.out_file.close()
        self.summary_file.close()
        self.index_file.close()

    def got_line(self, line):
        """Called when we get a line of output from our child processes."""
        self.out_file.write(line)
        self.out_file.flush()
        if self._echo_to_stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

    def got_result(self, successful, summary_filename, full_filename):
        """The tests are done and the results are known."""
        config = bzrlib.config.GlobalConfig()
        self._handle_pqm_submission(successful, config)
        if self._request.wants_email:
            summary = open(self.summary_filename, 'r').read()
            full_log_gz = open(gzip_file(self.out_file), 'rb').read()
            self._request.send_email(successful, summary, full_log_gz, config)

    def _handle_pqm_submission(self, successful, config):
        subject = self._request.submit_to_pqm(successful, config)
        if not subject:
            return
        if successful:
            self.write('\n\nSUBMITTED TO PQM:\n%s\n' % (subject,))
        else:
            self.write('\n\n**NOT** submitted to PQM:\n%s\n' % (subject,))

    def write(self, msg):
        """Write to the summary and full log file."""
        for fd in [self.out_file, self.summary_file]:
            fd.write(msg)
            fd.flush()

    def write_line(self, msg):
        """Write to the summary and full log file with a newline."""
        self.write(msg + '\n')

    def prepare(self):
        """Prepares the log files on disk.

        Writes three log files: the raw output log, the filtered "summary"
        log file, and a HTML index page summarizing the test run paramters.
        """
        self.open_logs()

        index_file   = self.index_file

        msg = 'Tests started at approximately %(now)s UTC' % {
            'now': datetime.datetime.utcnow().strftime(
                '%a, %d %b %Y %H:%M:%S')}
        index_file.write(textwrap.dedent('''\
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
            ''' % (msg,)))
        self.write_line(msg)

        index_file.write(textwrap.dedent('''\
            <h2>Branches Tested</h2>
            '''))

        # Describe the trunk branch.
        trunk, trunk_revno = self._request.get_trunk_details()
        msg = '%s, revision %d\n' % (trunk, trunk_revno)
        index_file.write(textwrap.dedent('''\
            <p><strong>%s</strong></p>
            ''' % (escape(msg),)))
        self.write_line(msg)

        branch_details = self._request.get_branch_details()
        if not branch_details:
            index_file.write('<p>(no merged branch)</p>\n')
            self.write_line('(no merged branch)')
        else:
            branch_name, branch_revno = branch_details
            data = {'name': branch_name,
                    'revno': branch_revno,
                    'commit': self._request.get_summary_commit()}
            msg = ('%(name)s, revision %(revno)d '
                   '(commit message: %(commit)s)\n' % data)
            index_file.write(textwrap.dedent('''\
               <p>Merged with<br />%(msg)s</p>
               ''' % {'msg': escape(msg)}))
            self.write_line("Merged with")
            self.write_line(msg)

        index_file.write('<dl>\n')
        self.write_line('\nDEPENDENCY BRANCHES USED\n')
        for name, branch, revno in self._request.iter_dependency_branches():
            data = {'name': name, 'branch': branch, 'revno': revno}
            self.write_line(
                '- %(name)s\n    %(branch)s\n    %(revno)d\n' % data)
            escaped_data = {'name': escape(name),
                            'branch': escape(branch.get_parent()),
                            'revno': branch.revno()}
            index_file.write(textwrap.dedent('''\
                <dt>%(name)s</dt>
                  <dd>%(branch)s</dd>
                  <dd>%(revno)s</dd>
                ''' % escaped_data))
        index_file.write(textwrap.dedent('''\
                </dl>
              </body>
            </html>'''))
        self.write_line('\n\nTEST RESULTS FOLLOW\n\n')
        self.flush_logs()


def daemonize(pid_filename):
    # this seems like the sort of thing that ought to be in the
    # standard library :-/
    pid = os.fork()
    if (pid == 0): # child 1
        os.setsid()
        pid = os.fork()
        if (pid == 0): # child 2
            pass # lookie, we're ready to do work in the daemon
        else:
            os._exit(0)
    else:
        # give the pidfile a chance to be written before we exit.
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


def gzip_file(filename):
    """Compress 'filename' to a new temporary file.

    :param filename: The path to a file.
    :return: The path to the compressed version of that file.
    """
    fd, path = tempfile.mkstemp()
    os.close(fd)
    gz = gzip.open(path, 'wb')
    full_log = open(filename, 'rb')
    gz.writelines(full_log)
    gz.close()
    return path


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

    request = Request(
        options.public_branch, options.public_branch_revno, TEST_DIR,
        SOURCECODE_DIR, options.email, pqm_message)
    # Only write to stdout if we are running as the foreground process.
    echo_to_stdout = not options.daemon
    logger = WebTestLogger(request, echo_to_stdout)

    runner = EC2Runner(
        options.daemon, pid_filename, options.shutdown, options.email)

    tester = LaunchpadTester(
        logger=logger, test_directory=TEST_DIR, test_options=' '.join(args))
    runner.run("Test runner", tester.test)


if __name__ == '__main__':
    main(sys.argv)
