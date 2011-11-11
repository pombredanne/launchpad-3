# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to actually run the tests in an EC2 instance."""

__metaclass__ = type
__all__ = [
    'EC2TestRunner',
    'TRUNK_BRANCH',
    ]

import os
import pickle
import re
import sys

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.config import GlobalConfig
from bzrlib.errors import UncommittedChanges
from bzrlib.plugins.pqm.pqm_submit import (
    NoPQMSubmissionAddress, PQMSubmission)


TRUNK_BRANCH = 'bzr+ssh://bazaar.launchpad.net/~launchpad-pqm/launchpad/devel'


class UnknownBranchURL(Exception):
    """Raised when we try to parse an unrecognized branch url."""

    def __init__(self, branch_url):
        Exception.__init__(
            self,
            "Couldn't parse '%s', not a Launchpad branch." % (branch_url,))


def parse_branch_url(branch_url):
    """Given the URL of a branch, return its components in a dict."""
    _lp_match = re.compile(
        r'lp:\~([^/]+)/([^/]+)/([^/]+)$').match
    _bazaar_match = re.compile(
        r'bzr+ssh://bazaar.launchpad.net/\~([^/]+)/([^/]+)/([^/]+)$').match
    match = _lp_match(branch_url)
    if match is None:
        match = _bazaar_match(branch_url)
    if match is None:
        raise UnknownBranchURL(branch_url)
    owner = match.group(1)
    product = match.group(2)
    branch = match.group(3)
    unique_name = '~%s/%s/%s' % (owner, product, branch)
    url = 'bzr+ssh://bazaar.launchpad.net/%s' % (unique_name,)
    return dict(
        owner=owner, product=product, branch=branch, unique_name=unique_name,
        url=url)


def normalize_branch_input(data):
    """Given 'data' return a ('dest', 'src') pair.

    :param data: One of::
       - a double of (sourcecode_location, branch_url).
         If 'sourcecode_location' is Launchpad, then 'branch_url' can
         also be the name of a branch of launchpad owned by
         launchpad-pqm.
       - a singleton of (branch_url,)
       - a singleton of (sourcecode_location,) where
         sourcecode_location corresponds to a Launchpad upstream
         project as well as a rocketfuel sourcecode location.
       - a string which could populate any of the above singletons.

    :return: ('dest', 'src') where 'dest' is the destination
        sourcecode location in the rocketfuel tree and 'src' is the
        URL of the branch to put there. The URL can be either a bzr+ssh
        URL or the name of a branch of launchpad owned by launchpad-pqm.
    """
    # XXX: JonathanLange 2009-06-05: Should convert lp: URL branches to
    # bzr+ssh:// branches.
    if isinstance(data, basestring):
        data = (data,)
    if len(data) == 2:
        # Already in dest, src format.
        return data
    if len(data) != 1:
        raise ValueError(
            'invalid argument for ``branches`` argument: %r' %
            (data,))
    branch_location = data[0]
    try:
        parsed_url = parse_branch_url(branch_location)
    except UnknownBranchURL:
        return branch_location, 'lp:%s' % (branch_location,)
    return parsed_url['product'], parsed_url['url']


def parse_specified_branches(branches):
    """Given 'branches' from the command line, return a sanitized dict.

    The dict maps sourcecode locations to branch URLs, according to the
    rules in `normalize_branch_input`.
    """
    return dict(map(normalize_branch_input, branches))


