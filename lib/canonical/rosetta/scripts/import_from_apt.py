#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 6c51db1e-9d35-4eaa-8dca-905f0b982589

import os, popen2
import apt_pkg
import bz2
from tempfile import TemporaryFile


downloadDir = '/tmp/rosetta/'

def download(local, uri, resume, md5sum=None):
    if resume:
        res = '-C -'
    else:
        res = ''
    curl = popen2.Popen3('/usr/bin/curl %s --create-dirs -o %s -s %s' %
            (uri, local, res), True)

    # Now we wait until the command ends
    status = curl.wait()

    if os.WIFEXITED(status):
        # XXX: Seems like with really small files curl fails, thus, we
        # ignore this error, it's safe to ignore it because we are checking
        # the md5 later so if there was a real problem, we will catch it
        # there.
        if os.WEXITSTATUS(status) != 0 and os.WEXITSTATUS(status) != 33:
            # The command failed.
            raise RuntimeError("Curl failed with %d code downloading %s" %
                (os.WEXITSTATUS(status), uri))
        elif md5sum is not None:
            # We verify the download
            import md5

            m = md5.new()
            m.update(open(local).read())
            if md5sum != m.hexdigest():
                RuntimeError("The md5sum is not valid for %s" % local)
    else:
        raise RuntimeError("There was an unknown error executing curl.")
    
def extractDeb(filename):
    dpkg = popen2.Popen3('/usr/bin/dpkg-source -x %s' % filename, True)

    # Now we wait until the command ends
    status = dpkg.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) != 0:
            # The command failed.
            raise RuntimeError("dpkg-source failed with %d code processing %s" %
                (os.WEXITSTATUS(status), filename))
    else:
        raise RuntimeError("There was an unknown error executing dpkg-source.")

def updateCDBS(path):
    oldPath = os.getcwd()
    os.chdir(path)

    rules = popen2.Popen3('./debian/rules common-configure-indep > /dev/null', True)

    # Now we wait until the command ends
    status = rules.wait()

    # Restore old path
    os.chdir(oldPath)

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) != 0:
            # The command failed.
            raise RuntimeError("debian/rules failed with %d code" %
                os.WEXITSTATUS(status))
    else:
        raise RuntimeError("There was an unknown error executing debian/rules.")


    
os.chdir(downloadDir)
# First, we download the Sources.bz2 file
# XXX: We should implement a way to use a cache
uri = 'http://archive.ubuntu.com/ubuntu/dists/warty/main/source/Sources.bz2'
file = 'Sources.bz2'
print "Getting %s" % uri
download(file, uri, False)
tmpFile = TemporaryFile()
tmpFile.write(bz2.decompress(open(file).read()))
tmpFile.seek(0)

# Here we can forget about the file format, apt_pkg will handle it for us.
parser = apt_pkg.ParseTagFile(tmpFile)

while parser.Step() == 1:

    # Every iteration is a new package from Sources.bz2
    print "Processing: %s" % parser.Section.get("Package")
    
    # We will work only with packages that work with cdbs
    if parser.Section.get("Build-Depends") is not None and \
       'cdbs' in parser.Section.get("Build-Depends").split():
        
        for srcFile in parser.Section.get("Files").strip().split('\n'):
        
            (md5, size, filename) = srcFile.strip().split()
            if filename.endswith('.dsc'):
                dscFile = filename
            elif filename.endswith('.tar.gz'):
                tarFile = filename
                # We get the directory name for this package from the .tar.gz
                if len(filename.split('.orig.tar.gz')) == 2:
                    dirName = filename.split('.orig.tar.gz')[0]
                else:
                    # For native packages
                    dirName = filename.split('.tar.gz')[0]
                # XXX: This is uuugly, but necessary, I'm open to other
                # options. The main idea behind this is that the directory
                # names have the '-' char instead of the '_' one from the
                # tar.gz
                dirName = dirName.replace('_', '-', 1)
                
            uri = ("http://archive.ubuntu.com/ubuntu/%s/%s" %
                (parser.Section.get("Directory").strip(), filename))
            print "Downloading %s" % filename
            download(filename, uri, True, md5)
            
        # At this point we have all needed files downloaded.
        print "Processing %s" % dscFile
        extractDeb(dscFile)
        updateCDBS(dirName)
