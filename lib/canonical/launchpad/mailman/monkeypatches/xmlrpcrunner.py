# Copyright 2007 Canonical Ltd.  All rights reserved.

"""XMLRPC runner for querying Launchpad."""

__all__ = [
    'XMLRPCRunner',
    ]

import os
import sys
import errno
import shutil
import socket
import tarfile
import traceback
import xmlrpclib

from cStringIO import StringIO

from Mailman import Utils
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog
from Mailman.MailList import MailList
from Mailman.Queue.Runner import Runner

COMMASPACE = ', '


# Mapping from modifiable attributes as they are named by the xmlrpc
# interface, to the attribute names on the MailList instances.
attrmap = {
    'welcome_message'   : 'welcome_msg',
    }


def log_exception():
    """Write the current exception stacktrace into the Mailman log file.

    This is really just a convenience function for a refactored chunk of
    common code.
    """
    out_file = StringIO()
    traceback.print_exc(file=out_file)
    syslog('xmlrpc', out_file.getvalue())


class XMLRPCRunner(Runner):
    """A Mailman 'queue runner' for talking to the Launchpad XMLRPC service."""

    def __init__(self, slice=None, numslices=None):
        """Create a faux runner which checks into Launchpad occasionally.

        Every XMLRPC_SLEEPTIME number of seconds, this runner wakes up and
        connects to a Launchpad XMLRPC service to see if there's anything for
        it to do.  slice and numslices are ignored, but required by the
        Mailman queue runner framework.
        """
        self.SLEEPTIME = mm_cfg.XMLRPC_SLEEPTIME
        # Instead of calling the superclass's __init__() method, just
        # initialize the two attributes that are actually used.  The reason
        # for this is that the XMLRPCRunner doesn't have a queue so it
        # shouldn't be trying to create a Switchboard instance.  Still, it
        # needs a dummy _kids and _stop attributes for the rest of the runner
        # to work.  We're using runners in a more general sense than Mailman 2
        # is designed for.
        self._kids = {}
        self._stop = False
        self._proxy = xmlrpclib.ServerProxy(mm_cfg.XMLRPC_URL)

    def _oneloop(self):
        """Check to see if there's anything for Mailman to do.

        Mailman makes an XMLRPC connection to Launchpad to see if there are
        any mailing lists to create, modify or deactivate.  It also requests
        updates to list subscriptions.  This method is called periodically by
        the base class's main loop.

        This method always returns 0 to indicate to the base class's main loop
        that it should sleep for a while after calling this method.
        """
        self._check_list_actions()
        self._get_subscriptions()
        syslog('xmlrpc', 'completed oneloop')
        # Snooze for a while.
        return 0

    def _check_list_actions(self):
        """See if there are any list actions to perform."""
        try:
            actions = self._proxy.getPendingActions()
        except (xmlrpclib.ProtocolError, socket.error), error:
            syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
            return
        except xmlrpclib.Fault, error:
            syslog('xmlrpc', 'Launchpad exception: %s', error)
            return
        if actions:
            syslog('xmlrpc', 'Received these actions: %s',
                   COMMASPACE.join(actions.keys()))
        else:
            return
        # There are three actions that can currently be taken.  A create
        # action creates a mailing list, possibly with some defaults, a modify
        # changes the settings on some existing mailing list, and a deactivate
        # means that the list should be deactivated.  This latter doesn't have
        # a directly corresponding semantic at the Mailman layer -- if a
        # mailing list exists, it's activated.  We'll take it to mean that the
        # list should be deleted, but its archives should remain.
        statuses = {}
        if 'create' in actions:
            self._create_or_reactivate(actions['create'], statuses)
            del actions['create']
        if 'modify' in actions:
            self._modify(actions['modify'], statuses)
            del actions['modify']
        if 'deactivate' in actions:
            self._deactivate(actions['deactivate'], statuses)
            del actions['deactivate']
        # Any other keys should be ignored because they specify actions that
        # we know nothing about.  We'll log them to Mailman's log files
        # though.
        if actions:
            syslog('xmlrpc', 'Invalid xmlrpc action keys: %s',
                   COMMASPACE.join(actions.keys()))
        # Report the statuses to Launchpad.
        self._proxy.reportStatus(statuses)

    def _get_subscriptions(self):
        """Get the latest subscription information."""
        # First, calculate the names of the active mailing lists.
        active_lists = [list_name for list_name in Utils.list_names()
                        if list_name <> mm_cfg.MAILMAN_SITE_LIST]
        try:
            info = self._proxy.getMembershipInformation(active_lists)
        except (xmlrpclib.ProtocolError, socket.error), error:
            syslog('xmlrpc', 'Cannot talk to Launchpad: %s', error)
            return
        except xmlrpclib.Fault, error:
            syslog('xmlrpc', 'Launchpad exception: %s', error)
            return
        if info:
            syslog('xmlrpc', 'Received subscription info for these lists: %s',
                   COMMASPACE.join(info.keys()))
        for list_name in info:
            mlist = MailList(list_name, lock=True)
            try:
                # Create a mapping of subscriber address to subscriber real
                # name.  Note that currently the flags and status are unused.
                member_map = dict((address, realname)
                                  for address, realname, flags, status
                                  in info[list_name])
                # Start by calculating two sets: one is the set of new members
                # who need to be added to the mailing list, and the other is
                # the set of old members who need to be removed from the
                # mailing list.
                current_members = set(mlist.getMembers())
                future_members = set(member_map)
                adds = future_members - current_members
                deletes = current_members - future_members
                updates = current_members & future_members

                # Handle additions first.
                for address in adds:
                    mlist.addNewMember(address, realname=member_map[address])
                # Handle deletions next.
                for address in deletes:
                    mlist.removeMember(address)
                # The members who are sticking around may have updates to
                # their real names, so it's just as easy to set that for
                # everyone as it is to check to see if there's a change.
                for address in updates:
                    mlist.setMemberName(address, member_map[address])
                # We're done, so flush the changes for this mailing list.
                mlist.Save()
            finally:
                mlist.Unlock()

    def _create_or_reactivate(self, actions, statuses):
        """Process mailing list creation and reactivation actions.

        actions is a sequence of (team_name, initializer) tuples where the
        team_name is the name of the mailing list to create and initializer is
        a dictionary of initial custom values to set on the new mailing list.

        statuses is a dictionary mapping team names to one of the strings
        'success' or 'failure'.
        """
        for team_name, initializer in actions:
            # This is a set of attributes defining the defaults for lists
            # created under Launchpad's control.  We need to map attribute
            # names as Launchpad sees them to attribute names on the MailList
            # object.
            list_defaults = {}
            # Verify that the initializer variables are what we expect.
            for key in attrmap:
                if key in initializer:
                    list_defaults[attrmap[key]] = initializer[key]
                    del initializer[key]
            if initializer:
                # Reject this list creation request.
                statuses[team_name] = 'failure'
                syslog('xmlrpc', 'Unexpected create settings: %s',
                       COMMASPACE.join(initializer.keys()))
                continue
            # Either the mailing list was deactivated at one point, or it
            # never existed in the first place.  Look for a backup tarfile; if
            # it exists, this is a reactivation, otherwise it is the initial
            # creation.
            tgz_file_name = os.path.join(
                mm_cfg.VAR_PREFIX, 'backups', team_name + '.tgz')
            try:
                tgz_file = tarfile.open(tgz_file_name, 'r:gz')
            except IOError, error:
                if error.errno != errno.ENOENT:
                    raise
                # The archive tarfile does not exist, meaning this is the
                # initial creation request.
                action = 'created'
                status = self._create(team_name)
            else:
                # This is a reactivation request.  Unpack the archived tarball
                # into the lists directory.
                action = 'reactivated'
                status = self._reactivate(team_name, tgz_file)
                tgz_file.close()
                if status:
                    os.remove(tgz_file_name)
            # If the list was successfully created or reactivated, apply
            # defaults.  Otherwise, set the failure status and return.
            if not status:
                syslog('xmlrpc', 'An error occurred; the list was not %s: %s',
                       action, team_name)
                statuses[team_name] = 'failure'
                return
            # Apply list defaults.
            mlist = MailList(team_name)
            try:
                for key, value in list_defaults.items():
                    setattr(mlist, key, value)
                # Do MTA specific creation steps.
                if mm_cfg.MTA:
                    modname = 'Mailman.MTA.' + mm_cfg.MTA
                    __import__(modname)
                    sys.modules[modname].create(mlist, quiet=True)
                statuses[team_name] = 'success'
                syslog('xmlrpc', 'Successfully %s list: %s', action, team_name)
                mlist.Save()
            finally:
                mlist.Unlock()

    def _reactivate(self, team_name, tgz_file):
        """Reactivate an archived mailing list from backup file."""
        lists_dir = os.path.join(mm_cfg.VAR_PREFIX, 'lists')
        # Temporarily change to the top level `lists` directory, since all the
        # tar files have paths relative to that.
        old_cwd = os.getcwd()
        try:
            os.chdir(lists_dir)
            extractall(tgz_file)
        finally:
            os.chdir(old_cwd)
        syslog('xmlrpc', '%s: %s', lists_dir, os.listdir(lists_dir))
        return True

    def _create(self, team_name):
        """Create a new mailing list."""
        # Create the mailing list and set the defaults.
        mlist = MailList()
        try:
            # Use a fake list admin password; Mailman will never be
            # administered from its web u/i.  Nor will the mailing list
            # require an owner that's different from the site owner.  Also by
            # default, only English is supported.
            try:
                mlist.Create(team_name,
                             mm_cfg.SITE_LIST_OWNER,
                             ' no password ')
                mlist.Save()
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            except:
                syslog('xmlrpc',
                       'List creation error for team: %s', team_name)
                log_exception()
                return False
            else:
                return True
        finally:
            mlist.Unlock()

    def _modify(self, actions, statuses):
        """Process mailing list modification actions.

        actions is a sequence of (team_name, modifications) tuples where the
        team_name is the name of the mailing list to create and modifications
        is a dictionary of values to set on the mailing list.

        statuses is a dictionary mapping team names to one of the strings
        'success' or 'failure'.
        """
        for team_name, modifications in actions:
            # First, validate the modification keywords.
            list_settings = {}
            for key in attrmap:
                if key in modifications:
                    list_settings[attrmap[key]] = modifications[key]
                    del modifications[key]
            if modifications:
                statuses[team_name] = 'failure'
                syslog('xmlrpc', 'Unexpected modify settings: %s',
                       COMMASPACE.join(modifications.keys()))
                continue
            try:
                try:
                    mlist = MailList(team_name)
                    for key, value in list_settings.items():
                        setattr(mlist, key, value)
                    mlist.Save()
                finally:
                    mlist.Unlock()
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            except:
                syslog('xmlrpc',
                       'List modification error for team: %s', team_name)
                log_exception()
                statuses[team_name] = 'failure'
            else:
                syslog('xmlrpc', 'Successfully modified list: %s',
                       team_name)
                statuses[team_name] = 'success'

    def _deactivate(self, actions, statuses):
        """Process mailing list deactivation actions.

        actions is a sequence of team names for the mailing lists to
        deactivate.

        statuses is a dictionary mapping team names to one of the strings
        'success' or 'failure'.
        """
        for team_name in actions:
            try:
                mlist = MailList(team_name, lock=False)
                if mm_cfg.MTA:
                    modname = 'Mailman.MTA.' + mm_cfg.MTA
                    __import__(modname)
                    sys.modules[modname].remove(mlist, quiet=True)
                # The archives are always persistent, so all we need to do to
                # deactivate a list is to delete the 'lists/team_name'
                # directory.  However, in order to support easy reactivation,
                # and to provide a backup in case of error, we create a gzip'd
                # tarball of the list directory.
                lists_dir = os.path.join(mm_cfg.VAR_PREFIX, 'lists')
                # To make reactivation easier, we temporarily cd to the
                # $var/lists directory and make the tarball from there.
                old_cwd = os.getcwd()
                # XXX BarryWarsaw 02-Aug-2007 Should we watch out for
                # collisions on the tar file name?  This can only happen if
                # the team is resurrected but the old archived tarball backup
                # wasn't removed.
                tgz_file_name = os.path.join(
                    mm_cfg.VAR_PREFIX, 'backups', team_name + '.tgz')
                tgz_file = tarfile.open(tgz_file_name, 'w:gz')
                try:
                    os.chdir(lists_dir)
                    # .add() works recursively by default.
                    tgz_file.add(team_name)
                    # Now delete the list's directory.
                    shutil.rmtree(team_name)
                finally:
                    tgz_file.close()
                    os.chdir(old_cwd)
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            except:
                syslog('xmlrpc', 'List deletion error for team: %s', team_name)
                log_exception()
                statuses[team_name] = 'failure'
            else:
                syslog('xmlrpc', 'Successfully deleted list: %s', team_name)
                statuses[team_name] = 'success'


def extractall(tgz_file):
    """Extract all members of `tgz_file` to the current working directory."""
    path = '.'
    # XXX BarryWarsaw 13-Nov-2007 TBD: This is nearly a straight ripoff of
    # Python 2.5's TarFile.extractall() method, though simplified for our
    # particular purpose.  When we upgrade Launchpad to Python 2.5, this
    # function can be removed.
    directories = []
    for tarinfo in tgz_file:
        if tarinfo.isdir():
            # Extract directory with a safe mode, so that
            # all files below can be extracted as well.
            try:
                os.makedirs(os.path.join(path, tarinfo.name), 0777)
            except EnvironmentError:
                pass
            directories.append(tarinfo)
        else:
            tgz_file.extract(tarinfo, path)
    # Reverse sort directories.
    directories.sort(lambda a, b: cmp(a.name, b.name))
    directories.reverse()
    # Set correct owner, mtime and filemode on directories.
    for tarinfo in directories:
        path = os.path.join(path, tarinfo.name)
        try:
            tgz_file.chown(tarinfo, path)
            tgz_file.utime(tarinfo, path)
            tgz_file.chmod(tarinfo, path)
        except tarfile.ExtractError, e:
            syslog('xmlrpc', 'tarfile: %s' % e)
