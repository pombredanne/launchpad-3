# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 5ce06dae-6ab3-4397-8ff2-e7fec441857f

__author__ = "David Allouche <david@canonical.com>"
__copyright__ = "Copyright (C) 2004 Canonical Ltd."
__metaclass__ = type

from canonical.arch import infoImporter
import logging
from canonical.launchpad.database import Product
from canonical.launchpad.database import ArchArchive
from canonical.launchpad.database import Person
from canonical.launchpad.database import SourceSource


def repositoryIsTar(cvsroot):
    for suffix in ["tar.gz", "tgz", "tar.bz2"]:
        if cvsroot.endswith(suffix):
            return True
    else:
        return False


def updateCvsrootFromInfoFile(infofile):
    import info2job
    info = info2job.read_info(infofile, logging)
    jobs = info2job.iter_jobs(info, logging)
    for job in jobs:
        cvsroot = info.get("cvsroot")
        if cvsroot is None: continue
        jobname = info2job.jobfile_name(info, job)
        query = (SourceSource.q.name == jobname
                 and SourceSource.q.processingapproved == None)
        for source in  SourceSource.select(query):
            print 'updateCvsroot: name    == ', source.name
            print 'updateCvsroot: cvsroot == ', source.cvsroot
            if repositoryIsTar(source.cvsroot):
                print 'updateCvsroot: cvsroot <= ', cvsroot
                source.cvsroot = cvsroot


def main(filelist):
    ok, bad = infoImporter.filterRunner(updateCvsrootFromInfoFile, filelist)
    print '%d ok, %d failed' % (ok, bad)

    
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "Usage: %s <info files>" % (sys.argv[0],)
    main(sys.argv[1:])

