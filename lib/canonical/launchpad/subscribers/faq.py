# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Subscribers for `IFAQ`."""

__metaclass__ = type
__all__ = ['update_last_updated']


from canonical.database.constants import UTC_NOW


def update_last_updated(faq, event):
    """Update the last_updated_by and date_last_updated attributes."""
    faq.last_updated_by = event.user
    faq.date_last_updated = UTC_NOW
