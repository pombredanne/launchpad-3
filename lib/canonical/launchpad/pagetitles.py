# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""This module is used by the Launchpad webapp to determine titles for pages.

https://launchpad.canonical.com/LaunchpadTitles

** IMPORTANT ** (Brad Bollenbach, 2006-07-20) This module should not be
put in webapp, because webapp is not domain-specific, and should not be
put in browser, because this would make webapp depend on browser. SteveA
has a plan to fix this overall soon.

This module contains string or unicode literals assigned to names, or
functions such as this one:

  def bug_index(context, view):
      return 'Bug %s: %s' % (context.id, context.title)

The names of string or unicode literals and functions are the names of
the page templates, but with hyphens changed to underscores.  So, the
function bug_index given about is for the page template bug-index.pt.

If the function needs to include details from the request, this is
available from view.request.  However, these functions should not access
view.request.  Instead, the view class should make a function or
attribute available that provides the required information.

If the function returns None, it means that the default page title for
the whole of Launchpad should be used.  This is defined in the variable
DEFAULT_LAUNCHPAD_TITLE.

There are shortcuts for some common substitutions at the top of this
module.

The strings and functions for page titles are arranged in alphabetical
order after the helpers.

"""
__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILaunchBag, IMaloneApplication, IPerson, IStructuralObjectPresentation)
from canonical.launchpad.webapp import smartquote

DEFAULT_LAUNCHPAD_TITLE = 'Launchpad'

# Helpers.

class BugTaskPageTitle:
    """Return the page title for a BugTask."""
    def __call__(self, context, view):
        return smartquote('%s: "%s"') % (
            IStructuralObjectPresentation(context).getMainHeading(),
            context.bug.title)


class SubstitutionHelper:
    """An abstract class for substituting values into formatted strings."""
    def __init__(self, text):
        self.text = text

    def __call__(self, context, view):
        raise NotImplementedError


class ContextDisplayName(SubstitutionHelper):
    """Return the formatted string with context's displayname."""
    def __call__(self, context, view):
        return self.text % context.displayname


class FilteredTranslationsTitle(SubstitutionHelper):
    """Return the formatted string with context's title and view's person."""
    def __call__(self, context, view):
        if view.person is not None:
            person = view.person.displayname
        else:
            person = 'unknown'
        return self.text % {'title' : context.title,
                            'person' : person }


class ContextId(SubstitutionHelper):
    """Return the formatted string with context's id."""
    def __call__(self, context, view):
        return self.text % context.id


class ContextTitle(SubstitutionHelper):
    """Return the formatted string with context's title."""
    def __call__(self, context, view):
        return self.text % context.title

class ContextBrowsername(SubstitutionHelper):
    """Return the formatted string with context's browsername."""
    def __call__(self, context, view):
        return self.text % context.browsername


class LaunchbagBugID(SubstitutionHelper):
    """Return the formatted string with the bug's id from LaunchBag."""
    def __call__(self, context, view):
        return self.text % getUtility(ILaunchBag).bug.id


class ContextBugId(SubstitutionHelper):
    """Helper to include the context's bug id in the title."""

    def __call__(self, context, view):
        return self.text % context.bug.id


class ViewLabel:
    """Helper to use the view's label as the title."""
    def __call__(self, context, view):
        return view.label


# Functions and strings used as the titles of pages.

archive_admin = ContextTitle('Administer %s')

archive_activate = 'Activate Personal Package Archive'

archive_builds = ContextTitle('Builds for %s')

archive_copy_packages = ContextTitle('Copy packages from %s')

archive_delete_packages = ContextTitle('Delete packages from %s')

archive_edit = ContextTitle('Edit %s')

archive_edit_dependencies = ContextTitle('Edit dependencies for %s')

archive_index = ContextTitle('%s')

bazaar_all_branches = 'All branches in the Launchpad Bazaar'

bazaar_index = 'Launchpad Code'

bazaar_sync_review = (
    'Review upstream repositories for Launchpad Bazaar syncing')

def binarypackagerelease_index(context, view):
    """Return the page title for context's binary packages."""
    return "%s binary package in Launchpad" % context.title

binarypackagenames_index = 'Binary package name set'

bounties_index = 'Bounties registered in Launchpad'

bounty_add = 'Register a bounty'

bounty_edit = ContextTitle(smartquote('Edit bounty "%s"'))

bounty_link = ContextTitle('Link a bounty to %s')

bounty_index = ContextTitle(smartquote('Bounty "%s" in Launchpad'))

bounty_subscription = ContextTitle(smartquote('Subscription to bounty "%s"'))

branch_associations = ContextDisplayName(smartquote(
    '"%s" branch associations'))

branch_delete = ContextDisplayName(smartquote('Delete branch "%s"'))

branch_edit = ContextDisplayName(smartquote('Change "%s" branch details'))

branch_edit_subscription = ContextDisplayName(smartquote(
    'Edit subscription to branch "%s"'))

branch_index = ContextDisplayName(smartquote(
    '"%s" branch in Launchpad'))

branch_link_to_bug = ContextDisplayName(smartquote(
    'Link branch "%s" to a bug report'))

branch_link_to_spec = ContextDisplayName(smartquote(
    'Link branch "%s" to a blueprint'))

def branch_listing_cross_product(context, view):
    """Return the view's page_title."""
    return view.page_title

branch_landing_candidates = ContextDisplayName(smartquote(
    'Landing candidates for "%s"'))

branch_merge_queue = ContextDisplayName(smartquote('Merge queue for "%s"'))

