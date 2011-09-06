# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The command classes for the 'ec2' utility."""

__metaclass__ = type
__all__ = []

from datetime import datetime
import os
import pdb
import socket

from bzrlib.bzrdir import BzrDir
from bzrlib.commands import Command
from bzrlib.errors import (
    BzrCommandError,
    ConnectionError,
    NoSuchFile,
    )
from bzrlib.help import help_commands
from bzrlib.option import (
    ListOption,
    Option,
    )
from bzrlib.transport import get_transport
from pytz import UTC
import simplejson

from devscripts import get_launchpad_root
from devscripts.ec2test.account import VALID_AMI_OWNERS
from devscripts.ec2test.credentials import EC2Credentials
from devscripts.ec2test.instance import (
    AVAILABLE_INSTANCE_TYPES,
    DEFAULT_INSTANCE_TYPE,
    EC2Instance,
    )
from devscripts.ec2test.session import EC2SessionName
from devscripts.ec2test.testrunner import (
    EC2TestRunner,
    TRUNK_BRANCH,
    )

# Options accepted by more than one command.

# Branches is a complicated option that lets the user specify which branches
# to use in the sourcecode directory.  Most of the complexity is still in
# EC2TestRunner.__init__, which probably isn't ideal.
branch_option = ListOption(
    'branch', type=str, short_name='b', argname='BRANCH',
    help=('Branches to include in this run in sourcecode. '
          'If the argument is only the project name, the trunk will be '
          'used (e.g., ``-b launchpadlib``).  If you want to use a '
          'specific branch, if it is on launchpad, you can usually '
          'simply specify it instead (e.g., '
          '``-b lp:~username/launchpadlib/branchname``).  If this does '
          'not appear to work, or if the desired branch is not on '
          'launchpad, specify the project name and then the branch '
          'after an equals sign (e.g., '
          '``-b launchpadlib=lp:~username/launchpadlib/branchname``). '
          'Branches for multiple projects may be specified with '
          'multiple instances of this option. '
          'You may also use this option to specify the branch of launchpad '
          'into which your branch may be merged.  This defaults to %s. '
          'Because typically the important branches of launchpad are owned '
          'by the launchpad-pqm user, you can shorten this to only the '
          'branch name, if desired, and the launchpad-pqm user will be '
          'assumed.  For instance, if you specify '
          '``-b launchpad=db-devel`` then this is equivalent to '
          '``-b lp:~launchpad-pqm/launchpad/db-devel``, or the even longer'
          '``-b launchpad=lp:~launchpad-pqm/launchpad/db-devel``.'
          % (TRUNK_BRANCH,)))


machine_id_option = Option(
    'machine', short_name='m', type=str,
    help=('The AWS machine identifier (AMI) on which to base this run. '
          'You should typically only have to supply this if you are '
          'testing new AWS images. Defaults to trying to find the most '
          'recent one with an approved owner.'))


def _convert_instance_type(arg):
    """Ensure that `arg` is acceptable as an instance type."""
    if arg not in AVAILABLE_INSTANCE_TYPES:
        raise BzrCommandError('Unknown instance type %r' % arg)
    return arg


instance_type_option = Option(
    'instance', short_name='i', type=_convert_instance_type,
    param_name='instance_type',
    help=('The AWS instance type on which to base this run. '
          'Available options are %r. Defaults to `%s`.' %
          (AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE)))


debug_option = Option(
    'debug', short_name='d',
    help=('Drop to pdb trace as soon as possible.'))


trunk_option = Option(
    'trunk', short_name='t',
    help=('Run the trunk as the branch, rather than the branch of the '
          'current working directory.'))


include_download_cache_changes_option = Option(
    'include-download-cache-changes', short_name='c',
    help=('Include any changes in the download cache (added or unknown) '
          'in the download cache of the test run.  Note that, if you have '
          'any changes in your download cache, trying to submit to pqm '
          'will always raise an error.  Also note that, if you have any '
          'changes in your download cache, you must explicitly choose to '
          'include or ignore the changes.'))


postmortem_option = Option(
    'postmortem', short_name='p',
    help=('Drop to interactive prompt after the test and before shutting '
          'down the instance for postmortem analysis of the EC2 instance '
          'and/or of this script.'))


attached_option = Option(
    'attached',
    help=("Remain attached, i.e. do not go headless. Implied by --postmortem "
          "and --file."))


