#!/usr/bin/env python
# Run tests in a daemon.
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metatype__ = type

import datetime
import optparse
import os
import pickle
import re
import subprocess
import sys
import textwrap
import time
import traceback

from xml.sax.saxutils import escape

import bzrlib.branch
import bzrlib.config
import bzrlib.email_message
import bzrlib.errors
import bzrlib.smtp_connection
import bzrlib.workingtree


class BaseTestRunner:

    def __init__(self, email=None, pqm_message=None, public_branch=None,
                 public_branch_revno=None, test_options=None):
        self.email = email
        self.pqm_message = pqm_message
        self.public_branch = public_branch
        self.public_branch_revno = public_branch_revno

        # Set up the testrunner options.
        if test_options is None:
            test_options = '-vv'
        self.test_options = test_options

        # Configure paths.
        self.lp_dir = os.path.join(os.path.sep, 'var', 'launchpad')
        self.tmp_dir = os.path.join(self.lp_dir, 'tmp')
        self.test_dir = os.path.join(self.lp_dir, 'test')
        self.sourcecode_dir = os.path.join(self.test_dir, 'sourcecode')

        # Set up logging.
        self.logger = WebTestLogger(
            self.test_dir,
            self.public_branch,
            self.public_branch_revno,
            self.sourcecode_dir
        )

        # Daemonization options.
        self.pid_filename = os.path.join(self.lp_dir, 'ec2test-remote.pid')
        self.daemonized = False

    def daemonize(self):
        """Turn the testrunner into a forked daemon process."""
        # This also writes our pidfile to disk to a specific location.  The
        # ec2test.py --postmortem command will look there to find our PID,
        # in order to control this process.
        daemonize(self.pid_filename)
        self.daemonized = True

    def remove_pidfile(self):
        if os.path.exists(self.pid_filename):
            os.remove(self.pid_filename)

    def ignore_line(self, line):
        """Return True if the line should be excluded from the summary log.

        Defaults to False.
        """
        return False

    def build_test_command(self):
        """Return the command that will execute the test suite.

        Should return a list of command options suitable for submission to
        subprocess.call()

        Subclasses must provide their own implementation of this method.
        """
        raise NotImplementedError

    def test(self):
        """Run the tests, log the results.

        Signals the ec2test process and cleans up the logs once all the tests
        have completed.  If necessary, submits the branch to PQM, and mails
        the user the test results.
        """
        # We need to open the log files here because earlier calls to
        # os.fork() may have tried to close them.
        self.logger.prepare()

        out_file     = self.logger.out_file
        summary_file = self.logger.summary_file
        config       = bzrlib.config.GlobalConfig()

        call = self.build_test_command()

        try:
            try:
                try:
                    popen = subprocess.Popen(
                        call, bufsize=-1,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        cwd=self.test_dir)

                    self._gather_test_output(popen, summary_file, out_file)

                    # Grab the testrunner exit status
                    result = popen.wait()

                    if self.pqm_message is not None:
                        subject = self.pqm_message.get('Subject')
                        if result:
                            # failure
                            summary_file.write(
                                '\n\n**NOT** submitted to PQM:\n%s\n' %
                                (subject,))
                        else:
                            # success
                            conn = bzrlib.smtp_connection.SMTPConnection(
                                config)
                            conn.send_email(self.pqm_message)
                            summary_file.write('\n\nSUBMITTED TO PQM:\n%s\n' %
                                               (subject,))
                except:
                    summary_file.write('\n\nERROR IN TESTRUNNER\n\n')
                    traceback.print_exc(file=summary_file)
                    result = 1
                    raise
            finally:
                # It probably isn't safe to close the log files ourselves,
                # since someone else might try to write to them later.
                summary_file.close()
                if self.email is not None:
                    subject = 'Test results: %s' % (
                        result and 'FAILURE' or 'SUCCESS')
                    summary_file = open(self.logger.summary_filename, 'r')
                    bzrlib.email_message.EmailMessage.send(
                        config, self.email[0], self.email,
                        subject, summary_file.read())
                    summary_file.close()
        finally:
            # we do this at the end because this is a trigger to ec2test.py
            # back at home that it is OK to kill the process and take control
            # itself, if it wants to.
            out_file.close()
            self.logger.close_logs()

    def _gather_test_output(self, test_process, summary_file, out_file):
        """Write the testrunner output to the logs."""
        # Only write to stdout if we are running as the foreground process.
        echo_to_stdout = not self.daemonized

        last_line = ''
        while 1:
            data = test_process.stdout.read(256)
            if data:
                out_file.write(data)
                out_file.flush()
                if echo_to_stdout:
                    sys.stdout.write(data)
                    sys.stdout.flush()
                lines = data.split('\n')
                lines[0] = last_line + lines[0]
                last_line = lines.pop()
                for line in lines:
                    if not self.ignore_line(line):
                        summary_file.write(line + '\n')
                summary_file.flush()
            else:
                summary_file.write(last_line)
                break


