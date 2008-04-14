# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401,C0301

__metaclass__ = type

# README:
# Please DO NOT put interfaces in this file. Put them in the correct
# file, one file for each interface type: person, project, bug, etc.

from canonical.launchpad.interfaces.launchpad import *
from canonical.launchpad.interfaces.validation import *

# these need to be at the top, because the others depend on them sometimes
from canonical.launchpad.interfaces.specificationtarget import *
from canonical.launchpad.interfaces.messagetarget import *
from canonical.launchpad.interfaces.pillar import *

from canonical.launchpad.interfaces.announcement import *
from canonical.launchpad.interfaces.answercontact import *
from canonical.launchpad.interfaces.binarypackagerelease import *
from canonical.launchpad.interfaces.binarypackagename import *
from canonical.launchpad.interfaces.bounty import *
from canonical.launchpad.interfaces.bountymessage import *
from canonical.launchpad.interfaces.bountysubscription import *
from canonical.launchpad.interfaces.branch import *
from canonical.launchpad.interfaces.branchmergeproposal import *
from canonical.launchpad.interfaces.branchref import *
from canonical.launchpad.interfaces.branchrevision import *
from canonical.launchpad.interfaces.branchsubscription import *
from canonical.launchpad.interfaces.branchvisibilitypolicy import *
from canonical.launchpad.interfaces.bugactivity import *
from canonical.launchpad.interfaces.bugattachment import *
from canonical.launchpad.interfaces.bug import *
from canonical.launchpad.interfaces.bugbranch import *
from canonical.launchpad.interfaces.bugsupervisor import *
from canonical.launchpad.interfaces.bugcve import *
from canonical.launchpad.interfaces.buglink import *
from canonical.launchpad.interfaces.bugmessage import *
from canonical.launchpad.interfaces.bugnomination import *
from canonical.launchpad.interfaces.bugnotification import *
from canonical.launchpad.interfaces.bugsubscription import *
from canonical.launchpad.interfaces.bugtask import *
from canonical.launchpad.interfaces.bugtarget import *
from canonical.launchpad.interfaces.bugtracker import *
from canonical.launchpad.interfaces.bugwatch import *
from canonical.launchpad.interfaces.build import *
from canonical.launchpad.interfaces.builder import *
from canonical.launchpad.interfaces.buildqueue import *
from canonical.launchpad.interfaces.codeimport import *
from canonical.launchpad.interfaces.codeimportevent import *
from canonical.launchpad.interfaces.codeimportjob import *
from canonical.launchpad.interfaces.codeimportmachine import *
from canonical.launchpad.interfaces.codeimportresult import *
from canonical.launchpad.interfaces.codeimportscheduler import *
from canonical.launchpad.interfaces.codeofconduct import *
from canonical.launchpad.interfaces.codereviewmessage import *
from canonical.launchpad.interfaces.component import *
from canonical.launchpad.interfaces.country import *
from canonical.launchpad.interfaces.cve import *
from canonical.launchpad.interfaces.cvereference import *
from canonical.launchpad.interfaces.distribution import *
from canonical.launchpad.interfaces.distributionbounty import *
from canonical.launchpad.interfaces.distributionmirror import *
from canonical.launchpad.interfaces.distributionsourcepackage import *
from canonical.launchpad.interfaces.distributionsourcepackagecache import *
from canonical.launchpad.interfaces.distributionsourcepackagerelease import *
from canonical.launchpad.interfaces.distroarchseries import *
from canonical.launchpad.interfaces.distroarchseriesbinarypackage import *
from canonical.launchpad.interfaces.distroarchseriesbinarypackagerelease\
    import *
