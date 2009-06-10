# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401

"""Launchpad Browser-Interface View classes.

This is the module to import for Launchpad View Classes. The classes are not
located in this specific module, but are in turn imported from each of the
files in this directory.
"""

# XXX flacoste 2009/03/18 We should use specific imports instead of
# importing from this module.
from lp.registry.browser.announcement import *
from lp.soyuz.browser.archive import *
from canonical.launchpad.browser.authtoken import *
from lp.code.browser.bazaar import *
from lp.soyuz.browser.binarypackagerelease import *
from canonical.launchpad.browser.bounty import *
from canonical.launchpad.browser.bountysubscription import *
from lp.code.browser.branchmergeproposal import *
from lp.code.browser.branchref import *
from lp.code.browser.branchsubscription import *
from lp.code.browser.branchvisibilitypolicy import *
from canonical.launchpad.browser.branding import *
from lp.bugs.browser.bug import *
from lp.bugs.browser.bugalsoaffects import *
from lp.bugs.browser.bugattachment import *
from lp.bugs.browser.bugbranch import *
from lp.bugs.browser.bugcomment import *
from lp.bugs.browser.buglinktarget import *
from lp.bugs.browser.bugmessage import *
from lp.bugs.browser.bugnomination import *
from lp.bugs.browser.bugsubscription import *
from lp.bugs.browser.bugsupervisor import *
from lp.bugs.browser.bugtarget import *
from lp.bugs.browser.bugtask import *
from lp.bugs.browser.bugtracker import *
from lp.bugs.browser.bugwatch import *
from lp.soyuz.browser.build import *
from lp.soyuz.browser.builder import *
from lp.code.browser.codeimport import *
from lp.code.browser.codeimportmachine import *
from lp.registry.browser.codeofconduct import *
from lp.code.browser.codereviewcomment import *
from lp.bugs.browser.cve import *
from lp.bugs.browser.cvereport import *
from lp.registry.browser.distribution import *
from lp.registry.browser.distributionmirror import *
from lp.registry.browser.distributionsourcepackage import *
from lp.soyuz.browser.distributionsourcepackagerelease import *
from lp.bugs.browser.distribution_upstream_bug_report import *
from lp.soyuz.browser.distroarchseries import *
from lp.soyuz.browser.distroarchseriesbinarypackage import *
from lp.soyuz.browser.distroarchseriesbinarypackagerelease import *
from lp.registry.browser.distroseries import *
from lp.soyuz.browser.distroseriesbinarypackage import *
from canonical.launchpad.browser.distroserieslanguage import *
from lp.soyuz.browser.distroseriessourcepackagerelease import *
from lp.answers.browser.faq import *
from lp.answers.browser.faqcollection import *
from lp.answers.browser.faqtarget import *
from lp.registry.browser.featuredproject import *
from canonical.launchpad.browser.feeds import *
from canonical.launchpad.browser.hastranslationimports import *
from canonical.launchpad.browser.hwdb import *
from lp.registry.browser.karma import *
from canonical.launchpad.browser.language import *
from canonical.launchpad.browser.launchpad import *
from canonical.launchpad.browser.launchpadstatistic import *
from canonical.launchpad.browser.librarian import *
from canonical.launchpad.browser.logintoken import *
from lp.registry.browser.mailinglists import *
from lp.registry.browser.mentoringoffer import *
from canonical.launchpad.browser.message import *
from lp.registry.browser.milestone import *
from canonical.launchpad.browser.oauth import *
from canonical.launchpad.browser.objectreassignment import *
from canonical.launchpad.browser.packagerelationship import *
from canonical.launchpad.browser.packaging import *
from lp.registry.browser.peoplemerge import *
from lp.registry.browser.person import *
from canonical.launchpad.browser.pofile import *
from lp.registry.browser.poll import *
from canonical.launchpad.browser.potemplate import *
from lp.registry.browser.product import *
from lp.registry.browser.productrelease import *
from lp.registry.browser.productseries import *
from lp.registry.browser.project import *
from lp.soyuz.browser.publishedpackage import *
from lp.soyuz.browser.publishing import *
from lp.answers.browser.question import *
from lp.answers.browser.questiontarget import *
from lp.soyuz.browser.queue import *
from lp.registry.browser.root import *
from lp.registry.browser.sourcepackage import *
from lp.soyuz.browser.sourcepackagerelease import *
from lp.blueprints.browser.specificationbranch import *
from lp.blueprints.browser.specificationdependency import *
from lp.blueprints.browser.specificationfeedback import *
from lp.blueprints.browser.specificationgoal import *
from lp.blueprints.browser.specificationsubscription import *
from lp.blueprints.browser.specificationtarget import *
from lp.blueprints.browser.sprint import *
from lp.blueprints.browser.sprintattendance import *
from lp.blueprints.browser.sprintspecification import *
from lp.registry.browser.team import *
from lp.registry.browser.teammembership import *
from canonical.launchpad.browser.temporaryblobstorage import *
from canonical.launchpad.browser.translationgroup import *
from canonical.launchpad.browser.translationimportqueue import *
from canonical.launchpad.browser.translationmessage import *
from canonical.launchpad.browser.translations import *
from canonical.launchpad.browser.translator import *
from canonical.launchpad.browser.widgets import *
