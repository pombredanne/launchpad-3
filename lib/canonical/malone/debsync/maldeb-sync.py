#!/usr/bin/python

import sys
import debbugs
import email
import email.Message
import email.Generator
from email.Utils import parsedate_tz, mktime_tz, parseaddr
import cStringIO
from sets import Set
import urlparse
import urllib
import urllib2
import re
import StringIO
import sys

import ginalog
from canonical.lp import initZopeless
from canonical.database.sqlbase import quote
ztm = initZopeless()
from canonical.lp.dbschema import *
from canonical.launchpad.database import BugFactory
from canonical.launchpad.scripts.nicole.database import Doap

from malone import Launchpad

# TODO:
#  - make sure Messages are created with the correct createdate and owner

# setup core values and defaults
deb = debbugs.Database('/srv/debzilla.no-name-yet.com/debbugs')
doap = Doap()
debian = Launchpad.get_distribution_by_name('debian')
ubuntu = Launchpad.get_distribution_by_name('ubuntu')

# setup mappings of source package names and binary package names
sourcepackageset = Set([ package[1] for package in ginalog.packages ])
binarypackagedict = dict(ginalog.packages)

statusmap = {'open': BugAssignmentStatus.NEW.value,
             'forwarded': BugAssignmentStatus.ACCEPTED.value,
             'done': BugAssignmentStatus.FIXED.value,
             }

bugzillaref = re.compile(r'(https?://.+/)show_bug.cgi.+id=(\d+).*')
msgidset = get_msgid_set()
newbugs = 0

def main():
    if len(sys.argv) > 1:
        # Import specified Debian bugs
        for arg in sys.argv[1:]:
            import_id(int(arg))
    else:
        # Sync everything
        sync()
    ztm.commit()


def get_source_package(pkgname):
    if pkgname in sourcepackageset:
        return doap.get_sourcepackagename_by_name(pkgname)
    srcpkgname = binarypackagedict.get(pkgname, None)
    return doap.get_sourcepackagename_by_name(srcpkgname)


def bug_filter(bug):
    # this decides which debian bugs will get processed by the sync
    # script.
    # temporarily sync everything
    return True
    #return (bug.id in previousimportset or
    #        (bug.affects_unstable() and
    #         bug.affects_package(ubuntupackageset)))


def sync():

    global newbugs

    print 'Selecting bugs...'
    debian_bugs = filter(bug_filter, deb)
    print len(debian_bugs), 'debian bugs to syncronise.'

    print 'Sorting bugs...'
    debian_bugs.sort(lambda a, b: cmp(a.id, b.id))

    print 'Importing bugs...'
    for debian_bug in debian_bugs:
        import_bug(debian_bug)
        if newbugs>1000:
            print 'Done 1000 new bugs!'
            break


def import_bug(debian_bug):
    global newbugs
    packagelist = debian_bug.packagelist()
    malone_bug = Launchpad.get_malonebug_for_debbug(debian_bug)

    if malone_bug is None:
        comment = """This bug was automatically imported from Debian bug
report #%d""" % debian_bug.id
        try:
            comment += ensure_unicode(get_body_text(debian_bug.emails()[0]))
        except:
            print '\t\tERROR extracting description for debian # %s: ' % \
                debian_bug.id
            return None
        # get the bug details
        title = debian_bug.subject
        if not title:
            title = 'Debian bug %d with unknown title' % debian_bug.id
            print '\t\t' + title
        title = ensure_unicode(title)
        # get the email which started it all
        initemail = debian_bug.emails()[0]
        # get the details of the person who created the debian bug
        debowneraddr = initemail['From']
        debownername, debowneremail = parseaddr(debowneraddr)
        # make sure we have a Person to work with
        owner = doap.ensurePerson(debownername, debowneremail)
        # figure out the date of the debian bug message
        datecreated = mktime_tz(parsedate_tz(initemail['Date']))
        firstpkg = get_source_package(debian_bug.packagelist()[0])
        malone_bug = BugFactory(
                         title=title,
                         comment=comment,
                         rfc822msgid=initemail['Message-ID'],
                         owner=owner, 
                         datecreated=datecreated,
                         )
        newbugs += 1
        # create a debwatch for this bug
        thewatch = add_watch(malone_bug, debian_bug, owner)
        print 'Created malone bug %d for debian bug %d' % \
            (malone_bug.id, debian_bug.id)


    print '%d/%s: %s: %s' % (debian_bug.id, malone_bug.id,
                             debian_bug.package, debian_bug.subject)

    # link the bug to the ubuntu package, if it isn't already linked
    for packagename in debian_bug.packagelist():
        if packagename not in sourcepackageset:
            continue
        ubuntu_package = ubuntupackagemap.get(packagename, None)
        if ubuntu_package is not None:
            bugass = get_bug_assignment(malone_bug, ubuntu_package)
            if bugass is None:
                print '\t\tLinking bug %d and package %s' % (malone_bug.id,
                    ubuntu_package.name)
                bugass is add_bug_assignment(malone_bug,
                                             ubuntu_package,
                                             statusmap[debian_bug.status],
                                             # XXX need the correct owner
                                             1)

    known_msg_ids = Set()
    for msg in malone_bug.messages:
        known_msg_ids.add(msg.rfc822msgid)

    for message in debian_bug.emails():
        message_id = message['message-id']

        if message_id in known_msg_ids:
            print "\tSkipping %s, already imported" % message_id
            continue

        print "\tExamining message %s" % message_id

        # make sure we don't process anything too long
        max_comment_size = 32*1024 # Bugzilla default
        if len(message.as_string())>max_comment_size:
            print "\t\tSkipping message: exceeds size limit"

        # check if this message is already in the db at all
        if message_id not in msgidset:
            # create a Message in the db
            print '\t\tAdding message to database.'
            # XXX owner should be the correct one
            lp_msg = add_message(message, 1)
            if lp_msg is None:
                print '\t\tERROR adding message %s to database' % message_id
                continue
            msgidset.add(message_id)
        lp_msg = get_msg_by_msgid(message_id)

        # create the link between the bug and this message
        print '\t\tLinking message %d to bug %d' % (lp_msg.id,
                malone_bug.id)
        bugmsg = link_bug_and_message(malone_bug, lp_msg)

        for item in EmailDigester(message):
            if isinstance(item, Attachment):
                print "\t\tSkipping attachment (not supported yet)"
                #self.bz.add_attachment(bugzilla_id, item.mimetype, item.text)
            elif isinstance(item, Comment):
                # look for bugzilla URL's and create the BugZilla if we need
                # to.
                find_bugzillas(item.text, debian_bug, malone_bug)
                pass
            else:
                raise Exception, 'EmailDigester returned a %s!?' % type(item)

        # now we know about this message for this bug
        known_msg_ids.add(message_id)

        # Mark all merged bugs as duplicates of the lowest-numbered bug
        if len(debian_bug.mergedwith) > 0 and min(debian_bug.mergedwith) > debian_bug.id:
            for merged_id in debian_bug.mergedwith:
                merged_bug = bugmap.get(merged_id, None)
                if merged_bug is not None:
                    # Bug has been imported, go ahead and merge it
                    print "\t\tMarking %d as a duplicate of %d" % (
                        merged_bug.id, malone_bug.id
                        )
                    merged_bug.duplicateof = malone_bug.id
                    # XXX we probably want to trigger an email, or add a
                    # comment, or at least touch the history here


    bugmap[debian_bug.id] = malone_bug
    return malone_bug


