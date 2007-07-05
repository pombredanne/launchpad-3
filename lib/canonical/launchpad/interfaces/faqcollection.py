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
    contain the FAQ.
    """

    def getFAQ(id):
        """Return the `IFAQ` in this target with the requested id.

        :return: The `IFAQ` with the requested id or None if there is no
            document with that id.
        """

    def searchFAQs(search_text=None, owner=None, sort=None):
        """Return the FAQs from the collection matching search criteria.

        :param search_text: A string that is matched against the FAQ title,
        keywords and content. If None, the search_text is not included as
        a filter criteria.

        :param owner: A person that is matched against the owner of the FAQ.
        If None, owner is not included as a filter criteria.

        :param sort:  One value from of FAQSort. If None, a default value
        is used. When there is a search_text value, the default is to sort by
        RELEVANCY, otherwise results are sorted NEWEST_FIRST.
        """