branchmergeproposal_delete = 'Delete proposal to merge branch'

branchmergeproposal_edit = 'Edit proposal to merge branch'

branchmergeproposal_enqueue = 'Queue branch for merging'

branchmergeproposal_index = 'Proposal to merge branch'

branchmergeproposal_request_review = ViewLabel()

branchmergeproposal_resubmit = ViewLabel()

branchmergeproposal_review = ViewLabel()

branchmergeproposal_work_in_progress = ViewLabel()

branch_register_merge_proposal = 'Propose branch for merging'

branch_subscription = ContextDisplayName(smartquote(
    'Subscription to branch "%s"'))

def branchsubscription_edit(context, view):
    """Return the page title with the branch name."""
    return smartquote(
        'Edit subscription to branch "%s"' % context.branch.displayname)

branch_visibility = ContextDisplayName('Set branch visibility policy for %s')

def branch_visibility_edit(context, view):
    """Return the view's pagetitle."""
    return view.pagetitle

branchtarget_branchlisting = ContextDisplayName('Details of Branches for %s')

bug_activity = ContextBugId('Bug #%s - Activity log')

bug_addsubscriber = LaunchbagBugID("Bug #%d - Add a subscriber")

def bug_attachment_edit(context, view):
    """Return the page title for the edit attachment page."""
    return smartquote('Bug #%d - Edit attachment "%s"') % (
        context.bug.id, context.title)

bug_branch_add = LaunchbagBugID('Bug #%d - Add branch')

bug_comment_add = LaunchbagBugID('Bug #%d - Add a comment or attachment')

bug_cve = LaunchbagBugID("Bug #%d - Add CVE reference")

bug_edit = ContextBugId('Bug #%d - Edit')

bug_edit_confirm = ContextBugId('Bug #%d - Edit confirmation')

bug_extref_add = LaunchbagBugID("Bug #%d - Add a web link")

def bug_extref_edit(context, view):
    """Return the page title for editing a bugs external web link."""
    return smartquote('Bug #%d - Edit web link "%s"') % (
        context.bug.id, context.title)

bug_mark_as_duplicate = ContextBugId('Bug #%d - Mark as duplicate')

bug_nominate_for_series = ViewLabel()

bug_removecve = LaunchbagBugID("Bug #%d - Remove CVE reference")

bug_secrecy = ContextBugId('Bug #%d - Set visibility')

bug_subscription = LaunchbagBugID('Bug #%d - Subscription options')

bug_create_question = LaunchbagBugID(
    'Bug #%d - Convert this bug to a question')

bug_remove_question = LaunchbagBugID(
    'Bug #%d - Convert this question back to a bug')

bug_watch_add = LaunchbagBugID('Bug #%d - Add external bug watch')

bugbranch_edit = "Edit branch fix status"
bugbranch_status = "Edit branch fix status"

def bugcomment_index(context, view):
    """Return the page title for a bug comment."""
    return "Bug #%d - Comment #%d" % (context.bug.id, view.comment.index)

buglinktarget_linkbug = 'Link to bug report'

buglinktarget_unlinkbugs = 'Remove links to bug reports'

buglisting_advanced = ContextTitle("Bugs in %s")

buglisting_default = ContextTitle("Bugs in %s")

def buglisting_embedded_advanced_search(context, view):
    """Return the view's page heading."""
    return view.getSearchPageHeading()

bug_listing_expirable = ContextTitle("Bugs that can expire in %s")

def bugnomination_edit(context, view):
    """Return the title for the page to manage bug nominations."""
    return 'Manage nomination for bug #%d in %s' % (
        context.bug.id, context.target.bugtargetdisplayname)

def bugwatch_editform(context, view):
    """Return the title for the page to edit an external bug watch."""
    return 'Bug #%d - Edit external bug watch (%s in %s)' % (
        context.bug.id, context.remotebug, context.bugtracker.title)

def bugwatch_comments(context, view):
    """Return the title for a page of imported comments for a bug watch."""
    return "Bug #%d - Comments imported from bug watch %s on %s" % (
        context.bug.id, context.remotebug, context.bugtracker.title)

# bugpackageinfestations_index is a redirect

# bugproductinfestations_index is a redirect

def bugs_assigned(context, view):
    """Return the page title for the bugs assigned to the logged-in user."""
    if view.user:
        return 'Bugs assigned to %s' % view.user.browsername
    else:
        return 'No-one to display bugs for'

bugtarget_advanced_search = ContextTitle("Search bugs in %s")

bugtarget_bugs = ContextTitle('Bugs in %s')

def bugtarget_filebug_advanced(context, view):
    """Return the page title for reporting a bug."""
    if IMaloneApplication.providedBy(context):
        # We're generating a title for a top-level, contextless bug
        # filing page.
        return 'Report a bug'
    else:
        # We're generating a title for a contextual bug filing page.
        return 'Report a bug about %s' % context.title

bugtarget_filebug_search = bugtarget_filebug_advanced

bugtarget_filebug_submit_bug = bugtarget_filebug_advanced

bugtask_affects_new_product = LaunchbagBugID(
    'Bug #%d - Record as affecting another project')

bugtask_choose_affected_product = bugtask_affects_new_product

# This page is used for both projects/distros so we have to say 'software'
# rather than distro or project here.
bugtask_confirm_bugtracker_creation = LaunchbagBugID(
    'Bug #%d - Record as affecting another software')

bugtask_edit = BugTaskPageTitle()

bugtask_index = BugTaskPageTitle()

bugtask_requestfix = LaunchbagBugID(
    'Bug #%d - Record as affecting another distribution/package')

