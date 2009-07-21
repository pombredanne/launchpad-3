# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenIDRPConfig related database classes."""

__metaclass__ = type
__all__ = [
    'OpenIDRPConfig',
    'OpenIDRPConfigSet',
    ]


import re

from sqlobject import BoolCol, ForeignKey, SQLObjectNotFound, StringCol
from storm.expr import Or
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IStore
from lp.registry.interfaces.person import PersonCreationRationale
from lp.services.openid.interfaces.openidrpconfig import (
    IOpenIDRPConfig, IOpenIDRPConfigSet)


class OpenIDRPConfig(SQLBase):
    implements(IOpenIDRPConfig)

    _table = 'OpenIDRPConfig'
    trust_root = StringCol(dbName='trust_root', notNull=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    _allowed_sreg = StringCol(dbName='allowed_sreg')
    creation_rationale = EnumCol(
        dbName='creation_rationale', notNull=True,
        schema=PersonCreationRationale,
        default=PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT)
    can_query_any_team = BoolCol(
        dbName='can_query_any_team', notNull=True, default=False)
    auto_authorize = BoolCol()

    def allowed_sreg(self):
        value = self._allowed_sreg
        if not value:
            return []
        return value.split(',')

    def _set_allowed_sreg(self, value):
        if not value:
            self._allowed_sreg = None
        self._allowed_sreg = ','.join(sorted(value))

    allowed_sreg = property(allowed_sreg, _set_allowed_sreg)


class OpenIDRPConfigSet:
    implements(IOpenIDRPConfigSet)

    url_re = re.compile("^(.+?)\/*$")

    def _normalizeTrustRoot(self, trust_root):
        """Given a trust root URL ensure it ends with exactly one '/'."""
        match = self.url_re.match(trust_root)
        assert match is not None, (
            "Attempting to normalize trust root %s failed." % trust_root)
        return "%s/" % match.group(1)

    def new(self, trust_root, displayname, description, logo=None,
            allowed_sreg=None,
            creation_rationale=
                PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT,
            can_query_any_team=False, auto_authorize=False):
        """See `IOpenIDRPConfigSet`"""
        if allowed_sreg:
            allowed_sreg = ','.join(sorted(allowed_sreg))
        else:
            allowed_sreg = None
        trust_root = self._normalizeTrustRoot(trust_root)
        return OpenIDRPConfig(
            trust_root=trust_root, displayname=displayname,
            description=description, logo=logo,
            _allowed_sreg=allowed_sreg, creation_rationale=creation_rationale,
            can_query_any_team=can_query_any_team,
            auto_authorize=auto_authorize)

    def get(self, id):
        """See `IOpenIDRPConfigSet`"""
        try:
            return OpenIDRPConfig.get(id)
        except SQLObjectNotFound:
            return None

    def getAll(self):
        """See `IOpenIDRPConfigSet`"""
        return OpenIDRPConfig.select(orderBy=['displayname', 'trust_root'])

    def getByTrustRoot(self, trust_root):
        """See `IOpenIDRPConfigSet`"""
        trust_root = self._normalizeTrustRoot(trust_root)
        # XXX: BradCrittenden 2008-09-26 bug=274774: Until the database is
        # updated to normalize existing data the query must look for
        # trust_roots that end in '/' and those that do not.
        return IStore(OpenIDRPConfig).find(
            OpenIDRPConfig,
            Or(OpenIDRPConfig.trust_root==trust_root,
               OpenIDRPConfig.trust_root==trust_root[:-1])).one()


