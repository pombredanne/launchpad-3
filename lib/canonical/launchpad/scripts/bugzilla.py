# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Bugzilla to Launchpad import logic"""


# Bugzilla schema:
# http://lxr.mozilla.org/mozilla/source/webtools/bugzilla/Bugzilla/DB/Schema.pm

# XXX: jamesh 2005-10-18
# Currently unhandled bug info:
#  * Operating system and platform
#  * version (not really used in Ubuntu bugzilla though)
#  * keywords
#  * private bugs (none of the canonical-only bugs seem sensitive though)
#  * bug dependencies
#  * "bug XYZ" references inside comment text (at the moment we just
#    insert the full URL to the bug afterwards).
#
# Not all of these are necessary though

__metaclass__ = type

from cStringIO import StringIO
import re
import logging
import datetime
import pytz

from zope.component import getUtility
from canonical.launchpad.interfaces import (
    BugAttachmentType, BugTaskImportance, BugTaskStatus, CreateBugParams,
    IBugAttachmentSet, IBugSet, IBugTaskSet, IBugWatchSet, ICveSet,
    IEmailAddressSet, ILaunchpadCelebrities, ILibraryFileAliasSet,
    IMessageSet, IPersonSet, NotFoundError, PersonCreationRationale)
from canonical.launchpad.webapp import canonical_url

logger = logging.getLogger('canonical.launchpad.scripts.bugzilla')

def _add_tz(dt):
    """Convert a naiive datetime value to a UTC datetime value."""
    assert dt.tzinfo is None, 'add_tz() only accepts naiive datetime values'
    return datetime.datetime(dt.year, dt.month, dt.day,
                             dt.hour, dt.minute, dt.second,
                             dt.microsecond, tzinfo=pytz.timezone('UTC'))