bugtask_requestfix_upstream = LaunchbagBugID('Bug #%d - Confirm project')

bugtask_view = BugTaskPageTitle()

bugtask_non_contributor_assignee_confirm = 'Confirm bug assignment'

# bugtask_macros_buglisting contains only macros
# bugtasks_index is a redirect

bugtracker_edit = ContextTitle(
    smartquote('Change details for "%s" bug tracker'))

bugtracker_index = ContextTitle(smartquote('Bug tracker "%s"'))

bugtrackers_add = 'Register an external bug tracker'

bugtrackers_index = 'Bug trackers registered in Launchpad'

build_buildlog = ContextTitle('Build log for %s')

build_changes = ContextTitle('Changes in %s')

build_index = ContextTitle('Build details for %s')

build_retry = ContextTitle('Retry %s')

build_rescore = ContextTitle('Rescore %s')

builder_admin = ContextTitle('Administer %s builder')

builder_cancel = ContextTitle('Cancel job for %s')

builder_edit = ContextTitle('Edit build machine %s')

builder_history = ContextTitle('Build history for %s')

builder_index = ContextTitle('Build machine %s')

builder_mode = ContextTitle('Change mode for %s')

builder_new = 'Register a new build machine'

builders_index = 'Launchpad build farm'

calendar_index = ContextTitle('%s')

calendar_event_addform = ContextTitle('Add event to %s')

calendar_event_display = ContextTitle(smartquote('Event "%s"'))

calendar_event_editform = ContextTitle(
    smartquote('Change "%s" event details'))

calendar_subscribe = ContextTitle(smartquote('Subscribe to "%s"'))

calendar_subscriptions = 'Calendar subscriptions'

def calendar_view(context, view):
    """Return calendar's page title with the date."""
    return '%s - %s' % (context.calendar.title, view.datestring)

calendar_view_day = calendar_view
calendar_view_week = calendar_view
calendar_view_month = calendar_view
calendar_view_year = calendar_view

canbementored_mentoringoffer = 'Offer to mentor this work'

canbementored_retractmentoring = 'Retract offer of mentorship'

def codeimport(context, view):
    """Return the view's title."""
    return view.title

codeimport_edit = 'Edit import details'

codeimport_list = 'Code Imports'

codeimport_machines = ViewLabel()

codeimport_new = ViewLabel()

codeofconduct_admin = 'Administer Codes of Conduct'

codeofconduct_index = ContextTitle('%s')

codeofconduct_list = 'Ubuntu Codes of Conduct'

cveset_all = 'All CVE entries registered in Launchpad'

cveset_index = 'Launchpad CVE tracker'

cve_index = ContextDisplayName('%s')

cve_linkbug = ContextDisplayName('Link %s to a bug report')

cve_unlinkbugs = ContextDisplayName('Remove links between %s and bug reports')

debug_root_changelog = 'Launchpad changelog'

debug_root_index = 'Launchpad Debug Home Page'

default_editform = 'Default "Edit" Page'

distributionmirror_delete = ContextTitle('Delete mirror %s')

distributionmirror_edit = ContextTitle('Edit mirror %s')

distributionmirror_index = ContextTitle('Mirror %s')

distributionmirror_prober_logs = ContextTitle('%s mirror prober logs')

distributionmirror_review = ContextTitle('Review mirror %s')

distribution_add = 'Register a new distribution'

distribution_allpackages = ContextTitle('All packages in %s')

distribution_upstream_bug_report = ContextTitle('Upstream Bug Report for %s')

distribution_change_mirror_admin = 'Change mirror administrator'

distribution_cvereport = ContextTitle('CVE reports for %s')

distribution_edit = 'Change distribution details'
# We don't mention its name here, because that might be what you're changing.

distribution_language_pack_admin = ContextTitle(
    'Change the language pack administrator for %s')

distribution_members = ContextTitle('%s distribution members')

distribution_memberteam = ContextTitle(
    smartquote("Change %s's distribution team"))

distribution_mirrors = ContextTitle("Mirrors of %s")

distribution_newmirror = ContextTitle("Register a new mirror for %s")

distribution_series = ContextTitle("%s version history")

distribution_translations = ContextDisplayName('Translating %s')

distribution_translators = ContextTitle(
    smartquote("Appoint %s's translation group"))

distribution_search = ContextDisplayName(smartquote("Search %s's packages"))

distribution_index = ContextTitle('%s in Launchpad')

distribution_builds = ContextTitle('%s builds')

distribution_uploadadmin = ContextTitle('Change Upload Manager for %s')

distribution_ppa_list = ContextTitle('%s Personal Package Archives')

distributionsourcepackage_bugs = ContextTitle('Bugs in %s')

distributionsourcepackage_index = ContextTitle('%s')

distributionsourcepackage_publishinghistory = ContextTitle(
    'Publishing history of %s')

structural_subscriptions_manage = ContextTitle(
    'Bug subscriptions for %s')

distributionsourcepackagerelease_index = ContextTitle('%s')

distroarchseries_admin = ContextTitle('Administer %s')

distroarchseries_index = ContextTitle('%s in Launchpad')

distroarchseries_builds = ContextTitle('%s builds')

distroarchseries_search = ContextTitle(
    smartquote("Search %s's binary packages"))

distroarchseriesbinarypackage_index = ContextTitle('%s')

distroarchseriesbinarypackagerelease_index = ContextTitle('%s')

distroseries_addport = ContextTitle('Add a port of %s')

distroseries_bugs = ContextTitle('Bugs in %s')

