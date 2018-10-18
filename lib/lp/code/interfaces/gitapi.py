# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for internal Git APIs."""

__metaclass__ = type
__all__ = [
    'IGitAPI',
    'IGitApplication',
    ]

from zope.interface import Interface

from lp.services.webapp.interfaces import ILaunchpadApplication


class IGitApplication(ILaunchpadApplication):
    """Git application root."""


class IGitAPI(Interface):
    """The Git XML-RPC interface to Launchpad.

    Published at "git" on the private XML-RPC server.

    The Git pack frontend uses this to translate user-visible paths to
    internal ones, and to notify Launchpad of ref changes.
    """

    def translatePath(path, permission, requester_id, can_authenticate):
        """Translate 'path' so that the Git pack frontend can access it.

        If the repository does not exist and write permission was requested,
        register a new repository if possible.

        :param path: The path being translated.  This should be a string
            representing an absolute path to a Git repository.
        :param permission: "read" or "write".
        :param requester_id: The database ID of the person requesting the
            path translation, or None for an anonymous request.
        :param can_authenticate: True if the frontend can request
            authentication, otherwise False.

        :returns: A `PathTranslationError` fault if 'path' cannot be
            translated; a `PermissionDenied` fault if the requester cannot
            see or create the repository; otherwise, a dict containing at
            least the following keys::
                "path", whose value is the repository's storage path;
                "writable", whose value is True if the requester can push to
                this repository, otherwise False.
        """

    def notify(translated_path):
        """Notify of a change to the repository at 'translated_path'.

        :param translated_path: The translated path to the repository.  (We
            use translated paths here in order to avoid problems with
            repository names etc. being changed during a push.)

        :returns: A `NotFound` fault if no repository can be found for
            'translated_path'; otherwise None.
        """

    def authenticateWithPassword(username, password):
        """Authenticate a user by username and password.

        :returns: An `Unauthorized` fault, as password authentication is
            not yet supported.
        """

    def listRefRules(self, repository, user):
        """Return the list of ref rules for `user` in `repository`

        :returns: A list of rules for the user in the specified repository
        """

    def checkRefPermissions(self, repository, ref_paths, user):
        """Return a list of ref rules for a `user` in a `repository` that
        match the input refs.

        :returns: A list of rules for the user in the specified repository
        """
