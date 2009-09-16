import code
import traceback

from bzrlib.commands import Command
from bzrlib.errors import BzrCommandError
from bzrlib.option import ListOption, Option

import paramiko
import socket

from devscripts.ec2test import error_and_quit
from devscripts.ec2test.commandline import (
    DEFAULT_INSTANCE_TYPE, AVAILABLE_INSTANCE_TYPES)
from devscripts.ec2test.credentials import CredentialsError, EC2Credentials
from devscripts.ec2test.instance import EC2Instance
from devscripts.ec2test.testrunner import EC2TestRunner, TRUNK_BRANCH


def run_with_instance(instance, run, postmortem):
    """Call run(), then allow post mortem debugging and shut down `instance`.

    :param instance: A running `EC2Instance`.  If `run` returns True, it will
        be shut down before this function returns.
    :param run: A callable that will be called with no arguments to do
        whatever needs to be done with the instance.
    :param postmortem: If this flag is true, any exceptions will be caught and
        an interactive session run to allow debugging the problem.
    """
    shutdown = True
    try:
        try:
            shutdown = run()
        except Exception:
            # If we are running in demo or postmortem mode, it is really
            # helpful to see if there are any exceptions before it waits
            # in the console (in the finally block), and you can't figure
            # out why it's broken.
            traceback.print_exc()
    finally:
        try:
            if postmortem:
                console = code.InteractiveConsole(locals())
                console.interact((
                    'Postmortem Console.  EC2 instance is not yet dead.\n'
                    'It will shut down when you exit this prompt (CTRL-D).\n'
                    '\n'
                    'Tab-completion is enabled.'
                    '\n'
                    'Test runner instance is available as `runner`.\n'
                    'Also try these:\n'
                    '  http://%(dns)s/current_test.log\n'
                    '  ssh -A %(dns)s') %
                                 {'dns': instance.hostname})
                print 'Postmortem console closed.'
        finally:
            if shutdown:
                instance.shutdown()


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

instance_type_option = Option(
    'instance', short_name='i', type=str, param_name='instance_type',
    help=('The AWS instance type on which to base this run. '
          'Available options are %r. Defaults to `%s`.' %
          (AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE)))

debug_option = Option(
    'debug', short_name='d',
    help=('Drop to pdb trace as soon as possible.'))

trunk_option = Option(
    'trunk', short_name='t',
    help=('Run the trunk as the branch'))

include_download_cache_changes_option = Option(
    'include-download-cache-changes', short_name='c',
    help=('Include any changes in the download cache (added or unknown) '
          'in the download cache of the test run.  Note that, if you have '
          'any changes in your download cache, trying to submit to pqm '
          'will always raise an error.  Also note that, if you have any '
          'changes in your download cache, you must explicitly choose to '
          'include or ignore the changes.'))


class EC2Command(Command):
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


def get_user_key():
    agent = paramiko.Agent()
    keys = agent.get_keys()
    if len(keys) == 0:
        error_and_quit(
            'You must have an ssh agent running with keys installed that '
            'will allow the script to rsync to devpad and get your '
            'branch.\n')
    user_key = agent.get_keys()[0]
    return user_key

def make_instance(instance_type, machine, demo_networks=None):
    # Get the AWS identifier and secret identifier.
    if instance_type not in AVAILABLE_INSTANCE_TYPES:
        raise BzrCommandError('Unknown instance type.')
    try:
        credentials = EC2Credentials.load_from_file()
    except CredentialsError, e:
        error_and_quit(str(e))

    return EC2Instance.make(
        credentials, EC2TestRunner.name, instance_type=instance_type,
        machine_id=machine, demo_networks=demo_networks)