class TestOnMergeRunner(BaseTestRunner):
    """Executes the Launchpad test_on_merge.py test suite."""

    def build_test_command(self):
        """See BaseTestRunner.build_test_command()."""
        command = ['make', 'check', 'VERBOSITY=' + self.test_options]
        return command

    # Used to filter lines in the summary log. See
    # `BaseTestRunner.ignore_line()`.
    ignore_line = re.compile(
        r'( [\w\.\/\-]+( ?\([\w\.\/\-]+\))?|'
        r'\s*Running.*|'
        r'\d{4}\-\d{2}\-\d{2} \d{2}\:\d{2}\:\d{2} INFO.+|'
        r'\s*Set up .+|'
        r'\s*Tear down .*|'
        r'  Ran \d+ tests with .+)$').match


class JSCheckTestRunner(BaseTestRunner):
    """Executes the Launchpad JavaScript integration test suite."""

    def build_test_command(self):
        """See BaseTestRunner.build_test_command()."""
        # We use the xvfb server's convenience script, xvfb-run, to
        # automagically set the display, start the command, shut down the
        # display, and return the exit code.  (See the xvfb-run man page for
        # details.)
        return [
            'xvfb-run',
            '-s', '-screen 0 1024x768x24',
            'make', 'jscheck']


class WebTestLogger:
    """Logs test output to disk and a simple web page."""

    def __init__(self, test_dir, public_branch, public_branch_revno,
                 sourcecode_dir):
        """ Class initialiser """
        self.test_dir = test_dir
        self.public_branch = public_branch
        self.public_branch_revno = public_branch_revno
        self.sourcecode_dir = sourcecode_dir

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

    def prepare(self):
        """Prepares the log files on disk.

        Writes three log files: the raw output log, the filtered "summary"
        log file, and a HTML index page summarizing the test run paramters.
        """
        self.open_logs()

        out_file     = self.out_file
        summary_file = self.summary_file
        index_file   = self.index_file

        def write(msg):
            msg += '\n'
            summary_file.write(msg)
            out_file.write(msg)
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
        write(msg)

        index_file.write(textwrap.dedent('''\
            <h2>Branches Tested</h2>
            '''))

        # Describe the trunk branch.
        branch = bzrlib.branch.Branch.open_containing(self.test_dir)[0]
        msg = '%(trunk)s, revision %(trunk_revno)d\n' % {
            'trunk': branch.get_parent().encode('utf-8'),
            'trunk_revno': branch.revno()}
        index_file.write(textwrap.dedent('''\
            <p><strong>%s</strong></p>
            ''' % (escape(msg),)))
        write(msg)
        tree = bzrlib.workingtree.WorkingTree.open(self.test_dir)
        parent_ids = tree.get_parent_ids()

        # Describe the merged branch.
        if len(parent_ids) == 1:
            index_file.write('<p>(no merged branch)</p>\n')
            write('(no merged branch)')
        else:
            summary = (
                branch.repository.get_revision(parent_ids[1]).get_summary())
            data = {'name': self.public_branch.encode('utf-8'),
                    'revno': self.public_branch_revno,
                    'commit': summary.encode('utf-8')}
            msg = ('%(name)s, revision %(revno)d '
                   '(commit message: %(commit)s)\n' % data)
            index_file.write(textwrap.dedent('''\
               <p>Merged with<br />%(msg)s</p>
               ''' % {'msg': escape(msg)}))
            write("Merged with")
            write(msg)

        index_file.write('<dl>\n')
        write('\nDEPENDENCY BRANCHES USED\n')
        for name in os.listdir(self.sourcecode_dir):
            path = os.path.join(self.sourcecode_dir, name)
            if os.path.isdir(path):
                try:
                    branch = bzrlib.branch.Branch.open_containing(path)[0]
                except bzrlib.errors.NotBranchError:
                    continue
                data = {'name': name,
                        'branch': branch.get_parent(),
                        'revno': branch.revno()}
                write(
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
        write('\n\nTEST RESULTS FOLLOW\n\n')
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


def write_pidfile(pid_filename):
    """Write a pidfile for the current process."""
    pid_file = open(pid_filename, "w")
    pid_file.write(str(os.getpid()))
    pid_file.close()


if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="%prog [options] [-- test options]",
        description=("Build and run tests for an instance."))
    parser.add_option(
        '-e', '--email', action='append', dest='email', default=None,
        help=('Email address to which results should be mailed.  Defaults to '
              'the email address from `bzr whoami`. May be supplied multiple '
              'times. The first supplied email address will be used as the '
              'From: address.'))
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
    parser.add_option(
        '--jscheck', dest='jscheck', default=False, action='store_true',
        help=('Run the JavaScript integration test suite.'))

    options, args = parser.parse_args()

    if options.debug:
        import pdb; pdb.set_trace()
    if options.pqm_message is not None:
        pqm_message = pickle.loads(
            options.pqm_message.decode('string-escape').decode('base64'))
    else:
        pqm_message = None

    if options.jscheck:
        runner_type = JSCheckTestRunner
    else:
        # Use the default testrunner.
        runner_type = TestOnMergeRunner

    runner = runner_type(
       options.email,
       pqm_message,
       options.public_branch,
       options.public_branch_revno,
       ' '.join(args)
    )

    try:
        try:
            if options.daemon:
                print 'Starting testrunner daemon...'
                runner.daemonize()

            runner.test()
        except:
            # Handle exceptions thrown by the test() or daemonize() methods.
            if options.email:
                bzrlib.email_message.EmailMessage.send(
                    bzrlib.config.GlobalConfig(), options.email[0],
                    options.email,
                    'Test Runner FAILED', traceback.format_exc())
            raise
    finally:

        # When everything is over, if we've been ask to shut down, then
        # make sure we're daemonized, then shutdown.  Otherwise, if we're
        # daemonized, just clean up the pidfile.
        if options.shutdown:
            # Make sure our process is daemonized, and has therefore
            # disconnected the controlling terminal.  This also disconnects
            # the ec2test.py SSH connection, thus signalling ec2test.py
            # that it may now try to take control of the server.
            if not runner.daemonized:
                # We only want to do this if we haven't already been
                # daemonized.  Nesting daemons is bad.
                runner.daemonize()

            # Give the script 60 seconds to clean itself up, and 60 seconds
            # for the ec2test.py --postmortem option to grab control if
            # needed.  If we don't give --postmortem enough time to log
            # in via SSH and take control, then this server will begin to
            # shutdown on it's own.
            #
            # (FWIW, "grab control" means sending SIGTERM to this script's
            # process id, thus preventing fail-safe shutdown.)
            time.sleep(60)

            # We'll only get here if --postmortem didn't kill us.  This is
            # our fail-safe shutdown, in case the user got disconnected
            # or suffered some other mishap that would prevent them from
            # shutting down this server on their own.
            subprocess.call(['sudo', 'shutdown', '-P', 'now'])
        elif runner.daemonized:
            # It would be nice to clean up after ourselves, since we won't
            # be shutting down.
            runner.remove_pidfile()
        else:
            # We're not a daemon, and we're not shutting down.  The user most
            # likely started this script manually, from a shell running on the
            # instance itself.
            pass
