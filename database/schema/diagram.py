#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath

import psycopg, sys, os, re
from security import DbSchema, CursorWrapper
from ConfigParser import SafeConfigParser, NoOptionError

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'lib'
    ))

config = SafeConfigParser()
config.read(['diagram.cfg'])

def trim(wanted_tables):
    '''Drop everything we don't want in the diagram'''
    con = psycopg.connect('dbname=launchpad_dev')
    cur = CursorWrapper(con.cursor())
    done = False

    # Drop everything we don't want to document
    schema = DbSchema(con)
    all_objs = schema.values()
    while not done:
        schema = DbSchema(con)
        for obj in schema.values():
            if obj.fullname in wanted_tables:
                continue
            if obj.type == "view":
                print 'Dropping view %s' % obj.fullname
                cur.execute("DROP VIEW %s CASCADE" % obj.fullname)
                break
            elif obj.type == "table":
                print 'Dropping table %s' % obj.fullname
                cur.execute("DROP TABLE %s CASCADE" % obj.fullname)
                break
            if obj == all_objs[-1]:
                done = True
    con.commit()

class Universe:
    def __contains__(self, i):
        '''The universe contains everything'''
        return True

all_tables = set()
graphed_tables = set()

def tartup(filename, outfile, section):
    dot = open(filename).read()

    # Shorten timestamp declarations
    dot = re.subn('timestamp without time zone', 'timestamp', dot)[0]

    # Collapse all whitespace that is safe
    dot = re.subn('\s+', ' ', dot)[0]
    dot = re.subn(';', ';\n', dot)[0]

    lines = dot.split('\n')

    counter = 0
    wanted_tables = [
        s.strip() for s in config.get(section, 'tables').split(',')
        if s.strip()
        ]

    if '*' in wanted_tables:
        wanted_tables = Universe()
    else:
        exploded_wanted_tables = []
        excluded_tables = []
        for table in wanted_tables:
            if table.endswith('+'):
                if table.endswith('++'):
                    table = table[:-2]
                    exploded_wanted_tables.extend(explode(table, True))
                else:
                    table = table[:-1]
                    exploded_wanted_tables.extend(explode(table, False))
            if table.endswith('-'):
                table = table[:-1]
                excluded_tables.append(table)
            else:
                exploded_wanted_tables.append(table)
        wanted_tables = [
            t for t in exploded_wanted_tables
            if t not in excluded_tables
            ]
        for t in wanted_tables:
            graphed_tables.add(t)

    for i in xrange(0, len(lines)):
        line = lines[i]

        # Trim tables we don't want to see
        m = re.search(r'^\s* "(.+?)" \s+ \[shape', line, re.X)
        if m is not None:
            table = m.group(1)
            all_tables.add(table)
            if table not in wanted_tables:
                lines[i] = ''
                continue

        # Trim foreign key relationships as specified, replacing with phantom
        # links
        m = re.search(
                r'^\s*"(.+?)" \s -> \s "(.*?)" \s '
                r'\[label="(.*?)"\]; \s* $',
                line, re.X
                )
        if m is None:
            continue

        counter += 1

        t1 = m.group(1)
        t2 = m.group(2)

        # No links from an unwanted table to any other tables
        if t1 not in wanted_tables:
            lines[i] = ''
            continue

        # Links to ourself are fine, unless the table is not wanted
        if t1 == t2:
            continue

        # Get allowed links
        allowed_link = True
        if t2 not in wanted_tables:
            allowed_link = False
        else:
            for source, end in [(t1, t2), (t2, t1)]:
                try:
                    allowed = config.get(section, source)
                except NoOptionError:
                    continue
                allowed = [a.strip() for a in allowed.split(',') if a.strip()]
                if end not in allowed:
                    allowed_link = False
                    break
        if allowed_link:
            continue

        fake_node = 'fake_%s_%d' % (t2, counter)
        counter += 1
        lines[i] = '''
            "%(fake_node)s" [shape="ellipse",label="%(t2)s",color=red ];
            "%(t1)s" -> "%(fake_node)s" [label="", len=.01, w=10000];
            ''' % vars()
    open(outfile, 'w').write('\n'.join(lines))

def explode(table, two_way=False):
    con = psycopg.connect(config.get('DEFAULT', 'dbconnect'))
    cur = con.cursor()
    cur.execute('''
        SELECT
            src.relname AS src,
            dst.relname AS dst
        FROM
            pg_constraint,
            pg_class AS src,
            pg_class AS dst
        WHERE
            (src.relname=%(table)s OR dst.relname=%(table)s)
            AND src.oid = conrelid
            AND dst.oid = confrelid
        ''', vars())
    references = list(cur.fetchall())
    rv = []
    for src, dst in references:
        if two_way:
            rv.append(src)
            rv.append(dst)
        elif src == table:
            rv.append(dst)
    return rv


def main(filetypes):

    print filetypes
    # Run postgresql_autodoc, creating autodoc.dot
    cmd = (
            "postgresql_autodoc -f autodoc -t dot -s public "
            "-d launchpad_dev -l %s -u postgres" % os.pardir
            )
    rv = os.system(cmd)
    assert rv == 0, 'Error %d running %r' % (rv, cmd)

    for section in config.sections():
        if sys.argv[1:]:
            render = False
            for a in sys.argv[1:]:
                if section in a:
                    render = True
                    break
            if not render:
                continue
        # Munge the dot file because by default it is renders badly
        print 'Tarting up autodoc.dot into +%s.dot' % section
        tartup('autodoc.dot', '+%s.dot' % section, section)

        # Render
        for lang in filetypes:
            print lang
            cmd = config.get(section, '%s_command' % lang)

            print (
                    'Producing %(section)s.%(lang)s from %(section)s.dot '
                    'using %(lang)s' % vars()
                    )

            csection = section.capitalize()

            cmd = (
                '%(cmd)s -Glabel=%(csection)s -o %(section)s.%(lang)s '
                '-T%(lang)s +%(section)s.dot' % vars()
                )
            print repr(cmd)
            rv = os.system(cmd)
            assert rv == 0, 'Error %d running %r' % (rv, cmd)

    ungraphed_tables = [t for t in all_tables if t not in graphed_tables]
    if ungraphed_tables:
        print "The following tables are not on any diagrams except '*': ",
        print ', '.join(ungraphed_tables)

if __name__ == '__main__':
    os.chdir('diagrams')
    filetypes = ['svg', 'ps', 'png']
    ft = []
    while 1:
        try:
            if sys.argv[1] in filetypes:
                ft.append(sys.argv[1])
                sys.argv = sys.argv[1:]
            else:
                break
        except IndexError:
            break

    if not ft:
        ft = filetypes

    main(ft)