def filename_type(filename):
    """An option validator for filenames.

    :raise: an error if 'filename' is not a file we can write to.
    :return: 'filename' otherwise.
    """
    if filename is None:
        return filename

    check_file = filename
    if os.path.exists(check_file):
        if not os.path.isfile(check_file):
            raise BzrCommandError(
                'file argument %s exists and is not a file' % (filename,))
    else:
        check_file = os.path.dirname(check_file)
        if (not os.path.exists(check_file) or
            not os.path.isdir(check_file)):
            raise BzrCommandError(
                'file %s cannot be created.' % (filename,))
    if not os.access(check_file, os.W_OK):
        raise BzrCommandError(
            'you do not have permission to write %s' % (filename,))
    return filename


def set_trace_if(enable_debugger=False):
    """If `enable_debugger` is True, drop into the debugger."""
    if enable_debugger:
        pdb.set_trace()


class EC2Command(Command):
    """Subclass of `Command` that customizes usage to say 'ec2' not 'bzr'.

    When https://bugs.edge.launchpad.net/bzr/+bug/431054 is fixed, we can
    delete this class, or at least make it less of a copy/paste/hack of the
    superclass.
    """

    def _usage(self):
        """Return single-line grammar for this command.

        Only describes arguments, not options.
        """
        s = 'ec2 ' + self.name() + ' '
        for aname in self.takes_args:
            aname = aname.upper()
            if aname[-1] in ['$', '+']:
                aname = aname[:-1] + '...'
            elif aname[-1] == '?':
                aname = '[' + aname[:-1] + ']'
            elif aname[-1] == '*':
                aname = '[' + aname[:-1] + '...]'
            s += aname + ' '
        s = s[:-1]      # remove last space
        return s


def _get_branches_and_test_branch(trunk, branch, test_branch):
    """Interpret the command line options to find which branch to test.

    :param trunk: The value of the --trunk option.
    :param branch: The value of the --branch options.
    :param test_branch: The value of the TEST_BRANCH argument.
    """
    if trunk:
        if test_branch is not None:
            raise BzrCommandError(
                "Cannot specify both a branch to test and --trunk")
        else:
            test_branch = TRUNK_BRANCH
    else:
        if test_branch is None:
            test_branch = '.'
    branches = [data.split('=', 1) for data in branch]
    return branches, test_branch


DEFAULT_TEST_OPTIONS = '--subunit -vvv'


class cmd_test(EC2Command):
    """Run the test suite in ec2."""

    takes_options = [
        branch_option,
        trunk_option,
        machine_id_option,
        instance_type_option,
        Option(
            'file', short_name='f', type=filename_type,
            help=('Store abridged test results in FILE.')),
        ListOption(
            'email', short_name='e', argname='EMAIL', type=str,
            help=('Email address to which results should be mailed.  '
                  'Defaults to the email address from `bzr whoami`. May be '
                  'supplied multiple times. `bzr whoami` will be used as '
                  'the From: address.')),
        Option(
            'noemail', short_name='n',
            help=('Do not try to email results.')),
        Option(
            'test-options', short_name='o', type=str,
            help=('Test options to pass to the remote test runner.  Defaults '
                  "to ``-o '-vv'``.  For instance, to run specific tests, "
                  "you might use ``-o '-vvt my_test_pattern'``.")),
        Option(
            'submit-pqm-message', short_name='s', type=str, argname="MSG",
            help=(
                'A pqm message to submit if the test run is successful.  If '
                'provided, you will be asked for your GPG passphrase before '
                'the test run begins.')),
        Option(
            'pqm-public-location', type=str,
            help=('The public location for the pqm submit, if a pqm message '
                  'is provided (see --submit-pqm-message).  If this is not '
                  'provided, for local branches, bzr configuration is '
                  'consulted; for remote branches, it is assumed that the '
                  'remote branch *is* a public branch.')),
        Option(
            'pqm-submit-location', type=str,
            help=('The submit location for the pqm submit, if a pqm message '
                  'is provided (see --submit-pqm-message).  If this option '
                  'is not provided, the script will look for an explicitly '
                  'specified launchpad branch using the -b/--branch option; '
                  'if that branch was specified and is owned by the '
                  'launchpad-pqm user on launchpad, it is used as the pqm '
                  'submit location. Otherwise, for local branches, bzr '
                  'configuration is consulted; for remote branches, it is '
                  'assumed that the submit branch is %s.'
                  % (TRUNK_BRANCH,))),
        Option(
            'pqm-email', type=str,
            help=(
                'Specify the email address of the PQM you are submitting to. '
                'If the branch is local, then the bzr configuration is '
                'consulted; for remote branches "Launchpad PQM '
                '<launchpad@pqm.canonical.com>" is used by default.')),
        postmortem_option,
        attached_option,
        debug_option,
        Option(
            'open-browser',
            help=('Open the results page in your default browser')),
        include_download_cache_changes_option,
        ]

    takes_args = ['test_branch?']

    def run(self, test_branch=None, branch=None, trunk=False, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE,
            file=None, email=None, test_options=DEFAULT_TEST_OPTIONS,
            noemail=False, submit_pqm_message=None, pqm_public_location=None,
            pqm_submit_location=None, pqm_email=None, postmortem=False,
            attached=False, debug=False, open_browser=False,
            include_download_cache_changes=False):
        set_trace_if(debug)
        if branch is None:
            branch = []
        branches, test_branch = _get_branches_and_test_branch(
            trunk, branch, test_branch)
        if (postmortem or file):
            attached = True
        if noemail:
            if email:
                raise BzrCommandError(
                    'May not supply both --no-email and an --email address')
        else:
            if email == []:
                email = True

        if not attached and not (email or submit_pqm_message):
            raise BzrCommandError(
                'You have specified no way to get the results '
                'of your headless test run.')

        if (test_options != DEFAULT_TEST_OPTIONS
            and submit_pqm_message is not None):
            raise BzrCommandError(
                "Submitting to PQM with non-default test options isn't "
                "supported")

        session_name = EC2SessionName.make(EC2TestRunner.name)
        instance = EC2Instance.make(session_name, instance_type, machine)

        runner = EC2TestRunner(
            test_branch, email=email, file=file,
            test_options=test_options, headless=(not attached),
            branches=branches, pqm_message=submit_pqm_message,
            pqm_public_location=pqm_public_location,
            pqm_submit_location=pqm_submit_location,
            open_browser=open_browser, pqm_email=pqm_email,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, launchpad_login=instance._launchpad_login,
            timeout=480)

        instance.set_up_and_run(postmortem, attached, runner.run_tests)


