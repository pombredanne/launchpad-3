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

_created_with_rosetta = 'Rosetta (http://launchpad.ubuntu.com/rosetta/)'


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

        # XXX Carlos Perello Marin 2005/01/24 disabled until we fix:
        # https://dogfood.ubuntu.com/malone/bugs/221
        #
        ## We update now the header with the new information from Rosetta
        ## First, we should get the POTemplate's POT-Creation-Date:
        #pot_header = POHeader(msgstr = self.potfile.header)
        #pot_header.finish()
        ## ...and update the POFile one with it:
        #header['POT-Creation-Date'] = pot_header['POT-Creation-Date']

        # First we get last translator that touched a string and the date when
        # it was done.
        last_changed = poFile.lastChangedSighting()

        if last_changed is not None:
            # We have at least one pomsgset with a translation so we are able
            # to update .po's headers.

            # It's safe to assume that all times in Rosetta are UTC dates.
            header['PO-Revision-Date'] = last_changed.datelastactive.strftime(
                '%F %R+0000')

            # Look for the email address of the last translator
            if last_changed.person.preferredemail is not None:
                # We have a preferred email address set.
                email = last_changed.person.preferredemail.email
            elif len(last_changed.person.validatedemails) > 0:
                # As our second choice, get one of the validated email
                # addresses of this translator.
                email = last_changed.person.validatedemails[0].email
            elif len(last_changed.person.notvalidatedemails) > 0:
                # We don't have preferred or validated address so we choose
                # any other email address we could have.
                email = last_changed.person.notvalidatedemails[0].email
            else:
                # We should never reach this line because we are supposed to
                # have always an email address for all our users.
                raise RuntimeError(
                    'All Person rows should have at least one email address!')

            # Now, it's time to get a name for our translator
            if last_changed.person.displayname is not None:
                name = last_changed.person.displayname
            else:
                name = last_changed.person.name

            # Finally the pofile header is updated.
            header['Last-Translator'] = '%s <%s>' % (name, email)

        # All .po exported from Rosetta get the X-Generator header:
        header['X-Generator'] = _created_with_rosetta

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

