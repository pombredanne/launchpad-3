# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for datetimeish things."""

from zope.interface import Interface, Attribute

class IAging(Interface):
    """Something that gets older as time passes."""

    def currentApproximateAge():
        """Return a human-readable string of how old this thing is.

        Values returned are things like '2 minutes', '3 hours', '1 month', etc.
        """

class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")
