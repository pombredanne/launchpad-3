# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Soyuz vocabularies."""

__metaclass__ = type

__all__ = [
    'ProcessorVocabulary',
    ]

from lp.buildmaster.model.processor import Processor
from lp.services.webapp.vocabulary import NamedSQLObjectVocabulary


class ProcessorVocabulary(NamedSQLObjectVocabulary):

    displayname = 'Select a processor'
    _table = Processor
    _orderBy = 'name'
