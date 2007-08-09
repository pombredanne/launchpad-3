#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 6ff81610-1bc0-4c22-960c-4e0c2f33c0c9

import os, popen2
from optparse import OptionParser
from datetime import datetime

from zope.component.tests.placelesssetup import PlacelessSetup

import canonical.lp
from canonical.launchpad.database import Person, Product, Project

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-p", "--project", dest="project",
                      help="Project name")
    parser.add_option("-n", "--name", dest="name",
                      help="Product name")
    parser.add_option("-d", "--display-name", dest="display",
                      help="Display name")
    parser.add_option("-t", "--title", dest="title",
                      help="Product title")
    parser.add_option("-s", "--short-description", dest="short",
                      help="Product's summary")
    parser.add_option("-e", "--description", dest="description",
                      help="Product's description")
    parser.add_option("-u", "--url", dest="url",
                      help="Product's Home page URL")
    parser.add_option("-w", "--wiki", dest="wiki",
                      help="Product's Wiki URL")
    parser.add_option("-l", "--lastdoap", dest="lastdoap",
                      help="Product's lastdoap")
    (options, args) = parser.parse_args()

    # If we get all needed options...
    for name in ('owner', 'project', 'name', 'display', 'title', 'short',
                 'description'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    ztm = canonical.lp.initZopeless()

    person = Person.get(int(options.owner))
    if person is None:
        raise RuntimeError("The person %s does not exist." % options.owner)

    projects = list(Project.selectBy(name=options.project))

    if len(projects) == 0:
        raise RuntimeError("The project %s does not exist." %
            options.project)

    project = projects[0]

    # XXX: daniels 2004-12-14:
    # https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
    product = Product(owner=person.id, project=project.id,
                      name=options.name,
                      displayname=options.display, title=options.title,
                      summary=options.short,
                      description=options.description,
                      datecreated=datetime.utcnow(),
                      homepageurl=options.url,
                      wikiurl=options.wiki,
                      lastdoap=options.lastdoap)

    if product is None:
        raise RuntimeError("There was an error creating the product %s.",
                           options.name)
    else:
        print "Product %s created." % options.name

        ztm.commit()

