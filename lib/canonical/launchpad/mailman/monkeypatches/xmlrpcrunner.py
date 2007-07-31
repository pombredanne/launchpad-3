# Copyright 2007 Canonical Ltd.  All rights reserved.

"""XMLRPC runner for querying Launchpad."""

__all__ = [
    'XMLRPCRunner',
    ]

import sys
import shutil
import tarfile
import xmlrpclib

from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog
from Mailman.MailList import MailList
from Mailman.Queue.Runner import Runner

from canonical.config import config


COMMASPACE = ', '


class XMLRPCRunner(Runner):
    def __init__(self, slice=None, numslices=1):
        self._proxy = xmlrpclib.ServerProxy(config.mailman.xmlrpc_url)
        self.SLEEPTIME = config.mailman.xmlrpc_runner_sleep

    def _oneloop(self):
        # See if Launchpad has anything for us to do.
        actions = self._proxy.getPendingAction()
        if not actions:
            # Always return 0 so self._snooze() will sleep for a while.
            return 0
        # There are three actions that can currently be taken.  A create
        # action creates a mailing list, possibly with some defaults, a modify
        # changes the settings on some existing mailing list, and a deactivate
        # means that the list should be deactivated.  This latter doesn't have
        # a directly corresponding semantic at the Mailman layer -- if a
        # mailing list exists, it's activated.  We'll take it to mean that the
        # list should be deleted, but its archives should remain.
        statuses = {}
        if 'create' in actions:
            self._create(actions['create'], statuses)
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
            syslog('error', 'Invalid xmlrpc action keys: %s',
                   COMMASPACE.join(actions.keys()))
        # Report the statuses to Launchpad.
        self._proxy.reportStatus(statuses)
        # Snooze for a while.
        return 0

    def _create(self, actions, statuses):
        for team_name, initializer in actions:
            # This is a set of attributes defining the defaults for lists
            # created under Launchpad's control.  XXX Figure out other
            # defaults and where to keep them -- in Launchpad's configuration
            # files?  Probably not.
            list_defaults = {}
            # Verify that the initializer variables are what we expect.
            for key in ['welcome_message']:
                if key in initializer:
                    list_defaults[key] = initializer[key]
                    del initializer[key]
            if initializer:
                # Reject this list creation request.
                statuses[team_name] = 'failure'
                continue
            # Create the mailing list and set the defaults.
            mlist = MailList.MailList()
            try:
                # Use a fake list admin password; Mailman will never be
                # administered from its web u/i.  Nor will the mailing list
                # require an owner that's different from the site owner.  Also
                # by default, only English is supported.
                try:
                    mlist.Create(team_name,
                                 config.mailman.site_list_owner,
                                 ' no password ',
                                 ['en'],
                                 config.mailman.smtp_host)
                # We have to use a bare except here because of the legacy
                # string exceptions that Mailman can raise.
                except:
                    syslog('error', 'List creation error for team "%s": %s',
                           team_name, sys.exc_info())
                    statuses[team_name] = 'failure'
                else:
                    # Apply defaults.
                    for key, value in list_defaults.items():
                        setattr(mlist, key, value)
                    status[team_name] = 'success'
                    mlist.Save()
            finally:
                mlist.Unlock()

    def _modify(self, actions, statuses):
        for team_name, modifications in actions:
            # First, validate the modification keywords.
            list_settings = {}
            for key in ['welcome_message']:
                if key in modification:
                    list_settings[key] = modifications[key]
                    del modifications[key]
            if modifications:
                statuses[team_name] = 'failure'
                continue
            try:
                try:
                    mlist = MailList(team_name)
                    for key, value in list_settings:
                        setattr(mlist, key, value)
                    if mm_cfg.MTA:
                        modname = 'Mailman.MTA.' + mm_cfg.MTA
                        __import__(modname)
                        sys.modules[modname].create(mlist, quiet=True)
                    mlist.Save()
                finally:
                    mlist.Unlock()
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            except:
                syslog('error', 'List modification error for team "%s": %s',
                       team_name, sys.exc_info())
                statuses[team_name] = 'failure'
            else:
                statuses[team_name] = 'success'

    def _deactivate(self, actions, statuses):
        for team_name in actions:
            try:
                mlist = MailList.MailList(team_name, lock=False)
                if mm_cfg.MTA:
                    modname = 'Mailman.MTA.' + mm_cfg.MTA
                    __import__(modname)
                    sys.modules[modname].remove(mlist, quiet=True)
                # We're keeping the archives, so all we need to do is delete
                # the 'lists/team_name' directory.  However, to be extra
                # specially paranoid, create a gzip'd tarball of the directory
                # for safe keeping, just in case we screwed up.
                list_dir = os.path.join(mm_cfg.VAR_PREFIX, 'lists', team_name)
                tgz_file_name = os.path.join(
                    mm_cfg.VAR_PREFIX, 'backups', team_name + '.tgz')
                tgz_file = tarfile.open(tgz_file_name, 'w:gz')
                try:
                    # .add() works recursively by default.
                    tgz_file.add(list_dir)
                finally:
                    tgz_file.close()
                # Now delete the list's directory.
                shutil.rmtree(list_dir)
            # We have to use a bare except here because of the legacy string
            # exceptions that Mailman can raise.
            except:
                syslog('error', 'List deletion error for team "%s": %s',
                       team_name, sys.exc_info())
                statuses[team_name] = 'failure'
            else:
                statuses[team_name] = 'success'
