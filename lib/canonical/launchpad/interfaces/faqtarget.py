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
        :param summary: A short description of the issue answered in the document.
        :param content: The document's content. Alternatively a URL can be provided.
        :param url: The URL to the document containing the answer.
        :param date_created: The creation time of the document. Defaults to now.

        Either content or url must be prrovided. It is an error to specify both.
        """