distroseries_cvereport = ContextDisplayName('CVE report for %s')

distroseries_edit = ContextTitle('Edit details of %s')

def distroseries_index(context, view):
    """Return the distribution and version page title."""
    return '%s %s in Launchpad' % (
        context.distribution.title, context.version)

distroseries_language_packs = ViewLabel()

def distroseries_language_packs_editing(context, view):
    """Return the view's page_title."""
    return view.page_title

distroseries_packaging = ContextDisplayName('Mapping packages to upstream '
    'for %s')

distroseries_search = ContextDisplayName('Search packages in %s')

distroseries_translations = ContextTitle('Translations of %s in Launchpad')

distroseries_translationsadmin = ContextTitle(
    'Admin translation options for %s')

distroseries_builds = ContextTitle('Builds for %s')

distroseries_queue = ContextTitle('Queue for %s')

distroseriesbinarypackage_index = ContextTitle('%s')

distroserieslanguage_index = ContextTitle('%s')

distroseriessourcepackagerelease_index = ContextTitle('%s')

distros_index = 'Distributions registered in Launchpad'

edit_bugcontact = ContextTitle('Edit bug supervisor for %s')

errorservice_config = 'Configure error log'

errorservice_entry = 'Error log entry'

errorservice_index = 'Error log report'

errorservice_tbentry = 'Traceback entry'

faq = 'Launchpad Frequently Asked Questions'

faq_edit = ContextId('Edit FAQ #%s details')

def faq_index(context, view):
    """Return the FAQ index page title."""
    return (
        smartquote('%s FAQ #%d: "%s"') %
        (context.target.displayname, context.id, context.title))

def faq_listing(context, view):
    """Return the FAQ lising page title."""
    return view.heading

def hasmentoringoffers_mentoring(context, view):
    """Return the mentoring title for the context."""
    if IPerson.providedBy(context):
        if context.teamowner is None:
            return 'Mentoring offered by %s' % context.title
        else:
            return ('Mentoring available for newcomers to %s'  %
                    context.displayname)
    else:
        return 'Mentoring available in %s' % context.displayname

hasannouncements_index = ContextDisplayName('%s news and announcements')

def hasspecifications_specs(context, view):
    """Return the secifications title for the context."""
    if IPerson.providedBy(context):
        return "Blueprints involving %s" % context.title
    else:
        return "Blueprints for %s" % context.title

hassprints_sprints = ContextTitle("Events related to %s")

hastranslationimports_index = 'Translation import queue'

hwdb_fingerprint_submissions = (
    "Hardware Database submissions for a fingerprint")

hwdb_submit_hardware_data = (
    'Submit New Data to the Launchpad Hardware Database')

karmaaction_index = 'Karma actions'

karmaaction_edit = 'Edit karma action'

karmacontext_topcontributors = ContextTitle('Top %s Contributors')

language_index = ContextDisplayName("%s in Launchpad")

language_add = 'Add a new Language to Launchpad'

language_admin = ContextDisplayName("Edit %s")

languageset_index = 'Languages in Launchpad'

# launchpad_debug doesn't need a title.

def launchpad_addform(context, view):
    """Return the page_title of the view, or None."""
    # Returning None results in the default Launchpad page title being used.
    return getattr(view, 'page_title', None)

launchpad_editform = launchpad_addform

launchpad_feedback = 'Help improve Launchpad'

launchpad_forbidden = 'Forbidden'

launchpad_forgottenpassword = 'Need a new Launchpad password?'

launchpad_graphics = 'Overview of Launchpad graphics and icons'

template_form = 'XXX PLEASE DO NOT USE THIS TEMPLATE XXX'

# launchpad_css is a css file

# launchpad_js is standard javascript

# XXX: kiko 2005-09-29:
# The general form is a fallback form; I'm not sure why it is
# needed, nor why it needs a pagetitle, but I can't debug this today.
launchpad_generalform = "Launchpad - General Form (Should Not Be Displayed)"

launchpad_legal = 'Launchpad legalese'

launchpad_login = 'Log in or register with Launchpad'

launchpad_log_out = 'Log out from Launchpad'

launchpad_notfound = 'Error: Page not found'

launchpad_onezerostatus = 'One-Zero Page Template Status'

launchpad_requestexpired = 'Error: Timeout'

launchpad_search = 'Search projects in Launchpad'

launchpad_translationunavailable = 'Translation page is not available'

launchpad_unexpectedformdata = 'Error: Unexpected form data'

launchpad_librarianfailure = "Sorry, you can't do this right now"

# launchpad_widget_macros doesn't need a title.

launchpadstatisticset_index = 'Launchpad statistics'

loginservice_email_sent = 'Launchpad Login Service - Email sent'

def loginservice_authorize(context, view):
    """Return the page title for authenticating to a system."""
    rpconfig = view.rpconfig
    if rpconfig is None:
        displayname = view.openid_request.trust_root
    else:
        displayname = rpconfig.displayname
    return 'Authenticate to %s' % displayname

loginservice_login = 'Launchpad Login Service'

loginservice_newaccount = 'Create a new account'

loginservice_resetpassword = 'Reset your password'

logintoken_claimprofile = 'Claim Launchpad profile'

logintoken_claimteam = 'Claim Launchpad team'

logintoken_index = 'Launchpad: redirect to the logintoken page'

logintoken_mergepeople = 'Merge Launchpad accounts'

logintoken_newaccount = 'Create a new Launchpad account'

logintoken_resetpassword = 'Forgotten your password?'

logintoken_validateemail = 'Confirm e-mail address'

