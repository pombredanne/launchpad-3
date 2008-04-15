# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

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
import itertools
import traceback
import xmlrpclib

from cStringIO import StringIO

# pylint: disable-msg=F0401
from Mailman import Errors
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
    """A Mailman 'queue runner' for talking to the Launchpad XMLRPC service.
    """

    # We increment this every time we see an actual change in the data coming
    # from Launchpad.  We write this to the xmlrpc log file for better
    # synchronization with the integration tests.  It's not used for any other
    # purpose.
    serial_number = itertools.count()

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
        # Ensure that the serial log file exists.
        syslog('serial', 'SERIAL: %s', self.serial_number.next())

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
        self._check_held_messages()
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
                   COMMASPACE.join(actions))
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
        if 'unsynchronized' in actions:
            self._resynchronize(actions['unsynchronized'], statuses)
            del actions['unsynchronized']
        # Any other keys should be ignored because they specify actions that
        # we know nothing about.  We'll log them to Mailman's log files
        # though.
        if actions:
            syslog('xmlrpc', 'Invalid xmlrpc action keys: %s',
                   COMMASPACE.join(actions))
        # Report the statuses to Launchpad.  Do this individually so as to
        # reduce the possibility that a bug in Launchpad causes the reporting
        # all subsequent mailing lists statuses to fail.  The reporting of
        # status triggers synchronous operations in Launchpad, such as
        # notifying team admins that their mailing list is ready, and those
        # operations could fail for spurious reasons.  That shouldn't affect
        # the status reporting for any other list.  This is a little more
        # costly, but it's not that bad.
        for team_name, status in statuses.items():
            this_status = {team_name: status}
            try:
                self._proxy.reportStatus(this_status)
            except (xmlrpclib.ProtocolError, socket.error), error:
                syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
            except xmlrpclib.Fault, error:
                syslog('xmlrpc', 'Launchpad exception: %s', error)
        # Changes were made, so bump the serial number.
        syslog('serial', 'SERIAL: %s', self.serial_number.next())

    def _get_subscriptions(self):
        """Get the latest subscription information."""
        # First, calculate the names of the active mailing lists.
        # pylint: disable-msg=W0331
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
                   COMMASPACE.join(info))
        # Maintain a flag to determine whether there were any changes to
        # Mailman data structures in this XMLRPC request.  If so, we'll need
        # to bump the serial number to ensure that the integration tests can
        # stay properly synchronized.
        changes_detected = False
        for list_name in info:
            mlist = MailList(list_name)
            try:
                # Create a mapping of email address to the member's real name,
                # flags, and status.  Note that flags is currently unused.
                member_map = dict((address, (realname, flags, status))
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
                # If there are any additions or deletions to the subscription
                # information, then obviously a change was detected.  Updates
                # need to be handled differently; they are the more common
                # case.
                if adds or deletes:
                    changes_detected = True
                # Handle additions first.
                for address in adds:
                    realname, flags, status = member_map[address]
                    mlist.addNewMember(address, realname=realname)
                    mlist.setDeliveryStatus(address, status)
                # Handle deletions next.
                for address in deletes:
                    mlist.removeMember(address)
                # The members who are sticking around may have updates to
                # their real names or statuses.  Check to see if there are
                # changes because we need to do that anyway to make sure the
                # serial number gets bumped only when necessary.
                for address in updates:
                    # flags are ignored for now.
                    realname, flags, status = member_map[address]
                    if realname <> mlist.getMemberName(address):
                        mlist.setMemberName(address, realname)
                        changes_detected = True
                    if status <> mlist.getDeliveryStatus(address):
                        mlist.setDeliveryStatus(address, status)
                        changes_detected = True
                # We're done, so flush the changes for this mailing list.
                mlist.Save()
            finally:
                mlist.Unlock()
        # If changes were detected, bump the serial number.
        if changes_detected:
            syslog('serial', 'SERIAL: %s', self.serial_number.next())

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
                       COMMASPACE.join(initializer))
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
            self._apply_list_defaults(team_name, list_defaults)
            statuses[team_name] = 'success'
            syslog('xmlrpc', 'Successfully %s list: %s', action, team_name)

    def _apply_list_defaults(self, team_name, list_defaults):
        """Apply mailing list defaults and tie the new list into the MTA."""
        mlist = MailList(team_name)
        try:
            for key, value in list_defaults.items():
                setattr(mlist, key, value)
            # Do MTA specific creation steps.
            if mm_cfg.MTA:
                modname = 'Mailman.MTA.' + mm_cfg.MTA
                __import__(modname)
                sys.modules[modname].create(mlist, quiet=True)
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
                # Additional hard coded list defaults.
                # - Personalize regular delivery so that we can VERP these.
                # - Turn off RFC 2369 headers; we'll do them differently
                # - enable $-string substitutions in headers/footers
                mlist.personalize = 1
                mlist.include_rfc2369_headers = False
                mlist.use_dollar_strings = True
                mlist.Save()
                # Now create the archive directory for MHonArc.
                path = os.path.join(mm_cfg.VAR_PREFIX, 'mhonarc', team_name)
                os.makedirs(path)
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            # pylint: disable-msg=W0702
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
                       COMMASPACE.join(modifications))
                continue
            try:
                mlist = MailList(team_name)
                try:
                    for key, value in list_settings.items():
                        setattr(mlist, key, value)
                    mlist.Save()
                finally:
                    mlist.Unlock()
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            # pylint: disable-msg=W0702
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
            # pylint: disable-msg=W0702
            except:
                syslog('xmlrpc',
                       'List deletion error for team: %s', team_name)
                log_exception()
                statuses[team_name] = 'failure'
            else:
                syslog('xmlrpc', 'Successfully deleted list: %s', team_name)
                statuses[team_name] = 'success'

    def _check_held_messages(self):
        """See if any held messages have been accepted or rejected."""
        try:
            dispositions = self._proxy.getMessageDispositions()
        except (xmlrpclib.ProtocolError, socket.error), error:
            syslog('xmlrpc', 'Cannot talk to Launchpad:\n%s', error)
            return
        except xmlrpclib.Fault, error:
            syslog('xmlrpc', 'Launchpad exception: %s', error)
            return
        if dispositions:
            syslog('xmlrpc',
                   'Received dispositions for these message-ids: %s',
                   COMMASPACE.join(dispositions))
        else:
            return
        changes_detected = False
        # For each message that has been acted upon in Launchpad, handle the
        # message in here in Mailman.  We need to resort the dispositions so
        # that we can handle all of them for a particular mailing list at the
        # same time.
        by_list = {}
        for message_id, (team_name, action) in dispositions.items():
            accepts, declines, discards = by_list.setdefault(
                team_name, ([], [], []))
            if action == 'accept':
                accepts.append(message_id)
            elif action == 'decline':
                declines.append(message_id)
            elif action == 'discard':
                discards.append(message_id)
            else:
                syslog('xmlrpc',
                       'Skipping invalid disposition "%s" for message-id: %s',
                       action, message_id)
        # Now cycle through the dispositions for every mailing list.
        for team_name in by_list:
            try:
                mlist = MailList(team_name)
            except Errors.MMUnknownListError:
                syslog('xmlrpc', 'Skipping dispositions for unknown list: %s',
                       team_name)
                continue
            try:
                accepts, declines, discards = by_list[team_name]
                for message_id in accepts:
                    request_id = mlist.held_message_ids.pop(message_id, None)
                    if request_id is None:
                        syslog('xmlrpc', 'Missing accepted message-id: %s',
                               message_id)
                    else:
                        mlist.HandleRequest(request_id, mm_cfg.APPROVE)
                        syslog('vette', 'Approved: %s', message_id)
                        changes_detected = True
                for message_id in declines:
                    request_id = mlist.held_message_ids.pop(message_id, None)
                    if request_id is None:
                        syslog('xmlrpc', 'Missing declined message-id: %s',
                               message_id)
                    else:
                        mlist.HandleRequest(request_id, mm_cfg.REJECT)
                        syslog('vette', 'Rejected: %s', message_id)
                        changes_detected = True
                for message_id in discards:
                    request_id = mlist.held_message_ids.pop(message_id, None)
                    if request_id is None:
                        syslog('xmlrpc', 'Missing declined message-id: %s',
                               message_id)
                    else:
                        mlist.HandleRequest(request_id, mm_cfg.DISCARD)
                        syslog('vette', 'Discarded: %s', message_id)
                        changes_detected = True
                mlist.Save()
            finally:
                mlist.Unlock()
        # If changes were detected, bump the serial number.
        if changes_detected:
            syslog('serial', 'SERIAL: %s', self.serial_number.next())

    def _resynchronize(self, actions, statuses):
        """Process resynchronization actions.

        actions is a sequence of 2-tuples specifying what needs to be
        resynchronized.  The tuple is of the form (listname, current-status).

        statuses is a dictionary mapping team names to one of the strings
        'success' or 'failure'.
        """
        syslog('xmlrpc', 'resynchronizing: %s',
               COMMASPACE.join(sorted(name for (name, status) in actions)))
        for name, status in actions:
            # There's no way to really know whether the original action
            # succeeded or not, however, it's unlikely that an action would
            # fail leaving the mailing list in a usable state.  Therefore, if
            # the list is loadable and lockable, we'll say it succeeded.
            # pylint: disable-msg=W0702
            try:
                mlist = MailList(name)
            except Errors.MMUnknownListError:
                # The list doesn't exist on the Mailman side, so if its status
                # is CONSTRUCTING, we can create it now.
                if status == 'constructing':
                    if self._create(name):
                        statuses[name] = 'success'
                    else:
                        statuses[name] = 'failure'
                else:
                    # Any other condition leading to an unknown list is a
                    # failure state.
                    statuses[name] = 'failure'
            except:
                # Any other exception is also a failure.
                statuses[name] = 'failure'
                syslog('xmlrpc', 'Mailing list does not load: %s', name)
            else:
                # The list loaded just fine, so it successfully
                # resynchronized.  Be sure to unlock it!
                mlist.Unlock()
                statuses[name] = 'success'


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
