# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The command classes for the 'ec2' utility."""

__metaclass__ = type
__all__ = []

import pdb

from bzrlib.commands import Command
from bzrlib.errors import BzrCommandError
from bzrlib.help import help_commands
from bzrlib.option import ListOption, Option

import socket

from devscripts.ec2test.credentials import EC2Credentials
from devscripts.ec2test.instance import (
    AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE, EC2Instance,
    get_user_key)
from devscripts.ec2test.testrunner import EC2TestRunner, TRUNK_BRANCH


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


class cmd_test(EC2Command):
    """Run the test suite in ec2."""

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
            'test-options', short_name='o', type=str,
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
        postmortem_option,
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
            pdb.set_trace()
        branches, test_branch = _get_branches_and_test_branch(
            trunk, branch, test_branch)
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

        if headless and not (email or submit_pqm_message):
            raise BzrCommandError(
                'You have specified no way to get the results '
                'of your headless test run.')


        instance = EC2Instance.make(
            EC2TestRunner.name, instance_type, machine)

        runner = EC2TestRunner(
            test_branch, email=email, file=file,
            test_options=test_options, headless=headless,
            branches=branches, pqm_message=submit_pqm_message,
            pqm_public_location=pqm_public_location,
            pqm_submit_location=pqm_submit_location,
            open_browser=open_browser, pqm_email=pqm_email,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, vals=instance._vals)

        instance.set_up_and_run(
            dict(postmortem=postmortem, shutdown=not headless),
            runner.run_tests)


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

    def run(self, test_branch=None, branch=[], trunk=False, machine=None,
            instance_type=DEFAULT_INSTANCE_TYPE, debug=False,
            include_download_cache_changes=False, demo=None):
        if debug:
            pdb.set_trace()
        branches, test_branch = _get_branches_and_test_branch(
            trunk, branch, test_branch)

        instance = EC2Instance.make(
            EC2TestRunner.name, instance_type, machine, demo)

        runner = EC2TestRunner(
            test_branch, branches=branches,
            include_download_cache_changes=include_download_cache_changes,
            instance=instance, vals=instance._vals)

        demo_network_string = '\n'.join(
            '  ' + network for network in demo)

        # Wait until the user exits the postmortem session, then kill the
        # instance.
        instance.set_up_and_run(
            dict(postmortem=True),
            self.run_server, runner, demo_network_string)

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


update_from_scratch = """
set -xe

sudo sed -ie 's/main universe/main universe multiverse/' /etc/apt/sources.list

sudo sh -c 'cat >> /etc/apt/sources.list' << EOF
deb http://ppa.launchpad.net/launchpad/ubuntu hardy main
deb http://ppa.launchpad.net/bzr/ubuntu hardy main
deb http://ppa.launchpad.net/bzr-beta-ppa/ubuntu hardy main
EOF

sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 2af499cb24ac5f65461405572d1ffb6c0a5174af
sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com ece2800bacf028b31ee3657cd702bf6b8c6c1efd
sudo apt-key adv --recv-keys --keyserver keyserver.ubuntu.com cbede690576d1e4e813f6bb3ebaf723d37b19b80

sudo aptitude update
sudo aptitude -y full-upgrade

sudo apt-get -y install launchpad-developer-dependencies apache2

sudo mkdir /var/launchpad

sudo chown -R ubuntu:ubuntu /var/www /var/launchpad

bzr launchpad-login %(launchpad-login)s
bzr init-repo --2a /var/launchpad
bzr branch lp:~launchpad-pqm/launchpad/devel /var/launchpad/test
mkdir /var/launchpad/sourcecode
/var/launchpad/test/utilities/update-sourcecode /var/launchpad/sourcecode
"""

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
                  'running the default update steps.  Can be passed more than '
                  'once, the commands will be run in the order specified.')),
        Option(
            'from-scratch',
            help=('XXX')),
        ]

    takes_args = ['ami_name']

    def run(self, ami_name, machine=None, instance_type='m1.large',
            debug=False, postmortem=False, extra_update_image_command=[],
            from_scratch=False):
        if debug:
            pdb.set_trace()

        credentials = EC2Credentials.load_from_file()

        instance = EC2Instance.make(
            EC2TestRunner.name, instance_type, machine,
            credentials=credentials)
        instance.check_bundling_prerequisites()

        instance.set_up_and_run(
            dict(postmortem=postmortem, set_up_user=True),
            self.update_image, instance, extra_update_image_command,
            from_scratch, False, ami_name, credentials)

    def add_ubuntu_user(self, instance):
        root_connection = instance.connect('root')
        as_root = root_connection.perform
        as_root('echo "root\tALL=NOPASSWD: ALL" >> /etc/sudoers')
        as_root('adduser --gecos "" --disabled-password ubuntu')
        as_root('echo "ubuntu\tALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers')
        as_root('sudo -u ubuntu mkdir /home/ubuntu/.ssh')
        remote_ssh_dir = '/home/ubuntu/.ssh'
        self.log('Setting up %s/authorized_keys\n' % remote_ssh_dir)
        as_root(
            'cp /root/.ssh/authorized_keys '
            '/home/ubuntu/.ssh/authorized_keys')
        as_root('chown -R ubuntu:ubuntu /home/ubuntu/')
        as_root('chmod 644 /home/ubuntu/.ssh/*')
        root_connection.close()
        instance.set_up_user(get_user_key())

    def update_image(self, instance, extra_update_image_command,
                     from_scratch, root_login, ami_name, credentials):
        """Bring the image up to date.

        The steps we take are:

         * run any commands specified with --extra-update-image-command
         * update sourcecode via rsync.
         * update the launchpad branch to the tip of the trunk branch.
         * update the copy of the download-cache.
         * remove the user account.
         * bundle the image

        :param instance: `EC2Instance` to operate on.
        :param extra_update_image_command: List of commands to run on the
            instance in addition to the usual ones.
        :param ami_name: The name to give the created AMI.
        :param credentials: An `EC2Credentials` object.
        """
        if from_scratch:
            if root_login:
                self.add_ubuntu_user(instance)
            user_connection = instance.connect()
            user_sftp = user_connection.ssh.open_sftp()
            update_sh = user_sftp.open('/home/ubuntu/update.sh', 'w')
            update_sh.write(update_from_scratch % instance._vals)
            update_sh.close()
            user_sftp.close()
            user_connection.run_with_ssh_agent(
                '/bin/sh /home/ubuntu/update.sh')
            user_connection.perform('rm /home/ubuntu/update.sh')
        else:
            user_connection = instance.connect()
        user_connection.perform('bzr launchpad-login %(launchpad-login)s')
        for cmd in extra_update_image_command:
            user_connection.run_with_ssh_agent(cmd)
        user_connection.run_with_ssh_agent(
            'bzr pull -d /var/launchpad/test ' + TRUNK_BRANCH)
        user_connection.run_with_ssh_agent(
            'bzr pull -d /var/launchpad/download-cache lp:lp-source-dependencies')
        user_connection.run_with_ssh_agent(
            "/var/launchpad/test/utilities/update-sourcecode "
            "/var/launchpad/sourcecode")
        user_connection.close()
        instance.bundle(ami_name, credentials)


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
