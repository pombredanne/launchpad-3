# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The command line parsing and entrypoint for ec2test."""

__metaclass__ = type
__all__ = [
    'main',
    ]

import code
import optparse
import os
import socket
import traceback
# The rlcompleter and readline modules change the behavior of the python
# interactive interpreter just by being imported.
import readline
import rlcompleter
import sys
# Shut up pyflakes.
rlcompleter

from bzrlib.plugins.launchpad.account import get_lp_login

import paramiko

from devscripts.ec2test import error_and_quit
from devscripts.ec2test.credentials import CredentialsError, EC2Credentials
from devscripts.ec2test.instance import EC2Instance
from devscripts.ec2test.testrunner import EC2TestRunner, TRUNK_BRANCH

readline.parse_and_bind('tab: complete')

DEFAULT_INSTANCE_TYPE = 'c1.xlarge'
AVAILABLE_INSTANCE_TYPES = ('m1.large', 'm1.xlarge', 'c1.xlarge')


# XXX: JonathanLange 2009-05-31: Strongly considering turning this into a
# Bazaar plugin -- probably would make the option parsing and validation
# easier.

def run_with_instance(instance, run, demo_networks, postmortem):
    try:
        try:
            run()
        except Exception:
            # If we are running in demo or postmortem mode, it is really
            # helpful to see if there are any exceptions before it waits
            # in the console (in the finally block), and you can't figure
            # out why it's broken.
            traceback.print_exc()
    finally:
        try:
            if demo_networks:
                demo_network_string = '\n'.join(
                    '  ' + network for network in demo_networks)
                ec2_ip = socket.gethostbyname(instance.hostname)
                print (
                    "\n\n"
                    "********************** DEMO *************************\n"
                    "It may take 20 seconds for the demo server to start up."
                    "\nTo demo to other users, you still need to open up\n"
                    "network access to the ec2 instance from their IPs by\n"
                    "entering command like this in the interactive python\n"
                    "interpreter at the end of the setup. "
                    "\n  runner.security_group.authorize("
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
            instance.shutdown()


def make_instance(instance_type, machine_id, demo_networks):
    # Validate instance_type and get default kernal and ramdisk.
    if instance_type not in AVAILABLE_INSTANCE_TYPES:
        raise ValueError('unknown instance_type %s' % (instance_type,))

    # Get the AWS identifier and secret identifier.
    try:
        credentials = EC2Credentials.load_from_file()
    except CredentialsError, e:
        error_and_quit(str(e))

    # Make the EC2 connection.
    account = credentials.connect(EC2TestRunner.name)

    # We do this here because it (1) cleans things up and (2) verifies
    # that the account is correctly set up. Both of these are appropriate
    # for initialization.
    #
    # We always recreate the keypairs because there is no way to
    # programmatically retrieve the private key component, unless we
    # generate it.
    account.delete_previous_key_pair()

    # get the image
    image = account.acquire_image(machine_id)

    vals = os.environ.copy()
    login = get_lp_login()
    if not login:
        error_and_quit(
            'you must have set your launchpad login in bzr.')
    vals['launchpad-login'] = login

    return EC2Instance(
        EC2TestRunner.name, image, instance_type, demo_networks,
        account, vals)


def main():
    parser = optparse.OptionParser(
        usage="%prog [options] [branch]",
        description=(
            "Check out a Launchpad branch and run all tests on an Amazon "
            "EC2 instance."))
    parser.add_option(
        '-f', '--file', dest='file', default=None,
        help=('Store abridged test results in FILE.'))
    parser.add_option(
        '-n', '--no-email', dest='no_email', default=False,
        action='store_true',
        help=('Do not try to email results.'))
    parser.add_option(
        '-e', '--email', action='append', dest='email', default=None,
        help=('Email address to which results should be mailed.  Defaults to '
              'the email address from `bzr whoami`. May be supplied multiple '
              'times. The first supplied email address will be used as the '
              'From: address.'))
    parser.add_option(
        '-o', '--test-options', dest='test_options', default='-vv',
        help=('Test options to pass to the remote test runner.  Defaults to '
              "``-o '-vv'``.  For instance, to run specific tests, you might "
              "use ``-o '-vvt my_test_pattern'``."))
    parser.add_option(
        '-b', '--branch', action='append', dest='branches',
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
    parser.add_option(
        '-t', '--trunk', dest='trunk', default=False,
        action='store_true',
        help=('Run the trunk as the branch'))
    parser.add_option(
        '-s', '--submit-pqm-message', dest='pqm_message', default=None,
        help=('A pqm message to submit if the test run is successful.  If '
              'provided, you will be asked for your GPG passphrase before '
              'the test run begins.'))
    parser.add_option(
        '--pqm-public-location', dest='pqm_public_location', default=None,
        help=('The public location for the pqm submit, if a pqm message is '
              'provided (see --submit-pqm-message).  If this is not provided, '
              'for local branches, bzr configuration is consulted; for '
              'remote branches, it is assumed that the remote branch *is* '
              'a public branch.'))
    parser.add_option(
        '--pqm-submit-location', dest='pqm_submit_location', default=None,
        help=('The submit location for the pqm submit, if a pqm message is '
              'provided (see --submit-pqm-message).  If this option is not '
              'provided, the script will look for an explicitly specified '
              'launchpad branch using the -b/--branch option; if that branch '
              'was specified and is owned by the launchpad-pqm user on '
              'launchpad, it is used as the pqm submit location. Otherwise, '
              'for local branches, bzr configuration is consulted; for '
              'remote branches, it is assumed that the submit branch is %s.'
              % (TRUNK_BRANCH,)))
    parser.add_option(
        '--pqm-email', dest='pqm_email', default=None,
        help=('Specify the email address of the PQM you are submitting to. '
              'If the branch is local, then the bzr configuration is '
              'consulted; for remote branches "Launchpad PQM '
              '<launchpad@pqm.canonical.com>" is used by default.'))
    parser.add_option(
        '-m', '--machine', dest='machine_id', default=None,
        help=('The AWS machine identifier (AMID) on which to base this run. '
              'You should typically only have to supply this if you are '
              'testing new AWS images. Defaults to trying to find the most '
              'recent one with an approved owner.'))
    parser.add_option(
        '-i', '--instance', dest='instance_type',
        default=DEFAULT_INSTANCE_TYPE,
        help=('The AWS instance type on which to base this run. '
              'Available options are %r. Defaults to `%s`.' %
              (AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE)))
    parser.add_option(
        '-p', '--postmortem', dest='postmortem', default=False,
        action='store_true',
        help=('Drop to interactive prompt after the test and before shutting '
              'down the instance for postmortem analysis of the EC2 instance '
              'and/or of this script.'))
    parser.add_option(
        '--headless', dest='headless', default=False,
        action='store_true',
        help=('After building the instance and test, run the remote tests '
              'headless.  Cannot be used with postmortem '
              'or file.'))
    parser.add_option(
        '-d', '--debug', dest='debug', default=False,
        action='store_true',
        help=('Drop to pdb trace as soon as possible.'))
    # Use tabs to force a newline in the help text.
    fake_newline = "\t\t\t\t\t\t\t"
    parser.add_option(
        '--demo', action='append', dest='demo_networks',
        help=("Don't run tests. Instead start a demo instance of Launchpad. "
              "You can allow multiple networks to access the demo by "
              "repeating the argument." + fake_newline +
              "Example: --demo 192.168.1.100 --demo 10.1.13.0/24" +
              fake_newline +
              "See" + fake_newline +
              "https://wiki.canonical.com/Launchpad/EC2Test/ForDemos" ))
    parser.add_option(
        '--open-browser', dest='open_browser', default=False,
        action='store_true',
        help=('Open the results page in your default browser'))
    parser.add_option(
        '-c', '--include-download-cache-changes',
        dest='include_download_cache_changes', action='store_true',
        help=('Include any changes in the download cache (added or unknown) '
              'in the download cache of the test run.  Note that, if you have '
              'any changes in your download cache, trying to submit to pqm '
              'will always raise an error.  Also note that, if you have any '
              'changes in your download cache, you must explicitly choose to '
              'include or ignore the changes.'))
    parser.add_option(
        '-g', '--ignore-download-cache-changes',
        dest='include_download_cache_changes', action='store_false',
        help=('Ignore any changes in the download cache (added or unknown) '
              'in the download cache of the test run.  Note that, if you have '
              'any changes in your download cache, trying to submit to pqm '
              'will always raise an error.  Also note that, if you have any '
              'changes in your download cache, you must explicitly choose to '
              'include or ignore the changes.'))
    parser.add_option(
        '--update-bundle', dest='bundle', action='store',
        help=('Start the image, update the system packages, sourcecode and '
              'Launchpad branch then bundle, upload and register a new AMI '
              'with the given name.'))
    options, args = parser.parse_args()
    if options.debug:
        import pdb; pdb.set_trace()
    if options.demo_networks:
        # We need the postmortem console to open the ec2 instance's
        # network access, and to keep the ec2 instance from being shutdown.
        options.postmortem = True
    if len(args) == 1:
        if options.trunk:
            parser.error(
                'Cannot supply both a branch and the --trunk argument.')
        branch = args[0]
    elif len(args) > 1:
        parser.error('Too many arguments.')
    elif options.trunk:
        branch = None
    else:
        branch = '.'
    if ((options.postmortem or options.file or options.demo_networks)
        and options.headless):
        parser.error(
            'Headless mode currently does not support postmortem, file '
            'or demo options.')
    if options.no_email:
        if options.email:
            parser.error(
                'May not supply both --no-email and an --email address')
        email = False
    else:
        email = options.email
        if email is None:
            email = True
    if options.instance_type not in AVAILABLE_INSTANCE_TYPES:
        parser.error('Unknown instance type.')
    if options.branches is None:
        branches = ()
    else:
        branches = [data.split('=', 1) for data in options.branches]

    agent = paramiko.Agent()
    keys = agent.get_keys()
    if len(keys) == 0:
        error_and_quit(
            'You must have an ssh agent running with keys installed that '
            'will allow the script to rsync to devpad and get your '
            'branch.\n')
    user_key = agent.get_keys()[0]

    if options.demo_networks is None:
        demo_networks = ()
    else:
        demo_networks = options.demo_networks

    instance = make_instance(
        instance_type=options.instance_type, machine_id=options.machine_id,
        demo_networks=demo_networks)

    if not options.bundle:
        runner = EC2TestRunner(
            branch, email=email, file=options.file,
            test_options=options.test_options, headless=options.headless,
            branches=branches,
            pqm_message=options.pqm_message,
            pqm_public_location=options.pqm_public_location,
            pqm_submit_location=options.pqm_submit_location,
            open_browser=options.open_browser, pqm_email=options.pqm_email,
            include_download_cache_changes=options.include_download_cache_changes,
            instance=instance, vals=instance._vals,
            )
        def run_tests():
            runner.configure_system()
            runner.prepare_tests()
            if demo_networks:
                runner.start_demo_webserver()
            else:
                runner.run_tests()
        run = run_tests
    else:
        instance.check_bundling_prerequisites()
        def make_new_image():
            user_connection = instance.connect_as_user()
            user_connection.perform('bzr launchpad-login %(launchpad-login)s')
            user_connection.run_with_ssh_agent(
                "rsync -avp --partial --delete "
                "--filter='P *.o' --filter='P *.pyc' --filter='P *.so' "
                "devpad.canonical.com:/code/rocketfuel-built/launchpad/sourcecode/* "
                "/var/launchpad/sourcecode/")
            user_connection.run_with_ssh_agent(
                'bzr pull -d /var/launchpad/test ' + TRUNK_BRANCH)
            user_connection.close()
            root_connection = instance.connect_as_root()
            root_connection.perform(
                'deluser --remove-home %(USER)s', ignore_failure=True)
            root_connection.close()
            instance.bundle(options.bundle)
        run = make_new_image

    instance.start()
    instance.set_up_user(user_key)

    run_with_instance(
        instance, run, options.demo_networks, options.postmortem)