class BugzillaBackend:
    """A wrapper for all the MySQL database access.

    The main purpose of this is to make it possible to test the rest
    of the import code without access to a MySQL database.
    """
    def __init__(self, conn, charset='UTF-8'):
        self.conn = conn
        self.cursor = conn.cursor()
        self.charset = charset

    def _decode(self, s):
        if s is not None:
            value = s.decode(self.charset, 'replace')
            # Postgres doesn't like values outside of the basic multilingual
            # plane (U+0000 - U+FFFF), so replace them (and surrogates) with
            # U+FFFD (replacement character).
            # Existance of these characters generally indicate an encoding
            # problem in the existing Bugzilla data.
            return re.sub(u'[^\u0000-\ud7ff\ue000-\uffff]', u'\ufffd', value)
        else:
            return None

    def lookupUser(self, user_id):
        """Look up information about a particular Bugzilla user ID"""
        self.cursor.execute('SELECT login_name, realname '
                            '  FROM profiles '
                            '  WHERE userid = %d' % user_id)
        if self.cursor.rowcount != 1:
            raise NotFoundError('could not look up user %d' % user_id)
        (login_name, realname) = self.cursor.fetchone()
        realname = self._decode(realname)
        return (login_name, realname)

    def getBugInfo(self, bug_id):
        """Retrieve information about a bug."""
        self.cursor.execute(
            'SELECT bug_id, assigned_to, bug_file_loc, bug_severity, '
            '    bug_status, creation_ts, short_desc, op_sys, priority, '
            '    products.name, rep_platform, reporter, version, '
            '    components.name, resolution, target_milestone, qa_contact, '
            '    status_whiteboard, keywords, alias '
            '  FROM bugs '
            '    INNER JOIN products ON bugs.product_id = products.id '
            '    INNER JOIN components ON bugs.component_id = components.id '
            '  WHERE bug_id = %d' % bug_id)
        if self.cursor.rowcount != 1:
            raise NotFoundError('could not look up bug %d' % bug_id)
        (bug_id, assigned_to, bug_file_loc, bug_severity, bug_status,
         creation_ts, short_desc, op_sys, priority, product,
         rep_platform, reporter, version, component, resolution,
         target_milestone, qa_contact, status_whiteboard, keywords,
         alias) = self.cursor.fetchone()

        bug_file_loc = self._decode(bug_file_loc)
        creation_ts = _add_tz(creation_ts)
        product = self._decode(product)
        version = self._decode(version)
        component = self._decode(component)
        status_whiteboard = self._decode(status_whiteboard)
        keywords = self._decode(keywords)
        alias = self._decode(alias)

        return (bug_id, assigned_to, bug_file_loc, bug_severity,
                bug_status, creation_ts, short_desc, op_sys, priority,
                product, rep_platform, reporter, version, component,
                resolution, target_milestone, qa_contact,
                status_whiteboard, keywords, alias)

    def getBugCcs(self, bug_id):
        """Get the IDs of the people CC'd to the bug."""
        self.cursor.execute('SELECT who FROM cc WHERE bug_id = %d'
                            % bug_id)
        return [row[0] for row in self.cursor.fetchall()]

    def getBugComments(self, bug_id):
        """Get the comments for the bug."""
        self.cursor.execute('SELECT who, bug_when, thetext '
                            '  FROM longdescs '
                            '  WHERE bug_id = %d '
                            '  ORDER BY bug_when' % bug_id)
        # XXX: jamesh 2005-12-07:
        # Due to a bug in Debzilla, Ubuntu bugzilla bug 248 has > 7800
        # duplicate comments,consisting of someone's signature.
        # For the import, just ignore those comments.
        return [(who, _add_tz(when), self._decode(thetext))
                 for (who, when, thetext) in self.cursor.fetchall()
                 if thetext != '\n--=20\n   Jacobo Tarr=EDo     |     '
                               'http://jacobo.tarrio.org/\n\n\n']

    def getBugAttachments(self, bug_id):
        """Get the attachments for the bug."""
        self.cursor.execute('SELECT attach_id, creation_ts, description, '
                            '    mimetype, ispatch, filename, thedata, '
                            '    submitter_id '
                            '  FROM attachments '
                            '  WHERE bug_id = %d '
                            '  ORDER BY attach_id' % bug_id)
        return [(attach_id, _add_tz(creation_ts),
                 self._decode(description), mimetype,
                 ispatch, self._decode(filename), thedata, submitter_id)
                for (attach_id, creation_ts, description,
                     mimetype, ispatch, filename, thedata,
                     submitter_id) in self.cursor.fetchall()]

    def findBugs(self, product=None, component=None, status=None):
        """Returns the requested bug IDs as a list"""
        if product is None:
            product = []
        if component is None:
            component = []
        if status is None:
            status = []
        joins = []
        conditions = []
        if product:
            joins.append('INNER JOIN products ON bugs.product_id = products.id')
            conditions.append('products.name IN (%s)' %
                ', '.join([self.conn.escape(p) for p in product]))
        if component:
            joins.append('INNER JOIN components ON bugs.component_id = components.id')
            conditions.append('components.name IN (%s)' %
                ', '.join([self.conn.escape(c) for c in component]))
        if status:
            conditions.append('bugs.bug_status IN (%s)' %
                ', '.join([self.conn.escape(s) for s in status]))
        if conditions:
            conditions = 'WHERE %s' % ' AND '.join(conditions)
        else:
            conditions = ''
        self.cursor.execute('SELECT bug_id FROM bugs %s %s ORDER BY bug_id' %
                            (' '.join(joins), conditions))
        return [bug_id for (bug_id,) in self.cursor.fetchall()]

    def getDuplicates(self):
        """Returns a list of (dupe_of, dupe) relations."""
        self.cursor.execute('SELECT dupe_of, dupe FROM duplicates '
                            'ORDER BY dupe, dupe_of')
        return [(dupe_of, dupe) for (dupe_of, dupe) in self.cursor.fetchall()]

