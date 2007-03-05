# Copyright 2006 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, Choice, Text, TextLine, Field

from canonical.lp.dbschema import RosettaFileFormat

__metaclass__ = type

__all__ = ('ITranslationImport', )

class ITranslationImport(Interface):
    """Rosetta translation file import."""

    allentries = Attribute('Templates and translations provided by this file.')

    def importSupported():
        """Checks if this import can be carried out using this class.

        Returns the weight of the importer compatibility in the range
        [0,10]. Zero indicates not-supported, and ten indicates most
        applicable importer.
        """

    def getTemplate(path):
        """Returns PO template for given path inside the file."""

    def getTranslation(path, language):
        """Returns translation in 'language' for template given by 'path'."""
