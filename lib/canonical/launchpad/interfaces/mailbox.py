# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Mail box interfaces."""

__metaclass__ = type

__all__ = [
    'MailBoxError',
    'IMailBox',
    ]

from zope.interface import Interface


class MailBoxError(Exception):
    """Indicates that some went wrong while interacting with the mail box."""


class IMailBox(Interface):
    def open():
        """Opens the mail box.

        Raises MailBoxError if the mail box can't be opened.

        This method has to be called before any operations on the mail
        box is performed.
        """

    def items():
        """Returns all the ids and mails in the mail box.

        Returns an iterable of (id, mail) tuples.

        Raises MailBoxError if there's some error while returning the mails.
        """

    def delete(id):
        """Deletes the mail with the given id.

        Raises MailBoxError if the mail couldn't be deleted.
        """

    def close():
        """Closes the mailbox."""
