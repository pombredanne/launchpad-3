# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import socket
import threading
import poplib

from zope.interface import implements

from canonical.launchpad.interfaces import IMailBox, MailBoxError
from canonical.launchpad.mail import stub

class TestMailBox:
    """Mail box used for testing.

    It operates on stub.test_emails.
    """
    implements(IMailBox)

    def __init__(self):
        self._lock = threading.Lock()

    def open(self):
        """See IMailBox."""
        if not self._lock.acquire(False):
            raise MailBoxError("The mail box is already open.")

    def items(self):
        """See IMailBox."""
        id = 0
        for item in stub.test_emails:
            if item is not None:
                from_addr, to_addr, raw_mail = item
                yield id, raw_mail
            id += 1

    def delete(self, id):
        """See IMailBox."""
        if id not in [valid_id for valid_id, mail in self.items()]:
            raise MailBoxError("No such id: %s" % id)

        # Mark it as deleted. We can't really delete it yet, since the
        # ids need to be preserved.
        stub.test_emails[id] = None

    def close(self):
        """See IMailBox."""
        # Clean up test_emails
        stub.test_emails = [item for item in stub.test_emails
                            if stub.test_emails is not None]
        self._lock.release()


class POP3MailBox:
    """Mail box which talks to a POP3 server."""
    implements(IMailBox)

    def __init__(self, host, user, password, ssl=False):
        self._host = host
        self._user = user
        self._password = password
        self._ssl = ssl

    def open(self):
        """See IMailBox."""
        try:
            if self._ssl:
                popbox = poplib.POP3_SSL(self._host)
            else:
                popbox = poplib.POP3(self._host)
        except socket.error, e:
            raise MailBoxError(str(e))
        try:
            popbox.user(self._user)
            popbox.pass_(self._password)
        except poplib.error_proto, e:
            popbox.quit()
            raise MailBoxError(str(e))
        self._popbox = popbox

    def items(self):
        """See IMailBox."""
        popbox = self._popbox
        try:
            count, size = popbox.stat()
        except poplib.error_proto, e:
            # This means we lost the connection.
            raise MailBoxError(str(e))

        for msg_id in range(1, count+1):
            response, msg_lines, size = popbox.retr(msg_id)
            yield (msg_id, '\n'.join(msg_lines))

    def delete(self, id):
        """See IMailBox."""
        try:
            self._popbox.dele(id)
        except poplib.error_proto, e:
            raise MailBoxError(str(e))

    def close(self):
        """See IMailBox."""
        self._popbox.quit()