def import_id(debian_id):
    print 'Selecting bugs...'
    debian_bugs = filter(None, deb)
    print len(debian_bugs), 'debian bugs to syncronise.'
    for item in debian_bugs:
        if item.id == debian_id:
            import_bug(item)


def get_body_text(message):
    if message.is_multipart():
        return get_body_text(message.get_payload()[0])
    return message.get_payload()

def find_bugzillas(text, debian_bug, malone_bug):
    match = bugzillaref.search(text)
    if match is None:
        return None
    else:
        baseurl = match.group(1)
        remotebug = match.group(2)
    bugtracker = get_bugtracker(baseurl)
    if not bugtracker:
        # create the bug tracker if needed
        name='autozilla%d' % debian_bug.id
        title=quote('Bugzilla related to: %s' % string.join(debian_bug.packagelist(), ', '))
        shortdesc="""This bugtracker was automatically created. Please
            edit the details to get it correct!"""
        contactdetails='unknown how to contact this bug tracker'
        bugtracker = BugTracker(name=name,
            bugtrackertype=1,
            title=title,
            shortdesc=shortdesc,
            baseurl=baseurl,
            contactdetails=contactdetails,
            # XXX can't make me owner of all these too!
            owner=1)
        print 'BugTracker created: %s' % bugtracker.name
    # see if there is a bugwatch for this bug on that bugtracker
    bugwatch = None
    for watch in malone_bug.watches:
        if watch.bugtracker is bugtracker:
            bugwatch = watch
            break
    if bugwatch is None:
        bugwatch = BugWatch(bugtracker=bugtracker.id,
                            bug=malone_bug.id,
                            remotebug=remotebug,
                            # XXX oh dear me again
                            owner=1)
        print '\t\tNew Bugzilla watch created: %d' % bugwatch.id
    return bugwatch

class EmailDigester:
    """Processes an email.Message.Message and breaks it up into Comments and Attachments
    as appropriate for the content."""

    def __init__(self, message):
        self.message = message


    def __iter__(self):
        if self.message.is_multipart():
            # Look for attachments
            
            for part in self.message.get_payload():
                if ('content-disposition' in part and
                    part['content-disposition'].startswith('attachment') and
                    part.get_content_type() not in ('application/pgp-signature',)):

                    if part.is_multipart():
                        yield Attachment(part.get_content_type(), part.as_string())
                    else:
                        yield Attachment(part.get_content_type(),
                                         part.get_payload(),
                                         part.get_filename(None))
                    
        # Output the complete, flattened message as a single comment

        output_message = TrimmedMessage()
        output_message.set_payload(self.message.get_payload())
        for header, value in self.message.items():
            output_message[header] = value
            
        fd = cStringIO.StringIO()
        g = email.Generator.Generator(fd, mangle_from_=False, maxheaderlen=100)
        g.flatten(output_message)
        output_str = fd.getvalue()

        yield Comment(output_str)
        raise StopIteration

class TrimmedMessage(email.Message.Message):
    """An email.Message.Message which only pays attention to certain
    headers, so that only those headers are output, and always in
    the specified order"""

    want_headers = ('message-id', 'date', 'from', 'to', 'cc', 'subject')
            
    def items(self):
        ret = []
        
        # This sucks a little in order to both preserve case, and
        # produce consistent ordering
        for desired_header in self.want_headers:
            
            # this is nicer, but doesn't work, probably
            # because email.Message.Message is not a new-style class
            # :-(
            #for header, value in super(email.Message.Message,self).items():
            
            for header, value in self._headers[:]:
                if header.lower() == desired_header:
                    ret.append((header,value))
        return ret

class Comment:
    """A comment on a bug"""

    def __init__(self, text):
        self.text = text

class Attachment:
    """An attachment for a bug"""

    def __init__(self, mimetype, text, filename=None):
        self.mimetype = mimetype
        self.text = text
        self.filename = filename

if __name__ == '__main__':
    main()


