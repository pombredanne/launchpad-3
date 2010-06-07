# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""*** PLEASE STOP ADDING TO THIS FILE ***

Use the page_title attribute of the view.

This module is used as a last resort by the Launchpad webapp to determine
titles for pages.

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
from canonical.lazr.utils import smartquote

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
        return self.text % context.displayname


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

archive_admin = ContextDisplayName('Administer %s')

archive_activate = 'Activate Personal Package Archive'

archive_copy_packages = ContextDisplayName('Copy packages from %s')

archive_delete_packages = ContextDisplayName('Delete packages from %s')

archive_edit = ContextDisplayName('Edit %s')

bazaar_all_branches = 'All branches in the Launchpad Bazaar'

bazaar_index = 'Launchpad Branches'

bazaar_sync_review = (
    'Review upstream repositories for Launchpad Bazaar syncing')

def binarypackagerelease_index(context, view):
    """Return the page title for context's binary packages."""
    return "%s binary package in Launchpad" % context.title

binarypackagenames_index = 'Binary package name set'

branch_bug_links = ContextDisplayName(smartquote('Bug links for %s'))

branch_index = ContextDisplayName(smartquote(
    '"%s" branch in Launchpad'))

def branch_merges(context, view):
    return 'Merges involving "%s" in Launchpad' % context.bzr_identity

branch_landing_candidates = ContextDisplayName(smartquote(
    'Landing candidates for "%s"'))

def branchmergeproposal_index(context, view):
    return 'Proposal to merge %s' % context.source_branch.bzr_identity

bug_activity = ContextBugId('Bug #%s - Activity log')

bug_addsubscriber = LaunchbagBugID("Bug #%d - Add a subscriber")

bug_branch_add = LaunchbagBugID('Bug #%d - Add branch')

bug_edit = ContextBugId('Bug #%d - Edit')

bug_edit_confirm = ContextBugId('Bug #%d - Edit confirmation')

bug_extref_add = LaunchbagBugID("Bug #%d - Add a web link")

def bug_extref_edit(context, view):
    """Return the page title for editing a bugs external web link."""
    return smartquote('Bug #%d - Edit web link "%s"') % (
        context.bug.id, context.title)

bug_mark_as_duplicate = ContextBugId('Bug #%d - Mark as duplicate')

bug_mark_as_affecting_user = ContextBugId(
    'Bug #%d - does this bug affect you?')

bug_nominate_for_series = ViewLabel()

bug_secrecy = ContextBugId('Bug #%d - Set visibility')

bug_subscription = LaunchbagBugID('Bug #%d - Subscription options')

bugbranch_delete = 'Delete bug branch link'

bugbranch_edit = "Edit branch fix status"

buglinktarget_linkbug = 'Link to bug report'

buglinktarget_unlinkbugs = 'Remove links to bug reports'

buglisting_advanced = ContextTitle("Bugs in %s")

buglisting_default = ContextTitle("Bugs in %s")

def buglisting_embedded_advanced_search(context, view):
    """Return the view's page heading."""
    return view.getSearchPageHeading()

def bugnomination_edit(context, view):
    """Return the title for the page to manage bug nominations."""
    return 'Manage nomination for bug #%d in %s' % (
        context.bug.id, context.target.bugtargetdisplayname)

def bugs_assigned(context, view):
    """Return the page title for the bugs assigned to the logged-in user."""
    if view.user:
        return 'Bugs assigned to %s' % view.user.displayname
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

bugtask_requestfix = LaunchbagBugID(
    'Bug #%d - Record as affecting another distribution/package')

bugtask_requestfix_upstream = LaunchbagBugID('Bug #%d - Confirm project')

bugtask_view = BugTaskPageTitle()

# bugtask_macros_buglisting contains only macros
# bugtasks_index is a redirect

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

code_in_branches = 'Projects with active branches'

def codeimport(context, view):
    """Return the view's title."""
    return view.title

