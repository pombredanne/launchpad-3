# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POFileTranslator',
    'POFileTranslatorSet',
    ]


from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    IPOFileTranslator, IPOFileTranslatorSet)
from lp.registry.interfaces.person import validate_public_person


class POFileTranslator(SQLBase):
    """See `IPOFileTranslator`."""

    implements(IPOFileTranslator)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    latest_message = ForeignKey(
        foreignKey='TranslationMessage', dbName='latest_message',
        notNull=True)
    date_last_touched = UtcDateTimeCol(
        dbName='date_last_touched', notNull=False, default=None)


class POFileTranslatorSet:
    """The set of all `POFileTranslator` records."""

    implements(IPOFileTranslatorSet)

    def prefetchPOFileTranslatorRelations(self, pofiletranslators):
        """See `IPOFileTranslatorSet`."""
        ids = set(record.id for record in pofiletranslators)
        if not ids:
            return None

        # Listify prefetch query to force its execution here.
        return list(POFileTranslator.select(
            "POFileTranslator.id IN %s" % sqlvalues(ids),
            prejoins=[
                'pofile',
                'pofile.potemplate',
                'pofile.potemplate.productseries',
                'pofile.potemplate.productseries.product',
                'pofile.potemplate.distroseries',
                'pofile.potemplate.sourcepackagename',
                'latest_message',
                'latest_message.potmsgset',
                'latest_message.potmsgset.msgid_singular',
                'latest_message.msgstr0',
                ]))