logintoken_validategpg = 'Confirm OpenPGP key'

logintoken_validatesignonlygpg = 'Confirm sign-only OpenPGP key'

logintoken_validateteamemail = 'Confirm e-mail address'

mailinglists_review = 'Pending mailing lists requests'

# main_template has the code to insert one of these titles.

malone_about = 'About Launchpad Bugs'

malone_distros_index = 'Report a bug about a distribution'

malone_index = 'Launchpad Bugs'

malone_filebug = "Report a bug"

# malone_people_index is a redirect

# malone_template is a means to include the mainmaster template

# marketing_about_template is used by the marketing pages

marketing_answers_about = "About Answers"

marketing_answers_faq = "FAQs about Answers"

marketing_blueprints_about = "About Blueprints"

marketing_blueprints_faq = "FAQs about Blueprints"

marketing_bugs_about = "About Bugs"

marketing_bugs_faq = "FAQs about Bugs"

marketing_code_about = "About Code"

marketing_code_faq = "FAQs about Code"

# marketing_faq_template is used by the marketing pages

marketing_home = "About Launchpad"

# marketing_main_template is used by the marketing pages

def marketing_tour(context, view):
    """Return the view's pagetitle."""
    return view.pagetitle

marketing_translations_about = "About Translations"

marketing_translations_faq = "FAQs about Translations"

mentoringofferset_success = "Successful mentorships over the past year."

# messagechunk_snippet is a fragment

# messages_index is a redirect

message_add = ContextBugId('Bug #%d - Add a comment')

milestone_add = ContextTitle('Add new milestone for %s')

milestone_index = ContextTitle('%s')

milestone_edit = ContextTitle('Edit %s')

announcement_add = 'Make an announcement'

announcement_delete = 'Permanently delete this announcement'

announcement_edit = 'Modify this announcement'

def announcement_index(context, view):
    return '%s announcement' % context.target.displayname

announcement_publish = 'Publish this announcement'

announcement_retarget = 'Move this announcement to a different project'

announcement_retract = 'Retract this announcement'

announcements_all = 'Announcements from all projects hosted in Launchpad'

notification_test = 'Notification test'

oauth_authorize = 'Authorize application to access Launchpad on your behalf'

object_branding = ContextDisplayName('Change the images used to represent '
    '%s in Launchpad')

object_driver = ContextTitle('Appoint the driver for %s')

object_milestones = ContextTitle(smartquote("%s's milestones"))

# object_pots is a fragment.

object_reassignment = ContextTitle('Reassign %s')

object_translations = ContextTitle('Translation templates for %s')

oops = 'Oops!'

def openid_decide(context, view):
    """Return the page title to authenticate to the system."""
    return 'Authenticate to %s' % view.openid_request.trust_root

openid_index = 'Launchpad OpenID Server'

def openid_invalid_identity(context, view):
    """Return the page title to the invalid identity page."""
    return 'Invalid OpenID identity %s' % view.openid_request.identity

openidrpconfig_add = 'Add an OpenID Relying Party Configuration'

openidrpconfig_edit = ContextDisplayName(
    'Edit Relying Party Configuration for %s')

openidrpconfigset_index = 'OpenID Relying Party Configurations'

def package_bugs(context, view):
    """Return the page title bug in a package."""
    return 'Bugs in %s' % context.name

people_index = 'People and teams in Launchpad'

people_adminrequestmerge = 'Merge Launchpad accounts'

def people_list(context, view):
    """Return the view's header."""
    return view.header

people_mergerequest_sent = 'Merge request sent'

people_newperson = 'Create a new Launchpad profile'

people_newteam = 'Register a new team in Launchpad'

people_requestmerge = 'Merge Launchpad accounts'

people_requestmerge_multiple = 'Merge Launchpad accounts'

person_answer_contact_for = ContextDisplayName(
    'Projects for which %s is an answer contact')

person_bounties = ContextDisplayName('Bounties for %s')

def person_branches(context, view):
    """Return the view's heading."""
    return view.heading

person_branch_add = 'Register a branch'

person_changepassword = 'Change your password'

person_claim = 'Claim account'

person_claim_team = 'Claim team'

person_deactivate_account = 'Deactivate your Launchpad account'

person_codesofconduct = ContextDisplayName(
    smartquote("%s's code of conduct signatures"))

person_edit = ContextDisplayName(smartquote("%s's details"))

person_editemails = ContextDisplayName(smartquote("%s's e-mail addresses"))

person_editlanguages = ContextDisplayName(
    smartquote("%s's preferred languages"))

person_editpgpkeys = ContextDisplayName(smartquote("%s's OpenPGP keys"))

person_edithomepage = ContextDisplayName(smartquote("%s's home page"))

person_editircnicknames = ContextDisplayName(smartquote("%s's IRC nicknames"))

person_editjabberids = ContextDisplayName(smartquote("%s's Jabber IDs"))

person_editsshkeys = ContextDisplayName(smartquote("%s's SSH keys"))

person_editwikinames = ContextDisplayName(smartquote("%s's wiki names"))

# person_foaf is an rdf file

person_hwdb_submissions = ContextDisplayName(
    "Hardware Database submissions by %s")

person_images = ContextDisplayName(smartquote("%s's hackergotchi and emblem"))

def person_index(context, view):
    """Return the page title to the person index page."""
    if context.is_valid_person_or_team:
        return '%s in Launchpad' % context.displayname
    else:
        return "%s does not use Launchpad" % context.displayname

person_karma = ContextDisplayName(smartquote("%s's karma in Launchpad"))