codeimport_list = 'Code Imports'

codeimport_machines = ViewLabel()

def codeimport_machine_index(context, view):
    return smartquote('Code Import machine "%s"' % context.hostname)

codeimport_new = ViewLabel()

codeofconduct_admin = 'Administer Codes of Conduct'

codeofconduct_list = 'Ubuntu Codes of Conduct'

def contact_user(context, view):
    return view.specific_contact_title_text

cveset_all = 'All CVE entries registered in Launchpad'

cveset_index = 'Launchpad CVE tracker'

cve_index = ContextDisplayName('%s')

cve_linkbug = ContextDisplayName('Link %s to a bug report')

cve_unlinkbugs = ContextDisplayName('Remove links between %s and bug reports')

debug_root_index = 'Launchpad Debug Home Page'

distributionmirror_index = ContextTitle('Mirror %s')

distribution_archive_list = ContextTitle('%s Copy Archives')

distribution_upstream_bug_report = ContextTitle('Upstream Bug Report for %s')

distribution_cvereport = ContextTitle('CVE reports for %s')

distribution_members = ContextTitle('%s distribution members')

distribution_mirrors = ContextTitle("Mirrors of %s")

distribution_translations = ContextDisplayName('Translating %s')

distribution_translation_settings = ContextTitle(
    smartquote("Change %s's translation settings"))

distribution_search = ContextDisplayName(smartquote("Search %s's packages"))

distribution_index = ContextTitle('%s in Launchpad')

distributionsourcepackage_bugs = ContextTitle('Bugs in %s')

distributionsourcepackage_index = ContextTitle('%s')

distributionsourcepackage_publishinghistory = ContextTitle(
    'Publishing history of %s')

distroarchseries_index = ContextTitle('%s in Launchpad')

distroarchseries_search = ContextTitle(
    smartquote("Search %s's binary packages"))

distroarchseriesbinarypackage_index = ContextTitle('%s')

distroarchseriesbinarypackagerelease_index = ContextTitle('%s')

distroseries_bugs = ContextTitle('Bugs in %s')

distroseries_cvereport = ContextDisplayName('CVE report for %s')

def distroseries_language_packs(context, view):
    return view.page_title

distroseries_translations = ContextTitle('Translations of %s in Launchpad')

distroseries_queue = ContextTitle('Queue for %s')

distroseriessourcepackagerelease_index = ContextTitle('%s')

errorservice_config = 'Configure error log'

errorservice_entry = 'Error log entry'

errorservice_index = 'Error log report'

errorservice_tbentry = 'Traceback entry'

faq = 'Launchpad Frequently Asked Questions'

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

hassprints_sprints = ContextTitle("Events related to %s")

# launchpad_debug doesn't need a title.

launchpad_feedback = 'Help improve Launchpad'

launchpad_forbidden = 'Forbidden'

# launchpad_css is a css file

# launchpad_js is standard javascript

launchpad_legal = 'Launchpad legalese'

launchpad_login = 'Log in or register with Launchpad'

launchpad_onezerostatus = 'One-Zero Page Template Status'

def launchpad_search(context, view):
    """Return the page title corresponding to the user's search."""
    return view.page_title

launchpad_unexpectedformdata = 'Error: Unexpected form data'

launchpad_librarianfailure = "Sorry, you can't do this right now"

# launchpad_widget_macros doesn't need a title.

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

loginservice_standalone_login = loginservice_login

# main_template has the code to insert one of these titles.

malone_about = 'About Launchpad Bugs'

malone_distros_index = 'Report a bug about a distribution'

malone_index = 'Launchpad Bugs'

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

marketing_translations_faq = "FAQs about Translations"

mentoringofferset_success = "Successful mentorships over the past year."

# messagechunk_snippet is a fragment

# messages_index is a redirect

milestone_add = ContextTitle('Add new milestone for %s')

