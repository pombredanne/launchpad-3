
import os
import tarfile

from StringIO import StringIO

def add_file(tf, name, contents):
    '''
    Convenience method for adding a file to a tar file.
    '''

    tarinfo = tarfile.TarInfo(name)
    tarinfo.size = len(contents)

    tf.addfile(tarinfo, StringIO(contents))

def add_files(tf, prefix, files):
    '''
    Convenience method for adding a tree of files represented as a dictionary
    to a tar file.
    '''

    # Keys are sorted in order to make test cases easier to write.

    names = files.keys()
    names.sort()

    for name in names:
        if isinstance(files[name], basestring):
            # Looks like a file.

            add_file(tf, prefix + name, files[name])
        else:
            # Should be a directory.

            tarinfo = tarfile.TarInfo(prefix + name)
            tarinfo.type = tarfile.DIRTYPE
            tf.addfile(tarinfo)

            add_files(tf, prefix + name + '/', files[name])

def make_tarfile(files):
    '''
    Convenience method for constructing a string containing tar file from a
    dictionary in memory.

    >>> s = make_tarfile({ 'foo' : 'bar', 'zot' : { 'gurgle' : 'sploink' } })
    >>> tf = string_to_tarfile(s)
    >>> tf.getnames()
    ['foo', 'zot/', 'zot/gurgle']
    >>> tf.extractfile('zot/gurgle').read()
    'sploink'
    '''

    sio = StringIO()

    tf = tarfile.open('', 'w', sio)

    add_files(tf, '', files)

    tf.close()

    return sio.getvalue()

def join_lines(*lines):
    r'''
    Concatenate a list of strings, adding a newline at the end of each.

    >>> join_lines('foo', 'bar', 'baz')
    'foo\nbar\nbaz\n'
    '''

    return ''.join([ x + '\n' for x in lines ])

def string_to_tarfile(s):
    '''
    Convert a binary string containing a tar file into a tar file object.
    '''

    return tarfile.open('', 'r', StringIO(s))

def make_test_string_1():
    '''
    Generate a test tarball that looks something like a source tarball which
    has exactly one directory called 'po' which is interesting (i.e. contains
    some files which look like POT/PO files).

    >>> tf = string_to_tarfile(make_test_string_1())

    Check it looks vaguely sensible.

    >>> names = tf.getnames()
    >>> 'uberfrob-0.1/po/cy.po' in names
    True
    '''

    return make_tarfile({
        'uberfrob-0.1' : {
            'README' : 'Uberfrob is an advanced frobnicator.',
            'po' : {
                'cy.po' : '# Blah.',
                'es.po' : '# Blah blah.',
                'uberfrob.pot' : '# Yowza!',
                 },
            'blah' : {
                'po' : {
                    'la' : 'la la' }
                },
            'uberfrob.py' :
                'import sys\n'
                'print "Frob!"\n'
            }
        })

def make_test_string_2():
    r'''
    Generate a test tarball string that has some interesting files in a common
    prefix.

    >>> tf = string_to_tarfile(make_test_string_2())

    Check the expected files are in the archive.

    >>> tf.getnames()
    ['test/', 'test/cy.po', 'test/es.po', 'test/test.pot']

    Check the contents.

    >>> f = tf.extractfile('test/cy.po')
    >>> f.readline()
    '# Test PO file.\n'
    '''

    po = join_lines(
        '# Test PO file.',
        'msgid "foo"',
        'msgstr "bar"',
        )

    return make_tarfile({
        'test' : {
            'test.pot' : join_lines(
                '# Test POT file.',
                'msgid "foo"',
                'msgstr ""',
                ),
            'cy.po' : po,
            'es.po' : po,
            }
        })

def find_po_directories(tarfile):
    '''
    Find all directories named 'po' in a tarfile.

    >>> tf = string_to_tarfile(make_test_string_1())
    >>> find_po_directories(tf)
    ['uberfrob-0.1/blah/po/', 'uberfrob-0.1/po/']
    '''

    return [
        member.name
        for member in tarfile.getmembers()
        if member.isdir()
        and os.path.basename(member.name.strip("/")) == 'po'
        ]

def examine_tarfile(tf):
    '''
    Find POT and PO files within a tar file object.

    Two methods of finding files are employed:

     1. Directories named 'po' are searched for in the tar file, and if there
        is exactly one non-empty such directory, it is searched for files
        ending in '.pot' and '.po'.

     2. Otherwise, files ending in '.pot' and '.po' are searched for directly.

    >>> pot, po = examine_tarfile(string_to_tarfile(make_test_string_1()))
    >>> pot
    ('uberfrob-0.1/po/uberfrob.pot',)
    >>> po
    ('uberfrob-0.1/po/cy.po', 'uberfrob-0.1/po/es.po')

    >>> pot, po = examine_tarfile(string_to_tarfile(make_test_string_2()))
    >>> pot
    ('test/test.pot',)
    >>> po
    ('test/cy.po', 'test/es.po')
    '''

    # All files in the tarfile.

    names = tf.getnames()

    # Directories named 'po' in the tarfile.

    po_directories = find_po_directories(tf)

    if po_directories:
        # Look for interesting PO directories. (I.e. ones that contain POT or
        # PO files.)

        interesting = []

        for d in po_directories:
            for name in names:
                if name != d and name.startswith(d) and (
                    name.endswith('.pot') or name.endswith('.po')):
                    if d not in interesting:
                        interesting.append(d)

        # If there's exactly one interesting PO directory, get a list of all
        # the interesting files in it. Otherwise, use method 2.

        if len(interesting) == 1:
            directory = interesting[0]
            pot_files, po_files = [], []

            for name in names:
                if name.startswith(directory):
                    if name.endswith('.pot'):
                        pot_files.append(name)
                    elif name.endswith('.po'):
                        po_files.append(name)

            return (tuple(pot_files), tuple(po_files))

    # All files which look interesting.

    pot_files = [name for name in names if name.endswith('.pot')]

    po_files =  [name for name in names if name.endswith('.po')]

    return (tuple(pot_files), tuple(po_files))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

