#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 6c618e88-b377-4ee6-8bfb-4d42fda1d378

import os, popen2

from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.sql import RosettaPerson, RosettaEmailAddress
from canonical.lp.placelessauth.encryption import SSHADigestEncryptor
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
    parser.add_option("-p", "--password", dest="password",
                      help="Optional password")
    (options, args) = parser.parse_args()

    # If we get all needed options...
    if options.given != None and options.family != None and \
       options.display != None and options.email != None:

        if options.password == None:
            # If we don't get a password from command line, we generate one
            # automaticaly.
            pwgen = popen2.Popen3('/usr/bin/pwgen -s -1', True)

            # Now we wait until the command ends
            status = pwgen.wait()

            if os.WIFEXITED(status):
                if os.WEXITSTATUS(status) == 0:
                    # The command worked
                    options.password = pwgen.fromchild.read()
                    options.password = options.password.strip('\n')

                else:
                    print "There was an error executing pwgen: " + \
                        pwgen.childerr.read()
                    os.exit(1)
            else:
                print "There was an unknown error executing pwgen."
                os.exit(1)

        ssha = SSHADigestEncryptor()

        passEncrypted = ssha.encrypt(options.password)

        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))

        # XXX: We don't check if the person already exists
        person = RosettaPerson(givenName=options.given,
                               familyName=options.family,
                               displayName=options.display,
                               password=passEncrypted)
        # XXX: Should be status=2? we know the people we add from here.
        email = RosettaEmailAddress(person=person, email=options.email, status=1)

        # XXX: Implement an email submit with all information filled so the
        # user knows his/her password.
        print "The password: " + options.password + " The encrypted: " + passEncrypted

    else:
        # XXX: We should do this message more descriptive.
        print "Please, review the command line, we need more options..."
