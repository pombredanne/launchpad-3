#!/usr/bin/python
# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: a1465e4f-ab19-4ed2-a7cf-da2a32861ef6

import sys, psycopg, codecs, canonical.rosetta.pofile

from cStringIO import StringIO
from zope.component import getUtility
from zope.interface import implements
from canonical.launchpad.interfaces import IPOExport
from canonical.rosetta.pofile import POMessage


class POExport:
    implements(IPOExport)

    def __init__(self, potfile):
        self.potfile = potfile

    def export(self, language):
        poFile = self.potfile.poFile(language)

        message = POMessage()

        message.comment = unicode(poFile.comment)
        message.msgstr = unicode(poFile.header)
        if poFile.headerFuzzy:
            message.flags.add('fuzzy')

        header = pofile.POHeader(message)
        header.finish()

        messages = []
        for msgid in self.potfile:
            translation = poFile.__getitem__(msgid)
            message = POMessage()
            message.msgid = unicode(msgid.text)
            message.msgstr = unicode(translation.text)
            message.comment = unicode(translation.comment)
            message.references = unicode(msgid.references)
            message.generated_comment = msgid.generatedComment
            message.flags.update(
                        [flag.strip() for flag in str(msgid.flags).split(',')])
            if translation.fuzzy:
                message.flags.add('fuzzy')
            message.obsolete = translation.obsolete
            messages.append(message)

        output = StringIO()
        writer = codecs.getwriter(header.charset)(output, 'strict')
        writer.write(unicode(header))
        for msg in messages:
            writer.write(u'\n\n')
            writer.write(unicode(msg))
        writer.write(u'\n')

        return output.getvalue()


# This class is not finished, is the old POExportAdapter
# it's just renamed so I could store here as a temp buffer
class POTFileDirectToDatabase:
    implements(IPOExport)

    def __init__(self, potfile):
        self.cnx = psycopg.connect("user=carlos dbname=launchpad")
        self.potfile = potfile

    def export(self, language):
        cr = self.cnx.cursor()

        # We get the potfile identificator
        cr.execute(
            """SELECT potfile FROM POTFile
                WHERE name='%s'""" % self.potfile.name)

        if cr.rowcount > 0:
            potfile = cr.fetchone()

            # and also, the language id
            cr.execute(
                """SELECT language FROM Language
                    WHERE code='%s'""" % language)

            # FIXME: We assume the language exists
            # but it should be added if it does not exists.
            row = cr.fetchone()
            lang_id = row[0]

            # Now, we look for an existent translation
            # to get its headers
            cr.execute(
                """SELECT pofile, topcomment, header FROM POFile
                    WHERE potfile=%(potfile)d AND
                          language=%(lang_id)d""",
                { 'potfile': potfile[0], 'lang_id': lang_id })

            # First, we extract/generate the .po header.
            message = POMessage()
