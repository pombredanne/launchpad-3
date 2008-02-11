# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to package-diff system."""

__metaclass__ = type

__all__ = [
    'IPackageDiff',
    'IPackageDiffSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Object

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias


class IPackageDiff(IHasOwner):
    """Package diff request and storage.

    See doc/packagediff.txt for details about the attributes.
    """

    date_requested = Datetime(
        title=_(u'Date Requested'), required=True)

    requester = Choice(
        title=_('Requester'),
        required=True,
        vocabulary='ValidPerson',
        description=_("The person requesting the diff."))

    # XXX cprov 20080211: pending proper vovabularies for
    # SourcePackageRelease.
    from_source = Attribute(_(u"The base ISourcePackageRelease."))
    to_source = Attribute(_(u"The target ISourcePackageRelease."))

    date_fulfilled = Datetime(
        title=_(u'Date Fulfilled'), required=False)

    diff_content = Object(
        schema=ILibraryFileAlias,
        title=_(u"The ILibraryFileAlias contaning the diff."),
        required=False)


class IPackageDiffSet(Interface):
    """The set of PackageDiff."""

    def get(diff_id):
        """Retrieve a PackageDiff for the given id."""
