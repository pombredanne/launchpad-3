# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os

from sets import Set
from datetime import datetime

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import DateTimeCol, ForeignKey, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

import canonical.sourcerer.deb.version

from canonical.database.sqlbase import SQLBase, quote
from canonical.lp.dbschema import BugSeverity, BugTaskStatus
from canonical.lp.dbschema import RosettaImportStatus, RevisionControlSystems
from canonical.rosetta.tar import string_to_tarfile, examine_tarfile
from canonical.rosetta.pofile import POSyntaxError, POInvalidInputError

from canonical.launchpad.database.sourcesource import SourceSource
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.pofile import POTemplate
from canonical.launchpad.interfaces import IProduct, IProductSet

class Product(SQLBase):
    """A Product."""

    implements(IProduct)

    _table = 'Product'

    #
    # db field names
    #
    project = ForeignKey(foreignKey="Project", dbName="project",
                         notNull=False, default=None)

    owner = ForeignKey(foreignKey="Person", dbName="owner",
                       notNull=True)

    name = StringCol(dbName='name', notNull=True, alternateID=True,
                     unique=True)

    displayname = StringCol(dbName='displayname', notNull=True)

    title = StringCol(dbName='title', notNull=True)

    shortdesc = StringCol(dbName='shortdesc', notNull=True)

    description = StringCol(dbName='description', notNull=True)

    datecreated = DateTimeCol(dbName='datecreated', notNull=True,
                              default=datetime.utcnow())

    homepageurl = StringCol(dbName='homepageurl', notNull=False,
            default=None)

    screenshotsurl = StringCol(dbName='screenshotsurl', notNull=False,
            default=None)

    wikiurl =  StringCol(dbName='wikiurl', notNull=False, default=None)

    programminglang = StringCol(dbName='programminglang', notNull=False,
            default=None)

    downloadurl = StringCol(dbName='downloadurl', notNull=False, default=None)

    lastdoap = StringCol(dbName='lastdoap', notNull=False, default=None)

    active = BoolCol(dbName='active', notNull=True, default=True)

    reviewed = BoolCol(dbName='reviewed', notNull=True, default=False)

    autoupdate = BoolCol(dbName='autoupdate', notNull=True, default=False)

    freshmeatproject = StringCol(notNull=False, default=None)

    sourceforgeproject = StringCol(notNull=False, default=None)

    #
    # useful Joins
    #
    potemplates = MultipleJoin('POTemplate', joinColumn='product')

    bugtasks = MultipleJoin('BugTask', joinColumn='product')

    branches = MultipleJoin('Branch', joinColumn='product')

    sourcesources = MultipleJoin('SourceSource', joinColumn='product')

    sourcepackages = RelatedJoin('SourcePackage', joinColumn='product',
                           otherColumn='sourcepackage',
                           intermediateTable='Packaging')

    serieslist = MultipleJoin('ProductSeries', joinColumn='product')

    releases = MultipleJoin('ProductRelease', joinColumn='product',
                             orderBy='-datereleased')

    milestones = MultipleJoin('Milestone', joinColumn = 'product')

    def newseries(self, form):
        # Extract the details from the form
        name = form['name']
        displayname = form['displayname']
        shortdesc = form['shortdesc']
        # Now create a new series in the db
        return ProductSeries(name=name,
                             displayname=displayname,
                             shortdesc=shortdesc,
                             product=self.id)

    def newSourceSource(self, form, owner):
        rcstype = RevisionControlSystems.CVS.value
        if form['svnrepository']:
            rcstype = RevisionControlSystems.SVN.value
        # XXX Robert Collins 05/10/04 need to handle arch too
        ss = SourceSource(name=form['name'],
            title=form['title'],
            description=form['description'],
            product=self.id,
            owner=owner,
            cvsroot=form['cvsroot'],
            cvsmodule=form['module'],
            cvstarfileurl=form['cvstarfile'],
            cvsbranch=form['branchfrom'],
            svnrepository=form['svnrepository'],
            #StringCol('releaseroot', dbName='releaseroot', default=None),
            #StringCol('releaseverstyle', dbName='releaseverstyle',
            #          default=None),
            #StringCol('releasefileglob', dbName='releasefileglob',
            #          default=None),
            #ForeignKey(name='releaseparentbranch', foreignKey='Branch',
            #       dbName='releaseparentbranch', default=None),
            #ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
            #       dbName='sourcepackage', default=None),
            #ForeignKey(name='branch', foreignKey='Branch',
            #       dbName='branch', default=None),
            #DateTimeCol('lastsynced', dbName='lastsynced', default=None),
            #IntCol('frequency', dbName='syncinterval', default=None),
            # WARNING: syncinterval column type is "interval", not "integer"
            # WARNING: make sure the data is what buildbot expects
            rcstype=rcstype,
            hosted=None,
            upstreamname=None,
            newarchive=None,
            newbranchcategory=None,
            newbranchbranch=None,
            newbranchversion=None)

    def getSourceSource(self,name):
        """get a sync"""
        return SourceSource(self,
            SourceSource.select("name=%s and sourcesource.product=%s" %
                                (quote(name), self._product.id)
                                )[0])

    def poTemplatesToImport(self):
        for template in iter(self.potemplates):
            if template.rawimportstatus == RosettaImportStatus.PENDING:
                yield template

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate WHERE
              POTemplate.product = id AND
              POTemplate.name = name;'''
        results = POTemplate.select('''
            POTemplate.product = %d AND
            POTemplate.name = %s''' %
            (self.id, quote(name)))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]

    def newPOTemplate(self, name, title, person=None):
        if POTemplate.selectBy(
                productID=self.id, name=name).count():
            raise KeyError(
                  "This product already has a template named %s" % name)
        potemplate = POTemplate(name=name,
                                title=title,
                                product=self,
                                iscurrent=False,
                                owner=person)

        return potemplate

    def messageCount(self):
        count = 0
        for t in self.potemplates:
            count += len(t)
        return count

    def currentCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.currentCount(language)
        return count

    def updatesCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.updatesCount(language)
        return count

    def rosettaCount(self, language):
        count = 0
        for t in self.potemplates:
            count += t.rosettaCount(language)
        return count

    def getRelease(self, version):
        return ProductRelease.selectBy(productID=self.id, version=version)[0]

    def packagedInDistros(self):
        # XXX: This function-local import is so we avoid a circular import
        #   --Andrew Bennetts, 2004/11/07
        from canonical.launchpad.database import Distribution

        # FIXME: The database access here could be optimised a lot, probably
        # with a view.  Whether it's worth the hassle remains to be seen...
        #  -- Andrew Bennetts, 2004/11/07

        # cprov 20041110
        # Added 'Product' in clauseTables but got MANY entries for "Ubuntu".
        # As it is written in template we expect a link to:
        #    distribution/distrorelease/sourcepackagename
        # But now it seems to be unrecheable.

        distros = Distribution.select(
            "Packaging.product = Product.id AND "
            "Packaging.sourcepackage = SourcePackage.id AND "
            "Distribution.id = SourcePackage.distro ",
            clauseTables=['Packaging', 'SourcePackage', 'Product'],
            orderBy='title',
            )
        return distros

    def bugsummary(self):
        """Return a matrix of the number of bugs for each status and severity.
        """
        # XXX: This needs a comment that gives an example of the structure
        #      within a typical dict that is returned.
        #      The code is hard to read when you can't picture exactly
        #      what it is doing.
        # - Steve Alexander, Tue Nov 30 16:49:40 UTC 2004
        bugmatrix = {}
        for severity in BugSeverity.items:
            bugmatrix[severity] = {}
            for status in BugTaskStatus.items:
                bugmatrix[severity][status] = 0
        for bugtask in self.bugtasks:
            bugmatrix[bugtask.severity][bugtask.bugstatus] += 1
        resultset = [['']]
        for status in BugTaskStatus.items:
            resultset[0].append(status.title)
        severities = BugSeverity.items
        for severity in severities:
            statuses = BugTaskStatus.items
            statusline = [severity.title]
            for status in statuses:
                statusline.append(bugmatrix[severity][status])
            resultset.append(statusline)
        return resultset

    def attachTranslations(self, tarfile, prefix=None, sourcepackagename=None,
                           distrorelease=None, version=None, logger=None):
        '''See IProduct.'''

        # updated is a list of .pot files that are being used to update an
        # existen POTemplate objects.
        updated = []
        # added is a list of .pot files that are being used to create new
        # POTemplate objects.
        added = []
        # errors is a list of .pot and .po files that gave us an error while
        # processing them.
        errors = []

        # Check to see if we have already imported this tarball successfully.
        # We do it before the tarfile.read() so we don't download the file if
        # it's not needed.
        for pot in self.potemplates:
            if (pot.distrorelease == distrorelease and
                version is not None and
                pot.sourcepackageversion is not None):
                deb = canonical.sourcerer.deb
                if deb.version.Version(version) <= pot.sourcepackageversion:
                    if logger is not None:
                        logger.info("This tarball or a newer one is already"
                                    " imported. Ignoring it...")
                    return updated, added, errors

        tf = string_to_tarfile(tarfile.read())
        pot_paths, po_paths = examine_tarfile(tf)

        if len(pot_paths) == 0:
            # It's not a valid tar file, it does not have any .pot file.
            if logger is not None:
                logger.warning("We didn't found any .pot file")

            return updated, added, errors
        else:
            # It's the first time we import this tarball or last try gave us
            # an error, we should retry it until the system accepts it.

            # Get the list of domains
            domains = []
            try:
                domains_file = tf.extractfile('domains.txt')
                # We have that file inside the tar file.
                for line in domains_file.readlines():
                    domains.append(line.strip())
            except KeyError, key:
                # The tarball does not have a domains.txt file.
                pass
            for pot_path in pot_paths:
                pot_base_dir = os.path.dirname(pot_path)
                pot_file = os.path.basename(pot_path)
                root, extension = os.path.splitext(pot_file)
                if pot_base_dir == 'debian/po':
                    # The .pot inside that directory are special ones and have
                    # a concrete name.
                    potname = 'debconf-templates'
                elif len(domains) == 1 and len(pot_paths) == 1:
                    # There is only a .pot file and we know its domain name.
                    potname = domains[0]
                elif len(domains) > 1:
                    # There are more than one .pot file and we have the list
                    # of names but don't know which one we should use.
                    # XXX: Carlos Perello Marin 2005-02-01 We should implement
                    # this case (a tarball with more than one .pot file
                    # without counting the debian/po directory).
                    if logger is not None:
                        logger.warning("We got more than one domain, this is"
                                       " a corner case and we should"
                                       " implement it...")
                        for domain in domains:
                            logger.warning(domain)

                    break
                else:
                     potname = root

                if prefix is not None:
                    potname = '%s-%s' % (prefix, potname)

                try:
                    potemplate = self.poTemplate(potname)
                    updated.append(pot_path)
                    # Check to detect pot files moved. It's not usual and
                    # logging it could help us to detect problems with the
                    # import.
                    if (potemplate.path is not None and
                       potemplate.path != pot_base_dir):
                        # The template has moved from its previous location,
                        # log it so it helps to detect errors.
                        if logger is not None:
                            logger.warning("The POTemplate %s has been moved"
                                           "from %s to %s" % (
                                            potname,
                                            potemplate.path,
                                            pot_base_dir))
                        # Update new path.
                        potemplate.path = pot_base_dir
                except KeyError:
                    # The POTemplate was not found, before creating a new one,
                    # we look for it based on the path.
                    potemplate = None
                    for pot in self.potemplates:
                        if (pot.distrorelease == distrorelease and
                           pot.path is not None and
                           pot.path == pot_base_dir):
                            # We have found a potemplate using this path so we
                            # log it, as always to be able to detect any
                            # problem and continue the normal process with it.
                            if logger is not None:
                                logger.warning("The POTemplate %s has been"
                                               " detected as beeing the same"
                                               " than %s because both share"
                                               " the same path." % (
                                                pot.name, potname))
                            potemplate = pot
                            updated.append(pot_path)
                            break
                    if potemplate is None:
                        # It's a new pot file.
                        potemplate = self.newPOTemplate(potname, potname)
                        added.append(pot_path)

                try:
                    potemplate.attachRawFileData(tf.extractfile(pot_path).read())
                except (POSyntaxError, POInvalidInputError):
                    # The file has an error detected by our parser.
                    errors.append(pot_path)
                    if logger is not None:
                        logger.error('Parser error with potfile: %s',
                                     pot_path, exc_info=1)
                    # Jump to the next .pot file
                    continue

                # Update always the sourcepackagename and distrorelease
                # fields. No matter if they are None or not.
                potemplate.sourcepackagename = sourcepackagename
                potemplate.distrorelease = distrorelease

                # The path from where the .pot file was extracted is also
                # stored inside the POTemplate object.
                potemplate.path = pot_base_dir

                for po_path in po_paths:
                    po_base_dir = os.path.dirname(po_path)
                    po_file = os.path.basename(po_path)
                    if pot_base_dir == po_base_dir:
                        # 99% of the time it should be this way, all .po and
                        # .pot files inside the same directory.
                        root, extension = os.path.splitext(po_file)

                        if '@' in root:
                            code, variant = [unicode(field) for field in root.split('@', 1)]
                        else:
                            code, variant = root, None

                        try:
                            pofile = potemplate.getOrCreatePOFile(code, variant)
                        except ValueError, value:
                            # The language code does not exists in our
                            # database. Usually, it's a translator error.
                            if logger is not None:
                                logger.warning("The '%s' code does not exist"
                                               " as a valid language code in"
                                               " Rosetta." % code)
                            errors.append(po_path)
                            continue
                        try:
                            pofile.attachRawFileData(tf.extractfile(po_path).read())
                        except (POSyntaxError, POInvalidInputError):
                            # The file has an error detected by our parser.
                            errors.append(po_path)
                            if logger is not None:
                                logger.error('Parser error with pofile: %s',
                                             po_path, exc_info=1)
                            # Jump to the next .pot file
                            continue
                    else:
                        # XXX: Carlos Perello Marin 2005-01-28, Implement
                        # support for Python/PHP like trees.
                        # https://dogfood.ubuntu.com/malone/bugs/235
                        errors.append(po_path)
                        continue

            if version is not None and len(errors) == 0:
                # If the list of errors is empty, the potemplates can be
                # marked as being in sync with the tarball attached. If
                # the version field is not None, we store that information
                # inside the potemplate.
                # This lets us prevent import a tar.gz twice or import an old
                # tarball.
                for potemplate in self.potemplates:
                    if potemplate.distrorelease == distrorelease:
                        # The version is stored only if the potemplate is
                        # related to the current distrorelease.
                        potemplate.sourcepackageversion = version

            return updated, added, errors


class ProductSet:
    implements(IProductSet)

    def __init__(self):
        self.title = "Launchpad Products"

    def __iter__(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return iter(Product.select())

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        ret = Product.selectBy(name=name)
        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]

    def get(self, productid):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        try:
            product = Product.get(productid)
        except SQLObjectNotFound, err:
            raise NotFoundError("Product with ID %s does not exist" %
                                str(productid))

        return product

    def createProduct(self, owner, name, displayname, title, shortdesc,
                      description, project=None, homepageurl=None,
                      screenshotsurl=None, wikiurl=None,
                      downloadurl=None, freshmeatproject=None,
                      sourceforgeproject=None):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product(owner=owner, name=name, displayname=displayname,
                       title=title, project=project, shortdesc=shortdesc,
                       description=description,
                       homepageurl=homepageurl,
                       screenshotsurl=screenshotsurl,
                       wikiurl=wikiurl,
                       downloadurl=downloadurl,
                       freshmeatproject=freshmeatproject,
                       sourceforgeproject=sourceforgeproject)
    
    def forReview(self):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        return Product.select("reviewed IS FALSE")

    def search(self, text=None, soyuz=None,
               rosetta=None, malone=None,
               bazaar=None,
               show_inactive=False):
        """See canonical.launchpad.interfaces.product.IProductSet."""
        clauseTables = Set()
        clauseTables.add('Product')
        query = '1=1 '
        if text:
            text = quote(text)
            query += " AND Product.fti @@ ftq(%s) " % (text,)
        if rosetta:
            clauseTables.add('POTemplate')
        if malone:
            clauseTables.add('BugTask')
        if bazaar:
            clauseTables.add('SourceSource')
        if 'POTemplate' in clauseTables:
            query += ' AND POTemplate.product=Product.id \n'
        if 'BugTask' in clauseTables:
            query += ' AND BugTask.product=Product.id \n'
        if 'SourceSource' in clauseTables:
            query += ' AND SourceSource.product=Product.id \n'
        if not show_inactive:
            query += ' AND Product.active IS TRUE \n'
        return Product.select(query, distinct=True, clauseTables=clauseTables)

    def translatables(self, translationProject=None):
        """See canonical.launchpad.interfaces.product.IProductSet.
        
        This will give a list of the translatables in the given Translation
        Project. For the moment it just returns every translatable product.
        """
        clauseTables = ['Product', 'POTemplate']
        query = """POTemplate.product=Product.id"""
        return Product.select(query, distinct=True,
                              clauseTables=clauseTables)

