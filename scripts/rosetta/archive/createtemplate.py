#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 34a8f99d-a803-4392-994f-c85ebb8b6fcc

from canonical.lp import initZopeless
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.database import Person, POTemplate, Product
from optparse import OptionParser
from zope.component.tests.placelesssetup import PlacelessSetup
from datetime import datetime

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-p", "--product", dest="product",
        help="The Product ID where this potemplate is")
    parser.add_option("-n", "--name", dest="name",
                      help="Template name")
    parser.add_option("-t", "--title", dest="title",
                      help="Template title")
    parser.add_option("-e", "--description", dest="description",
                      help="Template description")
    (options, args) = parser.parse_args()

    # If we get all needed options...
    for name in ('owner', 'product', 'name', 'title', 'description'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    ztm = initZopeless()

    person = Person.get(int(options.owner))

    if person is None:
        raise RuntimeError("The person %s does not exist." % options.owner)

    products = list(Product.selectBy(name = options.product))

    if len(products) == 0:
        raise RuntimeError("The product %s does not exist." %
            options.product)

    product = products[0]

    # XXX daniels 2004-12-14:
    # https://bugzilla.warthogs.hbd.com/bugzilla/show_bug.cgi?id=1968
    poTemplate = POTemplate(
        product=product,
        name=options.name,
        title=options.title,
        description=options.description,
        path='',
        iscurrent=True,
        datecreated=datetime.utcnow(),
        copyright='XXX: FIXME',
        priority=2, # XXX: FIXME
        branch=1, # XXX: FIXME
        license=1, # XXX: FIXME
        messagecount=0,
        owner=person)

    if poTemplate is None:
        raise RuntimeError("There was an error creating the template %s.",
            options.name)

    print "Template %s created." % options.name

    ztm.commit()

