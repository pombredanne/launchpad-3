# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface objects for the LAZR example web service."""

__metaclass__ = type
__all__ = ['ICookbook',
           'ICookbookSet',
           'IHasGet']

from zope.interface import Interface
from zope.schema import TextLine

from canonical.lazr.rest.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_as_webservice_entry, exported)


class IHasGet(Interface):
    """A marker interface objects that implement traversal with get()."""
    def get(name):
        """Traverse to a contained object."""


class ICookbook(Interface):
    """A cookbook, annotated for export to the web service."""
    export_as_webservice_entry()
    name = exported(TextLine(title=u"Name", required=True))
    cuisine = exported(
        TextLine(title=u"Cuisine", required=False, default=None))


class ICookbookSet(IHasGet):
    """The set of all cookbooks, annotated for export to the web service."""
    export_as_webservice_collection(ICookbook)

    @collection_default_content()
    def getCookbooks():
        """Return the list of cookbooks."""
