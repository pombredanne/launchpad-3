#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Guess the creation rationale for existing unvalidated profiles.

Look in tables like POSubmission and SourcePackageRelease for references to
unvalidated profiles, as these were probably created in order to create the
POSubmission or SourcePackageRelease entries that refer to them.

Also look for unvalidated profiles with a preferred email, as these were
probably created by the bugzilla-importer script.
"""

import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.lp.dbschema import PersonCreationRationale

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts import logger, logger_options
from canonical.launchpad.interfaces import IPersonSet

from canonical.launchpad.database import SourcePackageRelease, Person


def getFirstUploadedPackage(person):
    """Return the first SourcePackageRelease having this person as the
    maintainer or creator.

    Return None if there's no SourcePackageRelease with this person as
    maintainer or creator.

    The first SourcePackageRelease will be that with the oldest dateuploaded.
    """
    query = """
        (SourcePackageRelease.maintainer = %(person)s OR
         SourcePackageRelease.creator = %(person)s
        ) AND
        SourcePackageRelease.id IN (
            SELECT DISTINCT ON (uploaddistrorelease, sourcepackagename)
                   sourcepackagerelease.id
              FROM sourcepackagerelease
              ORDER BY uploaddistrorelease, sourcepackagename, 
                       dateuploaded
        ) """ % sqlvalues(person=person)
    return SourcePackageRelease.selectFirst(
        query,
        orderBy=['SourcePackageRelease.dateuploaded',
                 'SourcePackageRelease.id'])


def getUnvalidatedProfileIDs():
    """Return the IDs of all unvalidated Launchpad profiles.

    The unvalidated profiles are the ones not present in the
    ValidPersonOrTeamCache view.
    """
    query = """
        SELECT id FROM Person 
        EXCEPT 
        SELECT id FROM ValidPersonOrTeamCache
        """
    conn = Person._connection
    return [id for (id,) in conn.queryAll(query)]


def main():
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments: %s" % repr(arguments))

    execute_zcml_for_scripts()

    log = logger(options, 'guess-person-creation-rationale')
    log.info("Updating the creation rationale of Launchpad profiles.")

    ztm = initZopeless(dbuser='launchpad', implicitBegin=False)
    personset = getUtility(IPersonSet)
    ztm.begin()
    unvalidated_profile_ids = getUnvalidatedProfileIDs()
    ztm.abort()

    updated_profiles_by_rationale = {}
    non_updated_profiles = 0
    rationale = PersonCreationRationale
    for profile_id in unvalidated_profile_ids:
        ztm.begin()
        profile = personset.get(profile_id)
        if profile.is_valid_person:
            # Wow, somebody validated this profile since we started running
            # this script; no need to set its creation rationale, then.
            ztm.abort()
            continue

        if profile.creation_rationale != rationale.UNKNOWN:
            log.info(
                "Profile with id %s and name %s already had a creation "
                "rationale: %s" % sqlvalues(profile, profile.name,
                                            profile.creation_rationale.name))
            ztm.abort()
            continue

        pkg = getFirstUploadedPackage(profile)
        if pkg is not None:
            profile.creation_rationale = rationale.SOURCEPACKAGEIMPORT
            profile.creation_comment = (
                'when the %s package was imported into %s'
                % (pkg.sourcepackagename.name,
                   pkg.uploaddistrorelease.displayname))

        touched_pofiles = profile.touched_pofiles
        if touched_pofiles:
            if profile.creation_rationale == rationale.SOURCEPACKAGEIMPORT:
                # The rationale was set above, but this profile could also
                # have been created by the pofile importer; let's log it.
                log.info("Profile with id %s and name %s has references from "
                         "both SourcePackageRelease and POSubmission tables."
                         % sqlvalues(profile, profile.name))
            else:
                pofile = touched_pofiles[0]
                profile.creation_rationale = rationale.POFILEIMPORT
                profile.creation_comment = (
                    'when importing the %s' % pofile.title)

        # The bugzilla-import script had to set the preferredemail of a lot of
        # unvalidated profiles, in order to them to get notifications about
        # the bugs they were subscribed to. This is not a problem since we
        # knew these addresses had been confirmed on bugzilla, but still,
        # these profiles are unvalidated ones since they can't be used to log
        # into Launchpad as they don't have a password.
        if profile.preferredemail is not None:
            if profile.creation_rationale != rationale.UNKNOWN:
                # The rationale was set above, but this profile could also
                # have been created by the bugzilla importer. In fact, its
                # preferred email can only have been set by the bugzilla
                # importer; let's log it.
                log.info(
                    "Profile with id %s and name %s has references from the "
                    "POSubmission or SourcePackageRelease tables and could "
                    "also have been created by the bugzilla import of Ubuntu "
                    "bugs." % sqlvalues(profile, profile.name))
            else:
                profile.creation_rationale = rationale.BUGIMPORT
                profile.creation_comment = (
                    'when importing bugs from http://bugzilla.ubuntu.com/')

        creation_rationale = profile.creation_rationale
        if creation_rationale != rationale.UNKNOWN:
            count = updated_profiles_by_rationale.setdefault(
                creation_rationale, 0)
            updated_profiles_by_rationale[creation_rationale] = count + 1
        else:
            non_updated_profiles += 1

        ztm.commit()

    for rationale, count in updated_profiles_by_rationale.items():
        log.info("Updated %d profiles with the %s rationale"
                 % (count, rationale.name))
    log.info("%d profiles were not updated" % non_updated_profiles)


if __name__ == '__main__':
    main()
