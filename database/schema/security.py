#!/usr/bin/python -S
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath

from collections import defaultdict
from ConfigParser import SafeConfigParser
from itertools import chain
from optparse import OptionParser
import os
import sys

import psycopg2

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import logger_options, logger, db_options
from lp.services.log.loglevels import DEBUG2
from fti import quote_identifier
import replication.helpers


# The 'read' group does not get given select permission on the following
# tables. This is to stop the ro user being given access to secrurity
# sensitive information that interactive sessions don't need.
SECURE_TABLES = [
    'public.accountpassword',
    'public.oauthnonce',
    'public.openidnonce',
    'public.openidconsumernonce',
    ]


class DbObject(object):
    def __init__(
            self, schema, name, type_, owner, arguments=None, language=None):
        self.schema = schema
        self.name = name
        self.type = type_
        self.owner = owner
        self.arguments = arguments
        self.language = language

    def __eq__(self, other):
        return self.schema == other.schema and self.name == other.name

    @property
    def fullname(self):
        fn = "%s.%s" % (
                self.schema, self.name
                )
        if self.type == 'function':
            fn = "%s(%s)" % (fn, self.arguments)
        return fn

    @property
    def seqname(self):
        if self.type != 'table':
            return ''
        return "%s.%s" % (self.schema, self.name + '_id_seq')


class DbSchema(dict):
    groups = None # List of groups defined in the db
    users = None # List of users defined in the db
    def __init__(self, con):
        super(DbSchema, self).__init__()
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
            key = '%s.%s' % (schema, name)
            self[key] = DbObject(schema, name, type_, owner)

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
                LEFT JOIN pg_catalog.pg_type r ON r.oid = p.prorettype
            WHERE
                r.typname NOT IN ('trigger', 'language_handler')
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

    @property
    def principals(self):
        return chain(self.groups, self.users)


class CursorWrapper(object):
    def __init__(self, cursor):
        self.__dict__['_cursor'] = cursor

    def execute(self, cmd, params=None):
        cmd = cmd.encode('utf8')
        if params is None:
            log.debug2('%s' % (cmd, ))
            return self.__dict__['_cursor'].execute(cmd)
        else:
            log.debug2('%s [%r]' % (cmd, params))
            return self.__dict__['_cursor'].execute(cmd, params)

    def __getattr__(self, key):
        return getattr(self.__dict__['_cursor'], key)

    def __setattr__(self, key, value):
        return setattr(self.__dict__['_cursor'], key, value)


CONFIG_DEFAULTS = {
    'groups': ''
    }


def main(options):
    # Load the config file
    config = SafeConfigParser(CONFIG_DEFAULTS)
    configfile_name = os.path.join(os.path.dirname(__file__), 'security.cfg')
    config.read([configfile_name])

    con = connect(options.dbuser)
    cur = CursorWrapper(con.cursor())

    if options.cluster:
        nodes = replication.helpers.get_nodes(con, 1)
        if nodes:
            # If we have a replicated environment, reset permissions on all
            # Nodes.
            con.close()
            for node in nodes:
                log.info("Resetting permissions on %s (%s)" % (
                    node.nickname, node.connection_string))
                reset_permissions(
                    psycopg2.connect(node.connection_string), config, options)
        else:
            log.error("--cluster requested, but not a Slony-I cluster.")
            return 1
    else:
        log.info("Resetting permissions on single database")
        reset_permissions(con, config, options)


def list_identifiers(identifiers):
    """List all of `identifiers` as SQL, quoted and separated by commas.

    :param identifiers: A sequence of SQL identifiers.
    :return: A comma-separated SQL string consisting of all identifiers
        passed in.  Each will be quoted for use in SQL.
    """
    return ', '.join([
        quote_identifier(identifier) for identifier in identifiers])


