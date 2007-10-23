# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""
You probably don't want to import stuff from here. See __init__.py
for details
"""

__metaclass__ = type

__all__ = [
    'vocab_factory',
    'TranslationFileFormatVocabulary',
    'TranslationPermissionVocabulary',
    ]

from canonical.lp import dbschema

from canonical.launchpad.webapp.vocabulary import vocab_factory
from canonical.launchpad.interfaces import (
    TranslationFileFormat, TranslationPermission)

# DB Schema Vocabularies

TranslationFileFormatVocabulary = vocab_factory(TranslationFileFormat)
TranslationPermissionVocabulary = vocab_factory(TranslationPermission)