class cmd_land(EC2Command):
    """Land a merge proposal on Launchpad."""

    takes_options = [
        debug_option,
        Option('dry-run', help="Just print the equivalent ec2 test command."),
        Option('print-commit', help="Print the full commit message."),
        Option(
            'testfix',
            help="This is a testfix (tags commit with [testfix])."),
        Option(
            'no-qa',
            help="Does not require QA (tags commit with [no-qa])."),
        Option(
            'incremental',
            help="Incremental to other bug fix (tags commit with [incr])."),
        Option(
            'rollback', type=int,
            help=(
                "Rollback given revision number. (tags commit with "
                "[rollback=revno]).")),
        Option(
            'commit-text', short_name='s', type=str,
            help=(
                'A description of the landing, not including reviewer '
                'metadata etc.')),
        Option(
            'force',
            help="Land the branch even if the proposal is not approved."),
        attached_option,
        ]

    takes_args = ['merge_proposal?']

    def _get_landing_command(self, source_url, target_url, commit_message,
                             emails, attached):
        """Return the command that would need to be run to submit with ec2."""
        ec2_path = os.path.join(get_launchpad_root(), 'utilities', 'ec2')
        command = [ec2_path, 'test']
        if attached:
            command.extend(['--attached'])
        command.extend(['--email=%s' % email for email in emails])
        # 'ec2 test' has a bug where you cannot pass full URLs to branches to
        # the -b option. It has special logic for 'launchpad' branches, so we
        # piggy back on this to get 'devel' or 'db-devel'.
        target_branch_name = target_url.split('/')[-1]
        command.extend(
            ['-b', 'launchpad=%s' % (target_branch_name), '-s',
             commit_message, str(source_url)])
        return command

    def run(self, merge_proposal=None, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE, postmortem=False,
            debug=False, commit_text=None, dry_run=False, testfix=False,
            no_qa=False, incremental=False, rollback=None, print_commit=False,
            force=False, attached=False):
        try:
            from devscripts.autoland import (
                LaunchpadBranchLander, MissingReviewError, MissingBugsError,
                MissingBugsIncrementalError)
        except ImportError:
            self.outf.write(
                "***************************************************\n\n"
                "Could not load the autoland module; please ensure\n"
                "that launchpadlib and lazr.uri are installed and\n"
                "found in sys.path/PYTHONPATH.\n\n"
                "Note that these should *not* be installed system-\n"
                "wide because this will break the rest of Launchpad.\n\n"
                "***************************************************\n")
            raise
        set_trace_if(debug)
        if print_commit and dry_run:
            raise BzrCommandError(
                "Cannot specify --print-commit and --dry-run.")
        lander = LaunchpadBranchLander.load()

        if merge_proposal is None:
            (tree, bzrbranch, relpath) = (
                BzrDir.open_containing_tree_or_branch('.'))
            mp = lander.get_merge_proposal_from_branch(bzrbranch)
        else:
            mp = lander.load_merge_proposal(merge_proposal)
        if not mp.is_approved:
            if force:
                print "Merge proposal is not approved, landing anyway."
            else:
                raise BzrCommandError(
                    "Merge proposal is not approved. Get it approved, or use "
                    "--force to land it without approval.")
        if commit_text is None:
            commit_text = mp.commit_message
        if commit_text is None:
            raise BzrCommandError(
                "Commit text not specified. Use --commit-text, or specify a "
                "message on the merge proposal.")
        if rollback and (no_qa or incremental):
            print (
                "--rollback option used. Ignoring --no-qa and --incremental.")
        try:
            commit_message = mp.build_commit_message(
                commit_text, testfix, no_qa, incremental, rollback=rollback)
        except MissingReviewError:
            raise BzrCommandError(
                "Cannot land branches that haven't got approved code "
                "reviews. Get an 'Approved' vote so we can fill in the "
                "[r=REVIEWER] section.")
        except MissingBugsError:
            raise BzrCommandError(
                "Branch doesn't have linked bugs and doesn't have no-qa "
                "option set. Use --no-qa, or link the related bugs to the "
                "branch.")
        except MissingBugsIncrementalError:
            raise BzrCommandError(
                "--incremental option requires bugs linked to the branch. "
                "Link the bugs or remove the --incremental option.")

        # Override the commit message in the MP with the commit message built
        # with the proper tags.
        try:
            mp.set_commit_message(commit_message)
        except Exception, e:
            raise BzrCommandError(
                "Unable to set the commit message in the merge proposal.\n"
                "Got: %s" % e)

        if print_commit:
            print commit_message
            return

        emails = mp.get_stakeholder_emails()

        target_branch_name = mp.target_branch.split('/')[-1]
        branches = [('launchpad', target_branch_name)]

        landing_command = self._get_landing_command(
            mp.source_branch, mp.target_branch, commit_message,
            emails, attached)

        if dry_run:
            print landing_command
            return

        session_name = EC2SessionName.make(EC2TestRunner.name)
        instance = EC2Instance.make(
            session_name, instance_type, machine)

        runner = EC2TestRunner(
            mp.source_branch, email=emails,
            headless=(not attached),
            branches=branches, pqm_message=commit_message,
            instance=instance,
            launchpad_login=instance._launchpad_login,
            test_options=DEFAULT_TEST_OPTIONS,
            timeout=480)

        instance.set_up_and_run(postmortem, attached, runner.run_tests)