#            message.msgid = u""
            if cr.rowcount > 0:
                pofile_query = cr.fetchone()
                message.comment = unicode(pofile_query[1], 'UTF-8')
                message.msgstr = unicode(pofile_query[2], 'UTF-8')
                pofile = pofile_query[0]
            else:
                # We don't have that translation in the database, thus
                # we will create a .pot file with empty translations
                message.comment = u""" SOME DESCRIPTIVE TITLE.
 Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
 This file is distributed under the same license as the PACKAGE package.
 FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
, fuzzy"""
                # By default, we generate new UTF-8 .po files instead
                # of using 'ENCODING' like gettext does. It's my way
                # of promote UTF-8.
                message.msgstr = u"""Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To:
POT-Creation-Date: 2004-07-18 23:00+0200
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit"""
                pofile = 0

            header = pofile.POHeader(message)
            header.finish()

            # First we extract the valid msgid looking at the .pot ones
            cr.execute(
                """SELECT pomsgid, "references", generatedcomment,
                          flags, plural FROM POTMsgIDSighting
                    WHERE potfile = %d AND iscurrent = TRUE
                    ORDER BY sequence""" % potfile)

            messages = []
            cr_msgid = self.cnx.cursor()
            cr_msgid_plural = self.cnx.cursor()
            cr_msgstr = self.cnx.cursor()
            cr_rosetta = self.cnx.cursor()
            cr_comments = self.cnx.cursor()
            cr_po = self.cnx.cursor()
            for row in cr.fetchall():
                message = POMessage()

                # We can assume that it will always exists
                # because we have a reference from a POTFile
                cr_msgid.execute(
                    "SELECT msgid FROM POMsgID WHERE pomsgid = %d" % row[0])
                msg_row = cr_msgid.fetchone()

                # The string is stored inside Postgresql as UTF-8
                message.msgid = unicode(msg_row[0], "UTF-8")

                # Check to see if it has a plural form.
                if row[4]:
                    # We can assume that it will always exists
                    # because we have a reference from a POTFile
                    cr_msgid_plural.execute(
                        "SELECT msgid FROM POMsgID WHERE pomsgid = %d" % row[4])
                    msg_plural_row = cr_msgid_plural.fetchone()

                    message.msgidPlural = unicode(msg_plural_row[0], "UTF-8")

                # Now it's time to fill the headers:
                message.references = str(row[1])
                message.generated_comment = unicode(str(row[2]), "UTF-8")
                if row[3]:
                    message.flags.update(
                        [flag.strip() for flag in str(row[3]).split(',')])

                # First we look at Rosetta translations
                # and we sort them with datetouched so we
                # can pick the latest one easily.
                cr_rosetta.execute(
                    """SELECT potranslation, pluralform, datetouched
                        FROM RosettaPOTranslationSighting
                        WHERE potfile=%(potfile)d AND
                              pomsgid=%(pomsgid)d AND
                              language=%(lang_id)d
                        ORDER BY datetouched, pluralform""",
                    { 'potfile': potfile[0],
                      'pomsgid': row[0],
                      'lang_id': lang_id })

                if (cr_rosetta.rowcount > 0):
                    # We need to choose the latest one so we only look for the
                    # first row.
                    rosetta_row = cr_rosetta.fetchone()
                    rosetta_ts = rosetta_row[2]

                # Now we pick the latest translation from the .po
                # FIXME: If the po string has the obsolete flag but matchs
                # and is newer than any other Rosetta entry, we should choose
                # it and save that msgid so we don't add it again as obsolete
                cr_po.execute(
                    """SELECT potranslation, pluralform, firstseen,
                              commenttext, fuzzy
                        FROM POTranslationSighting
                        WHERE pofile=%(pofile)d AND
                              pomsgid=%(pomsgid)d AND
                              fuzzy=FALSE AND
                              obsolete=FALSE
                        ORDER BY lastseen, pluralform, fuzzy""",
                    { 'pofile': pofile, 'pomsgid': row[0] })

                if cr_po.rowcount > 0:
                    po_row = cr_po.fetchone()
                    po_ts = po_row[2]

                    # We choose the Rosetta translation if it's newer than the
                    # po one or we only have fuzzy strings with .po files.
                    if (cr_rosetta.rowcount > 0 and
                       (rosetta_ts >= po_ts or bool(po_row[4]))):
                        # Rosetta wins
                        translation_row = rosetta_row
                        cr_translation = cr_rosetta
                        rosetta_wins = True
                    else:
                        # PO wins
                        translation_row = po_row
                        cr_translation = cr_po
                        rosetta_wins = False
                elif cr_rosetta.rowcount > 0:
                    # We pick the Rosetta one, we don't have a po one
                    translation_row = rosetta_row
                    cr_translation = cr_rosetta
                    rosetta_wins = True
                else:
                    translation_row = None

                if translation_row:
                    # We have a translation available.

                    # The main msgstr is needed to get the comments.
                    translation = translation_row[0]

                    cr_msgstr.execute(
                        """SELECT text FROM POTranslation
                            WHERE potranslation = %d""" % translation)
                    msgstr_row = cr_msgstr.fetchone()

                    if row[4]:
                        # If it's a plural form
                        message.msgstrPlurals.append(
                            unicode(msgstr_row[0], 'UTF-8'))
                        old_plural = translation_row[1]
                        for translation_row in cr_translation.fetchall():
                            if translation_row[1] == old_plural:
                                # We got already a newer version of this
                                # string
                                continue
                            cr_msgstr.execute(
                                """SELECT text FROM POTranslation WHERE
                                    potranslation = %d""" % translation_row[0])
                            msgstr_row = cr_msgstr.fetchone()
                            message.msgstrPlurals.append(
                                unicode(msgstr_row[0], 'UTF-8'))
                            old_plural = translation_row[1]
                    else:
                        # It's not a plural form
                        message.msgstr = unicode(msgstr_row[0], 'UTF-8')

                    # If it's a fuzzy translation, we should update the flags
                    if not rosetta_wins and po_row[4]:
                       message.flags.add('fuzzy')
                else:
                    message.msgstr = u""

                    # This way we get the comments although we don't have a
                    # translation.
                    translation = 0

                # We get here all comments for that translation + all
                # comments for that msgid in that file
                cr_comments.execute(
                    """SELECT commenttext FROM POComment
                        WHERE potfile=%(potfile)d AND
                              pomsgid=%(pomsgid)d AND
                              (language=%(lang_id)d OR
                               language IS NULL) AND
                              (potranslation=%(potranslation)d OR
                               potranslation IS NULL)
                        ORDER BY date""",
                        { 'potfile': potfile[0],
                          'pomsgid': row[0],
                          'lang_id': lang_id,
                          'potranslation': translation })

                if (cr_comments.rowcount > 0):
                    for comment_row in  cr_comments.fetchall():
                        message.comment +=  unicode(comment_row[0] + '\n',
                                                    "UTF-8")

                messages.append(message)

            # We DUMP the .po
            output = StringIO()
            writer = codecs.getwriter(header.charset)(output, 'strict')
            writer.write(unicode(header))
            for msg in messages:
                writer.write(u'\n\n')
                writer.write(unicode(msg))
            writer.write(u'\n')

            return output.getvalue()

        else:
            return "Export failed"
            # FIXME: We should add error control with execptions.
#            print("The potfile '" + self.potfile.name + "' does not exists")

#if __name__ == '__main__':
#    if len(sys.argv) < 3:
#        print "Usage: "
#        print "\t" + sys.argv[0] + " pot_name language"
#    else:
#        exporter = POExporter()
#        exporter.export(sys.argv[1], sys.argv[2])

