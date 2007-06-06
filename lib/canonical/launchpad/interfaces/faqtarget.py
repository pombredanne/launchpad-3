# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interface for things that can host IFAQ."""

__metaclass__ = type

__all__ = [
    'IFAQTarget',
    ]


from zope.interface import Interface


class IFAQTarget(Interface):
    """An object that can contain a FAQ document."""

    def newFAQ(owner, title, summary, content=None, url=None,
               date_created=None):
        """Create a new FAQ hosted in this target.

        :param owner: The `IPerson` creating the FAQ document.
        :param title: The document's title.
        :param summary: A short description of the issue answered in the
            document.
        :param content: The document's content. Alternatively a URL can be
            provided.
        :param url: The URL to the document containing the answer.
        :param date_created: The creation time of the document.
            Defaults to now.

        Either content or url must be prrovided. It is an error to specify
        both.
        """

    def getFAQ(id):
        """Return the `IFAQ` in this target with the requested id.

        :return: The `IFAQ` with the requested id or None if there is no
            document with that id.
        """

    def findSimilarFAQs(summary):
        """Return FAQs contained in this target similar to summary.

        Return a list of FAQs similar to the summary provided. These
        FAQs should be found using a fuzzy search. The list should be
        ordered from the most similar FAQ to the least similar FAQ

        :param summary: A summary phrase.
        """