milestone_edit = ContextTitle('Edit %s')

milestone_delete = ContextTitle('Delete %s')

oauth_authorize = 'Authorize application to access Launchpad on your behalf'

def object_driver(context, view):
    """Return the page title to change the driver."""
    return view.page_title

# object_pots is a fragment.

object_translations = ContextDisplayName('Translation templates for %s')

object_templates = ContextDisplayName('Translation templates for %s')

oops = 'Oops!'

openid_account_change_password = 'Change your password'

def openid_account_edit(context, view):
    return smartquote("%s's details") % view.account.displayname

def openid_account_edit_emails(context, view):
    return smartquote("%s's e-mail addresses") % view.account.displayname

openid_default = 'OpenID Endpoint'

def openid_index(context, view):
    return 'Welcome %s' % view.account.displayname

def openid_invalid_identity(context, view):
    """Return the page title to the invalid identity page."""
    return 'Invalid OpenID identity %s' % view.openid_request.identity

def package_bugs(context, view):
    """Return the page title bug in a package."""
    return 'Bugs in %s' % context.name

people_adminrequestmerge = 'Merge Launchpad accounts'

def people_list(context, view):
    """Return the view's header."""
    return view.header

people_mergerequest_sent = 'Merge request sent'

person_answer_contact_for = ContextDisplayName(
    'Projects for which %s is an answer contact')

# person_foaf is an rdf file

person_images = ContextDisplayName(smartquote("%s's hackergotchi and emblem"))

person_karma = ContextDisplayName(smartquote("%s's karma in Launchpad"))

person_mentoringoffers = ContextTitle('Mentoring offered by %s')

def person_mergeproposals(context, view):
    """Return the view's heading."""
    return view.heading

person_packagebugs = ContextDisplayName("%s's package bug reports")

person_packagebugs_overview = person_packagebugs

person_packagebugs_search = person_packagebugs

person_specfeedback = ContextDisplayName('Feature feedback requests for %s')

person_specworkload = ContextDisplayName('Blueprint workload for %s')

person_translations_to_review = ContextDisplayName(
    'Translations for review by %s')

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

product_admin = ContextTitle('Administer %s in Launchpad')

product_bugs = ContextDisplayName('Bugs in %s')

product_code_index = ContextDisplayName("Bazaar branches of %s")

product_cvereport = ContextTitle('CVE reports for %s')

product_edit = 'Change project details'
# We don't mention its name here, because that might be what you're changing.

product_edit_people = "Change the roles of people"

product_index = ContextTitle('%s in Launchpad')

def product_mergeproposals(context, view):
    """Return the view's heading."""
    return view.heading

product_new_guided = 'Before you register your project...'

product_purchase_subscription = ContextDisplayName(
    'Purchase Subscription for %s')

product_review_license = ContextTitle('Review %s')

product_timeline = ContextTitle('Timeline Diagram for %s')

product_translations = ContextTitle('Translations of %s in Launchpad')

productrelease_admin = ContextTitle('Administer %s in Launchpad')

productrelease_index = ContextDisplayName('%s in Launchpad')

productseries_translations = ContextTitle('Translations overview for %s')

productseries_translations_settings = 'Settings for translations'

project_index = ContextTitle('%s in Launchpad')

project_bugs = ContextTitle('Bugs in %s')

project_edit = 'Change project group details'
# We don't mention its name here, because that might be what you're changing.

project_filebug_search = bugtarget_filebug_advanced

project_interest = 'Launchpad Translations: Project group not translatable'

project_rosetta_index = ContextTitle('Launchpad Translations: %s')

project_specs = ContextTitle('Blueprints for %s')

project_translations = ContextTitle('Translatable projects for %s')

projects_request = 'Launchpad Translations: Request a project group'

projects_search = 'Search for project groups in Launchpad'

# redirect_up is a redirect

def reference_index(context, view):
    """Return the page title for bug reference web links."""
    return 'Web links for bug %s' % context.bug.id