class cmd_test(EC2Command):
    """Run the tests in ec2."""

    takes_options = [
        branch_option,
        trunk_option,
        machine_id_option,
        instance_type_option,
        Option(
            'file', short_name='f',
            help=('Store abridged test results in FILE.')),
        ListOption(
            'email', short_name='e', argname='EMAIL', type=str,
            help=('Email address to which results should be mailed.  Defaults to '
                  'the email address from `bzr whoami`. May be supplied multiple '
                  'times. The first supplied email address will be used as the '
                  'From: address.')),
        Option(
            'noemail', short_name='n',
            help=('Do not try to email results.')),
        Option(
            'test-options', short_name='o',
            help=('Test options to pass to the remote test runner.  Defaults to '
                  "``-o '-vv'``.  For instance, to run specific tests, you might "
                  "use ``-o '-vvt my_test_pattern'``.")),
        Option(
            'submit-pqm-message', short_name='s', type=str, argname="MSG",
            help=('A pqm message to submit if the test run is successful.  If '
                  'provided, you will be asked for your GPG passphrase before '
                  'the test run begins.')),
        Option(
            'pqm-public-location', type=str,
            help=('The public location for the pqm submit, if a pqm message is '
                  'provided (see --submit-pqm-message).  If this is not provided, '
                  'for local branches, bzr configuration is consulted; for '
                  'remote branches, it is assumed that the remote branch *is* '
                  'a public branch.')),
        Option(
            'pqm-submit-location', type=str,
            help=('The submit location for the pqm submit, if a pqm message is '
                  'provided (see --submit-pqm-message).  If this option is not '
                  'provided, the script will look for an explicitly specified '
                  'launchpad branch using the -b/--branch option; if that branch '
                  'was specified and is owned by the launchpad-pqm user on '
                  'launchpad, it is used as the pqm submit location. Otherwise, '
                  'for local branches, bzr configuration is consulted; for '
                  'remote branches, it is assumed that the submit branch is %s.'
                  % (TRUNK_BRANCH,))),
        Option(
            'pqm-email', type=str,
            help=('Specify the email address of the PQM you are submitting to. '
                  'If the branch is local, then the bzr configuration is '
                  'consulted; for remote branches "Launchpad PQM '
                  '<launchpad@pqm.canonical.com>" is used by default.')),
        Option(
            'postmortem', short_name='p',
            help=('Drop to interactive prompt after the test and before shutting '
                  'down the instance for postmortem analysis of the EC2 instance '
                  'and/or of this script.')),
        Option(
            'headless',
            help=('After building the instance and test, run the remote tests '
                  'headless.  Cannot be used with postmortem '
                  'or file.')),
        debug_option,
        Option(
            'open-browser',
            help=('Open the results page in your default browser')),
        include_download_cache_changes_option,
        ]

    takes_args = ['test_branch?']

    def run(self, test_branch=None, branch=[], trunk=False, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE,
            file=None, email=None, test_options='-vv', noemail=False,
            submit_pqm_message=None, pqm_public_location=None,
            pqm_submit_location=None, pqm_email=None, postmortem=False,
            headless=False, debug=False, open_browser=False,
            include_download_cache_changes=False):
        if debug:
            import pdb; pdb.set_trace()
        if trunk:
            if test_branch is not None:
                raise BzrCommandError(
                    "Cannot specify both a branch to test and --trunk")
            else:
                test_branch = TRUNK_BRANCH
        else:
            if test_branch is None:
                test_branch = '.'
        if ((postmortem or file) and headless):
            raise BzrCommandError(
                'Headless mode currently does not support postmortem or file '
                ' options.')
        if noemail:
            if email:
                raise BzrCommandError(
                    'May not supply both --no-email and an --email address')
        else:
            if email == []:
                email = True
        branches = [data.split('=', 1) for data in branch]

        if headless and not (email or submit_pqm_message):
            raise BzrCommandError(
                'You have specified no way to get the results '
                'of your headless test run.')


        instance = make_instance(instance_type, machine)

        user_key = get_user_key()

        runner = EC2TestRunner(
            branch, email=email, file=file,
            test_options=test_options, headless=headless,
            branches=branches,
            pqm_message=submit_pqm_message,
            pqm_public_location=pqm_public_location,
            pqm_submit_location=pqm_submit_location,
            open_browser=open_browser, pqm_email=pqm_email,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, vals=instance._vals)

        instance.start()
        instance.set_up_user(user_key)
        run_with_instance(
            instance, runner.run_tests, postmortem)


class cmd_demo(EC2Command):
    """Start a demo instance of Launchpad.

    See https://wiki.canonical.com/Launchpad/EC2Test/ForDemos
    """

    takes_options = [
        branch_option,
        trunk_option,
        machine_id_option,
        instance_type_option,
        Option(
            'postmortem', short_name='p',
            help=('Drop to interactive prompt after the test and before shutting '
                  'down the instance for postmortem analysis of the EC2 instance '
                  'and/or of this script.')),
        debug_option,
        include_download_cache_changes_option,
        ListOption(
            'demo-network', type=str,
            help="Allow this netmask to connect to the instance."),
        ]

    takes_args = ['test_branch?']

    def run(self, test_branch=None, branch=[], trunk=False, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE, debug=False,
            include_download_cache_changes=False, demo=None):
        if debug:
            import pdb; pdb.set_trace()
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

        instance = make_instance(instance_type, machine, demo)

        user_key = get_user_key()

        runner = EC2TestRunner(
            branch, branches=branches,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, vals=instance._vals)

        instance.start()
        instance.set_up_user(user_key)

        def run_server():
            runner.run_demo_server()
            demo_network_string = '\n'.join(
                '  ' + network for network in demo)
            ec2_ip = socket.gethostbyname(instance.hostname)
            print (
                "\n\n"
                "********************** DEMO *************************\n"
                "It may take 20 seconds for the demo server to start up."
                "\nTo demo to other users, you still need to open up\n"
                "network access to the ec2 instance from their IPs by\n"
                "entering command like this in the interactive python\n"
                "interpreter at the end of the setup. "
                "\n  instance.security_group.authorize("
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

        run_with_instance(
            instance, run_server, True)


class cmd_update_image(EC2Command):
    def run(self):
        print 'foo'
