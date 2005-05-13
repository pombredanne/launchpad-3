#!/usr/bin/python
#
#
#
#
#

import apt_pkg, tempfile, os, sys

from canonical.lp import initZopeless
from canonical.lp import encoding 
from canonical.foaf import nickname
from canonical.launchpad import database
from zope.app.zapi import getUtility

#
# Utility functions
#

def parse_person(val):
    name, email = val.split("<", 2)
    email = email.split(">")[0].lower()
    return (name.strip(), email.strip())

def nick_registered(nick):
    if list(database.Person.selectBy(name=nick)):
        return True
    else:
        return False

def ensure_debdistro():
    debdistro = database.Distribution.selectBy(name="debian")
    if debdistro:
        assert len(debdistro) == 1
        return debdistro[0]
    return database.Distribution(name="debian", displayname="Debian", 
                                 # XXX hardcoded owner
                                 title="Debian GNU/Linux", owner=1)

def do_stanza(bdata, debdistro, ztm, sources):
    if bdata.has_key("Source"):
        srcpkg = bdata["Source"]
    else:
        srcpkg = bdata["Package"]

    if sources.has_key(srcpkg):
        print "- Skipping package %s: it already exists" % srcpkg
        return

    maintainer_data = bdata["Maintainer"]
    mname, memail = parse_person(maintainer_data)
   
    nick=nickname.generate_nick(memail)
    maintainer = database.Person.selectBy(name=nick)
    if maintainer:
        assert len(maintainer) == 1
        maintainer = maintainer[0]
    else:
        existing_email = database.EmailAddress.selectBy(email=memail)
        if existing_email:
            maintainer = existing_email[0].person
        else:
            print "* Creating maintainer %s" % nick
            mname = encoding.guess(mname)
            maintainer = database.Person(name=nick, displayname=mname)
            # XXX status hardcoded
            emailaddy = database.EmailAddress(email=memail, status=1,
                                     person=maintainer)

    summary = bdata["Description"].split("\n")[0].strip()
    description = bdata["Description"].split("\n", 1)[1].strip()

    # srcpkg can actually contain a version, which we don't care about
    srcpkg = srcpkg.split()[0]
    res = database.SourcePackageName.selectBy(name=srcpkg)
    if res:
        assert len(res) == 1
        sourcepackagename=res[0]
    else:
        sourcepackagename = database.SourcePackageName(name=srcpkg)

    if database.SourcePackage.select("sourcepackagename=%s AND distro=%s" % 
                                     (sourcepackagename.id, debdistro.id)).count():
        print "- Skipping package %s: it already exists" % srcpkg
        sources[srcpkg] = None
        return
        
    print "* Creating source package %s" % srcpkg
    print "  + Summary: %s" % summary.split("\n")[0]
    print "  + Description: %s [...]" % description.split("\n")[0]
    print "  + Maintainer: %s" % maintainer.name
    summary = encoding.guess(summary)
    description = encoding.guess(description)
    sources[srcpkg] = database.SourcePackage(summary=summary,
                                             description=description,
                                             manifestID=None,
                                             distro=debdistro,
                                             maintainer=maintainer,
                                             # XXX hardcoded format
                                             srcpackageformat=1,
                                             sourcepackagename=sourcepackagename)

#
#
#

if __name__ == "__main__":
    try:
        try:
            ztm = initZopeless()

            binfd, packages_tagfile = tempfile.mkstemp()

            os.system("gzip -dc %s > %s" % (sys.argv[1], packages_tagfile))
            binfile = os.fdopen(binfd)
            tagfile = apt_pkg.ParseTagFile(binfile)

            debdistro = ensure_debdistro()

            sources = {}
            while tagfile.Step():
                bdata = tagfile.Section
                do_stanza(bdata, debdistro, ztm, sources)
        
        finally:
            os.unlink(packages_tagfile)
    except:
        print "--- Baby gina cries!"
        raise
    else:
        print "Committing changes..."
        ztm.commit()

