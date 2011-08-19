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
SECURE_TABLES = set((
    'public.accountpassword',
    'public.accountpassword_id_seq',
    'public.oauthnonce',
    'public.oauthnonce_id_seq',
    'public.openidnonce',
    'public.openidnonce_id_seq',
    'public.openidconsumernonce',
    'public.openidconsumernonce_id_seq',
    ))

POSTGRES_ACL_MAP = {
    'r': 'SELECT',
    'w': 'UPDATE',
    'a': 'INSERT',
    'd': 'DELETE',
    'D': 'TRUNCATE',
    'x': 'REFERENCES',
    't': 'TRIGGER',
    'X': 'EXECUTE',
    'U': 'USAGE',
    'C': 'CREATE',
    'c': 'CONNECT',
    'T': 'TEMPORARY',
    }


def _split_postgres_aclitem(aclitem):
    """Split a PostgreSQL aclitem textual representation.

    Returns the (grantee, privs, grantor), unquoted and separated.
    """
    components = {'grantee': '', 'privs': '', 'grantor': ''}
    current_component = 'grantee'
    inside_quoted = False
    maybe_finished_quoted = False
    for char in aclitem:
        if inside_quoted:
            if maybe_finished_quoted:
                maybe_finished_quoted = False
                if char == '"':
                    components[current_component] += '"'
                    continue
                else:
                    inside_quoted = False
            elif char == '"':
                maybe_finished_quoted = True
                continue
        # inside_quoted may have just been made False, so no else block
        # for you.
        if not inside_quoted:
            if char == '"':
                inside_quoted = True
                continue
            elif char == '=':
                current_component = 'privs'
                continue
            elif char == '/':
                current_component = 'grantor'
                continue
        components[current_component] += char
    return components['grantee'], components['privs'], components['grantor']


def parse_postgres_acl(acl):
    """Parse a PostgreSQL object ACL into a dict with permission names.

    The dict is of the form {user: {permission: grant option}}.
    """
    parsed = {}
    if acl is None:
        return parsed
    for entry in acl:
        grantee, privs, grantor = _split_postgres_aclitem(entry)
        if grantee == '':
            grantee = 'public'
        parsed_privs = []
        for priv in privs:
            if priv == '*':
                parsed_privs[-1] = (parsed_privs[-1][0], True)
                continue
            parsed_privs.append((POSTGRES_ACL_MAP[priv], False))
        parsed[grantee] = dict(parsed_privs)
    return parsed