person_mentoringoffers = ContextTitle('Mentoring offered by %s')

person_oauth_tokens = "Applications you authorized to access Launchpad"

person_packages = ContextDisplayName('Packages maintained by %s')

person_packagebugs = ContextDisplayName("%s's package bug reports")

person_packagebugs_overview = person_packagebugs

person_packagebugs_search = person_packagebugs

person_participation = ContextTitle("Team participation by %s")

person_projects = ContextTitle("Projects %s is involved with")

person_review = ContextDisplayName("Review %s")

person_specfeedback = ContextDisplayName('Feature feedback requests for %s')

person_specworkload = ContextDisplayName('Blueprint workload for %s')

person_translations = ContextDisplayName('Translations made by %s')

person_teamhierarchy = ContextDisplayName('Team hierarchy for %s')

pofile_edit = ContextTitle(smartquote('Edit "%s" details'))

pofile_export = ContextTitle(smartquote('Download translation for "%s"'))

pofile_filter = FilteredTranslationsTitle(
    smartquote('Translations by %(person)s in "%(title)s"'))

pofile_index = ContextTitle(smartquote('Translation overview for "%s"'))

def pofile_translate(context, view):
    """Return the page to translate a template into a language."""
    return 'Translating %s into %s' % (
        context.potemplate.displayname, context.language.englishname)

pofile_upload = ContextTitle(smartquote('Upload file for "%s"'))

# portlet_* are portlets

poll_edit = ContextTitle(smartquote('Edit poll "%s"'))

poll_index = ContextTitle(smartquote('Poll: "%s"'))

poll_newoption = ContextTitle(smartquote('New option for poll "%s"'))

def poll_new(context, view):
    """Return a page title to create a new poll."""
    return 'Create a new Poll in team %s' % context.team.displayname

def polloption_edit(context, view):
    """Return the page title to edit a poll's option."""
    return 'Edit option: %s' % context.title

poll_options = ContextTitle(smartquote('Options for poll "%s"'))

poll_vote_condorcet = ContextTitle(smartquote('Vote in poll "%s"'))

poll_vote_simple = ContextTitle(smartquote('Vote in poll "%s"'))

# potemplate_chart is a fragment

potemplate_edit = ContextTitle(smartquote('Edit "%s" details'))

potemplate_index = ContextTitle(smartquote('Translation status for "%s"'))

potemplate_upload = ContextTitle(smartquote('Upload files for "%s"'))

potemplate_export = ContextTitle(smartquote('Download translations for "%s"'))

product_add = 'Register a project in Launchpad'

product_admin = ContextTitle('Administer %s in Launchpad')

product_bugs = ContextDisplayName('Bugs in %s')

product_branches = ContextDisplayName(
    smartquote("%s's Bazaar branches registered in Launchpad"))

product_branch_overview = ContextDisplayName("Code overview for %s")

product_distros = ContextDisplayName(
    '%s packages: Comparison of distributions')

product_code_index = 'Projects with active branches'

product_cvereport = ContextTitle('CVE reports for %s')

product_edit = 'Change project details'
# We don't mention its name here, because that might be what you're changing.

product_index = ContextTitle('%s in Launchpad')

product_new = 'Register a project in Launchpad'

product_packages = ContextDisplayName('%s packages in Launchpad')

product_files = ContextDisplayName('%s project files')

product_series = ContextDisplayName('%s timeline')

product_translations = ContextTitle('Translations of %s in Launchpad')

product_translators = ContextTitle('Set translation group for %s')

productrelease_add = ContextTitle('Register a new %s release in Launchpad')

productrelease_file_add = ContextDisplayName('Add a file to %s')

productrelease_admin = ContextTitle('Administer %s in Launchpad')

productrelease_edit = ContextDisplayName('Edit details of %s in Launchpad')

productrelease_index = ContextDisplayName('%s in Launchpad')

products_index = 'Projects registered in Launchpad'

productseries_export = ContextTitle('Download translations for "%s"')

productseries_linkbranch = ContextTitle('Link an existing branch to %s')

productseries_index = ContextTitle('Overview of %s')

productseries_packaging = ContextDisplayName(
    'Packaging of %s in distributions')

productseries_source = ContextDisplayName(
    'Set upstream revision control system for %s')

productseries_translations_upload = 'Request new translations upload'

productseries_ubuntupkg = 'Ubuntu source package'

project_add = 'Register a project group with Launchpad'

project_index = ContextTitle('%s in Launchpad')

project_branches = ContextTitle(
    smartquote("%s's Bazaar branches registered in Launchpad"))

project_bugs = ContextTitle('Bugs in %s')

project_edit = 'Change project group details'
# We don't mention its name here, because that might be what you're changing.

project_filebug_search = bugtarget_filebug_advanced

project_interest = 'Launchpad Translations: Project group not translatable'

project_rosetta_index = ContextTitle('Launchpad Translations: %s')

project_specs = ContextTitle('Blueprints for %s')

project_translations = ContextTitle('Translatable projects for %s')

project_translators = ContextTitle('Set translation group for %s')

projects_index = 'Project groups registered in Launchpad'

projects_request = 'Launchpad Translations: Request a project group'

projects_search = 'Search for project groups in Launchpad'

rdf_index = "Launchpad RDF"

# redirect_up is a redirect

def reference_index(context, view):
    """Return the page title for bug reference web links."""
    return 'Web links for bug %s' % context.bug.id

# references_index is a redirect

registry_about = 'About the Launchpad Registry'

registry_index = 'Project and group registration in Launchpad'

