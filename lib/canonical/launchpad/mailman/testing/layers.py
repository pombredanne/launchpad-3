# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A marker layer for the Mailman integration tests."""

__metaclass__ = type
__all__ = [
    'MailmanLayer',
    ]


from canonical.testing.layers import AppServerLayer


class MailmanLayer(AppServerLayer):
    """A marker layer for the Mailman integration tests."""
