# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'SourcePackageName',
    'SourcePackageNameSet',
    'getSourcePackageDescriptions',
    ]

from sqlobject import (
    SQLMultipleJoin,
    SQLObjectNotFound,
    StringCol,
    )
from zope.interface import implements

from canonical.database.sqlbase import (
    cursor,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.helpers import ensure_unicode
from lp.app.errors import NotFoundError
from lp.app.validators.name import valid_name
from lp.registry.errors import (
    InvalidName,
    NoSuchSourcePackageName,
    )
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageName,
    ISourcePackageNameSet,
    )


class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True, unique=True,
        alternateID=True)

    potemplates = SQLMultipleJoin(
        'POTemplate', joinColumn='sourcepackagename')
    packagings = SQLMultipleJoin(
        'Packaging', joinColumn='sourcepackagename', orderBy='Packaging.id')

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)

    def ensure(klass, name):
        try:
            return klass.byName(name)
        except SQLObjectNotFound:
            return klass(name=name)
    ensure = classmethod(ensure)


class SourcePackageNameSet:
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        name = ensure_unicode(name)
        try:
            return SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise NoSuchSourcePackageName(name)

    def get(self, sourcepackagenameid):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.get(sourcepackagenameid)
        except SQLObjectNotFound:
            raise NotFoundError(sourcepackagenameid)

    def getAll(self):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        return SourcePackageName.select()

    def findByName(self, name):
        """Find sourcepackagenames by its name or part of it."""
        query = "name ILIKE '%%' || %s || '%%'" % quote_like(name)
        return SourcePackageName.select(query)

    def queryByName(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        return SourcePackageName.selectOneBy(name=name)

    def new(self, name):
        if not valid_name(name):
            raise InvalidName(
                "%s is not a valid name for a source package." % name)
        return SourcePackageName(name=name)

    def getOrCreateByName(self, name):
        try:
            return self[name]
        except NotFoundError:
            return self.new(name)


def getSourcePackageDescriptions(
    results, use_names=False, max_title_length=50):
    """Return a dictionary with descriptions keyed on source package names.

    Takes an ISelectResults of a *PackageName query. The use_names
    flag is a hack that allows this method to work for the
    BinaryAndSourcePackageName view, which lacks IDs.

    WARNING: this function assumes that there is little overlap and much
    coherence in how package names are used, in particular across
    distributions if derivation is implemented. IOW, it does not make a
    promise to provide The Correct Description, but a pretty good guess
    at what the description should be.
    """
    # XXX: kiko, 2007-01-17:
    # Use_names could be removed if we instead added IDs to the
    # BinaryAndSourcePackageName view, but we'd still need to find
    # out how to specify the attribute, since it would be
    # sourcepackagename_id and binarypackagename_id depending on
    # whether the row represented one or both of those cases.
    if use_names:
        clause = ("SourcePackageName.name in %s" %
                 sqlvalues([pn.name for pn in results]))
    else:
        clause = ("SourcePackageName.id in %s" %
                 sqlvalues([spn.id for spn in results]))

    cur = cursor()
    cur.execute("""SELECT DISTINCT BinaryPackageName.name,
                          SourcePackageName.name
                     FROM BinaryPackageRelease, SourcePackageName,
                          BinaryPackageBuild, SourcePackageRelease,
                          BinaryPackageName
                    WHERE
                       BinaryPackageName.id =
                           BinaryPackageRelease.binarypackagename AND
                       BinaryPackageRelease.build = BinaryPackageBuild.id AND
                       SourcePackageRelease.sourcepackagename =
                           SourcePackageName.id AND
                       BinaryPackageBuild.source_package_release =
                           SourcePackageRelease.id AND
                       %s
                   ORDER BY BinaryPackageName.name,
                            SourcePackageName.name"""
                    % clause)

    descriptions = {}
    for binarypackagename, sourcepackagename in cur.fetchall():
        if not sourcepackagename in descriptions:
            descriptions[sourcepackagename] = (
                "Source of: %s" % binarypackagename)
        else:
            if len(descriptions[sourcepackagename]) > max_title_length:
                description = "..."
            else:
                description = ", %s" % binarypackagename
            descriptions[sourcepackagename] += description
    return descriptions
