"""Malone / Debbugs Interface

Based on debzilla/bugzilla.py by Matt Zimmerman

(c) Canonical Ltd 2004
"""

import sys
import psycopg2

from canonical.launchpad.database import *
from canonical.launchpad.validators.name import valid_name
from canonical.foaf.nickname import generate_nick
from canonical.database.sqlbase import quote
from canonical import guess as ensure_unicode
from canonical.lp.dbschema import EmailAddressStatus
from sets import Set



class Launchpad:
    
    def ensure_sourcepackagename(self, name):
        name = name.strip().lower()
        if not valid_name(name):
            raise ValueError, "'%s' is not a valid name" % name
        try:
            return SourcePackageName.selectBy(name=name)[0]
        except IndexError:
            return SourcePackageName(name=name)

    def ensure_binarypackagename(self, name):
        name = name.strip().lower()
        if not valid_name(name):
            raise ValueError, "'%s' is not a valid name" % name
        try:
            return BinaryPackageName.selectBy(name=name)[0]
        except IndexError:
            return BinaryPackageName(name=name)

    def all_deb_watches(self):
        """Return a list of all debian bug numbers being watched by
        Malone"""
        watchlist = BugWatch.select("bugtracker = %d" % self.debtrackerid)
        return [int(watch.remotebug) for watch in watchlist]

    def get_watch_on_debbug(self, debian_bug):
        query = """remotebug = %s AND 
                   bugtracker = %d
                   """ % (quote(str(debian_bug.id)),
                          self.debtrackerid)
        try:
            return BugWatch.select(query)[0]
        except IndexError:
            return None

    def add_debbug_watch(self, malone_bug, debian_bug, owner):
        newwatch = BugWatch(bug=malone_bug.id,
                            remotebug=str(debian_bug.id),
                            owner=owner,
                            bugtracker=self.debtrackerid
                            )

    def get_bugtracker_by_baseurl(self, baseurl):
        query = "baseurl = %s" % quote(baseurl)
        try:
            return BugTracker.select(query)[0]
        except IndexError:
            return None

    def get_msg_by_msgid(self, msgid):
        query = "rfc822msgid = %s" % quote(msgid)
        try:
            return Message.select(query)[0]
        except IndexError:
            return None

    def link_bug_and_message(self, bug, msg):
        bugmsg = BugMessage(bug=bug.id, message=msg.id)
        return bugmsg

    def get_bug_task(self, bug, distribution, sourcepackagename):
        for bugtask in bug.bugtasks:
            if (bugtask.sourcepackagename == sourcepackagename and
                bugtask.distribution == distribution):
                return bugtask

        return None

    def add_bug_task(self, bug, distro, srcpackagename, status, owner,
                     datecreated):
        sourcepackagename = srcpackagename.id
        newbugtask = BugTask(
            bug=bug.id,
            distribution=distro.id,
            sourcepackagename=sourcepackagename,
            status=status,
            owner=owner.id,
            datecreated=datecreated)

    def bug_message_ids(self, bug):
        """Return a list of message IDs found embedded in comments for
        the specified bug"""
        return [msg.rfc822msgid for msg in bug.messages]

    def sourcepackages(self, distroname):
        """return a dictionary mapping sourcepackagename to a sourcepackage in
        the given distribution"""
        # XXX David Allouche 2005-01-26:
        # This should rather look at the publishing table.
        clauseTables = ['SourcePackage', 'Distribution']
        query = '''SourcePackage.distro = Distribution.id AND
                   Distribution.name = %s
                ''' % quote(distroname)
        spmap = {}
        for sp in SourcePackage.select(query, clauseTables=clauseTables):
            spmap[sp.sourcepackagename.name] = sp
        return spmap

    def get_sourcepackage(self, srcpkgname, distroname):
        clauseTables = ['Distribution', 'SourcePackage', 'SourcePackageName']
        query = """Distribution.name=%s AND
                   SourcePackage.distro = Distribution.id AND
                   SourcePackage.sourcepackagename = SourcePackageName.id AND
                   SourcePackageName.name = %s
                   """ % ( quote(distroname), quote(srcpkgname) )
        try:
            return SourcePackage.select(query, clauseTables=clauseTables)[0]
        except IndexError:
            return None

    def get_sourcepackagename(self, srcpkgname):
        query = "name = %s" % quote(srcpkgname)
        try:
            return SourcePackageName.select(query)[0]
        except IndexError:
            return None

    def get_binarypackagename(self, srcpkgname):
        query = "name = %s" % quote(srcpkgname)
        try:
            return BinaryPackageName.select(query)[0]
        except IndexError:
            return None

    def get_distro_by_name(self, distroname):
        query = "name = %s" % quote(distroname)
        try:
            return Distribution.select(query)[0]
        except IndexError:
            return None

    def get_message_by_id(self, message_id):
        query = "rfc822msgid = %s" % quote(message_id)
        try:
            return Message.select(query)[0]
        except IndexError:
            return None

    def add_message(self, message, owner, datecreated):
        msgid = message['message-id']
        if msgid is None:
            print 'ERROR: Message has no message-id'
            return None
        title=message.get('subject', None)
        if not title:
            print 'ERROR getting message title for %s ' % msgid
            title = 'message without subject'
        title = ensure_unicode(title)
        contents = ensure_unicode(message.as_string())
        try:
            newmsg = Message(title=title,
                             contents=contents,
                             rfc822msgid=msgid,
                             owner=owner,
                             datecreated=datecreated)
        except psycopg2.ProgrammingError:
            print 'ERROR STORING %s IN DATABASE:' % msgid
            print '    ', sys.exc_value
            return None
        return newmsg


