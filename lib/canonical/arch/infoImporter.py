"""A script to take one or more info files, and import them into the database.

It will create ArchArchive and Branch entries as needed.
"""

import sys

from canonical.database.sqlbase import quote
from canonical.launchpad.database import Product, ArchArchive, Person, SourceSource
from canonical.lp import dbschema
import canonical.lp

from sqlobject import ForeignKey, IntCol, StringCol, DateTimeCol, BoolCol, \
                      EnumCol

import importd
import importd.Job

import logging

def make_lifeless():
    query = Person.select(Person.q.displayname == 'Robert Collins')
    assert query.count() == 1
    return query[0]

def make_unassigned_product():
    query = Product.select(Product.q.name == 'unassigned')
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
                        rcstype=dbschema.RevisionControlSystems.CVS,
                        cvsroot=job.repository,
                        cvsmodule=job.module,
                        cvstarfileurl=info.get("cvstarfile") or None,
                        cvsbranch=job.sourceBranch(),
                        **kwargs)
            if job.RCS == 'svn':
                ss = SourceSource(
                    rcstype=dbschema.RevisionControlSystems.SVN
                    svnrepository=job.svnrepository,
                    **kwargs)
        elif job.RCS == "package":
            ss = SourceSource(
                    rcstype=dbschema.RevisionControlSystems.PACKAGE
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


def filterRunner(func, filelist):
    txnManager = canonical.lp.initZopeless()
    ok = bad = 0
    for filename in filelist:
        try:
            func(filename)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            sys.excepthook(*sys.exc_info())
            sys.exc_clear()
            logging.warning('Failure processing: %s' % filename)
            bad += 1
        else:
            ok += 1
    txnManager.commit()
    print '%d ok, %d failed' % (ok, bad)


def main(filelist):
    filterRunner(importInfoFile, filelist)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "Usage: %s <info files>" % (sys.argv[0],)
    main(sys.argv[1:])


