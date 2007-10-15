# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""External bug reference interfaces."""

__metaclass__ = type

__all__ = [
    'BugExternalReferenceType',
    'IBugExternalRef',
    'IBugExternalRefSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, TextLine

from canonical.launchpad.fields import Title
from canonical.launchpad.interfaces.validation import valid_webref
from canonical.launchpad import _

from canonical.lazr import DBEnumeratedType, DBItem


class BugExternalReferenceType(DBEnumeratedType):
    """Bug External Reference Type

    Malone allows external information references to be attached to
    a bug. This schema lists the known types of external references.
    """

    CVE = DBItem(1, """
        CVE Reference

        This external reference is a CVE number, which means it
        exists in the CVE database of security bugs.
        """)

    URL = DBItem(2, """
        URL

        This external reference is a URL. Typically that means it
        is a reference to a web page or other internet resource
        related to the bug.
        """)


class IBugExternalRef(Interface):
    """An external reference for a bug, not supported remote bug systems."""

    id = Int(
            title=_('ID'), required=True, readonly=True)
    bug = Int(
            title=_('Bug ID'), required=True, readonly=True)
    url = TextLine(
            title=_('URL'), required=True, readonly=False,
            description = _("""The url of the content that is related to
            this bug."""), constraint=valid_webref)
    title = Title(
            title=_('Title'), required=True, readonly=False,
            description=_("""A brief description of the content that is
            being linked to."""))
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,)
    owner = Int(
            title=_('Owner'), required=False, readonly=True,)


class IBugExternalRefSet(Interface):
    """A set for IBugExternalRef objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    title = Attribute('Title')

    def __getitem__(key):
        """Get a BugExternalRef."""

    def __iter__():
        """Iterate through BugExternalRefs for a given bug."""

    def search():
        """Search through all the IBugExternalRefs in the system."""

    def createBugExternalRef(bug, url, title, owner):
        """Create and link an external web link to an IBug.

        Returns the IBugExternalRef that's created.
        """
