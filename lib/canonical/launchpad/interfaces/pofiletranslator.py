# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

__metaclass__ = type

__all__ = [
    'IPOFileTranslator',
    'IPOFileTranslatorSet',
    ]


from zope.interface import Interface
from zope.schema import Datetime, Int, Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.pofile import IPOFile
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.translationmessage import (
    ITranslationMessage)


class IPOFileTranslator(Interface):
    """Represents contributions from people to `POFile`s."""

    id = Int(title=_("ID"), readonly=True, required=True)

    person = Object(
        title=_(u"The `Person` whose contribution this record represents."),
        required=True, readonly=True, schema=IPerson)

    pofile = Object(
        title=_(u"The `POFile` modified by the translator."), required=True,
        readonly=True, schema=IPOFile)

    latest_message = Object(
        title=_(u"Latest `TranslationMessage` for this person and file."),
        required=True, readonly=True, schema=ITranslationMessage)

    date_last_touched = Datetime(
        title=_(u"When the latest translation message was added."),
        required=True, readonly=True)


class IPOFileTranslatorSet(Interface):
    """Interface representing the set of `IPOFileTranslator`records.

    You won't find a "new" method here.  POFileTranslator records are
    created directly in the database by a trigger that watches for
    translation updates.
    """

    def prefetchPOFileTranslatorRelations(pofiletranslators):
        """Batch-prefetch objects attached to given `POFileTranslator`s.

        Fetches a large amount of data relevant to rendering the given
        `POFileTranslator` objects in the user interface, to reduce the
        number of queries needed while rendering the page.
        """
