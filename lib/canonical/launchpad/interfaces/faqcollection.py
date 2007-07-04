# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interface for things that contains a collection of FAQs."""

__metaclass__ = type

__all__ = [
    'IFAQCollection',
    ]


from zope.interface import Interface


class IFAQCollection(Interface):
    """Interface provided by collection of FAQs.

    This interface allows for retrieving and searching for FAQs. The
    more specific `IFAQTarget` interface is used for objects that directly
    contain the answer."""

    def getFAQ(id):
        """Return the `IFAQ` in this target with the requested id.

        :return: The `IFAQ` with the requested id or None if there is no
            document with that id.
        """

