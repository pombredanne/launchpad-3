"""A script to take one or more info files, and import them into the database.

It will create ArchArchive and Branch entries as needed.
"""

#from canonical.launchpad.database import Archive
from canonical.database.sqlbase import SQLBase, quote
from canonical.soyuz.importd import SoyuzProduct
import canonical.lp
from canonical.launchpad.database import ArchArchive, Person, SourceSource

from sqlobject import ForeignKey, IntCol, StringCol, DateTimeCol, BoolCol, \
                      EnumCol, connectionForURI
#from sqlobject.sqlbuilder.func import NOW

# import canonical.arch.broker as arch

import importd
import importd.Job

import logging


class ImporterSourceSource(SourceSource):

    def _get_repository(self):
        if self.rcstype == RCSTypeEnum.cvs:
            return self.cvsroot
        elif self.rcstype == RCSTypeEnum.svn:
            return self.svnrepository
        else:
            # FIXME!
            return None

    # Translate importd.Job.Job's instance variables to database columns by
    # creating some simple properties.  [Note that SQLObject turns _get_* and
    # _sets_* methods into properties automagically]
    #FIXME: buildbot should updated this on mirror completion.
    def _get_TYPE(self):
 #       if self.lastsynced is None:
        if self.frequency is None or int(self.frequency) == 0:
            return 'import'
        else:
            return 'sync'
    def _get_package_files(self):
        if self.package_files_collapsed is None: return None
        return self.package_files_collapsed.split()
    def _get_RCS(self): return RCSNames[self.rcstype]
    def _set_RCS(self, value): self.rcstype = getattr(RCSTypeEnum, value)
    def _get_module(self): return self.cvsmodule
    def _set_module(self, value): self.cvsmodule = value
    def _get_category(self): return self.newbranchcategory
    def _set_category(self, value): return self.newbranchcategory
    def _get_archivename(self): return self.newarchive
    def _set_archivename(self, value): self.archivename = value
    def _get_branchfrom(self): return self.cvsbranch # FIXME: assumes cvs!
    def _set_branchfrom(self, value): self.cvsbranch = value # FIXME: ditto
    def _get_branchto(self): return self.newbranchbranch
    def _set_branchto(self, value): self.newbranchbranch = value
    def _get_archversion(self): return self.newbranchversion
    def _set_archversion(self, value): self.newbranchversion = value
    
    def buildJob(self):
        # FIXME: The rest of this method can probably be deleted now.
        # it so can't, inheritance doesn't work here.
        from importd.Job import CopyJob
        job = CopyJob()
        job.repository = str(self.repository)
 #       if self.lastsynced is None:
        if self.syncingapproved is None:
	#self.frequency is None or int(self.frequency) == 0:
            job.TYPE = 'import'
            if self.cvstarfileurl is not None and self.cvstarfileurl != "":
                job.repository = str(self.cvstarfileurl)
            job.frequency=0
        else:
            job.TYPE = 'sync'

            job.frequency=int(self.frequency)

        job.tagging_rules=[]

  
        job.name = str(self.name)
        job.RCS = RCSNames[self.rcstype]
        job.svnrepository = self.svnrepository
        job.module = str(self.cvsmodule)

        job.category = str(self.newbranchcategory)
        job.archivename = str(self.newarchive)
        job.branchfrom = str(self.cvsbranch) # FIXME: assumes cvs!
        job.branchto = str(self.newbranchbranch)
        job.archversion = str(self.newbranchversion)

        job.package_distro = self.package_distro
        job.package_files = self.package_files
        return job

# XXX: This hack should go away when everything is properly refactored
SourceSource = ImporterSourceSource


def make_lifeless():
    query = Person.select(Person.q.displayname == 'Robert Collins')
    assert query.count() == 1
    return query[0]

def make_unassigned_product():
    query = SoyuzProduct.select(SoyuzProduct.q.name == 'unassigned')
    assert query.count() == 1
    return query[0]

def importInfoFile(infofile):
    import info2job
    info = info2job.read_info(infofile, logging)
    lifeless = make_lifeless()
    unassigned = make_unassigned_product()
    for job in info2job.iter_jobs(info, logging):
        print 'importInfoFile: job =', job
        jobname = info2job.jobfile_name(info, job)
        lastsynced=None
        if SourceSource.select(SourceSource.q.name == jobname).count() != 0:
            continue
        if job.TYPE == 'sync':
            lastsynced='NOW'
        if job.RCS in ('cvs', 'svn'):
            # Find the right database ID for archive in job.archivename.  If it
            # doesn't exist in the database yet, use NULL
            results = ArchArchive.select(ArchArchive.q.name == job.archivename)
            try:
                archive = results[0]
            except IndexError:
                archive = None
            print 'importInfoFile: [%s] archive = %s' % (job.RCS, archive)

            # Ditto Branch
            if archive:
                branch = None ### FIXME ###
                ### Note that branch name can be emtpy
#                 results = Branch.select(
#                     "id=%d" %  mapper._getDBBranchId(version)))
#                             "archive=%s AND category=%s AND branch=%s"
#                             % (quote(archive.id), quote(job.category),
#                                quote(job.branchto)))
#                 try:
#                     branch = results[0]
#                 except IndexError:
#                     branch = None
            else:
                branch = None

            summary = info.get('summary', '')
            kwargs = {
                'name': jobname,
                'title': info.get('source',jobname),
                'description': summary,
                'sourcepackage': None, # FIXME!
                'branch': branch,
                'lastsynced': lastsynced,
                'hosted': info.get('hosted') or None,
                'upstreamname': info.get('upstreamname') or None,
                'newarchive': job.archivename,
                'newbranchcategory': job.category,
                'newbranchbranch': job.branchto,
                'newbranchversion': job.archversion,
                'owner': lifeless,
                'product': unassigned,
                }

            if job.RCS == 'cvs':
                ss = SourceSource(
                        cvsroot=job.repository,
                        cvsmodule=job.module,
                        cvstarfileurl=info.get("cvstarfile") or None,
                        cvsbranch=job.sourceBranch(),
                        **kwargs)
            if job.RCS == 'svn':
                ss = SourceSource(
                    rcstype=RCSTypeEnum.svn,
                    svnrepository=job.svnrepository,
                    **kwargs)
        elif job.RCS == "package":
            ss = SourceSource(
                    rcstype=RCSTypeEnum.package,
                    name=jobname,
                    title="",
                    description="",
                    newarchive="",
                    newbranchcategory="",
                    newbranchbranch="",
                    newbranchversion="",
                    owner=lifeless,
                    package_distro=info["packagedistro"],
                    package_files_collapsed=" ".join(info["packagefile"])
                    )
        else:
            #raise ValueError, 'Unimplemented job RCS: ' + repr(job.RCS)
            logging.warning('Unimplemented job RCS: ' + repr(job.RCS))
            continue


def clearDatabase():
    """For testing."""
    SourceSource.clearTable()
    Branch.clearTable()
    ArchArchive.clearTable()

def main(filelist):
    SQLBase.initZopeless(connectionForURI('postgres://'+ canonical.lp.dbhost + '/' + canonical.lp.dbname))

    # clearDatabase() ## XXX: For testing

    ok = bad = 0
    for filename in filelist:
        try:
            importInfoFile(filename)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            logging.warning('Failed to import %s: %s' % (filename, e))
            bad += 1
        else:
            ok += 1
    print '%d imported ok, %d failed' % (ok, bad)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "Usage: %s <info files>" % (sys.argv[0],)
    main(sys.argv[1:])


