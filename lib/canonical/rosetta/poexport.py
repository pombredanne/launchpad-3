#!/usr/bin/python
# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: aef7f683-dbd0-46d0-944d-6442bfdbdb13

import sys, codecs

from cStringIO import StringIO
from zope.interface import implements
from canonical.rosetta.interfaces import IPOExport
from canonical.rosetta.pofile import POMessage, POHeader
## from canonical.rosetta.pofile_adapters import MessageProxy


class POExport:
    implements(IPOExport)

    def __init__(self, potfile):
        self.potfile = potfile

    def export(self, language):
        poFile = self.potfile.poFile(language)

        header = POHeader(
            comment = unicode(poFile.commentText),
            msgstr = unicode(poFile.header))
        
        if poFile.headerFuzzy:
            header.flags.add('fuzzy')

        header.finish()

        messages = []
        for msgid in self.potfile:
            # suggested implementation:
            ## translation = poFile[msgid]
            ## messages.append(MessageProxy(translation))
            # delete <
            translation = poFile[msgid]
            message = POMessage()
            message.msgid = unicode(msgid.text)
            if len(msgid.text) > 1:
                message.msgidPlural = unicode(msgid.pluralText)
            if len(translation.text) > 1:
                for text in translation.text:
                    message.msgstrPlurals.append(unicode(text))
            else:
                message.msgstr = unicode(unicode(translation.text[0]))
            message.commentText = unicode(translation.commentText)
            message.references = unicode(msgid.fileReferences)
            message.generated_comment = msgid.sourceComment
            message.flags.update(
                        [flag.strip() for flag in str(msgid.flags).split(',')])
            if translation.fuzzy:
                message.flags.add('fuzzy')
            message.obsolete = translation.obsolete
            messages.append(message)
            # > delete

        output = StringIO()
        writer = codecs.getwriter(header.charset)(output, 'strict')
        writer.write(unicode(header))
        for msg in messages:
            writer.write(u'\n\n')
            writer.write(unicode(msg))
        writer.write(u'\n')

        return output.getvalue()

