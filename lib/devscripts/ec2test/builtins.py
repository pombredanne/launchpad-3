from bzrlib.commands import Command
from bzrlib.option import ListOption, Option

from devscripts.ec2test.commandline import (
    DEFAULT_INSTANCE_TYPE, AVAILABLE_INSTANCE_TYPES)
from devscripts.ec2test.testrunner import TRUNK_BRANCH

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
    'instance', short_name='i', type=str, argname='instance_type',
    help=('The AWS instance type on which to base this run. '
          'Available options are %r. Defaults to `%s`.' %
          (AVAILABLE_INSTANCE_TYPES, DEFAULT_INSTANCE_TYPE)))

debug_option = Option(
    'debug', short_name='d',
    help=('Drop to pdb trace as soon as possible.'))

include_download_cache_changes_option = Option(
    'include-download-cache-changes', short_name='c',
    help=('Include any changes in the download cache (added or unknown) '
          'in the download cache of the test run.  Note that, if you have '
          'any changes in your download cache, trying to submit to pqm '
          'will always raise an error.  Also note that, if you have any '
          'changes in your download cache, you must explicitly choose to '
          'include or ignore the changes.'))

ignore_download_cache_changes_option = Option(
    'ignore-download-cache-changes', short_name='g',
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


class cmd_test(EC2Command):
    """Run the tests in ec2."""

    takes_options = [
        branch_option,
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
        ignore_download_cache_changes_option,
        include_download_cache_changes_option,
        ]

    takes_args = ['test_branch?']

    def run(self, branch=None, file=None, noemail=False, test_options='-vv', **kw):
        print locals()

class cmd_demo(EC2Command):
    def run(self):
        print 'foo'

class cmd_update_image(EC2Command):
    def run(self):
        print 'foo'
