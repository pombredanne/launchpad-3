# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = [
    'ITranslationImport'
    ]

class ITranslationImport(Interface):
    """Rosetta translation file import."""

    allentries = Attribute('List of Templates and translations provided by this file.')

    def getTemplate(path):
        """Return a dictionary representing a translation template.

        :arg path: Location of the template.
        """

    def getTranslation(path, language):
        """Return a dictionary representing a translation.

        :arg path: Location of the translation.
        :arg language: Language we are interested on.
        """