class EC2TestRunner:

    name = 'ec2-test-runner'

    message = image = None
    _running = False

    def __init__(self, branch, email=False, file=None, test_options=None,
                 headless=False, branches=(),
                 pqm_message=None, pqm_public_location=None,
                 pqm_submit_location=None,
                 open_browser=False, pqm_email=None,
                 include_download_cache_changes=None, instance=None,
                 launchpad_login=None,
                 timeout=None):
        """Create a new EC2TestRunner.

        :param timeout: Number of minutes before we force a shutdown. This is
            useful because sometimes the normal instance termination might
            fail.

          - original_branch
          - test_options
          - headless
          - include_download_cache_changes
          - download_cache_additions
          - branches (parses, validates)
          - message (after validating PQM submisson)
          - email (after validating email capabilities)
          - image (after connecting to ec2)
          - file
          - timeout
        """
        self.original_branch = branch
        self.test_options = test_options
        self.headless = headless
        self.include_download_cache_changes = include_download_cache_changes
        self.open_browser = open_browser
        self.file = file
        self._launchpad_login = launchpad_login
        self.timeout = timeout

        trunk_specified = False
        trunk_branch = TRUNK_BRANCH

        # normalize and validate branches
        branches = parse_specified_branches(branches)
        try:
            launchpad_url = branches.pop('launchpad')
        except KeyError:
            # No Launchpad branch specified.
            pass
        else:
            try:
                parsed_url = parse_branch_url(launchpad_url)
            except UnknownBranchURL:
                user = 'launchpad-pqm'
                src = ('bzr+ssh://bazaar.launchpad.net/'
                       '~launchpad-pqm/launchpad/%s' % (launchpad_url,))
            else:
                user = parsed_url['owner']
                src = parsed_url['url']
            if user == 'launchpad-pqm':
                trunk_specified = True
            trunk_branch = src
        self._trunk_branch = trunk_branch
        self.branches = branches.items()

        # XXX: JonathanLange 2009-05-31: The trunk_specified stuff above and
        # the pqm location stuff below are actually doing the equivalent of
        # preparing a merge directive. Perhaps we can leverage that to make
        # this code simpler.
        self.download_cache_additions = None
        if branch is None:
            config = GlobalConfig()
            if pqm_message is not None:
                raise ValueError('Cannot submit trunk to pqm.')
        else:
            (tree,
             bzrbranch,
             relpath) = BzrDir.open_containing_tree_or_branch(branch)
            config = bzrbranch.get_config()

            if pqm_message is not None or tree is not None:
                # if we are going to maybe send a pqm_message, we're going to
                # go down this path. Also, even if we are not but this is a
                # local branch, we're going to use the PQM machinery to make
                # sure that the local branch has been made public, and has all
                # working changes there.
                if tree is None:
                    # remote.  We will make some assumptions.
                    if pqm_public_location is None:
                        pqm_public_location = branch
                    if pqm_submit_location is None:
                        pqm_submit_location = trunk_branch
                elif pqm_submit_location is None and trunk_specified:
                    pqm_submit_location = trunk_branch
                # modified from pqm_submit.py
                submission = PQMSubmission(
                    source_branch=bzrbranch,
                    public_location=pqm_public_location,
                    message=pqm_message or '',
                    submit_location=pqm_submit_location,
                    tree=tree)
                if tree is not None:
                    # this is the part we want to do whether or not we're
                    # submitting.
                    submission.check_tree() # any working changes
                    submission.check_public_branch() # everything public
                    branch = submission.public_location
                    if (include_download_cache_changes is None or
                        include_download_cache_changes):
                        # We need to get the download cache settings
                        cache_tree, cache_bzrbranch, cache_relpath = (
                            BzrDir.open_containing_tree_or_branch(
                                os.path.join(
                                    self.original_branch, 'download-cache')))
                        cache_tree.lock_read()
                        try:
                            cache_basis_tree = cache_tree.basis_tree()
                            cache_basis_tree.lock_read()
                            try:
                                delta = cache_tree.changes_from(
                                    cache_basis_tree, want_unversioned=True)
                                unversioned = [
                                    un for un in delta.unversioned
                                    if not cache_tree.is_ignored(un[0])]
                                added = delta.added
                                self.download_cache_additions = (
                                    unversioned + added)
                            finally:
                                cache_basis_tree.unlock()
                        finally:
                            cache_tree.unlock()
                if pqm_message is not None:
                    if self.download_cache_additions:
                        raise UncommittedChanges(cache_tree)
                    # get the submission message
                    mail_from = config.get_user_option('pqm_user_email')
                    if not mail_from:
                        mail_from = config.username()
                    # Make sure this isn't unicode
                    mail_from = mail_from.encode('utf8')
                    if pqm_email is None:
                        if tree is None:
                            pqm_email = (
                                "Launchpad PQM <launchpad@pqm.canonical.com>")
                        else:
                            pqm_email = config.get_user_option('pqm_email')
                    if not pqm_email:
                        raise NoPQMSubmissionAddress(bzrbranch)
                    mail_to = pqm_email.encode('utf8') # same here
                    self.message = submission.to_email(mail_from, mail_to)
                elif (self.download_cache_additions and
                      self.include_download_cache_changes is None):
                    raise UncommittedChanges(
                        cache_tree,
                        'You must select whether to include download cache '
                        'changes (see --include-download-cache-changes and '
                        '--ignore-download-cache-changes, -c and -g '
                        'respectively), or '
                        'commit or remove the files in the download-cache.')
        self._branch = branch

        if email is not False:
            if email is True:
                email = [config.username()]
                if not email[0]:
                    raise ValueError('cannot find your email address.')
            elif isinstance(email, basestring):
                email = [email]
            else:
                tmp = []
                for item in email:
                    if not isinstance(item, basestring):
                        raise ValueError(
                            'email must be True, False, a string, or a list '
                            'of strings')
                    tmp.append(item)
                email = tmp
        else:
            email = None
        self.email = email

        # Email configuration.
        if email is not None or pqm_message is not None:
            self._smtp_server = config.get_user_option('smtp_server')
            # Refuse localhost, because there's no SMTP server _on the actual
            # EC2 instance._
            if self._smtp_server is None or self._smtp_server == 'localhost':
                raise ValueError(
                    'To send email, a remotely accessible smtp_server (and '
                    'smtp_username and smtp_password, if necessary) must be '
                    'configured in bzr.  See the SMTP server information '
                    'here: https://wiki.canonical.com/EmailSetup .'
                    'This server must be reachable from the EC2 instance.')
            self._smtp_username = config.get_user_option('smtp_username')
            self._smtp_password = config.get_user_option('smtp_password')
            self._from_email = config.username()
            if not self._from_email:
                raise ValueError(
                    'To send email, your bzr email address must be set '
                    '(use ``bzr whoami``).')

        self._instance = instance

    def log(self, msg):
        """Log a message on stdout, flushing afterwards."""
        # XXX: JonathanLange 2009-05-31 bug=383076: This should use Python
        # logging, rather than printing to stdout.
        sys.stdout.write(msg)
        sys.stdout.flush()

    def configure_system(self):
        user_connection = self._instance.connect()
        if self.timeout is not None:
            # Activate a fail-safe shutdown just in case something goes
            # really wrong with the server or suite.
            user_connection.perform("sudo shutdown -P +%d &" % self.timeout)
        as_user = user_connection.perform
        for ppa in 'bzr', 'bzr-beta-ppa', 'launchpad':
            as_user("sudo add-apt-repository ppa:" + ppa)
        as_user("sudo aptitude update")
        as_user("sudo DEBIAN_FRONTEND=noninteractive aptitude -y full-upgrade")
        # Set up bazaar.conf with smtp information if necessary
        if self.email or self.message:
            as_user('[ -d .bazaar ] || mkdir .bazaar')
            bazaar_conf_file = user_connection.sftp.open(
                ".bazaar/bazaar.conf", 'w')
            bazaar_conf_file.write(
                'email = %s\n' % (self._from_email.encode('utf-8'),))
            bazaar_conf_file.write(
                'smtp_server = %s\n' % (self._smtp_server,))
            if self._smtp_username:
                bazaar_conf_file.write(
                    'smtp_username = %s\n' % (self._smtp_username,))
            if self._smtp_password:
                bazaar_conf_file.write(
                    'smtp_password = %s\n' % (self._smtp_password,))
            bazaar_conf_file.close()
        # Copy remote ec2-remote over
        self.log('Copying remote.py to remote machine.\n')
        user_connection.sftp.put(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'remote.py'),
            '/var/launchpad/ec2test-remote.py')
        # Set up launchpad login and email
        as_user('bzr launchpad-login %s' % (self._launchpad_login,))
        user_connection.close()

    def prepare_tests(self):
        user_connection = self._instance.connect()
        # Clean up the test branch left in the instance image.
        user_connection.perform('rm -rf /var/launchpad/test')
        # Get trunk.
        user_connection.run_with_ssh_agent(
            'bzr branch %s /var/launchpad/test' % (self._trunk_branch,))
        # Merge the branch in.
        if self._branch is not None:
            user_connection.run_with_ssh_agent(
                'cd /var/launchpad/test; bzr merge %s' % (self._branch,))
        else:
            self.log('(Testing trunk, so no branch merge.)')
        # get newest sources
        user_connection.run_with_ssh_agent(
            "/var/launchpad/test/utilities/update-sourcecode "
            "/var/launchpad/sourcecode")
        # Get any new sourcecode branches as requested
        for dest, src in self.branches:
            fulldest = os.path.join('/var/launchpad/test/sourcecode', dest)
            user_connection.run_with_ssh_agent(
                'bzr branch --standalone %s %s' % (src, fulldest))
        # prepare fresh copy of sourcecode and buildout sources for building
        p = user_connection.perform
        p('rm -rf /var/launchpad/tmp')
        p('mkdir /var/launchpad/tmp')
        p('mv /var/launchpad/sourcecode /var/launchpad/tmp/sourcecode')
        p('mkdir /var/launchpad/tmp/eggs')
        p('mkdir /var/launchpad/tmp/yui')
        user_connection.run_with_ssh_agent(
            'bzr pull lp:lp-source-dependencies '
            '-d /var/launchpad/download-cache')
        p('mv /var/launchpad/download-cache /var/launchpad/tmp/download-cache')
        if (self.include_download_cache_changes and
            self.download_cache_additions):
            root = os.path.realpath(
                os.path.join(self.original_branch, 'download-cache'))
            for info in self.download_cache_additions:
                src = os.path.join(root, info[0])
                self.log('Copying %s to remote machine.\n' % (src,))
                user_connection.sftp.put(
                    src,
                    os.path.join('/var/launchpad/tmp/download-cache', info[0]))
        p('/var/launchpad/test/utilities/link-external-sourcecode '
          '-p/var/launchpad/tmp -t/var/launchpad/test'),
        # set up database
        p('/var/launchpad/test/utilities/launchpad-database-setup $USER')
        p('mkdir -p /var/tmp/launchpad_mailqueue/cur')
        p('mkdir -p /var/tmp/launchpad_mailqueue/new')
        p('mkdir -p /var/tmp/launchpad_mailqueue/tmp')
        p('chmod -R a-w /var/tmp/launchpad_mailqueue/')
        # close ssh connection
        user_connection.close()

    def run_demo_server(self):
        """Turn ec2 instance into a demo server."""
        self.configure_system()
        self.prepare_tests()
        user_connection = self._instance.connect()
        p = user_connection.perform
        p('make -C /var/launchpad/test schema')
        p('mkdir -p /var/tmp/bazaar.launchpad.dev/static')
        p('mkdir -p /var/tmp/bazaar.launchpad.dev/mirrors')
        p('sudo a2enmod proxy > /dev/null')
        p('sudo a2enmod proxy_http > /dev/null')
        p('sudo a2enmod rewrite > /dev/null')
        p('sudo a2enmod ssl > /dev/null')
        p('sudo a2enmod deflate > /dev/null')
        p('sudo a2enmod headers > /dev/null')
        # Install apache config file.
        p('cd /var/launchpad/test/; sudo make install')
        # Use raw string to eliminate the need to escape the backslash.
        # Put eth0's ip address in the /tmp/ip file.
        p(r"ifconfig eth0 | grep 'inet addr' "
          r"| sed -re 's/.*addr:([0-9.]*) .*/\1/' > /tmp/ip")
        # Replace 127.0.0.88 in Launchpad's apache config file with the
        # ip address just stored in the /tmp/ip file. Perl allows for
        # inplace editing unlike sed.
        p('sudo perl -pi -e "s/127.0.0.88/$(cat /tmp/ip)/g" '
          '/etc/apache2/sites-available/local-launchpad')
        # Restart apache.
        p('sudo /etc/init.d/apache2 restart')
        # Build mailman and minified javascript, etc.
        p('cd /var/launchpad/test/; make')
        # Start launchpad in the background.
        p('cd /var/launchpad/test/; make start')
        # close ssh connection
        user_connection.close()

    def _build_command(self):
        """Build the command that we'll use to run the tests."""
        # Make sure we activate the failsafe --shutdown feature.  This will
        # make the server shut itself down after the test run completes, or
        # if the test harness suffers a critical failure.
        cmd = ['python /var/launchpad/ec2test-remote.py --shutdown']

        # Do we want to email the results to the user?
        if self.email:
            for email in self.email:
                cmd.append("--email='%s'" % (
                    email.encode('utf8').encode('string-escape'),))

        # Do we want to submit the branch to PQM if the tests pass?
        if self.message is not None:
            cmd.append(
                "--submit-pqm-message='%s'" % (
                    pickle.dumps(
                        self.message).encode(
                        'base64').encode('string-escape'),))

        # Do we want to disconnect the terminal once the test run starts?
        if self.headless:
            cmd.append('--daemon')

        # Which branch do we want to test?
        if self._branch is not None:
            branch = self._branch
            remote_branch = Branch.open(branch)
            branch_revno = remote_branch.revno()
        else:
            branch = self._trunk_branch
            branch_revno = None
        cmd.append('--public-branch=%s' % branch)
        if branch_revno is not None:
            cmd.append('--public-branch-revno=%d' % branch_revno)

        # Add any additional options for ec2test-remote.py
        cmd.extend(['--', self.test_options])
        return ' '.join(cmd)

    def run_tests(self):
        self.configure_system()
        self.prepare_tests()

        self.log(
            'Running tests... (output is available on '
            'http://%s/)\n' % self._instance.hostname)

        # Try opening a browser pointed at the current test results.
        if self.open_browser:
            try:
                import webbrowser
            except ImportError:
                self.log("Could not open web browser due to ImportError.")
            else:
                status = webbrowser.open(self._instance.hostname)
                if not status:
                    self.log("Could not open web browser.")

        # Run the remote script!  Our execution will block here until the
        # remote side disconnects from the terminal.
        cmd = self._build_command()
        user_connection = self._instance.connect()
        user_connection.perform(cmd)
        self._running = True

        if not self.headless:
            # We ran to completion locally, so we'll be in charge of shutting
            # down the instance, in case the user has requested a postmortem.
            #
            # We only have 60 seconds to do this before the remote test
            # script shuts the server down automatically.
            user_connection.perform(
                'kill `cat /var/launchpad/ec2test-remote.pid`')

            # deliver results as requested
            if self.file:
                self.log(
                    'Writing abridged test results to %s.\n' % self.file)
                user_connection.sftp.get('/var/www/summary.log', self.file)
        user_connection.close()
