#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 6c618e88-b377-4ee6-8bfb-4d42fda1d378

import os, popen2, smtplib
from textwrap import wrap

from canonical.foaf.nickname import generate_nick
from canonical.lp import initZopeless
from canonical.lp.dbschema import EmailAddressStatus
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.database import Person, EmailAddress
from optparse import OptionParser
from zope.component.tests.placelesssetup import PlacelessSetup

def pwgen():
    pwgen = popen2.Popen3('/usr/bin/pwgen -s -1', True)

    # Now we wait until the command ends
    status = pwgen.wait()

    if os.WIFEXITED(status):
        if os.WEXITSTATUS(status) == 0:
            # The command worked
            return pwgen.fromchild.read().strip('\n')
        else:
            raise RuntimeError("There was an error executing pwgen: " +
                pwgen.childerr.read().strip('\n'))
    else:
        raise RuntimeError("There was an unknown error executing pwgen.")

def createUser(givenName, familyName, displayname, email, password=None):
    if password is None:
        # If we don't get a password from command line, we generate one
        # automaticaly.

        password = pwgen()

    encrypted_password = SSHADigestEncryptor().encrypt(password)

    ztm = initZopeless()

    # XXX daniels 2004-12-14: We don't check if the person already exists.
    person = Person(
        name = generate_nick(email),
        givenname = givenName,
        familyname = familyName,
        displayname = displayname,
        password = encrypted_password)

    email = EmailAddress(
        person = person,
        email = email,
        status = int(EmailAddressStatus.NEW))

    ztm.commit()

    return (person, password, encrypted_password)

def send_email(person, address, password):
    smtp = smtplib.SMTP('localhost')
    paragraphs = (
        "Hello %s," % person.displayname,
        "A Rosetta account has been created for you. To log in, use the "
        "email address this message was sent to as your username.",
        "Your password is: %s" % password,
        "Feel free to change it from within Rosetta using the preferences "
        "page.")
    body = "\n\n".join([ "\n".join(wrap(x)) for x in paragraphs ])
    smtp.sendmail('launchpad@canonical.com', address, (
        "From: Rosetta\n"
        "To: %s <%s>\n"
        "Subject: New Rosetta account\n"
        "\n" % (person.displayname, address)) + body)
    smtp.quit()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        "-g", "--given-name", dest="given", help="Given name")
    parser.add_option(
        "-f", "--family-name", dest="family", help="Family name")
    parser.add_option(
        "-d", "--display-name", dest="display", help="Display name")
    parser.add_option(
        "-e", "--email", dest="email", help="Email address")
    parser.add_option(
        "-p", "--password", dest="password", help="Optional password")
    parser.add_option(
        "-s", "--send-email", dest="send_email", help="Email the new user",
        action="store_true", default=False)
    (options, args) = parser.parse_args()

    # If we get all needed options...
    if not None in (options.given, options.family, options.display,
            options.email):
        person, password, encrypted_password = createUser(
            givenName = options.given,
            familyName = options.family,
            displayname = options.display,
            email = options.email,
            password = options.password)

        print "New user created."
        print "ID: %d" % person.id
        print "Password: " + password
        print "Encrypted password: " + encrypted_password

        if options.send_email:
            print "Sending email to %s..." % options.email
            send_email(person, options.email, password)
    else:
        # XXX daniels 2004-12-14: We should do this message more descriptive.
        print "Please, review the command line, we need more options..."