class cmd_demo(EC2Command):
    """Start a demo instance of Launchpad.

    See https://wiki.canonical.com/Launchpad/EC2Test/ForDemos
    """

    takes_options = [
        branch_option,
        trunk_option,
        machine_id_option,
        instance_type_option,
        postmortem_option,
        debug_option,
        include_download_cache_changes_option,
        ListOption(
            'demo', type=str,
            help="Allow this netmask to connect to the instance."),
        ]

    takes_args = ['test_branch?']

    def run(self, test_branch=None, branch=None, trunk=False, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE, debug=False,
            include_download_cache_changes=False, demo=None):
        set_trace_if(debug)
        if branch is None:
            branch = []
        branches, test_branch = _get_branches_and_test_branch(
            trunk, branch, test_branch)

        session_name = EC2SessionName.make(EC2TestRunner.name)
        instance = EC2Instance.make(
            session_name, instance_type, machine, demo)

        runner = EC2TestRunner(
            test_branch, branches=branches,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, launchpad_login=instance._launchpad_login)

        demo_network_string = '\n'.join(
            '  ' + network for network in demo)

        # Wait until the user exits the postmortem session, then kill the
        # instance.
        postmortem = True
        shutdown = True
        instance.set_up_and_run(
            postmortem, shutdown, self.run_server, runner, instance,
            demo_network_string)

    def run_server(self, runner, instance, demo_network_string):
        runner.run_demo_server()
        ec2_ip = socket.gethostbyname(instance.hostname)
        print (
            "\n\n"
            "********************** DEMO *************************\n"
            "It may take 20 seconds for the demo server to start up."
            "\nTo demo to other users, you still need to open up\n"
            "network access to the ec2 instance from their IPs by\n"
            "entering command like this in the interactive python\n"
            "interpreter at the end of the setup. "
            "\n  self.security_group.authorize("
            "'tcp', 443, 443, '10.0.0.5/32')\n\n"
            "These demo networks have already been granted access on "
            "port 80 and 443:\n" + demo_network_string +
            "\n\nYou also need to edit your /etc/hosts to point\n"
            "launchpad.dev at the ec2 instance's IP like this:\n"
            "  " + ec2_ip + "    launchpad.dev\n\n"
            "See "
            "<https://wiki.canonical.com/Launchpad/EC2Test/ForDemos>."
            "\n*****************************************************"
            "\n\n")


