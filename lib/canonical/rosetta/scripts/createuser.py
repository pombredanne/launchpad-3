#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 6c618e88-b377-4ee6-8bfb-4d42fda1d378

from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.sql import RosettaPerson, RosettaEmailAddress
from sqlobject import connectionForURI
from optparse import OptionParser

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-g", "--given-name", dest="given",
                      help="Given name")
    parser.add_option("-f", "--family-name", dest="family",
                      help="Family name")
    parser.add_option("-d", "--display-name", dest="display",
                      help="Display name")
    parser.add_option("-e", "--email", dest="email",
                      help="Email address")
    (options, args) = parser.parse_args()

    SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))
   

    # XXX: We don't check if the person already exists
    person = RosettaPerson(givenName=options.given, familyName=options.family,
                           displayName=options.display)
    # XXX: Should the email's be status=2? we know the people we add from here.
    email = RosettaEmailAddress(person=person, email=options.email, status=1)
