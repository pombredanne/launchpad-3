#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 6c51db1e-9d35-4eaa-8dca-905f0b982589

import httplib
import apt_pkg
import bz2
from tempfile import TemporaryFile

# First, we download the Sources.bz2 file
# XXX: We should implement a way to use a cache
conn = httplib.HTTPConnection("archive.ubuntu.com")
conn.request("GET", "/ubuntu/dists/warty/main/source/Sources.bz2")
r1 = conn.getresponse()
if r1.status == 200:
    # The file was downloaded correctly, we dump it into a temporal file
    # because apt_pkg needs it, a StringIO is not valid here :-(
    tmpFile = TemporaryFile()
    tmpFile.write(bz2.decompress(r1.read()))
    tmpFile.seek(0)
    # Here we can forget about the file format, apt_pkg will handle it for us.
    parser = apt_pkg.ParseTagFile(tmpFile)
    while parser.Step() == 1:
        # Every iteration is a new package from Sources.bz2
        print "Processing: %s" % parser.Section.get("Package")
        for srcFile in parser.Section.get("Files").strip().split('\n'):
            (md5, size, filename) = srcFile.strip().split()
            uri = "/ubuntu/" + parser.Section.get("Directory").strip() + \
                "/" + filename
            print "Downloading %s" % filename
            conn.request("GET", uri)
            response = conn.getresponse()
            if response.status == 200:
                out = file('/tmp/%s' % filename, 'w+')
                out.write(response.read())
            else:
                raise RuntimeError("We were not able to download %s file" %
                        filename)
else:
    raise RuntimeError("We were not able to download Sources.bz2 file")
