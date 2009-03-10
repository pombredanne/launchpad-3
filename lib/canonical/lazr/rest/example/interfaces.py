# pylint: disable-msg=E0211,E0213

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
    export_as_webservice_entry()
    name = exported(TextLine(title=u"Name", required=True))
    cuisine = exported(
        TextLine(title=u"Cuisine", required=False, default=None))


class ICookbookSet(IHasGet):
    export_as_webservice_collection(ICookbook)

    @collection_default_content()
    def getCookbooks():
        pass