class cmd_update_image(EC2Command):
    """Make a new AMI."""

    takes_options = [
        machine_id_option,
        instance_type_option,
        postmortem_option,
        debug_option,
        ListOption(
            'extra-update-image-command', type=str,
            help=('Run this command (with an ssh agent) on the image before '
                  'running the default update steps.  Can be passed more '
                  'than once, the commands will be run in the order '
                  'specified.')),
        Option(
            'public',
            help=('Remove proprietary code from the sourcecode directory '
                  'before bundling.')),
        ]

    takes_args = ['ami_name']

    def run(self, ami_name, machine=None, instance_type='m1.large',
            debug=False, postmortem=False, extra_update_image_command=None,
            public=False):
        set_trace_if(debug)

        if extra_update_image_command is None:
            extra_update_image_command = []

        # These environment variables are passed through ssh connections to
        # fresh Ubuntu images and cause havoc if the locales they refer to are
        # not available. We kill them here to ease bootstrapping, then we
        # later modify the image to prevent sshd from accepting them.
        for variable in ['LANG', 'LC_ALL', 'LC_TIME']:
            os.environ.pop(variable, None)

        credentials = EC2Credentials.load_from_file()

        session_name = EC2SessionName.make(EC2TestRunner.name)
        instance = EC2Instance.make(
            session_name, instance_type, machine,
            credentials=credentials)
        instance.check_bundling_prerequisites(
            ami_name, credentials)
        instance.set_up_and_run(
            postmortem, True, self.update_image, instance,
            extra_update_image_command, ami_name, credentials, public)

    def update_image(self, instance, extra_update_image_command, ami_name,
                     credentials, public):
        """Bring the image up to date.

        The steps we take are:

         * run any commands specified with --extra-update-image-command
         * update sourcecode
         * update the launchpad branch to the tip of the trunk branch.
         * update the copy of the download-cache.
         * bundle the image

        :param instance: `EC2Instance` to operate on.
        :param extra_update_image_command: List of commands to run on the
            instance in addition to the usual ones.
        :param ami_name: The name to give the created AMI.
        :param credentials: An `EC2Credentials` object.
        :param public: If true, remove proprietary code from the sourcecode
            directory before bundling.
        """
        # Do NOT accept environment variables via ssh connections.
        user_connection = instance.connect()
        user_connection.perform('sudo apt-get -qqy update')
        user_connection.perform('sudo apt-get -qqy upgrade')
        user_connection.perform(
            'sudo sed -i "s/^AcceptEnv/#AcceptEnv/" /etc/ssh/sshd_config')
        user_connection.perform(
            'sudo kill -HUP $(< /var/run/sshd.pid)')
        # Reconnect to ensure that the environment is clean.
        user_connection.reconnect()
        user_connection.perform(
            'bzr launchpad-login %s' % (instance._launchpad_login,))
        for cmd in extra_update_image_command:
            user_connection.run_with_ssh_agent(cmd)
        user_connection.run_with_ssh_agent(
            'bzr pull -d /var/launchpad/test ' + TRUNK_BRANCH)
        user_connection.run_with_ssh_agent(
            'bzr pull -d /var/launchpad/download-cache '
            'lp:lp-source-dependencies')
        if public:
            update_sourcecode_options = ' --public-only'
        else:
            update_sourcecode_options = ''
        user_connection.run_with_ssh_agent(
            "/var/launchpad/test/utilities/update-sourcecode "
            "/var/launchpad/sourcecode" + update_sourcecode_options)
        user_connection.perform(
            'rm -rf .ssh/known_hosts .bazaar .bzr.log')
        user_connection.close()
        instance.bundle(ami_name, credentials)


