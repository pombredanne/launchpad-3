# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Message queue utilities."""

__metaclass__ = type
__all__ = [
    "make_finish_ro_request_handler",
    ]


from zope.component import adapter

from canonical.launchpad.webapp.interfaces import IFinishReadOnlyRequestEvent


def make_finish_ro_request_handler(session):
    @adapter(IFinishReadOnlyRequestEvent)
    def session_flush_handler(event):
        session.flush()
    return session_flush_handler