products_all = 'Upstream projects registered in Launchpad'

projects_all = 'Project groups registered in Launchpad'

registry_review = 'Review Launchpad items'

related_bounties = ContextDisplayName('Bounties for %s')

remotebug_index = ContextTitle('%s')

root_featuredprojects = 'Manage featured projects in Launchpad'

root_index = 'Launchpad'

rosetta_about = 'About Launchpad Translations'

rosetta_index = 'Launchpad Translations'

rosetta_products = 'Projects with Translations in Launchpad'

product_branch_add = 'Register a branch'

def productseries_edit(context, view):
    """Return the page title for changing a product series details."""
    return 'Change %s %s details' % (
        context.product.displayname, context.name)

productseries_new = ContextDisplayName('Register a new %s release series')

def question_add(context, view):
    """Return the page title to add a question."""
    return view.pagetitle

question_add_search = question_add

question_bug = ContextId('Link question #%s to a bug report')

question_change_status = ContextId('Change status of question #%s')

question_confirm_answer = ContextId('Confirm an answer to question #%s')

def question_createfaq(context, view):
    """Return the page title to create an FAQ for a question."""
    return "Create a FAQ for %s" % view.faq_target.displayname

question_edit = ContextId('Edit question #%s details')

question_history = ContextId('History of question #%s')

def question_index(context, view):
    """Return the page title to a question's index view."""
    text = (
        smartquote('%s question #%d: "%s"') %
        (context.target.displayname, context.id, context.title))
    return text

question_linkbug = ContextId('Link question  #%s to a bug report')

question_linkfaq = ContextId('Is question #%s a FAQ?')

def question_listing(context, view):
    """Return the page title list questions."""
    return view.pagetitle

question_makebug = ContextId('Create bug report based on question #%s')

question_reject = ContextId('Reject question #%s')

question_subscription = ContextId('Subscription to question #%s')

question_unlinkbugs = ContextId('Remove bug links from question #%s')

questions_index = 'Launchpad Answers'

questiontarget_manage_answercontacts = ContextTitle("Answer contact for %s")

securitycontact_edit = ContextDisplayName("Edit %s security contact")

series_bug_nominations = ContextDisplayName('Bugs nominated for %s')

shipit_adminrequest = 'ShipIt admin request'

shipit_exports = 'ShipIt exports'

shipit_forbidden = 'Forbidden'

shipit_index = 'ShipIt'

shipit_index_ubuntu = 'Request an Ubuntu CD'

shipit_login = 'ShipIt'

shipit_myrequest = "Your ShipIt order"

shipit_oops = 'Error: Oops'

shipit_reports = 'ShipIt reports'

shipit_requestcds = 'Your ShipIt Request'

shipit_survey = 'ShipIt Survey'

shipitrequests_index = 'ShipIt requests'

shipitrequests_search = 'Search ShipIt requests'

shipitrequest_edit = 'Edit ShipIt request'

shipit_notfound = 'Error: Page not found'

signedcodeofconduct_index = ContextDisplayName('%s')

signedcodeofconduct_add = ContextTitle('Sign %s')

signedcodeofconduct_acknowledge = 'Acknowledge code of conduct signature'

signedcodeofconduct_activate = ContextDisplayName('Activating %s')

signedcodeofconduct_deactivate = ContextDisplayName('Deactivating %s')

sourcepackage_bugs = ContextDisplayName('Bugs in %s')

sourcepackage_builds = ContextTitle('Builds for %s')

sourcepackage_translate = ContextTitle('Help translate %s')

sourcepackage_changelog = 'Source package changelog'

sourcepackage_filebug = ContextTitle("Report a bug about %s")

sourcepackage_gethelp = ContextTitle('Help and support options for %s')

sourcepackage_packaging = ContextTitle('%s upstream links')

sourcepackage_export = ContextTitle('Download translations for "%s"')

def sourcepackage_index(context, view):
    """Return the page title for a source package in a distroseries."""
    return '%s source packages' % context.distroseries.title

sourcepackage_edit_packaging = ContextTitle('Define upstream link for %s')

sourcepackage_translate = ContextTitle('Help translate %s')

sourcepackagenames_index = 'Source package name set'

sourcepackagerelease_index = ContextTitle('Source package %s')

def sourcepackages(context, view):
    """Return the page title for a source package in a distroseries."""
    return '%s source packages' % context.distroseries.title

sourcepackages_comingsoon = 'Coming soon'

sources_index = 'Bazaar: Upstream revision control imports to Bazaar'

sources_list = 'Available code imports'

sourcesource_index = 'Upstream source import'

specification_add = 'Register a blueprint in Launchpad'

specification_addsubscriber = 'Subscribe someone else to this blueprint'

specification_linkbug = ContextTitle(
  u'Link blueprint \N{left double quotation mark}%s'
  u'\N{right double quotation mark} to a bug report')

specification_new = 'Register a proposal as a blueprint in Launchpad'

specification_unlinkbugs = 'Remove links to bug reports'

specification_retargeting = 'Attach blueprint to a different project'

specification_superseding = 'Mark blueprint as superseded by another'

specification_goaldecide = 'Approve or decline blueprint goal'

specification_dependency = 'Create a blueprint dependency'

specification_deptree = 'Complete dependency tree'

specification_milestone = 'Target feature to milestone'

specification_people = 'Change blueprint assignee, drafter, and reviewer'

specification_priority = 'Change blueprint priority'

specification_distroseries = ('Target blueprint to a distribution release')

specification_productseries = 'Target blueprint to a series'

specification_removedep = 'Remove a dependency'