# references_index is a redirect

registry_about = 'About the Launchpad Registry'

registry_index = 'Project and group registration in Launchpad'

remotebug_index = ContextTitle('%s')

root_index = 'Launchpad'

rosetta_about = 'About Launchpad Translations'

rosetta_index = 'Launchpad Translations'

rosetta_products = 'Projects with Translations in Launchpad'

question_confirm_answer = ContextId('Confirm an answer to question #%s')

questions_index = 'Launchpad Answers'

series_bug_nominations = ContextDisplayName('Bugs nominated for %s')

shipit_adminrequest = 'ShipIt admin request'

shipit_exports = 'ShipIt exports'

shipit_forbidden = 'Forbidden'

shipit_index = 'ShipIt'

shipit_index_edubuntu = 'Getting Edubuntu'

shipit_index_ubuntu = 'Request an Ubuntu CD'

shipit_login = 'ShipIt'

shipit_login_error = 'ShipIt - Unsuccessful login'

shipit_myrequest = "Your Ubuntu CD order"

shipit_oops = 'Error: Oops'

shipit_reports = 'ShipIt reports'

shipit_requestcds = 'Your Ubuntu CD Request'

shipit_survey = 'Ubuntu Server Edition survey'

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

sourcepackage_changelog = 'Source package changelog'

sourcepackage_filebug = ContextTitle("Report a bug about %s")

sourcepackagenames_index = 'Source package name set'

sourcepackagerelease_index = ContextTitle('Source package %s')

def sourcepackages(context, view):
    """Return the page title for a source package in a distroseries."""
    return '%s source packages' % context.distroseries.title

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

specification_distroseries = ('Target blueprint to a distribution release')

specification_productseries = 'Target blueprint to a series'

specification_removedep = 'Remove a dependency'

specification_givefeedback = 'Clear feedback requests'

specification_edit = 'Edit blueprint details'

specification_linksprint = 'Put blueprint on sprint agenda'

specification_queue = 'Queue blueprint for review'

specification_linkbranch = 'Link branch to blueprint'

specifications_index = 'Launchpad Blueprints'

specificationbranch_status = 'Edit blueprint branch status'

specificationgoal_specs = ContextTitle('List goals for %s')

def specificationsubscription_edit(context, view):
    """Return the page title for subscribing to a specification."""
    return "Subscription of %s" % context.person.displayname

specificationtarget_index = ContextTitle('Blueprint listing for %s')

def specificationtarget_specs(context, view):
    """Return the page title for a specificationtarget."""
    return view.title

specificationtarget_workload = ContextTitle('Blueprint workload in %s')

sprint_attend = ContextTitle('Register your attendance at %s')

sprint_edit = ContextTitle(smartquote('Edit "%s" details'))

sprint_new = 'Register a meeting or sprint in Launchpad'

sprint_specs = ContextTitle('Blueprints for %s')

sprint_workload = ContextTitle('Workload at %s')

sprintspecification_admin = 'Approve blueprint for sprint agenda'

standardshipitrequests_index = 'Standard ShipIt options'

standardshipitrequest_new = 'Create a new standard option'

standardshipitrequest_edit = 'Edit standard option'

team_index = ContextBrowsername('%s in Launchpad')

team_mentoringoffers = ContextTitle('Mentoring available for newcomers to %s')

team_newpoll = ContextTitle('New poll for team %s')

team_polls = ContextTitle('Polls for team %s')

template_auto_add = 'Launchpad Auto-Add Form'

template_auto_edit = 'Launchpad Auto-Edit Form'

template_edit = 'EXAMPLE EDIT TITLE'

template_index = '%EXAMPLE TITLE'

template_new = 'EXAMPLE NEW TITLE'

token_authorized = 'Almost finished ...'

translationimportqueueentry_index = 'Translation import queue entry'

unauthorized = 'Error: Not authorized'
