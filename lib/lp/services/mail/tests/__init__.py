# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for mail services."""

__metaclass__ = type
__all__ = ['ListHandler']


from contextlib import contextmanager

from lp.services.mail.handlers import mail_handlers


class ListHandler:
    """A mail handler that simply adds the message to a list."""
    def __init__(self):
        self.processed = []

    def process(self, signed_msg, to_addr, filealias=None, log=None):
        self.processed.append(signed_msg)
        return True


@contextmanager
def active_handler(domain, handler):
    """In the context, the specified handler is registered for the domain."""
    mail_handlers.add(domain, handler)
    try:
        yield handler
    finally:
        del mail_handlers._handlers[domain]
