# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""A module for CodeOfConduct (CoC) related classes.

https://wiki.launchpad.canonical.com/CodeOfConduct
"""

__metaclass__ = type
__all__ = ['CodeOfConduct', 'CodeOfConductSet', 'CodeOfConductConf',
           'SignedCodeOfConduct', 'SignedCodeOfConductSet',
           'sendAdvertisementEmail']

import os
from datetime import datetime
from sha import sha

from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.database.sqlbase import SQLBase, quote, flush_database_updates
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.mail.sendmail import simple_sendmail

from canonical.launchpad.interfaces import \
    ICodeOfConduct, ICodeOfConductSet, ICodeOfConductConf, \
    ISignedCodeOfConduct, ISignedCodeOfConductSet, IGpgHandler


class CodeOfConduct:
    """CoC class model.

    A set of properties allow us to properly handle the CoC stored
    in the filesystem, so it's not a database class.
    """

    implements(ICodeOfConduct)

    def __init__(self, version):
        self.version = version

    def title(self):
        """Return preformatted title (config_prefix + version)."""

        ## XXX: cprov 20050218
        ## Missed doctest, problems initing ZopeComponentLookupError

        # Recover the prefix for CoC from a Component
        prefix = getUtility(ICodeOfConductConf).prefix

        # Build a fancy title
        return prefix + self.version 
    title = property(title)

    def content(self):
        """Return the content of the CoC file."""
        # Recover the path for CoC from a Component
        path = getUtility(ICodeOfConductConf).path

        # Rebuild filename
        filename = os.path.join(path, self.version + '.txt')

        try:
            fp = open(filename)
        except IOError, e:
            if e.errno == errno.EEXIST:
                # File not found means the requested CoC was not found.
                raise NotFoundError('CoC Release Not Found')

            # All other IOErrors are a problem, though.
            raise
        else:
            data = fp.read()
            fp.close()

        return data
    content = property(content)

    def current(self):
        """Is this the current release of the Code of Conduct?"""
        return getUtility(ICodeOfConductConf).current == self.version
    current = property(current)


class CodeOfConductSet:
    """A set of CodeOfConducts."""

    implements(ICodeOfConductSet)

    title = 'Codes of Conduct Page'

    def __getitem__(self, version):
        """See ICodeOfConductSet."""
        # Create an entry point for the Admin Console
        # Obviously we are excluding a CoC version called 'console'
        if version == 'console':
            return SignedCodeOfConductSet()
        # in normal conditions return the CoC Release
        return CodeOfConduct(version)

    def __iter__(self):
        """See ICodeOfConductSet."""
        releases = []

        # Recover the path for CoC from a component
        cocs_path = getUtility(ICodeOfConductConf).path

        # iter through files and store the the CoC Object
        for filename in os.listdir(cocs_path):
            # Select the correct filenames
            if filename.endswith('.txt'):
                # Extract the version from filename
                version = filename.replace('.txt', '')
                releases.append(CodeOfConduct(version))

        # Return the available list of CoCs objects
        return iter(releases)


class CodeOfConductConf:
    """Abstract Component to store the current CoC configuration."""

    implements(ICodeOfConductConf)

    ## XXX: cprov 20050217
    ## Integrate this class with LaunchpadCentral configuration
    ## in the future

    path = 'lib/canonical/launchpad/codesofconduct/'
    prefix = 'Ubuntu Code of Conduct - '
    current = '1.0'


class SignedCodeOfConduct(SQLBase):
    """Code of Conduct."""

    implements(ISignedCodeOfConduct)

    _table = 'SignedCodeOfConduct'

    owner = ForeignKey(foreignKey="Person", dbName="owner", notNull=True)

    signedcode = StringCol(dbName='signedcode', notNull=False, default=None)

    signingkey = ForeignKey(foreignKey="GPGKey", dbName="signingkey",
                            notNull=False, default=None)

    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=False,
                                 default=UTC_NOW)

    recipient = ForeignKey(foreignKey="Person", dbName="recipient",
                           notNull=False, default=None)

    admincomment = StringCol(dbName='admincomment', notNull=False,
                             default=None)

    active = BoolCol(dbName='active', notNull=False, default=False)

    def displayName(self):
        """Build a Fancy Title for CoC."""
        # XXX: cprov 20040224
        # We need the proposed field 'version'
        displayname = '%s' % self.owner.displayname

        if self.signingkey:
            displayname += '(%s)' % self.signingkey.keyid
        else:
            displayname += '(PAPER)'

        if self.active:
            displayname += '[ACTIVE]'
        else:
            displayname += '[DEACTIVE]'

        return displayname
    displayname = property(displayName)

    # XXX cprov 20050301
    # Might be replace for something similar to displayname
    title = 'Signed Code of Conduct Page'


class SignedCodeOfConductSet:
    """A set of CodeOfConducts"""

    implements(ISignedCodeOfConductSet)

    # XXX cprov 20050301
    # Might be replace for something similar to displayname
    title = 'Signed Codes of Conduct Set Page'

    def __getitem__(self, id):
        """Get a Signed CoC Entry."""
        return SignedCodeOfConduct.get(id)


    def __iter__(self):
        """Iterate through the Signed CoC."""
        return iter(SignedCodeOfConduct.select())

    def verifyAndStore(self, user, signedcode):
        """See ISignedCodeOfConductSet."""
        # XXX cprov 20050224
        # Are we missing the version field in SignedCoC table ?
        # how to figure out how CoC version is signed ?

        # XXX: cprov 20050227
        # To be implemented:
        # * Valid Person (probably always true via permission lp.AnyPerson),
        # * Valid GPGKey (valid and active),
        # * Person and GPGkey matches (done on DB side too),
        # * CoC is the current version available, or the previous
        #   still-supported version in old.txt,
        # * CoC was signed (correctly) by the GPGkey.

        # use a utility to perform the GPG operations
        gpghandler = getUtility(IGpgHandler)
        fingerprint, plain = gpghandler.verifySignature(signedcode)

        if not fingerprint:
            return 'Failed to verify the signature'

        # XXX cprov 20050328
        # Do not support multiple keys
        gpg = user.gpgkeys[0]

        if fingerprint != gpg.fingerprint:
            return ('User and Signature do not match.\n'
                    'Sig %s != User %s' % (fingerprint, gpg.fingerprint))

        if gpg.revoked:
            return  'Signed with a revoked Key.'

        # recover the current CoC release
        coc = CodeOfConduct(getUtility(ICodeOfConductConf).current)
        current = coc.content

        # calculate text digest 
        plain_dig = sha(plain).hexdigest()
        current_dig = sha(current).hexdigest()

        if plain_dig != current_dig:
            return ('CoCs digest do not match: %s vs. %s'
                     % (plain_dig, current_dig))

        subject = 'Launchpad: Code of Conduct Signature Acknowledge'
        content = ('Digitally Signed by %s\n\n'
                   '----- Signed Code Of Conduct -----\n'
                   '%s\n'
                   '-------------- End ---------------\n'
                   % (fingerprint, plain))
        # Send Advertisement Email
        sendAdvertisementEmail(user, subject, content)

        # Store the signature 
        SignedCodeOfConduct(owner=user.id, signingkey=gpg.id,
                            signedcode=signedcode, active=True)

    def searchByDisplayname(self, displayname, searchfor=None):
        """See ISignedCodeOfConductSet."""
        clauseTables = ['Person']

        # XXX: cprov 20050227
        # FTI presents problems when query by incomplete names
        # and I'm not sure if the best solution here is to use
        # trivial ILIKE query. Oppinion required on Review.

        # glue Person and SignedCoC table
        query = 'SignedCodeOfConduct.owner = Person.id'

        # XXX cprov 20050302
        # I'm not sure if the it is correct way to query ALL
        # entries. If it is it should be part of FTI queries,
        # isn't it ?

        # if displayname was '%' return all SignedCoC entries
        if displayname != '%':
            query +=' AND Person.fti @@ ftq(%s)' % quote(displayname)

        # Attempt to search for directive
        if searchfor == 'activeonly':
            query += ' AND SignedCodeOfConduct.active = true'

        elif searchfor == 'inactiveonly':
            query += ' AND SignedCodeOfConduct.active = false'

        return SignedCodeOfConduct.select(query, clauseTables=clauseTables,
                                          orderBy='SignedCodeOfConduct.active')

    def searchByUser(self, user_id):
        """See ISignedCodeOfConductSet."""
        return list(SignedCodeOfConduct.selectBy(ownerID=user_id))

    def modifySignature(self, sign_id, recipient, admincomment, state):
        """See ISignedCodeOfConductSet."""
        sign = SignedCodeOfConduct.get(sign_id)
        sign.active = state
        sign.admincomment = admincomment
        sign.recipient = recipient.id

        subject = 'Launchpad: Code Of Conduct Signature Modified'
        content = ('State: %s\n'
                   'Comment: %s\n'
                   'Modified by %s'
                    % (state, admincomment, recipient.displayname))

        # Send Advertisement Email if preferredemail is set.
        if sign.owner.preferredemail:
            sendAdvertisementEmail(sign.owner, subject, content)

        flush_database_updates()

    def acknowledgeSignature(self, user, recipient):
        """See ISignedCodeOfConductSet."""
        active = True

        subject = 'Launchpad: Code Of Conduct Signature Acknowledge'
        content = 'Paper Submitted acknowledge by %s' % recipient.displayname

        # Send Advertisement Email if preferredemail is set
        if user.preferredemail:
            sendAdvertisementEmail(user, subject, content)

        SignedCodeOfConduct(owner=user.id, recipient=recipient.id,
                            active=active)

def sendAdvertisementEmail(user, subject, content):
    template = open('lib/canonical/launchpad/emailtemplates/'
                    'signedcoc-acknowledge.txt').read()

    fromaddress = "Launchpad Code Of Conduct System <noreply@ubuntu.com>"

    replacements = {'user': user.displayname,
                    'content': content}

    message = template % replacements

    simple_sendmail(fromaddress, user.preferredemail.email, subject, message)

