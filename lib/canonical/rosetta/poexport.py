#!/usr/bin/python
# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: aef7f683-dbd0-46d0-944d-6442bfdbdb13

import sys, codecs

from cStringIO import StringIO
from zope.interface import implements
from canonical.launchpad.interfaces import IPOExport
from canonical.rosetta.pofile import POMessage, POHeader
from canonical.rosetta.pofile_adapters import MessageProxy


class POExport:
    implements(IPOExport)

    def __init__(self, potfile):
        self.potfile = potfile

    def export(self, language):
        poFile = self.potfile.getPOFileByLang(language)

        header = POHeader(
            commentText = poFile.topcomment,
            msgstr = poFile.header)

        if poFile.fuzzyheader:
            header.flags.add('fuzzy')

        header.finish()

        messages = []
        for potmsgset in self.potfile:
            try:
                pomsgset = poFile[potmsgset.primemsgid_.msgid]
                fuzzy = True
            except KeyError:
                # the pofile doesn't have that msgid; include the
                # one from the template
                pomsgset = None
                fuzzy = False
            messages.append(
                MessageProxy(potmsgset=potmsgset, pomsgset=pomsgset, fuzzy=fuzzy))
        # export obsolete messages
        # XXX: Carlos Perello Marin 08/11/2004: Should we mark as fuzzy also
        # the incompleted and obsolete msgsets?
        obsolete_messages = []
        for pomsgset in poFile.messageSetsNotInTemplate():
            potmsgset = pomsgset.potmsgset
            obsolete_messages.append(
                MessageProxy(potmsgset=potmsgset, pomsgset=pomsgset))

        output = StringIO()
        writer = codecs.getwriter(header.charset)(output, 'strict')
        writer.write(unicode(header))
        for msg in messages:
            writer.write(u'\n\n')
            writer.write(unicode(msg))
        for msg in obsolete_messages:
            writer.write(u'\n\n')
            writer.write(unicode(msg))
        writer.write(u'\n')

        return output.getvalue()

