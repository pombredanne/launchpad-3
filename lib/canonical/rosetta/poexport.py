#!/usr/bin/python
# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: aef7f683-dbd0-46d0-944d-6442bfdbdb13

import sys, codecs

from cStringIO import StringIO
from zope.interface import implements
from canonical.rosetta.interfaces import IPOExport
from canonical.rosetta.pofile import POMessage, POHeader
from canonical.rosetta.pofile_adapters import MessageProxy


class POExport:
    implements(IPOExport)

    def __init__(self, potfile):
        self.potfile = potfile

    def export(self, language):
        poFile = self.potfile.poFile(language)

        header = POHeader(
            commentText = unicode(poFile.topComment, 'UTF-8'),
            msgstr = unicode(poFile.header, 'UTF-8'))
        
        # FIXME: This field does not exists (yet) in the database.
#        if poFile.headerFuzzy:
#            header.flags.add('fuzzy')

        header.finish()

        messages = []
        for msgid in self.potfile:
            # suggested implementation:
            translation = poFile[msgid]
            messages.append(MessageProxy(translation))

        output = StringIO()
        writer = codecs.getwriter(header.charset)(output, 'strict')
        writer.write(unicode(header))
        for msg in messages:
            writer.write(u'\n\n')
            writer.write(unicode(msg))
        writer.write(u'\n')

        return output.getvalue()

