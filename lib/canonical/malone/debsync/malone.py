"""Malone / Debbugs Interface

Based on debzilla/bugzilla.py by Matt Zimmerman

(c) Canonical Ltd 2004
"""

from canonical.launchpad.database import *
from canonical.database.sqlbase import quote
from canonical.lp.encoding import guess as ensure_unicode
from sets import Set


class Launchpad:
    
    def __init__(self):
        # get the debbugs remote bug tracker id
        self.debtrackerid = list(BugTracker.select("name='debbugs'"))[0].id

    def get_distribution_by_name(self, name):
        return Distribution.selectBy(name=name)[0]

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
        try: return BugWatch.select(query)[0]
        except: return None

    def add_debbug_watch(self, malone_bug, debian_bug, owner):
        newwatch = BugWatch(bug=malone_bug.id,
                            remotebug=str(debian_bug.id),
                            owner=owner,
                            bugtracker=debtrackerid
                            )

    def get_bugtracker_by_baseurl(self, baseurl):
        query = "baseurl = %s" % quote(baseurl)
        try: return BugTracker.select(query)[0]
        except: return None

    def get_msg_by_msgid(self, msgid):
        query = "rfc822msgid = %s" % quote(msgid)
        try: return Message.select(query)[0]
        except: return None

    def get_malonebug_for_debbug(self, debian_bug):
        """Return a malone bugfor a debian bug number,
        based on the bug watches."""
        try:
            return BugWatch.select("""
               bugtracker = %d AND
               remotebug = %s
               """ % (self.debtrackerid, quote(str(debian_bug.id)))).bug
        except:
            return None
 
    def link_bug_and_message(self, bug, msg):
        bugmsg = BugMessage(bug=bug.id, message=msg.id)
        return bugmsg

    def get_bug_task_for_package(self, bug, package):
        for bugtask in bug.tasks:
            if bugtask.sourcepackage.name == package:
                return bugtask
        return None

    def add_bug_task(self, bug, distro, package, status, owner):
        newbugtask = BugTask(bug=bug.id,
                             sourcepackage=package.id,
                             bugstatus=status,
                             owner=owner)

    def bug_message_ids(self, bug):
        """Return a list of message IDs found embedded in comments for
        the specified bug"""
        return [msg.rfc822msgid for msg in bug.messages]

    def get_all_messageids(self):
        """Return a list of all known messageids"""
        return [msg.rfc822msgid for msg in Message.select()]

    def sourcepackages(self, distroname):
        """return a dictionary mapping sourcepackagename to a sourcepackage in
        the given distribution"""
        # XXX this should rather look at the publishing table
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
        try: return SourcePackage.select(query, clauseTables=clauseTables)[0]
        except: return None

    def get_sourcepackagename_by_name(self, srcpkgname):
        query = "name = %s" % quote(srcpkgname)
        try: return SourcePackageName.select(query)[0]
        except: return None

    def get_distro_by_name(self, distroname):
        query = "name = %s" % quote(distroname)
        try: return Distribution.select(query)[0]
        except: return None

    def XXXget_message_by_id(self, message_id):
        query = "rfc822msgid = %s" % quote(message_id)
        try: return Message.select(query)[0]
        except: return None

    def add_message(self, message, owner):
        msgid = message['message-id']
        if msgid is None:
            return None
        title=message.get('subject', None)
        if not title:
            print '\t\tERROR getting message title for %s ' % msgid
            title = 'debbugs message'
        title = ensure_string_format(title)
        contents = ensure_string_format(message.as_string())
        newmsg = Message(title=title,
                         contents=contents,
                         rfc822msgid=msgid,
                         owner=owner)
        return newmsg
        
    def add_sourcepackage(self, srcpkgname, distroname, maintainer):
        if get_sourcepackagename(srcpkgname) is None:
            srcpkgname_id = SourcePackageName(name=srcpkgname).id
        else:
            srcpkgname_id = get_sourcepackagename(srcpkgname).id
        distribution = get_distro(distroname)
        if distribution is None:
            raise Error, 'Unknown distribution "%s"' % distroname
        newsrcpkg = get_sourcepackage(srcpkgname, distroname)
        if newsrcpkg is None:
            newsrcpkg = SourcePackage(maintainer=maintainer,
                                      shortdesc=distroname+' package '+srcpkgname,
                                      description=distroname +' package '+srcpkgname,
                                      distro=distribution.id,
                                      sourcepackagename=srcpkgname_id,
                                      srcpackageformat=1)
        return newsrcpkg


