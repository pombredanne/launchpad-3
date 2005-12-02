# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""A module for CodeOfConduct (CoC) related classes.

https://wiki.launchpad.canonical.com/CodeOfConduct
"""

__metaclass__ = type
__all__ = ['CodeOfConduct', 'CodeOfConductSet', 'CodeOfConductConf',
           'SignedCodeOfConduct', 'SignedCodeOfConductSet']

import os
from sha import sha
from datetime import datetime

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.database.sqlbase import SQLBase, quote, flush_database_updates
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.interfaces import (
    ICodeOfConduct, ICodeOfConductSet, ICodeOfConductConf,
    ISignedCodeOfConduct, ISignedCodeOfConductSet, IGPGHandler,
    IGPGKeySet, NotFoundError, GPGVerificationError)


class CodeOfConduct:
    """CoC class model.

    A set of properties allow us to properly handle the CoC stored
    in the filesystem, so it's not a database class.
    """

    implements(ICodeOfConduct)

    def __init__(self, version):
        self.version = version
        # verify if the respective file containing the code of conduct exists
        if not os.path.exists(self._filename):
            # raise something sane
            raise NotFoundError(version)

    @property
    def title(self):
        """Return preformatted title (config_prefix + version)."""

        ## XXX: cprov 20050218
        ## Missed doctest, problems initing ZopeComponentLookupError

        # Recover the prefix for CoC from a Component
        prefix = getUtility(ICodeOfConductConf).prefix

        # Build a fancy title
        return '%s' % prefix + self.version

    @property
    def content(self):
        """Return the content of the CoC file."""
        fp = open(self._filename)
        data = fp.read()
        fp.close()

        return data

    @property
    def current(self):
        """Is this the current release of the Code of Conduct?"""
        return getUtility(ICodeOfConductConf).currentrelease == self.version

    @property
    def _filename(self):
        """Rebuild filename according the local version."""
        # Recover the path for CoC from a Component
        path = getUtility(ICodeOfConductConf).path
        return os.path.join(path, self.version + '.txt')

    
class CodeOfConductSet:
    """A set of CodeOfConducts."""

    implements(ICodeOfConductSet)

    title = 'Launchpad Codes of Conduct'

    def __getitem__(self, version):
        """See ICodeOfConductSet."""
        # Create an entry point for the Admin Console
        # Obviously we are excluding a CoC version called 'console'
        if version == 'console':
            return SignedCodeOfConductSet()
        # in normal conditions return the CoC Release
        try:
            return CodeOfConduct(version)
        except NotFoundError:
            return None
        
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
    currentrelease = '1.0'
    datereleased = '2005/04/12'

class SignedCodeOfConduct(SQLBase):
    """Code of Conduct."""

    implements(ISignedCodeOfConduct)

    _table = 'SignedCodeOfConduct'

    owner = ForeignKey(foreignKey="Person", dbName="owner", notNull=True)

    signedcode = StringCol(dbName='signedcode', notNull=False, default=None)

    signingkey = ForeignKey(foreignKey="GPGKey", dbName="signingkey",
                            notNull=False, default=None)

    datecreated = UtcDateTimeCol(dbName='datecreated', notNull=True,
                                 default=UTC_NOW)

    recipient = ForeignKey(foreignKey="Person", dbName="recipient",
                           notNull=False, default=None)

    admincomment = StringCol(dbName='admincomment', notNull=False,
                             default=None)

    active = BoolCol(dbName='active', notNull=True, default=False)

    @property
    def displayname(self):
        """Build a Fancy Title for CoC."""
        displayname = self.datecreated.strftime('%Y-%m-%d')

        if self.signingkey:
            displayname += (' (DIGITALLY SIGNED by %s)'
                            % self.signingkey.displayname)
        else:
            displayname += (' (PAPER SUBMITTED by %s)'
                            % self.recipient.browsername)

        return displayname

    def sendAdvertisementEmail(self, subject, content):
        """See ISignedCodeOfConduct."""
        assert self.owner.preferredemail
        template = open('lib/canonical/launchpad/emailtemplates/'
                        'signedcoc-acknowledge.txt').read()
        fromaddress = "Launchpad Code Of Conduct System <noreply@ubuntu.com>"
        replacements = {'user': self.owner.browsername,
                        'content': content}
        message = template % replacements
        simple_sendmail(fromaddress, self.owner.preferredemail.email, subject,
                        message)


class SignedCodeOfConductSet:
    """A set of CodeOfConducts"""

    implements(ISignedCodeOfConductSet)

    title = 'Code of Conduct Administrator Page'

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
        gpghandler = getUtility(IGPGHandler)

        try:
            sane_signedcode = signedcode.encode('utf-8')
        except UnicodeEncodeError:
            raise TypeError('Signed Code Could not be encoded as UTF-8')

        try:
            sig = gpghandler.getVerifiedSignature(sane_signedcode)
        except GPGVerificationError, e:
            return str(e)

        if not sig.fingerprint:
            return ('Failed to verify the signature, check if the GPG key '
                    'you used to sign is correctly published in the global '
                    'key ring.')

        gpgkeyset = getUtility(IGPGKeySet)

        gpg = gpgkeyset.getByFingerprint(sig.fingerprint)

        if not gpg:
            return ('The key you used, which has the fingerprint <kbd>%s'
                    '</kbd>, is not registered in Launchpad. Please '
                    '<a href="%s/+editgpgkeys">follow the '
                    'instructions</a> and try again.'
                    % (sig.fingerprint, canonical_url(user)))

        if gpg.owner.id != user.id:
            return ('GPG key onwer (%s) and current Launchpad user (%s) '
                    'does not match.' % (gpg.owner.displayname,
                                         user.displayname))
        
        if not gpg.active:
            return ('The GPG key used to sign (%s) has been deactivated. '
                    'Please <a href="%s/+editgpgkeys">reactivate</a> it '
                    'again before proceeding.'
                    % (gpg.displayname, canonical_url(user)))

        # recover the current CoC release
        coc = CodeOfConduct(getUtility(ICodeOfConductConf).currentrelease)
        current = coc.content

        # calculate text digest
        if sig.plain_data.split() != current.split():
            return ('The signed text does not match the Code of Conduct. '
                    'Make sure that you signed the correct text (white '
                    'space differences are acceptable.')

        # Store the signature 
        signed = SignedCodeOfConduct(owner=user.id, signingkey=gpg.id,
                                     signedcode=signedcode, active=True)

        # Send Advertisement Email
        subject = 'Launchpad: Code of Conduct Signature Acknowledge'
        content = ('Digitally Signed by %s\n' % sig.fingerprint)
        signed.sendAdvertisementEmail(subject, content)


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

        # the name shoudl work like a filter, if you don't enter anything
        # you get everything.
        if displayname:
            query +=' AND Person.fti @@ ftq(%s)' % quote(displayname)

        # Attempt to search for directive
        if searchfor == 'activeonly':
            query += ' AND SignedCodeOfConduct.active = true'

        elif searchfor == 'inactiveonly':
            query += ' AND SignedCodeOfConduct.active = false'

        return SignedCodeOfConduct.select(query, clauseTables=clauseTables,
                                          orderBy='SignedCodeOfConduct.active')

    def searchByUser(self, user_id, active=True):
        """See ISignedCodeOfConductSet."""
        return SignedCodeOfConduct.selectBy(ownerID=user_id,
                                            active=active)

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
                    % (state, admincomment, recipient.browsername))

        sign.sendAdvertisementEmail(subject, content)

        flush_database_updates()

    def acknowledgeSignature(self, user, recipient):
        """See ISignedCodeOfConductSet."""
        active = True
        sign = SignedCodeOfConduct(owner=user.id, recipient=recipient.id,
                                   active=active)
        
        subject = 'Launchpad: Code Of Conduct Signature Acknowledge'
        content = 'Paper Submitted acknowledge by %s' % recipient.browsername

        sign.sendAdvertisementEmail(subject, content)


    def getLastAcceptedDate(self):
        """See ISignegCodeOfConductSet."""
        conf = getUtility(ICodeOfConductConf)
        return datetime(
            *[int(item) for item in conf.datereleased.strip().split('/')])
