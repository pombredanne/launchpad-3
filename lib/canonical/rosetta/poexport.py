# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: aef7f683-dbd0-46d0-944d-6442bfdbdb13
"""Implementation of the export class from a POFile object into a .po file

"""

import codecs

from cStringIO import StringIO
from zope.interface import implements
from canonical.launchpad.interfaces import IPOExport
from canonical.rosetta.pofile import POHeader
from canonical.rosetta.pofile_adapters import MessageProxy


class POExport:
    """Class that exports pofiles from the database.

    It gets a potemplate from where we want to get po files exported and give
    us the selected translation for a concrete language.
    """

    implements(IPOExport)

    def __init__(self, potfile):
        self.potfile = potfile

    def export(self, language):
        """This method returns a string stream with the translation of
        self.potfile into the language.

        The language argument is a string with the code of the language like
        cy or pt_BR
        """

        poFile = self.potfile.getPOFileByLang(language)

        # Get all current messagesets from the POTemplate and the translations
        # for this concrete language. Also, we ask to set the fuzzy flag in
        # case a translation is not complete.
        messages = []
        for potmsgset in self.potfile:
            try:
                pomsgset = poFile[potmsgset.primemsgid_.msgid]
                # If the message is incomplete, this flag will make that
                # MessageProxy set it as fuzzy.
                fuzzy = True
            except KeyError:
                # the pofile doesn't have that msgid; include the
                # one from the template
                pomsgset = None
                # We don't have any translation, thus it makes no sense to
                # mark the message as incomplete.
                fuzzy = False
            messages.append(
                MessageProxy(
                    potmsgset=potmsgset,
                    pomsgset=pomsgset,
                    fuzzy=fuzzy))

        # Get all obsolete messages from the POFile, that's all messagesets
        # that were in the POFile last time we imported it but are not anymore
        # in the POTemplate.
        obsolete_messages = []
        for pomsgset in poFile.messageSetsNotInTemplate():
            potmsgset = pomsgset.potmsgset
            # By default we export the obsolete messages that are also
            # incomplete as fuzzy.
            obsolete_messages.append(
                MessageProxy(
                    potmsgset=potmsgset,
                    pomsgset=pomsgset,
                    fuzzy=True))

        # We parse the header of the POFile before exporting it to be able to
        # know the POFile encoding
        header = POHeader(
            commentText = poFile.topcomment,
            msgstr = poFile.header)
        if poFile.fuzzyheader:
            header.flags.add('fuzzy')
        header.finish()

        # Write out the messages followed by the obsolete messages into a
        # StringIO buffer.  Then, return the contents of the buffer.
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

