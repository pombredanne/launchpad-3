# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'TranslationTemplateItem',
    ]

from zope.interface import implements
from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ITranslationTemplateItem


class TranslationTemplateItem(SQLBase):
    implements(ITranslationTemplateItem)

    _table = 'TranslationTemplateItem'

    potemplate = ForeignKey(
        foreignKey='POTemplate', dbName='potemplate', notNull=False,
        default=None)
    potmsgset = ForeignKey(
        foreignKey='POTMsgSet', dbName='potmsgset', notNull=True)