specification_givefeedback = 'Clear feedback requests'

specification_requestfeedback = 'Request feedback on this blueprint'

specification_edit = 'Edit blueprint details'

specification_linksprint = 'Put blueprint on sprint agenda'

specification_status = 'Edit blueprint status'

specification_index = ContextTitle(smartquote('Blueprint: "%s"'))

specification_subscription = 'Subscribe to blueprint'

specification_queue = 'Queue blueprint for review'

specification_linkbranch = 'Link branch to blueprint'

specifications_index = 'Launchpad Blueprints'

specificationbranch_status = 'Edit blueprint branch status'

specificationgoal_specs = ContextTitle('List goals for %s')

specificationgoal_setgoals = ContextTitle('Set goals for %s')

def specificationsubscription_edit(context, view):
    """Return the page title for subscribing to a specification."""
    return "Subscription of %s" % context.person.browsername

specificationtarget_documentation = ContextTitle('Documentation for %s')

specificationtarget_index = ContextTitle('Blueprint listing for %s')

def specificationtarget_specs(context, view):
    """Return the page title for a specificationtarget."""
    return view.title

specificationtarget_roadmap = ContextTitle('Project plan for %s')

specificationtarget_assignments = ContextTitle('Blueprint assignments for %s')

specificationtarget_workload = ContextTitle('Blueprint workload in %s')

sprint_attend = ContextTitle('Register your attendance at %s')

sprint_edit = ContextTitle(smartquote('Edit "%s" details'))

sprint_index = ContextTitle('%s (sprint or meeting)')

sprint_new = 'Register a meeting or sprint in Launchpad'

sprint_register = 'Register someone to attend this meeting'

sprint_specs = ContextTitle('Blueprints for %s')

sprint_settopics = ContextTitle('Review topics proposed for discussion at %s')

sprint_workload = ContextTitle('Workload at %s')

sprints_all = 'All sprints and meetings registered in Launchpad'

sprints_index = 'Meetings and sprints registered in Launchpad'

sprintspecification_decide = 'Consider spec for sprint agenda'

sprintspecification_admin = 'Approve blueprint for sprint agenda'

standardshipitrequests_index = 'Standard ShipIt options'

standardshipitrequest_new = 'Create a new standard option'

standardshipitrequest_edit = 'Edit standard option'

team_addmember = ContextBrowsername('Add members to %s')

team_add_my_teams = 'Propose/add one of your teams to another one'

team_contactaddress = ContextDisplayName('%s contact address')

team_edit = 'Edit team information'

team_editproposed = ContextBrowsername('Proposed members of %s')

team_index = ContextBrowsername(smartquote('"%s" team in Launchpad'))

team_invitations = ContextBrowsername("Invitations sent to %s")

team_join = ContextBrowsername('Join %s')

team_leave = ContextBrowsername('Leave %s')

team_mailinglist = 'Configure mailing list'

team_mailinglist_moderate = 'Moderate mailing list'

team_members = ContextBrowsername(smartquote('"%s" members'))

team_mugshots = ContextBrowsername(smartquote('Mugshots in the "%s" team'))

def teammembership_index(context, view):
    """Return the page title to the persons status in a team."""
    return smartquote("%s's membership status in %s") % (
        context.person.browsername, context.team.browsername)

def teammembership_invitation(context, view):
    """Return the page title to invite a person to become a team member."""
    return "Make %s a member of %s" % (
        context.person.browsername, context.team.browsername)

def teammembership_self_renewal(context, view):
    """Return the page title renew membership in a team."""
    return "Renew membership of %s in %s" % (
        context.person.browsername, context.team.browsername)

team_mentoringoffers = ContextTitle('Mentoring available for newcomers to %s')

team_newpoll = ContextTitle('New poll for team %s')

team_polls = ContextTitle('Polls for team %s')

template_auto_add = 'Launchpad Auto-Add Form'

template_auto_edit = 'Launchpad Auto-Edit Form'

template_edit = 'EXAMPLE EDIT TITLE'

template_index = '%EXAMPLE TITLE'

template_new = 'EXAMPLE NEW TITLE'

temporaryblobstorage_storeblob = 'Store a BLOB temporarily in Launchpad'

token_authorized = 'Almost finished ...'

translationgroup_index = ContextTitle(
    smartquote('"%s" Launchpad translation group'))

translationgroup_add = 'Add a new translation group to Launchpad'

translationgroup_appoint = ContextTitle(
    smartquote('Appoint a new translator to "%s"'))

translationgroup_edit = ContextTitle(smartquote(
    'Edit "%s" translation group details'))

translationgroup_reassignment = ContextTitle(smartquote(
    'Change the owner of "%s" translation group'))

translationgroups_index = 'Launchpad translation groups'

translationimportqueueentry_index = 'Translation import queue entry'

translationimportqueue_index = 'Translation import queue'

translationimportqueue_blocked = 'Translation import queue - Blocked'

def translationmessage_translate(context, view):
    """Return the page to translate a template into a language per message."""
    return 'Translating %s into %s' % (
        context.pofile.potemplate.displayname,
        context.pofile.language.englishname)

def translator_edit(context, view):
    """Return the page title for editing a translator in a group."""
    return "Edit %s translator for %s" % (
        context.language.englishname, context.translationgroup.title)

def translator_remove(context, view):
    """Return the page title to remove a translator from a group."""
    return "Remove %s as the %s translator for %s" % (
        context.translator.displayname, context.language.englishname,
        context.translationgroup.title)

unauthorized = 'Error: Not authorized'
