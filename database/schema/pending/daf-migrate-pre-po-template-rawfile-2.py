
import base64
from StringIO import StringIO

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.database import POTemplate, POFile
from canonical.librarian.client import LibrarianClient
from canonical.librarian.interfaces import UploadFailed

def migrate(table, desc, filename_function):
    tablename = table.__name__
    client = LibrarianClient()

    # Get a list of template IDs.
    c = cursor()
    c.execute('SELECT id FROM %s WHERE rawfile_ IS NOT NULL' % tablename)
    ids = [id for (id,) in c.fetchall()]

    if not ids:
        print "no unmigrated %ss" % desc
        return

    for id in ids:
        print "migrating %s %d" % (desc, id)

        # Get the raw PO file from the old column.
        c.execute('SELECT rawfile_ FROM %s WHERE id = %d' % (tablename, id))
        (rawfile,) = c.fetchone()
        contents = base64.decodestring(rawfile)

        # Upload it to the Librarian and update the new column.
        obj = table.get(id)
        filename = filename_function(obj)

        try:
            obj.rawfile = client.addFile(
                name=filename,
                size=len(contents),
                file=StringIO(contents),
                contentType='application/x-po')
        except UploadFailed, e:
            print "%s %d failed: %s" % (desc, id, str(e))

        c.execute('UPDATE %s SET rawfile_ = NULL WHERE id = %d' %
            (tablename, id))

def filename_from_template(template):
    return '%s.pot' % template.potemplatename.translationdomain

def filename_from_pofile(pofile):
    if pofile.variant:
        filename = '%s@%s.po' % (
            pofile.language.code, pofile.variant.encode('utf8'))
    else:
        filename = '%s.po' % pofile.language.code

    return filename

def main():
    ztm = initZopeless()
    migrate(POTemplate, 'PO template', filename_from_template)
    migrate(POFile, 'PO file', filename_from_pofile)
    ztm.commit()

if __name__ == '__main__':
    main()

