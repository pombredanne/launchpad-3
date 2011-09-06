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
        fn = "%s.%s" % (self.schema, self.name)
        if self.type == 'function':
            fn = "%s(%s)" % (fn, self.arguments)
        return fn

    @property
    def seqname(self):
        if self.type != 'table':
            return ''
        return "%s.%s" % (self.schema, self.name + '_id_seq')


class DbSchema(dict):
    groups = None  # List of groups defined in the db
    users = None  # List of users defined in the db

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
                    schema, name, 'function', owner, arguments, language)
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
    'groups': '',
    }


def main(options):
    # Load the config file
    config = SafeConfigParser(CONFIG_DEFAULTS)
    configfile_name = os.path.join(os.path.dirname(__file__), 'security.cfg')
    config.read([configfile_name])

    con = connect()

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
            return 0
        log.warning("--cluster requested, but not a Slony-I cluster.")
    log.info("Resetting permissions on single database")
    reset_permissions(con, config, options)
    return 0


def list_identifiers(identifiers):
    """List all of `identifiers` as SQL, quoted and separated by commas.

    :param identifiers: A sequence of SQL identifiers.
    :return: A comma-separated SQL string consisting of all identifiers
        passed in.  Each will be quoted for use in SQL.
    """
    return ', '.join([
        quote_identifier(identifier) for identifier in identifiers])


