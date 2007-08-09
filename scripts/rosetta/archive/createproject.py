#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: b9019fba-02b5-4d42-87e4-39b4754da09b

import os, popen2
from optparse import OptionParser
from datetime import datetime

from zope.component.tests.placelesssetup import PlacelessSetup

import canonical.lp
from canonical.launchpad.database import Person, Project

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-n", "--name", dest="name",
                      help="Project name")
    parser.add_option("-d", "--display-name", dest="display",
                      help="Display name")
    parser.add_option("-t", "--title", dest="title",
                      help="Project title")
    parser.add_option("-s", "--short-description", dest="short",
                      help="Project's summary")
    parser.add_option("-e", "--description", dest="description",
                      help="Project's description")
    parser.add_option("-u", "--url", dest="url",
                      help="Project's Home page URL")
    parser.add_option("-w", "--wiki", dest="wiki",
                      help="Project's Wiki URL")
    parser.add_option("-l", "--lastdoap", dest="lastdoap",
                      help="Project's lastdoap")
    (options, args) = parser.parse_args()

    # If we get all needed options...
    for name in ('owner', 'name', 'display', 'title', 'short', 'description'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    ztm = canonical.lp.initZopeless()

    person = Person.get(int(options.owner))
    if person is None:
        raise RuntimeError("The person %s does not exists." % options.owner)

    # XXX daniels 2004-12-14:
    # https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
    project = Project(owner=int(options.owner), name=options.name,
                        displayname=options.display, title=options.title,
                        summary=options.short,
                        description=options.description,
                        datecreated=datetime.utcnow(),
                        homepageurl=options.url,
                        wikiurl=options.wiki,
                        lastdoap=options.lastdoap)

    if project is None:
        raise RuntimeError("There was an error creating the project %s.",
                           options.name)
    else:
        print "Project %s created." % options.name

        ztm.commit()