class DbObject(object):

    def __init__(
        self, schema, name, type_, owner, acl, arguments=None, language=None):
        self.schema = schema
        self.name = name
        self.type = type_
        self.owner = owner
        self.acl = acl
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
                u.usename as "Owner",
                c.relacl::text[] as "ACL"
            FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_user u ON u.usesysid = c.relowner
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r','v','S','')
                AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                AND pg_catalog.pg_table_is_visible(c.oid)
            ORDER BY 1,2
            ''')
        for schema, name, type_, owner, acl in cur.fetchall():
            key = '%s.%s' % (schema, name)
            self[key] = DbObject(
                schema, name, type_, owner, parse_postgres_acl(acl))

        cur.execute(r"""
            SELECT
                n.nspname as "schema",
                p.proname as "name",
                pg_catalog.oidvectortypes(p.proargtypes) as "Argument types",
                u.usename as "owner",
                p.proacl::text[] as "acl",
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
        for schema, name, arguments, owner, acl, language in cur.fetchall():
            self['%s.%s(%s)' % (schema, name, arguments)] = DbObject(
                    schema, name, 'function', owner, parse_postgres_acl(acl),
                    arguments, language)
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
            log.debug3('%s' % (cmd, ))
            return self.__dict__['_cursor'].execute(cmd)
        else:
            log.debug3('%s [%r]' % (cmd, params))
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

    con = connect(options.dbuser)

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

    def add(self, permission, entity, principal):
        """Add a permission.

        Add all privileges you want to grant or revoke first, then use
        `grant` or `revoke` to process them in bulk.

        :param permission: A permission: SELECT, INSERT, EXECUTE, etc.
        :param entity: Table, function, or sequence on which to grant
            or revoke a privilege.
        :param principal: User or group to which the privilege should
            apply.
        """
        self.permissions[permission].setdefault(principal, set()).add(entity)

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
            for principal, entities in parties.iteritems():
                result.append(
                    (permission, ", ".join(entities), principal))
        return result

    def countPermissions(self):
        """Count the number of different permissions."""
        return len(self.permissions)

    def countEntities(self):
        """Count the number of different entities."""
        entities = set()
        for entities_and_entities in self.permissions.itervalues():
            for extra_entities in entities_and_entities.itervalues():
                entities.update(extra_entities)
        return len(entities)

    def countPrincipals(self):
        """Count the number of different principals."""
        return len(set(sum([
            principals.keys()
            for principals in self.permissions.itervalues()], [])))

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


def alter_permissions(cur, which, revoke=False):
    """Efficiently apply a set of permission changes.

    :param cur: a database cursor
    :param which: an iterable of (object, role, permissions)
    :param revoke: whether to revoke or grant permissions
    """
    gatherers = {
        'table': PermissionGatherer("TABLE"),
        'function': PermissionGatherer("FUNCTION"),
        'sequence': PermissionGatherer("SEQUENCE"),
        }

    for obj, role, perms in which:
        gatherers.get(obj.type, gatherers['table']).add(
            ', '.join(perms), obj.fullname, quote_identifier(role))

    for gatherer in gatherers.values():
        if revoke:
            gatherer.revoke(cur)
        else:
            gatherer.grant(cur)


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
                        log.debug2("Revoking membership of %s role", username)
                        cur.execute("REVOKE %s FROM %s" % (
                            quote_identifier(username), all_users))
                else:
                    # Note - we don't drop the user because it might own
                    # objects in other databases. We need to ensure they are
                    # not superusers though!
                    log.debug2("Resetting role options of %s role.", username)
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
            log.debug2("Adding %s to %s roles", user, ', '.join(groups))
            for group in groups:
                cur.execute(r"""ALTER GROUP %s ADD USER %s""" % (
                    quote_identifier(group), quote_identifier(user)))
        else:
            log.debug2("%s not in any roles", user)

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
    else:
        log.info("Not resetting ownership of database objects")

    managed_roles = set(['read', 'admin'])
    for section_name in config.sections():
        managed_roles.add(section_name)
        if section_name != 'public':
            managed_roles.add(section_name + "_ro")

    # Set of all tables we have granted permissions on. After we have assigned
    # permissions, we can use this to determine what tables have been
    # forgotten about.
    found = set()

    # Set permissions as per config file
    desired_permissions = defaultdict(lambda: defaultdict(set))

    valid_objs = set(schema.iterkeys())

    # Any object with permissions granted is accessible to the 'read'
    # role. Some (eg. the lp_* replicated tables and internal or trigger
    # functions) aren't readable.
    granted_objs = set()

    for username in config.sections():
        who = username
        if username == 'public':
            who_ro = who
        else:
            who_ro = '%s_ro' % username

        for obj_name, perm in config.items(username):
            if '.' not in obj_name:
                continue
            if obj_name not in valid_objs:
                log.warn('Bad object name %r', obj_name)
                continue
            obj = schema[obj_name]

            found.add(obj)

            perm = perm.strip()
            if not perm:
                # No perm means no rights. We can't grant no rights, so skip.
                continue

            granted_objs.add(obj)

            if obj.type == 'function':
                desired_permissions[obj][who].update(perm.split(', '))
                if who_ro:
                    desired_permissions[obj][who_ro].add("EXECUTE")
            else:
                desired_permissions[obj][who].update(perm.split(', '))
                if who_ro:
                    desired_permissions[obj][who_ro].add("SELECT")
                if obj.seqname in valid_objs:
                    seq = schema[obj.seqname]
                    granted_objs.add(seq)
                    if 'INSERT' in perm:
                        seqperm = 'USAGE'
                    elif 'SELECT' in perm:
                        seqperm = 'SELECT'
                    else:
                        seqperm = None
                    if seqperm:
                        desired_permissions[seq][who].add(seqperm)
                    desired_permissions[seq][who_ro].add("SELECT")

    # read gets read access to all non-secure objects that we've granted
    # anybody access to.
    for obj in granted_objs:
        if obj.type == 'function':
            desired_permissions[obj]['read'].add("EXECUTE")
        else:
            if obj.fullname not in SECURE_TABLES:
                desired_permissions[obj]['read'].add("SELECT")

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
            desired_permissions[obj]['public'].add('EXECUTE')
        else:
            desired_permissions[obj]['public'].add('SELECT')

    # For every object in the DB, ensure that the privileges held by our
    # managed roles match our expectations. If not, store the delta
    # to be applied later.
    # Also grants/revokes access by the admin role, which isn't a
    # traditionally managed role.
    unmanaged_roles = set()
    required_grants = []
    required_revokes = []
    for obj in schema.values():
        # We only care about roles that are in either the desired or
        # existing ACL, and are also our managed roles. But skip admin,
        # because it's done at the end.
        interesting_roles = set(desired_permissions[obj]).union(obj.acl)
        unmanaged_roles.update(interesting_roles.difference(managed_roles))
        for role in managed_roles.intersection(interesting_roles):
            if role == 'admin':
                continue
            new = desired_permissions[obj][role]
            old_privs = obj.acl.get(role, {})
            old = set(old_privs)
            if any(old_privs.itervalues()):
                log.warning("%s has grant option on %s", role, obj.fullname)
            if new == old:
                continue
            missing = new.difference(old)
            extra = old.difference(new)
            if missing:
                required_grants.append((obj, role, missing))
            if extra:
                required_revokes.append((obj, role, extra))

        # admin get all privileges on anything with privileges granted
        # in security.cfg. We don't have a mapping from ALL to real
        # privileges for each object type, so we just grant or revoke ALL
        # each time.
        if obj in granted_objs:
            required_grants.append((obj, "admin", ("ALL",)))
        else:
            if "admin" in obj.acl:
                required_revokes.append((obj, "admin", ("ALL",)))

    log.debug("Unmanaged roles on managed objects: %r", list(unmanaged_roles))

    alter_permissions(cur, required_grants)
    if options.revoke:
        alter_permissions(cur, required_revokes, revoke=True)

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