class cmd_images(EC2Command):
    """Display all available images.

    The first in the list is the default image.
    """

    def run(self):
        credentials = EC2Credentials.load_from_file()
        session_name = EC2SessionName.make(EC2TestRunner.name)
        account = credentials.connect(session_name)
        format = "%5s  %-12s  %-12s  %-12s %s\n"
        self.outf.write(
            format % ("Rev", "AMI", "Owner ID", "Owner", "Description"))
        for revision, images in account.find_images():
            for image in images:
                self.outf.write(format % (
                    revision, image.id, image.ownerId,
                    VALID_AMI_OWNERS.get(image.ownerId, "unknown"),
                    image.description or ''))


class cmd_list(EC2Command):
    """List all your current EC2 test runs.

    If an instance is publishing an 'info.json' file with 'description' and
    'failed-yet' fields, this command will list that instance, whether it has
    failed the test run and how long it has been up for.

    [FAILED] means that the has been a failing test. [OK] means that the test
    run has had no failures yet, it's not a guarantee of a successful run.
    """

    aliases = ["ls"]

    takes_options = [
        Option('show-urls',
               help="Include more information about each instance"),
        Option('all', short_name='a',
               help="Show all instances, not just ones with ec2test data."),
        ]

    def iter_instances(self, account):
        """Iterate through all instances in 'account'."""
        for reservation in account.conn.get_all_instances():
            for instance in reservation.instances:
                yield instance

    def get_uptime(self, instance):
        """How long has 'instance' been running?"""
        expected_format = '%Y-%m-%dT%H:%M:%S.000Z'
        launch_time = datetime.strptime(instance.launch_time, expected_format)
        return (
            datetime.utcnow().replace(tzinfo=UTC)
            - launch_time.replace(tzinfo=UTC))

    def get_http_url(self, instance):
        hostname = instance.public_dns_name
        if not hostname:
            return
        return 'http://%s/' % (hostname,)

    def get_ec2test_info(self, instance):
        """Load the ec2test-specific information published by 'instance'."""
        url = self.get_http_url(instance)
        if url is None:
            return
        try:
            json = get_transport(url).get_bytes('info.json')
        except (ConnectionError, NoSuchFile):
            # Probably not an ec2test instance, or not ready yet.
            return None
        return simplejson.loads(json)

    def format_instance(self, instance, data, verbose):
        """Format 'instance' for display.

        :param instance: The EC2 instance to display.
        :param data: Launchpad-specific data.
        :param verbose: Whether we want verbose output.
        """
        uptime = self.get_uptime(instance)
        if data is None:
            description = instance.id
            current_status =     'unknown '
        else:
            description = data['description']
            if data['failed-yet']:
                current_status = '[FAILED]'
            else:
                current_status = '[OK]    '
        output = '%s  %s (up for %s)' % (description, current_status, uptime)
        if verbose:
            url = self.get_http_url(instance)
            if url is None:
                url = "No web service"
            output += '\n  %s' % (url,)
        return output

    def format_summary(self, by_state):
        return ', '.join(
            ': '.join((state, str(num)))
            for (state, num) in sorted(list(by_state.items())))

    def run(self, show_urls=False, all=False):
        credentials = EC2Credentials.load_from_file()
        session_name = EC2SessionName.make(EC2TestRunner.name)
        account = credentials.connect(session_name)
        instances = list(self.iter_instances(account))
        if len(instances) == 0:
            print "No instances running."
            return

        by_state = {}
        for instance in instances:
            by_state[instance.state] = by_state.get(instance.state, 0) + 1
            data = self.get_ec2test_info(instance)
            if data is None and not all:
                continue
            print self.format_instance(instance, data, show_urls)
        print 'Summary: %s' % (self.format_summary(by_state),)


class cmd_help(EC2Command):
    """Show general help or help for a command."""

    aliases = ["?", "--help", "-?", "-h"]
    takes_args = ["topic?"]

    def run(self, topic=None):
        """
        Show help for the C{bzrlib.commands.Command} matching C{topic}.

        @param topic: Optionally, the name of the topic to show.  Default is
            to show some basic usage information.
        """
        if topic is None:
            self.outf.write('Usage:    ec2 <command> <options>\n\n')
            self.outf.write('Available commands:\n')
            help_commands(self.outf)
        else:
            command = self.controller._get_command(None, topic)
            if command is None:
                self.outf.write("%s is an unknown command.\n" % (topic,))
            text = command.get_help_text()
            if text:
                self.outf.write(text)