def reset_permissions(con, config, options):
    schema = DbSchema(con)
    all_users = list_identifiers(schema.users)

    cur = CursorWrapper(con.cursor())

    # Add our two automatically maintained groups
    for group in ['read', 'admin']:
        if group in schema.principals:
            log.debug("Removing managed users from %s role" % group)
            cur.execute("ALTER GROUP %s DROP USER %s" % (
                    quote_identifier(group), all_users))
        else:
            log.debug("Creating %s role" % group)
            cur.execute("CREATE GROUP %s" % quote_identifier(group))
            schema.groups.append(group)

    # Create all required groups and users.
    for section_name in config.sections():
        if section_name.lower() == 'public':
            continue

        assert not section_name.endswith('_ro'), (
            '_ro namespace is reserved (%s)' % repr(section_name))

        type_ = config.get(section_name, 'type')
        assert type_ in ['user', 'group'], 'Unknown type %s' % type_

        role_options = [
            'NOCREATEDB', 'NOCREATEROLE', 'NOCREATEUSER', 'INHERIT']
        if type_ == 'user':
            role_options.append('LOGIN')
        else:
            role_options.append('NOLOGIN')

        for username in [section_name, '%s_ro' % section_name]:
            if username in schema.principals:
                if type_ == 'group':
                    if options.revoke:
                        log.debug("Revoking membership of %s role", username)
                        cur.execute("REVOKE %s FROM %s" % (
                            quote_identifier(username), all_users))
                else:
                    # Note - we don't drop the user because it might own
                    # objects in other databases. We need to ensure they are
                    # not superusers though!
                    log.debug("Resetting role options of %s role.", username)
                    cur.execute(
                        "ALTER ROLE %s WITH %s" % (
                            quote_identifier(username),
                            ' '.join(role_options)))
            else:
                log.debug("Creating %s role.", username)
                cur.execute(
                    "CREATE ROLE %s WITH %s"
                    % (quote_identifier(username), ' '.join(role_options)))
                schema.groups.append(username)

        # Set default read-only mode for our roles.
        cur.execute(
            'ALTER ROLE %s SET default_transaction_read_only TO FALSE'
            % quote_identifier(section_name))
        cur.execute(
            'ALTER ROLE %s SET default_transaction_read_only TO TRUE'
            % quote_identifier('%s_ro' % section_name))

    # Add users to groups
    for user in config.sections():
        if config.get(user, 'type') != 'user':
            continue
        groups = [
            g.strip() for g in config.get(user, 'groups', '').split(',')
            if g.strip()
            ]
        # Read-Only users get added to Read-Only groups.
        if user.endswith('_ro'):
            groups = ['%s_ro' % group for group in groups]
        if groups:
            log.debug("Adding %s to %s roles", user, ', '.join(groups))
            for group in groups:
                cur.execute(r"""ALTER GROUP %s ADD USER %s""" % (
                    quote_identifier(group), quote_identifier(user)))
        else:
            log.debug("%s not in any roles", user)

    # Change ownership of all objects to OWNER
    for obj in schema.values():
        if obj.type in ("function", "sequence"):
            pass # Can't change ownership of functions or sequences
        else:
            if obj.owner != options.owner:
                log.info("Resetting ownership of %s", obj.fullname)
                cur.execute("ALTER TABLE %s OWNER TO %s" % (
                    obj.fullname, quote_identifier(options.owner)))

    # Revoke all privs from known groups. Don't revoke anything for
    # users or groups not defined in our security.cfg.
    revocations = defaultdict(list)
    # Gather all revocations.
    for section_name in config.sections():
        for obj in schema.values():
            if obj.type == 'function':
                t = 'FUNCTION'
            else:
                t = 'TABLE'

            item = "%s %s" % (t, obj.fullname)

            roles = [section_name]
            if section_name != 'public':
                roles.append(section_name + '_ro')

            revocations[item] += roles

            if schema.has_key(obj.seqname):
                revocations["SEQUENCE %s" % obj.seqname] += roles

    # Now batch up and execute all revocations.
    if options.revoke:
        for item, roles in revocations.iteritems():
            if roles:
                log.debug("Revoking permissions on %s", item)
                cur.execute(
                    "REVOKE ALL ON %s FROM %s"
                    % (item, list_identifiers(roles)))
    else:
        log.info("Not revoking permissions on database objects")

    # Set of all tables we have granted permissions on. After we have assigned
    # permissions, we can use this to determine what tables have been
    # forgotten about.
    found = set()

    # Set permissions as per config file

    functions = set()
    tables = set()

    for username in config.sections():
        for obj_name, perm in config.items(username):
            if '.' not in obj_name:
                continue
            if obj_name not in schema.keys():
                log.warn('Bad object name %r', obj_name)
                continue
            obj = schema[obj_name]

            found.add(obj)

            perm = perm.strip()
            if not perm:
                # No perm means no rights. We can't grant no rights, so skip.
                continue

            who = quote_identifier(username)
            if username == 'public':
                who_ro = who
            else:
                who_ro = quote_identifier('%s_ro' % username)

            log.debug(
                "Granting %s on %s to %s", perm, obj.fullname, who)
            if obj.type == 'function':
                functions.add(obj.fullname)
                cur.execute(
                    'GRANT %s ON FUNCTION %s TO %s'
                    % (perm, obj.fullname, who))
                cur.execute(
                    'GRANT EXECUTE ON FUNCTION %s TO GROUP %s'
                    % (obj.fullname, who_ro))
            else:
                tables.add(obj.fullname)
                cur.execute(
                    'GRANT %s ON TABLE %s TO %s'
                    % (perm, obj.fullname, who))
                cur.execute(
                    'GRANT SELECT ON TABLE %s TO %s'
                    % (obj.fullname, who_ro))
                if schema.has_key(obj.seqname):
                    if 'INSERT' in perm:
                        seqperm = 'USAGE'
                    elif 'SELECT' in perm:
                        seqperm = 'SELECT'
                    log.debug(
                        "Granting %s on %s to %s", seqperm, obj.seqname, who)
                    cur.execute(
                        'GRANT %s ON %s TO %s'
                        % (seqperm, obj.seqname, who))
                    if obj.fullname not in SECURE_TABLES:
                        cur.execute(
                            'GRANT SELECT ON %s TO GROUP read'
                            % obj.seqname)
                    cur.execute(
                        'GRANT ALL ON %s TO GROUP admin'
                        % obj.seqname)
                    cur.execute(
                        'GRANT SELECT ON %s TO %s'
                        % (obj.seqname, who_ro))

    # A few groups get special rights to every function or table.  Batch
    # the schema manipulations to save time.
    log.debug(
        "Granting permissions to %d functions to magic roles",
        len(functions))
    if functions:
        functions_text = ', '.join(functions)
        cur.execute(
            "GRANT EXECUTE ON FUNCTION %s TO GROUP read" % functions_text)
        cur.execute(
            "GRANT ALL ON FUNCTION %s TO GROUP admin" % functions_text)
    log.debug(
        "Granting permissions to %d tables to admin role",
        len(tables))
    if tables:
        tables_text = ', '.join(tables)
        cur.execute("GRANT ALL ON TABLE %s TO GROUP admin" % tables_text)
    nonsecure_tables = tables - set(SECURE_TABLES)
    log.debug(
        "Granting permissions to %d nonsecure tables to read role",
        len(nonsecure_tables))
    if nonsecure_tables:
        nonsecure_tables_text = ', '.join(nonsecure_tables)
        cur.execute(
            "GRANT SELECT ON TABLE %s TO GROUP read" % nonsecure_tables_text)

    # Set permissions on public schemas
    public_schemas = [
        s.strip() for s in config.get('DEFAULT','public_schemas').split(',')
        if s.strip()
        ]
    log.debug("Granting access to %d public schemas", len(public_schemas))
    for schema_name in public_schemas:
        cur.execute("GRANT USAGE ON SCHEMA %s TO PUBLIC" % (
            quote_identifier(schema_name),
            ))
    for obj in schema.values():
        if obj.schema not in public_schemas:
            continue
        found.add(obj)
        if obj.type == 'function':
            cur.execute('GRANT EXECUTE ON FUNCTION %s TO PUBLIC' %
                        obj.fullname)
        else:
            cur.execute('GRANT SELECT ON TABLE %s TO PUBLIC' % obj.fullname)

    # Raise an error if we have database objects lying around that have not
    # had permissions assigned.
    forgotten = set()
    for obj in schema.values():
        if obj not in found:
            forgotten.add(obj)
    forgotten = [obj.fullname for obj in forgotten
        if obj.type in ['table','function','view']]
    if forgotten:
        log.warn('No permissions specified for %r', forgotten)

    if options.dryrun:
        log.info("Dry run - rolling back changes")
        con.rollback()
    else:
        log.debug("Committing changes")
        con.commit()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        "-n", "--dry-run", dest="dryrun", default=False,
        action="store_true", help="Don't commit any changes")
    parser.add_option(
        "--revoke", dest="revoke", default=True, action="store_true",
        help="Revoke privileges as well as add them")
    parser.add_option(
        "--no-revoke", dest="revoke", default=True, action="store_false",
        help="Do not revoke any privileges. Just add.")
    parser.add_option(
        "-o", "--owner", dest="owner", default="postgres",
        help="Owner of PostgreSQL objects")
    parser.add_option(
        "-c", "--cluster", dest="cluster", default=False,
        action="store_true",
        help="Rebuild permissions on all nodes in the Slony-I cluster.")
    db_options(parser)
    logger_options(parser)

    (options, args) = parser.parse_args()

    log = logger(options)

    sys.exit(main(options))
