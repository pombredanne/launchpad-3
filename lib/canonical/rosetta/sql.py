# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

import canonical.launchpad.interfaces as interfaces
from canonical.database.constants import nowUTC

from zope.interface import implements, directlyProvides
from zope.component import getUtility
from canonical.rosetta import pofile
from types import NoneType
from datetime import datetime
from sets import Set

standardTemplateCopyright = 'Canonical Ltd'

# XXX: in the four strings below, we should fill in owner information
standardTemplateTopComment = ''' PO template for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 PROJECT MAINTAINER OR MAILING LIST <EMAIL@ADDRESS>, %(year)s.

'''

# XXX: project-id-version needs a version
standardTemplateHeader = (
"Project-Id-Version: %(productname)s\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE NAME <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
)

standardPOFileTopComment = ''' %(languagename)s translation for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.

'''

standardPOFileHeader = (
"Project-Id-Version: %(productname)s\n"
"Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>\n"
"POT-Creation-Date: %(templatedate)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(languagename)s <%(languagecode)s@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
"Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)


def createMessageIDSighting(messageSet, messageID):
    """Creates in the database a new message ID sighting.

    Returns None.
    """

    RosettaPOMessageIDSighting(
        poMessageSet=messageSet,
        poMessageID_=messageID,
        dateFirstSeen=nowUTC,
        dateLastSeen=nowUTC,
        inLastRevision=True,
        pluralForm=0)


def createMessageSetFromMessageID(poTemplate, messageID, poFile=None):
    """Creates in the database a new message set.

    As a side-effect, creates a message ID sighting in the database for the
    new set's prime message ID.

    Returns that message set.
    """
    messageSet = RosettaPOMessageSet(
        poTemplateID=poTemplate.id,
        poFile=poFile,
        primeMessageID_=messageID,
        sequence=0,
        isComplete=False,
        obsolete=False,
        fuzzy=False,
        commentText='',
        fileReferences='',
        sourceComment='',
        flagsComment='')

    createMessageIDSighting(messageSet, messageID)

    return messageSet


def createMessageSetFromText(potemplate_or_pofile, text):
    context = potemplate_or_pofile

    if isinstance(text, unicode):
        text = text.encode('utf-8')

    try:
        messageID = RosettaPOMessageID.byMsgid(text)
        if context.hasMessageID(messageID):
            raise KeyError(
                "There is already a message set for this template, file and "
                "primary msgid")
                
    except SQLObjectNotFound:
        # If there are no existing message ids, create a new one.
        # We do not need to check whether there is already a message set
        # with the given text in this template.
        messageID = RosettaPOMessageID(msgid=text)
        
    return context.createMessageSetFromMessageID(messageID)




def personFromPrincipal(principal):
    from zope.app.security.interfaces import IUnauthenticatedPrincipal
    from canonical.lp.placelessauth.launchpadsourceutility import \
        LaunchpadPrincipal

    if IUnauthenticatedPrincipal.providedBy(principal):
        return None

    if not isinstance(principal, LaunchpadPrincipal):
        return None

    return RosettaPerson.get(principal.id)