class PermissionGatherer:
    """Gather permissions for bulk granting or revocation.

    Processing such statements in bulk (with multiple users, tables,
    or permissions in one statement) is faster than issuing very large
    numbers of individual statements.
    """

    def __init__(self, entity_keyword):
        """Gather for SQL entities of one kind (TABLE, FUNCTION, SEQUENCE).

        :param entity_keyword: The SQL keyword for the kind of entity
            that permissions will be gathered for.
        """
        self.entity_keyword = entity_keyword
        self.permissions = defaultdict(dict)

    def add(self, permission, entity, principal, is_group=False):
        """Add a permission.

        Add all privileges you want to grant or revoke first, then use
        `grant` or `revoke` to process them in bulk.

        :param permission: A permission: SELECT, INSERT, EXECUTE, etc.
        :param entity: Table, function, or sequence on which to grant
            or revoke a privilege.
        :param principal: User or group to which the privilege should
            apply.
        :param is_group: Is `principal` a group?
        """
        if is_group:
            full_principal = "GROUP " + principal
        else:
            full_principal = principal
        self.permissions[permission].setdefault(entity, set()).add(
            full_principal)

    def tabulate(self):
        """Group privileges into single-statement work items.

        Each entry returned by this method represents a batch of
        privileges that can be granted or revoked in a single SQL
        statement.

        :return: A sequence of tuples of strings: permission(s) to
            grant/revoke, entity or entities to act on, and principal(s)
            to grant or revoke for.  Each is a string.
        """
        result = []
        for permission, parties in self.permissions.iteritems():
            for entity, principals in parties.iteritems():
                result.append(
                    (permission, entity, ", ".join(principals)))
        return result

    def countPermissions(self):
        """Count the number of different permissions."""
        return len(self.permissions)

    def countEntities(self):
        """Count the number of different entities."""
        return len(set(sum([
            entities.keys()
            for entities in self.permissions.itervalues()], [])))

    def countPrincipals(self):
        """Count the number of different principals."""
        principals = set()
        for entities_and_principals in self.permissions.itervalues():
            for extra_principals in entities_and_principals.itervalues():
                principals.update(extra_principals)
        return len(principals)

    def grant(self, cur):
        """Grant all gathered permissions.

        :param cur: A cursor to operate on.
        """
        log.debug(
            "Granting %d permission(s) on %d %s(s) for %d user(s)/group(s).",
            self.countPermissions(),
            self.countEntities(),
            self.entity_keyword,
            self.countPrincipals())
        grant_count = 0
        for permissions, entities, principals in self.tabulate():
            grant = "GRANT %s ON %s %s TO %s" % (
                permissions, self.entity_keyword, entities, principals)
            log.debug2(grant)
            cur.execute(grant)
            grant_count += 1
        log.debug("Issued %d GRANT statement(s).", grant_count)

    def revoke(self, cur):
        """Revoke all gathered permissions.

        :param cur: A cursor to operate on.
        """
        log.debug(
            "Revoking %d permission(s) on %d %s(s) for %d user(s)/group(s).",
            self.countPermissions(),
            self.countEntities(),
            self.entity_keyword,
            self.countPrincipals())
        revoke_count = 0
        for permissions, entities, principals in self.tabulate():
            revoke = "REVOKE %s ON %s %s FROM %s" % (
                permissions, self.entity_keyword, entities, principals)
            log.debug2(revoke)
            cur.execute(revoke)
            revoke_count += 1
        log.debug("Issued %d REVOKE statement(s).", revoke_count)


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
            if g.strip()]
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

    if options.revoke:
        # Change ownership of all objects to OWNER.
        # We skip this in --no-revoke mode as ownership changes may
        # block on a live system.
        for obj in schema.values():
            if obj.type in ("function", "sequence"):
                pass  # Can't change ownership of functions or sequences
            else:
                if obj.owner != options.owner:
                    log.info("Resetting ownership of %s", obj.fullname)
                    cur.execute("ALTER TABLE %s OWNER TO %s" % (
                        obj.fullname, quote_identifier(options.owner)))

        # Revoke all privs from known groups. Don't revoke anything for
        # users or groups not defined in our security.cfg.
        table_revocations = PermissionGatherer("TABLE")
        function_revocations = PermissionGatherer("FUNCTION")
        sequence_revocations = PermissionGatherer("SEQUENCE")

        # Gather all revocations.
        for section_name in config.sections():
            role = quote_identifier(section_name)
            if section_name == 'public':
                ro_role = None
            else:
                ro_role = quote_identifier(section_name + "_ro")

            for obj in schema.values():
                if obj.type == 'function':
                    gatherer = function_revocations
                else:
                    gatherer = table_revocations

                gatherer.add("ALL", obj.fullname, role)

                if obj.seqname in schema:
                    sequence_revocations.add("ALL", obj.seqname, role)
                    if ro_role is not None:
                        sequence_revocations.add("ALL", obj.seqname, ro_role)

        table_revocations.revoke(cur)
        function_revocations.revoke(cur)
        sequence_revocations.revoke(cur)
    else:
        log.info("Not resetting ownership of database objects")
        log.info("Not revoking permissions on database objects")

    # Set of all tables we have granted permissions on. After we have assigned
    # permissions, we can use this to determine what tables have been
    # forgotten about.
    found = set()

    # Set permissions as per config file

    table_permissions = PermissionGatherer("TABLE")
    function_permissions = PermissionGatherer("FUNCTION")
    sequence_permissions = PermissionGatherer("SEQUENCE")

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
                function_permissions.add(perm, obj.fullname, who)
                function_permissions.add("EXECUTE", obj.fullname, who_ro)
                function_permissions.add(
                    "EXECUTE", obj.fullname, "read", is_group=True)
                function_permissions.add(
                    "ALL", obj.fullname, "admin", is_group=True)
            else:
                table_permissions.add(
                    "ALL", obj.fullname, "admin", is_group=True)
                table_permissions.add(perm, obj.fullname, who)
                table_permissions.add("SELECT", obj.fullname, who_ro)
                is_secure = (obj.fullname in SECURE_TABLES)
                if not is_secure:
                    table_permissions.add(
                        "SELECT", obj.fullname, "read", is_group=True)
                if obj.seqname in schema:
                    if 'INSERT' in perm:
                        seqperm = 'USAGE'
                    elif 'SELECT' in perm:
                        seqperm = 'SELECT'
                    sequence_permissions.add(seqperm, obj.seqname, who)
                    if not is_secure:
                        sequence_permissions.add(
                            "SELECT", obj.seqname, "read", is_group=True)
                    sequence_permissions.add("SELECT", obj.seqname, who_ro)
                    sequence_permissions.add(
                        "ALL", obj.seqname, "admin", is_group=True)

    function_permissions.grant(cur)
    table_permissions.grant(cur)
    sequence_permissions.grant(cur)

    # Set permissions on public schemas
    public_schemas = [
        s.strip() for s in config.get('DEFAULT', 'public_schemas').split(',')
        if s.strip()]
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
        if obj.type in ['table', 'function', 'view']]
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