class Bug:
    """Representation of a Bugzilla Bug"""
    def __init__(self, backend, bug_id):
        self.backend = backend
        (self.bug_id, self.assigned_to, self.bug_file_loc, self.bug_severity,
         self.bug_status, self.creation_ts, self.short_desc, self.op_sys,
         self.priority, self.product, self.rep_platform, self.reporter,
         self.version, self.component, self.resolution,
         self.target_milestone, self.qa_contact, self.status_whiteboard,
         self.keywords, self.alias) = backend.getBugInfo(bug_id)

        self._ccs = None
        self._comments = None
        self._attachments = None

    @property
    def ccs(self):
        """Return the IDs of people CC'd to this bug"""
        if self._ccs is not None: return self._ccs
        self._ccs = self.backend.getBugCcs(self.bug_id)
        return self._ccs

    @property
    def comments(self):
        """Return the comments attached to this bug"""
        if self._comments is not None: return self._comments
        self._comments = self.backend.getBugComments(self.bug_id)
        return self._comments

    @property
    def attachments(self):
        """Return the attachments for this bug"""
        if self._attachments is not None: return self._attachments
        self._attachments = self.backend.getBugAttachments(self.bug_id)
        return self._attachments

    def mapSeverity(self, bugtask):
        """Set a Launchpad bug task's importance based on this bug's severity."""
        bugtask.importance = {
            'blocker': BugTaskImportance.CRITICAL,
            'critical': BugTaskImportance.CRITICAL,
            'major': BugTaskImportance.HIGH,
            'normal': BugTaskImportance.MEDIUM,
            'minor': BugTaskImportance.LOW,
            'trivial': BugTaskImportance.LOW,
            'enhancement': BugTaskImportance.WISHLIST
            }.get(self.bug_severity, BugTaskImportance.UNKNOWN)

    def mapStatus(self, bugtask):
        """Set a Launchpad bug task's status based on this bug's status.

        If the bug is in the RESOLVED, VERIFIED or CLOSED states, the
        bug resolution is also taken into account when mapping the
        status.

        Additional information about the bugzilla status is appended
        to the bug task's status explanation.
        """
        bug_importer = getUtility(ILaunchpadCelebrities).bug_importer

        if self.bug_status == 'ASSIGNED':
            bugtask.transitionToStatus(
                BugTaskStatus.CONFIRMED, bug_importer)
        elif self.bug_status == 'NEEDINFO':
            bugtask.transitionToStatus(
                BugTaskStatus.INCOMPLETE, bug_importer)
        elif self.bug_status == 'PENDINGUPLOAD':
            bugtask.transitionToStatus(
                BugTaskStatus.FIXCOMMITTED, bug_importer)
        elif self.bug_status in ['RESOLVED', 'VERIFIED', 'CLOSED']:
            # depends on the resolution:
            if self.resolution == 'FIXED':
                bugtask.transitionToStatus(
                    BugTaskStatus.FIXRELEASED, bug_importer)
            else:
                bugtask.transitionToStatus(
                    BugTaskStatus.INVALID, bug_importer)
        else:
            bugtask.transitionToStatus(
                BugTaskStatus.NEW, bug_importer)

        # add the status to the notes section, to account for any lost
        # information
        bugzilla_status = 'Bugzilla status=%s' % self.bug_status
        if self.resolution:
            bugzilla_status += ' %s' % self.resolution
        bugzilla_status += ', product=%s' % self.product
        bugzilla_status += ', component=%s' % self.component

        if bugtask.statusexplanation:
            bugtask.statusexplanation = '%s (%s)' % (bugtask.statusexplanation,
                                                     bugzilla_status)
        else:
            bugtask.statusexplanation = bugzilla_status


