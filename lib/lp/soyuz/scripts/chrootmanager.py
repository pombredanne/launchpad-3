# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Chroot management utilities."""

__metaclass__ = type

__all__ = [
    'ChrootManager',
    'ChrootManagerError',
    'ManageChrootScript',
    ]

import os

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.services.helpers import filenameToContentType
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.librarian.interfaces.client import (
    ILibrarianClient,
    UploadFailed,
    )
from lp.services.librarian.utils import copy_and_close
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )


class ChrootManagerError(Exception):
    """Any error generated during the ChrootManager procedures."""


class ChrootManager:
    """Chroot actions wrapper.

    The 'distroarchseries' argument is mandatory and 'filepath' is
    optional.

    'filepath' is required by some allowed actions as source or destination,

    ChrootManagerError will be raised if anything wrong occurred in this
    class, things like missing parameter or infrastructure pieces not in
    place.
    """

    allowed_actions = ['add', 'update', 'remove', 'get']

    def __init__(self, distroarchseries, filepath=None):
        self.distroarchseries = distroarchseries
        self.filepath = filepath
        self._messages = []

    def _upload(self):
        """Upload the self.filepath contents to Librarian.

        Return the respective ILibraryFileAlias instance.
        Raises ChrootManagerError if it could not be found.
        """
        try:
            fd = open(self.filepath)
        except IOError:
            raise ChrootManagerError('Could not open: %s' % self.filepath)

        flen = os.stat(self.filepath).st_size
        filename = os.path.basename(self.filepath)
        ftype = filenameToContentType(filename)

        try:
            alias_id = getUtility(ILibrarianClient).addFile(
                filename, flen, fd, contentType=ftype)
        except UploadFailed as info:
            raise ChrootManagerError("Librarian upload failed: %s" % info)

        lfa = getUtility(ILibraryFileAliasSet)[alias_id]

        self._messages.append(
            "LibraryFileAlias: %d, %s bytes, %s"
            % (lfa.id, lfa.content.filesize, lfa.content.md5))

        return lfa

    def _getPocketChroot(self):
        """Retrive PocketChroot record.

        Return the respective IPocketChroot instance.
        Raises ChrootManagerError if it could not be found.
        """
        pocket_chroot = self.distroarchseries.getPocketChroot()
        if pocket_chroot is None:
            raise ChrootManagerError(
                'Could not find chroot for %s'
                % (self.distroarchseries.title))

        self._messages.append(
            "PocketChroot for '%s' (%d) retrieved."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

        return pocket_chroot

    def _update(self):
        """Base method for add and update action."""
        if self.filepath is None:
            raise ChrootManagerError('Missing local chroot file path.')
        alias = self._upload()
        return self.distroarchseries.addOrUpdateChroot(alias)

    def add(self):
        """Create a new PocketChroot record.

        Raises ChrootManagerError if self.filepath isn't set.
        Update of pre-existing PocketChroot record will be automatically
        handled.
        It's a bind to the self.update method.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s' (%d) added."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def update(self):
        """Update a PocketChroot record.

        Raises ChrootManagerError if filepath isn't set
        Creation of non-existing PocketChroot records will be automatically
        handled.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s' (%d) updated."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def remove(self):
        """Overwrite existing PocketChroot file to none.

        Raises ChrootManagerError if the chroot record isn't found.
        """
        pocket_chroot = self._getPocketChroot()
        self.distroarchseries.addOrUpdateChroot(None)
        self._messages.append(
            "PocketChroot for '%s' (%d) removed."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def get(self):
        """Download chroot file from Librarian and store."""
        pocket_chroot = self._getPocketChroot()

        if self.filepath is None:
            abs_filepath = os.path.abspath(pocket_chroot.chroot.filename)
            if os.path.exists(abs_filepath):
                raise ChrootManagerError(
                    'cannot overwrite %s' % abs_filepath)
            self._messages.append(
                "Writing to '%s'." % abs_filepath)
            local_file = open(pocket_chroot.chroot.filename, "w")
        else:
            abs_filepath = os.path.abspath(self.filepath)
            if os.path.exists(abs_filepath):
                raise ChrootManagerError(
                    'cannot overwrite %s' % abs_filepath)
            self._messages.append(
                "Writing to '%s'." % abs_filepath)
            local_file = open(abs_filepath, "w")

        if pocket_chroot.chroot is None:
            raise ChrootManagerError('Chroot was deleted.')

        pocket_chroot.chroot.open()
        copy_and_close(pocket_chroot.chroot, local_file)


class ManageChrootScript(SoyuzScript):
    """`SoyuzScript` that manages chroot files."""

    usage = "%prog -d <distribution> -s <suite> -a <architecture> -f file"
    description = "Manage the chroot files used by the builders."
    success_message = "Success."

    def add_my_options(self):
        """Add script options."""
        SoyuzScript.add_distro_options(self)
        SoyuzScript.add_transaction_options(self)
        self.parser.add_option(
            '-a', '--architecture', dest='architecture', default=None,
            help='Architecture tag')
        self.parser.add_option(
            '-f', '--filepath', dest='filepath', default=None,
            help='Chroot file path')

    def mainTask(self):
        """Set up a ChrootManager object and invoke it."""
        if len(self.args) != 1:
            raise SoyuzScriptError(
                "manage-chroot.py <add|update|remove|get>")

        [action] = self.args

        series = self.location.distroseries

        try:
            distroarchseries = series[self.options.architecture]
        except NotFoundError as info:
            raise SoyuzScriptError("Architecture not found: %s" % info)

        # We don't want to have to force the user to confirm transactions
        # for manage-chroot.py, so disable that feature of SoyuzScript.
        self.options.confirm_all = True

        self.logger.debug(
            "Initializing ChrootManager for '%s'" % (distroarchseries.title))
        chroot_manager = ChrootManager(
            distroarchseries, filepath=self.options.filepath)

        if action in chroot_manager.allowed_actions:
            chroot_action = getattr(chroot_manager, action)
        else:
            self.logger.error(
                "Allowed actions: %s" % chroot_manager.allowed_actions)
            raise SoyuzScriptError("Unknown action: %s" % action)

        try:
            chroot_action()
        except ChrootManagerError as info:
            raise SoyuzScriptError(info)
        else:
            # Collect extra debug messages from chroot_manager.
            for debug_message in chroot_manager._messages:
                self.logger.debug(debug_message)
