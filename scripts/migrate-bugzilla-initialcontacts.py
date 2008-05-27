#!/usr/bin/python2.4
# Copyright 2005-2006 Canonical Ltd.  All rights reserved.

import logging
import re
import MySQLdb

import _pythonpath

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, ILaunchpadCelebrities, NotFoundError)

execute_zcml_for_scripts()
ztm = initZopeless()
logging.basicConfig(level=logging.INFO)

ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
techboard = getUtility(IPersonSet).getByName('techboard')

def getPerson(email, realname):
    # The debzilla user acts as a placeholder for "no specific maintainer".
    # We don't create a bug contact record for it.
    if email is None or email == 'debzilla@ubuntu.com':
        return None

    personset = getUtility(IPersonSet)
    person = personset.getByEmail(email)
    if person:
        return person

    # we mark the bugzilla email as preferred email, since it has been
    # validated there.
    if email.endswith('@lists.ubuntu.com'):
        logging.info('creating team for %s (%s)', email, realname)
        person = personset.newTeam(techboard, email[:-17], realname)
        email = getUtility(IEmailAddressSet).new(email, person.id)
        person.setPreferredEmail(email)
    else:
        logging.info('creating person for %s (%s)', email, realname)
        person, email = personset.createPersonAndEmail(email,
                                                       displayname=realname)
        person.setPreferredEmail(email)

    return person


conn = MySQLdb.connect(db='bugs_warty')
cursor = conn.cursor()

# big arse query that gets all the default assignees and QA contacts:
cursor.execute(
    "SELECT components.name, owner.login_name, owner.realname, "
    "    qa.login_name, qa.realname "
    "  FROM components "
    "    JOIN products ON components.product_id = products.id "
    "    LEFT JOIN profiles AS owner ON components.initialowner = owner.userid"
    "    LEFT JOIN profiles AS qa ON components.initialqacontact = qa.userid "
    "  WHERE  products.name = 'Ubuntu'")

for (component, owneremail, ownername, qaemail, qaname) in cursor.fetchall():
    logging.info('Processing %s', component)
    try:
        srcpkgname, binpkgname = ubuntu.getPackageNames(component)
    except NotFoundError, e:
        logging.warning('could not find package name for "%s": %s', component,
                        str(e))
        continue

    srcpkg = ubuntu.getSourcePackage(srcpkgname)

    # default assignee => maintainer
    person = getPerson(owneremail, ownername)
    if person:
        if not srcpkg.isBugContact(person):
            srcpkg.addBugContact(person)

    # QA contact => maintainer
    person = getPerson(qaemail, qaname)
    if person:
        if not srcpkg.isBugContact(person):
            srcpkg.addBugContact(person)

ztm.commit()