class Bugzilla:
    """Representation of a bugzilla instance"""

    def __init__(self, conn):
        if conn is not None:
            self.backend = BugzillaBackend(conn)
        else:
            self.backend = None
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.debian = getUtility(ILaunchpadCelebrities).debian
        self.bugtracker = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla
        self.debbugs = getUtility(ILaunchpadCelebrities).debbugs
        self.bugset = getUtility(IBugSet)
        self.bugtaskset = getUtility(IBugTaskSet)
        self.bugwatchset = getUtility(IBugWatchSet)
        self.cveset = getUtility(ICveSet)
        self.personset = getUtility(IPersonSet)
        self.emailset = getUtility(IEmailAddressSet)
        self.person_mapping = {}

    def person(self, bugzilla_id):
        """Get the Launchpad person corresponding to the given Bugzilla ID"""
        # Bugzilla treats a user ID of 0 as a NULL
        if bugzilla_id == 0:
            return None

        # Try and get the person using a cache of the mapping.  We
        # check to make sure the person still exists and has not been
        # merged.
        person = None
        launchpad_id = self.person_mapping.get(bugzilla_id)
        if launchpad_id is not None:
            person = self.personset.get(launchpad_id)
            if person is not None and person.merged is not None:
                person = None

        # look up the person
        if person is None:
            email, displayname = self.backend.lookupUser(bugzilla_id)

            person = self.personset.ensurePerson(
                email, displayname, PersonCreationRationale.BUGIMPORT,
                comment=('when importing bugs from %s'
                         % self.bugtracker.baseurl))

            # Bugzilla performs similar address checks to Launchpad, so
            # if the Launchpad account has no preferred email, use the
            # Bugzilla one.
            emailaddr = self.emailset.getByEmail(email)
            assert emailaddr is not None
            if person.preferredemail != emailaddr:
                person.validateAndEnsurePreferredEmail(emailaddr)

            self.person_mapping[bugzilla_id] = person.id

        return person

    def _getPackageNames(self, bug):
        """Returns the source and binary package names for the given bug."""
        # we currently only support mapping Ubuntu bugs ...
        if bug.product != 'Ubuntu':
            raise AssertionError('product must be Ubuntu')

        # kernel bugs are currently filed against the "linux"
        # component, which is not a source or binary package.  The
        # following mapping was provided by BenC:
        if bug.component == 'linux':
            cutoffdate = datetime.datetime(2004, 12, 1,
                                           tzinfo=pytz.timezone('UTC'))
            if bug.bug_status == 'NEEDINFO' and bug.creation_ts < cutoffdate:
                pkgname = 'linux-source-2.6.12'
            else:
                pkgname = 'linux-source-2.6.15'
        else:
            pkgname = bug.component.encode('ASCII')

        try:
            srcpkg, binpkg = self.ubuntu.guessPackageNames(pkgname)
        except NotFoundError, e:
            logger.warning('could not find package name for "%s": %s',
                           pkgname, str(e))
            srcpkg = binpkg = None

        return srcpkg, binpkg

    def getLaunchpadBugTarget(self, bug):
        """Returns a dictionary of arguments to createBug() that correspond
        to the given bugzilla bug.
        """
        srcpkg, binpkg = self._getPackageNames(bug)
        return {
            'distribution': self.ubuntu,
            'sourcepackagename': srcpkg,
            }

    def getLaunchpadMilestone(self, bug):
        """Return the Launchpad milestone for a Bugzilla bug.

        If the milestone does not exist, then it is created.
        """
        if bug.product != 'Ubuntu':
            raise AssertionError('product must be Ubuntu')

        # Bugzilla uses a value of "---" to represent "no selected Milestone"
        # Launchpad represents this by setting the milestone column to NULL.
        if bug.target_milestone is None or bug.target_milestone == '---':
            return None

        # generate a Launchpad name from the Milestone name:
        name = re.sub(r'[^a-z0-9\+\.\-]', '-', bug.target_milestone.lower())

        milestone = self.ubuntu.getMilestone(name)
        if milestone is not None:
            return milestone
        else:
            return self.ubuntu.currentseries.newMilestone(name)

    def getLaunchpadUpstreamProduct(self, bug):
        """Find the upstream product for the given Bugzilla bug.

        This function relies on the package -> product linkage having been
        entered in advance.
        """
        srcpkgname, binpkgname = self._getPackageNames(bug)
        # find a product series
        series = None
        for series in self.ubuntu.serieses:
            srcpkg = series.getSourcePackage(srcpkgname)
            if srcpkg:
                series = srcpkg.productseries
                if series:
                    return series.product
        else:
            logger.warning('could not find upstream product for '
                           'source package "%s"', srcpkgname.name)
            return None

    _bug_re = re.compile('bug\s*#?\s*(?P<id>\d+)', re.IGNORECASE)
    def replaceBugRef(self, match):
        # XXX: jamesh 2005-10-24:
        # this is where bug number rewriting would be plugged in
        bug_id = int(match.group('id'))
        url = '%s/%d' % (canonical_url(self.bugtracker), bug_id)
        return '%s [%s]' % (match.group(0), url)


    def handleBug(self, bug_id):
        """Maybe import a single bug.

        If the bug has already been imported (detected by checking for
        a bug watch), it is skipped.
        """
        logger.info('Handling Bugzilla bug %d', bug_id)

        # is there a bug watch on the bug?
        lp_bug = self.bugset.queryByRemoteBug(self.bugtracker, bug_id)

        # if we already have an associated bug, don't add a new one.
        if lp_bug is not None:
            logger.info('Bugzilla bug %d is already being watched by '
                        'Launchpad bug %d', bug_id, lp_bug.id)
            return lp_bug

        bug = Bug(self.backend, bug_id)

        comments = bug.comments[:]

        # create a message for the initial comment:
        msgset = getUtility(IMessageSet)
        who, when, text = comments.pop(0)
        text = self._bug_re.sub(self.replaceBugRef, text)
        # If a URL is associated with the bug, add it to the description:
        if bug.bug_file_loc:
            text = text + '\n\n' + bug.bug_file_loc
        # the initial comment can't be empty:
        if not text.strip():
            text = '<empty comment>'
        msg = msgset.fromText(bug.short_desc, text, self.person(who), when)

        # create the bug
        target = self.getLaunchpadBugTarget(bug)
        params = CreateBugParams(
            msg=msg, datecreated=bug.creation_ts, title=bug.short_desc,
            owner=self.person(bug.reporter))
        params.setBugTarget(**target)
        lp_bug = self.bugset.createBug(params)

        # add the bug watch:
        lp_bug.addWatch(self.bugtracker, str(bug.bug_id), lp_bug.owner)

        # add remaining comments, and add CVEs found in all text
        lp_bug.findCvesInText(text, lp_bug.owner)
        for (who, when, text) in comments:
            text = self._bug_re.sub(self.replaceBugRef, text)
            msg = msgset.fromText(msg.followup_title, text,
                                  self.person(who), when)
            lp_bug.linkMessage(msg)

        # subscribe QA contact and CC's
        if bug.qa_contact:
            lp_bug.subscribe(
                self.person(bug.qa_contact), self.person(bug.reporter))
        for cc in bug.ccs:
            lp_bug.subscribe(self.person(cc), self.person(bug.reporter))

        # translate bugzilla status and severity to LP equivalents
        task = lp_bug.bugtasks[0]
        task.datecreated = bug.creation_ts
        task.transitionToAssignee(self.person(bug.assigned_to))
        task.statusexplanation = bug.status_whiteboard
        bug.mapSeverity(task)
        bug.mapStatus(task)

        # bugs with an alias of the form "deb1234" have been imported
        # from the Debian bug tracker by the "debzilla" program.  For
        # these bugs, generate a task and watch on the corresponding
        # bugs.debian.org bug.
        if bug.alias:
            if re.match(r'^deb\d+$', bug.alias):
                watch = self.bugwatchset.createBugWatch(
                    lp_bug, lp_bug.owner, self.debbugs, int(bug.alias[3:]))
                debtask = self.bugtaskset.createTask(
                    lp_bug,
                    owner=lp_bug.owner,
                    distribution=self.debian,
                    sourcepackagename=target['sourcepackagename'])
                debtask.datecreated = bug.creation_ts
                debtask.bugwatch = watch
            else:
                # generate a Launchpad name from the alias:
                name = re.sub(r'[^a-z0-9\+\.\-]', '-', bug.alias.lower())
                lp_bug.name = name

        # for UPSTREAM bugs, try to find whether the URL field contains
        # a bug reference.
        if bug.bug_status == 'UPSTREAM':
            # see if the URL field contains a bug tracker reference
            watches = self.bugwatchset.fromText(bug.bug_file_loc,
                                                lp_bug, lp_bug.owner)
            # find the upstream product for this bug
            product = self.getLaunchpadUpstreamProduct(bug)

            # if we created a watch, and there is an upstream product,
            # create a new task and link it to the watch.
            if len(watches) > 0:
                if product:
                    upstreamtask = self.bugtaskset.createTask(
                        lp_bug, product=product, owner=lp_bug.owner)
                    upstreamtask.datecreated = bug.creation_ts
                    upstreamtask.bugwatch = watches[0]
                else:
                    logger.warning('Could not find upstream product to link '
                                   'bug %d to', lp_bug.id)

        # translate milestone linkage
        task.milestone = self.getLaunchpadMilestone(bug)

        # import attachments
        for (attach_id, creation_ts, description, mimetype, ispatch,
             filename, thedata, submitter_id) in bug.attachments:
            # if the filename is missing for some reason, use a generic one.
            if filename is None or filename.strip() == '':
                filename = 'untitled'
            logger.debug('Creating attachment %s for bug %d',
                         filename, bug.bug_id)
            if ispatch:
                attach_type = BugAttachmentType.PATCH
                mimetype = 'text/plain'
            else:
                attach_type = BugAttachmentType.UNSPECIFIED

            # look for a message starting with "Created an attachment (id=NN)"
            for msg in lp_bug.messages:
                if msg.text_contents.startswith(
                        'Created an attachment (id=%d)' % attach_id):
                    break
            else:
                # could not find the add message, so create one:
                msg = msgset.fromText(description,
                                      'Created attachment %s' % filename,
                                      self.person(submitter_id),
                                      creation_ts)
                lp_bug.linkMessage(msg)

            filealias = getUtility(ILibraryFileAliasSet).create(
                name=filename,
                size=len(thedata),
                file=StringIO(thedata),
                contentType=mimetype)

            getUtility(IBugAttachmentSet).create(
                bug=lp_bug, filealias=filealias, attach_type=attach_type,
                title=description, message=msg)

        return lp_bug

    def processDuplicates(self, trans):
        """Mark Launchpad bugs as duplicates based on Bugzilla duplicates.

        Launchpad bug A will be marked as a duplicate of bug B if:
         * bug A watches bugzilla bug A'
         * bug B watches bugzilla bug B'
         * bug A' is a duplicate of bug B'
         * bug A is not currently a duplicate of any other bug.
        """
        logger.info('Processing duplicate bugs')
        bugmap = {}
        def getlpbug(bugid):
            """Get the Launchpad bug corresponding to the given remote ID

            This function makes use of a cache dictionary to reduce the
            number of lookups.
            """
            lpbugid = bugmap.get(bugid)
            if lpbugid is not None:
                if lpbugid != 0:
                    lpbug = self.bugset.get(lpbugid)
                else:
                    lpbug = None
            else:
                lpbug = self.bugset.queryByRemoteBug(self.bugtracker, bugid)
                if lpbug is not None:
                    bugmap[bugid] = lpbug.id
                else:
                    bugmap[bugid] = 0
            return lpbug

        for (dupe_of, dupe) in self.backend.getDuplicates():
            # get the Launchpad bugs corresponding to the two Bugzilla bugs:
            trans.begin()
            lpdupe_of = getlpbug(dupe_of)
            lpdupe = getlpbug(dupe)
            # if both bugs exist in Launchpad, and lpdupe is not already
            # a duplicate, mark it as a duplicate of lpdupe_of.
            if (lpdupe_of is not None and lpdupe is not None and
                lpdupe.duplicateof is None):
                logger.info('Marking %d as a duplicate of %d',
                            lpdupe.id, lpdupe_of.id)
                lpdupe.duplicateof = lpdupe_of
            trans.commit()

    def importBugs(self, trans, product=None, component=None, status=None):
        """Import Bugzilla bugs matching the given constraints.

        Each of product, component and status gives a list of
        products, components or statuses to limit the import to.  An
        empty list matches all products, components or statuses.
        """
        if product is None:
            product = []
        if component is None:
            component = []
        if status is None:
            status = []

        bugs = self.backend.findBugs(product=product,
                                     component=component,
                                     status=status)
        for bug_id in bugs:
            trans.begin()
            try:
                self.handleBug(bug_id)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception('Could not import Bugzilla bug #%d', bug_id)
                trans.abort()
            else:
                trans.commit()
