# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import psycopg, sys, os
from ConfigParser import SafeConfigParser
from fti import quote_identifier

DEBUG = False
OWNER = 'postgres'

class DbObject(object):
    def __init__(
            self, schema, name, type_, owner, arguments=None, language=None
            ):
        self.schema = schema
        self.name = name
        self.type = type_
        self.owner = owner
        self.arguments = arguments
        self.language = language

    def fullname(self):
        fn = "%s.%s" % (
                quote_identifier(self.schema), quote_identifier(self.name)
                )
        if self.type == 'function':
            fn = "%s(%s)" % (fn, self.arguments)
        return fn
    fullname = property(fullname)

    def seqname(self):
        if self.type != 'table':
            return ''
        return "%s.%s" % (self.schema, self.name + '_id_seq')
    seqname = property(seqname)



class DbSchema(dict):
    groups = None # List of groups defined in the db
    users = None # List of users defined in the db
    def __init__(self, con):
        cur = con.cursor()
        cur.execute('''
            SELECT 
                n.nspname as "Schema",
                c.relname as "Name",
                CASE c.relkind
                    WHEN 'r' THEN 'table'
                    WHEN 'v' THEN 'view'
                    WHEN 'i' THEN 'index'
                    WHEN 'S' THEN 'sequence'
                    WHEN 's' THEN 'special'
                END as "Type",
                u.usename as "Owner"
            FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_user u ON u.usesysid = c.relowner
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r','v','S','')
                AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                AND pg_catalog.pg_table_is_visible(c.oid)
            ORDER BY 1,2
            ''')
        for schema, name, type_, owner in cur.fetchall():
            self['%s.%s' % (schema,name)] = DbObject(schema, name, type_, owner)

        cur.execute(r"""
            SELECT
                n.nspname as "schema",
                p.proname as "name",
                pg_catalog.oidvectortypes(p.proargtypes) as "Argument types",
                u.usename as "owner",
                l.lanname as "language"
            FROM pg_catalog.pg_proc p
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                LEFT JOIN pg_catalog.pg_language l ON l.oid = p.prolang
                LEFT JOIN pg_catalog.pg_user u ON u.usesysid = p.proowner
            WHERE p.prorettype <> 'pg_catalog.cstring'::pg_catalog.regtype
                AND p.proargtypes[0] <> 'pg_catalog.cstring'::pg_catalog.regtype
                AND NOT p.proisagg
                AND pg_catalog.pg_function_is_visible(p.oid)
                AND n.nspname <> 'pg_catalog'
                """)
        for schema, name, arguments, owner, language in cur.fetchall():
            self['%s.%s(%s)' % (schema, name, arguments)] = DbObject(
                    schema, name, 'function', owner, arguments, language
                    )
        # Pull a list of groups
        cur.execute("SELECT groname FROM pg_group")
        self.groups = [r[0] for r in cur.fetchall()]

        # Pull a list of users
        cur.execute("SELECT usename FROM pg_user")
        self.users = [r[0] for r in cur.fetchall()]

        # Combined list
        self.principals = self.groups + self.users


class CursorWrapper(object):
    def __init__(self, cursor):
        self.__dict__['_cursor'] = cursor

    def execute(self, cmd, params=None):
        cmd = cmd.encode('utf8')
        if DEBUG:
            print >> sys.stderr, '%s [%r]' % (cmd, params)
        if params is None:
            return self.__dict__['_cursor'].execute(cmd)
        else:
            return self.__dict__['_cursor'].execute(cmd, params)

    def __getattr__(self, key):
        return getattr(self.__dict__['_cursor'], key)

    def __setattr__(self, key, value):
        return setattr(self.__dict__['_cursor'], key, value)

CONFIG_DEFAULTS = {
    'groups': ''
    }

def main():
    # Load the config file
    config = SafeConfigParser(CONFIG_DEFAULTS)
    config.read(['security.cfg'])

    con = psycopg.connect('dbname=%s' % os.environ['LP_DBNAME'])
    cur = CursorWrapper(con.cursor())
    schema = DbSchema(con)

    # Create all required groups and users.
    for section_name in config.sections():
        if section_name in schema.principals:
            continue
        if section_name.lower() == 'public':
            continue
        type_ = config.get(section_name, 'type')
        if type_ == 'group':
            cur.execute("CREATE GROUP %s" % quote_identifier(section_name))
            schema.groups.append(section_name)
            schema.principals.append(section_name)
        elif type_ == 'user':
            cur.execute("CREATE USER %s" % quote_identifier(section_name))
            schema.users.append(section_name)
            schema.principals.append(section_name)
        else:
            assert 0, "Unknown type %r for %r" % (type_, section_name)

    # Add users to groups
    for user in config.sections():
        if config.get(user, 'type') != 'user':
            continue
        groups = [
            g.strip() for g in config.get(user, 'groups', '').split(',')
            if g.strip()
            ]
        for group in groups:
            cur.execute(r"""ALTER GROUP %s ADD USER %s""" % (
                quote_identifier(group), quote_identifier(user)
                ))
            
    
    # Change ownership of all objects to OWNER
    for obj in schema.values():
        if obj.type == "function":
            pass # Can't change ownership of functions
        else:
            cur.execute("ALTER TABLE %s OWNER TO %s" % (
                obj.fullname, quote_identifier(OWNER)
                ))

    # Revoke all privs
    for section_name in config.sections():
        for obj in schema.values():
            if obj.type == 'function':
                t = 'FUNCTION'
            else:
                t = 'TABLE'

            if section_name in schema.groups:
                g = 'GROUP '
            else:
                g = ''

            cur.execute('REVOKE ALL ON %s %s FROM %s%s' % (
                t, obj.fullname, g, quote_identifier(section_name)
                ))
            if schema.has_key(obj.seqname):
                cur.execute('REVOKE ALL ON %s FROM %s%s' % (
                    obj.seqname, g, quote_identifier(section_name),
                    ))

    # Set permissions as per config file
    for username in config.sections():
        for obj_name, perm in config.items(username):
            if '.' not in obj_name:
                continue
            assert obj_name in schema.keys(), 'Bad object name %r'%(obj_name,)
            obj = schema[obj_name]
            if obj.type == 'function':
                t = 'FUNCTION'
            else:
                t = 'TABLE'
            if username in schema.groups:
                g = 'GROUP '
            else:
                g = ''
            cur.execute('GRANT %s ON %s %s TO %s%s' % (
                perm, t, obj.fullname, g, quote_identifier(username)
                ))
            if schema.has_key(obj.seqname):
                cur.execute('GRANT %s ON %s TO %s%s' % (
                    perm, obj.seqname, g, quote_identifier(username)
                    ))

    # Set permissions on public schemas
    public_schemas = [
        s.strip() for s in config.get('DEFAULT','public_schemas').split(',')
        if s.strip()
        ]
    for schema_name in public_schemas:
        cur.execute("GRANT USAGE ON SCHEMA %s TO PUBLIC" % (
            quote_identifier(schema_name),
            ))
    for obj in schema.values():
        if obj.schema not in public_schemas:
            continue
        if obj.type == 'function':
            cur.execute('GRANT EXECUTE ON FUNCTION %s TO PUBLIC' % obj.fullname)
        else:
            cur.execute('GRANT SELECT ON TABLE %s TO PUBLIC' % obj.fullname)

    con.commit()

if __name__ == '__main__':
    main()