from canonical.launchpad.interfaces.distroseries import *
from canonical.launchpad.interfaces.distroseriesbinarypackage import *
from canonical.launchpad.interfaces.distroserieslanguage import *
from canonical.launchpad.interfaces.distroseriespackagecache import *
from canonical.launchpad.interfaces.distroseriessourcepackagerelease import *
from canonical.launchpad.interfaces.emailaddress import *
from canonical.launchpad.interfaces.entitlement import *
from canonical.launchpad.interfaces.externalbugtracker import *
from canonical.launchpad.interfaces.faq import *
from canonical.launchpad.interfaces.faqcollection import *
from canonical.launchpad.interfaces.faqtarget import *
from canonical.launchpad.interfaces.featuredproject import *
from canonical.launchpad.interfaces.files import *
from canonical.launchpad.interfaces.geoip import *
from canonical.launchpad.interfaces.gpg import *
from canonical.launchpad.interfaces.gpghandler import *
from canonical.launchpad.interfaces.hwdb import *
from canonical.launchpad.interfaces.infestation import *
from canonical.launchpad.interfaces.irc import *
from canonical.launchpad.interfaces.jabber import *
from canonical.launchpad.interfaces.karma import *
from canonical.launchpad.interfaces.language import *
from canonical.launchpad.interfaces.languagepack import *
from canonical.launchpad.interfaces.launchpad import *
from canonical.launchpad.interfaces.launchpadstatistic import *
from canonical.launchpad.interfaces.librarian import *
from canonical.launchpad.interfaces.location import *
from canonical.launchpad.interfaces.logintoken import *
from canonical.launchpad.interfaces.mail import *
from canonical.launchpad.interfaces.mailbox import *
from canonical.launchpad.interfaces.mailinglist import *
from canonical.launchpad.interfaces.mentoringoffer import *
from canonical.launchpad.interfaces.message import *
from canonical.launchpad.interfaces.milestone import *
from canonical.launchpad.interfaces.oauth import *
from canonical.launchpad.interfaces.openidserver import *
from canonical.launchpad.interfaces.package import *
from canonical.launchpad.interfaces.packagerelationship import *
from canonical.launchpad.interfaces.packaging import *
from canonical.launchpad.interfaces.pathlookup import *
from canonical.launchpad.interfaces.person import *
from canonical.launchpad.interfaces.pofile import *
from canonical.launchpad.interfaces.poll import *
from canonical.launchpad.interfaces.pomsgid import *
from canonical.launchpad.interfaces.potemplate import *
from canonical.launchpad.interfaces.potmsgset import *
from canonical.launchpad.interfaces.potranslation import *
from canonical.launchpad.interfaces.processor import *
from canonical.launchpad.interfaces.product import *
from canonical.launchpad.interfaces.productbounty import *
from canonical.launchpad.interfaces.productlicense import *
from canonical.launchpad.interfaces.productrelease import *
from canonical.launchpad.interfaces.productseries import *
from canonical.launchpad.interfaces.project import *
from canonical.launchpad.interfaces.projectbounty import *
from canonical.launchpad.interfaces.publishedpackage import *
from canonical.launchpad.interfaces.publishing import *
from canonical.launchpad.interfaces.queue import *
from canonical.launchpad.interfaces.revision import *
from canonical.launchpad.interfaces.rosettastats import *
from canonical.launchpad.interfaces.schema import *
from canonical.launchpad.interfaces.scriptactivity import *
from canonical.launchpad.interfaces.section import *
from canonical.launchpad.interfaces.shipit import *
from canonical.launchpad.interfaces.sourcepackage import *
from canonical.launchpad.interfaces.sourcepackagename import *
from canonical.launchpad.interfaces.sourcepackagerelease import *
from canonical.launchpad.interfaces.specification import *
from canonical.launchpad.interfaces.specificationbranch import *
from canonical.launchpad.interfaces.specificationbug import *
from canonical.launchpad.interfaces.specificationdependency import *
from canonical.launchpad.interfaces.specificationfeedback import *
from canonical.launchpad.interfaces.specificationsubscription import *
from canonical.launchpad.interfaces.spokenin import *
from canonical.launchpad.interfaces.sprint import *
from canonical.launchpad.interfaces.sprintattendance import *
from canonical.launchpad.interfaces.sprintspecification import *
from canonical.launchpad.interfaces.ssh import *
from canonical.launchpad.interfaces.structuralsubscription import *
from canonical.launchpad.interfaces.teammembership import *
from canonical.launchpad.interfaces.temporaryblobstorage import *
from canonical.launchpad.interfaces.translationcommonformat import *
from canonical.launchpad.interfaces.translationexporter import *
from canonical.launchpad.interfaces.translationfileformat import *
from canonical.launchpad.interfaces.translationimporter import *
from canonical.launchpad.interfaces.translationmessage import *
from canonical.launchpad.interfaces.translations import *
from canonical.launchpad.interfaces.translationsoverview import *
from canonical.launchpad.interfaces.question import *
from canonical.launchpad.interfaces.questionbug import *
from canonical.launchpad.interfaces.questioncollection import *
from canonical.launchpad.interfaces.questionenums import *
from canonical.launchpad.interfaces.questionmessage import *
from canonical.launchpad.interfaces.questionreopening import *
from canonical.launchpad.interfaces.questionsubscription import *
from canonical.launchpad.interfaces.questiontarget import *
from canonical.launchpad.interfaces.translationcommonformat import *
from canonical.launchpad.interfaces.translationgroup import *
from canonical.launchpad.interfaces.translationimportqueue import *
from canonical.launchpad.interfaces.translator import *
from canonical.launchpad.interfaces.vpoexport import *
from canonical.launchpad.interfaces.vpotexport import *
from canonical.launchpad.interfaces.wikiname import *
from canonical.launchpad.interfaces.poexportrequest import *
from canonical.launchpad.interfaces.distrocomponentuploader import *
from canonical.launchpad.interfaces.archive import *
from canonical.launchpad.interfaces.archivedependency import *
from canonical.launchpad.interfaces.packagediff import *
