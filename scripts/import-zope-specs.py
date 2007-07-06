#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

# A script to import metadata about the Zope 3 specs into Launchpad

__metaclass__ = type

import itertools
import re
import sys
import urllib2

import _pythonpath
from zope.component import getUtility
from BeautifulSoup import BeautifulSoup

from canonical.lp import initZopeless
from canonical.lp.dbschema import (
    SpecificationStatus, SpecificationGoalStatus, SpecificationDelivery,
    SpecificationPriority)
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, ISpecificationSet)

WIKI_BASE = 'http://wiki.zope.org/zope3/'
PROPOSAL_LISTS = ['Zope3Proposals', 'OldProposals', 'DraftProposals']
specroot = WIKI_BASE + 'Zope3Proposals'

at_replacements = ['_at_', '(at)', '&#64;']
author_email_pat = re.compile('[-.A-Za-z0-9]+(?:@|%s)[-.A-Za-z0-9]+' %
                              '|'.join([re.escape(replacement)
                                        for replacement in at_replacements]))

def getTextContent(tag):
    if tag is None:
        return ''
    if isinstance(tag, basestring):
        return tag
    return ''.join([e for e in tag.recursiveChildGenerator()
                    if isinstance(e, basestring)])


class ZopeSpec:

    def __init__(self, url, title, summary):
        self.url = url
        self.name = self.url.split('/')[-1]
        self.title = title
        self.summary = summary
        self.authors = set()
        self.statuses = set()

    def parseAuthorEmails(self, text):
        author_email_list = author_email_pat.findall(text)
        for author in author_email_list:
            # unmangle at symbol in email:
            for replacement in at_replacements:
                author = author.replace(replacement, '@')
            self.authors.add(author)

    def parseStatuses(self, soup):
        wiki_badges = [
            'IsWorkInProgress',

            'IsProposal',
            'IsRejectedProposal',
            'IsSupercededProposal',
            'IsRetractedProposal',
            'IsAcceptedProposal',
            'IsImplementedProposal',
            'IsExpiredProposal',
            'IsDraftProposal',

            'IsPlanned',
            'IsResolved',
            'IsImplemented',

            'IsReplaced',
            'IsOutdated',
            'IsDraft',
            'IsEditedDraft',
            'IsRoughDraft',
            ]
        for badge in wiki_badges:
            url = WIKI_BASE + badge
            if soup.fetch('a', {'href': url}):
                self.statuses.add(badge)

    def parseSpec(self):
        contents = urllib2.urlopen(self.url).read()
        soup = BeautifulSoup(contents)
        contentdivs = soup('div', {'class': 'content'})
        assert len(contentdivs) == 1
        contentdiv = contentdivs[0]

        # Specification statuses are represented by "wiki badges",
        # which are just hyperlinks to particular pages.
        self.parseStatuses(soup)

        # There are two styles of spec.  One of them has a table with
        # RFC-822 style headers in it.  The other has minor level headings
        # with text under the heading.
        tables = soup('table')
        # Every page has one table, for the main page layout.  So, if the page
        # has two tables, it means that it will be using the RFC-822 style.
        if len(tables) >= 2:
            # This is a spec with RFC-822 style headers.
            docinfo = tables[1]
            for row in docinfo('tr'):
                if len(row('th')) < 1 or len(row('td')) < 1:
                    continue
                key = row('th')[0].renderContents()
                if key.endswith(':'):
                    key = key[:-1]
                value = row('td')[0].renderContents()

                if 'Author' in key:
                    self.parseAuthorEmails(value)
        else:
            # This is a spec with minor level headings, or perhaps with no
            # headings at all.

            # Look for an author heading.
            author_headers = soup(text=re.compile('Author.*', re.I))
            if author_headers:
                author = author_headers[0].findNext().renderContents()
                self.parseAuthorEmails(author)
        
    @property
    def lpname(self):
        # add dashes before capitalised words
        name = re.sub(r'([^A-Z])([A-Z])', r'\1-\2', self.name)
        # lower case name
        name = name.lower()
        # remove leading dashes
        while name.startswith('-'):
            name = name[1:]
        # if name doesn't begin with an alphabetical character prefix it
        if not name[0].isalpha():
            name = 'x-' + name
        return name

    @property
    def lpstatus(self):
        # implemented and accepted specs => APPROVED
        for status in ['IsImplemented',
                       'IsImplementedProposal',
                       'IsAcceptedProposal']:
            if status in self.statuses:
                return SpecificationStatus.APPROVED
        # WIP => DISCUSSION
        if 'IsWorkInProgress' in self.statuses:
            return SpecificationStatus.DISCUSSION
        for status in ['IsSupercededProposal', 'IsReplaced']:
            if status in self.statuses:
                return SpecificationStatus.SUPERSEDED
        for status in ['IsExpiredProposal', 'IsOutdated']:
            if status in self.statuses:
                return SpecificationStatus.OBSOLETE
        # draft statuses:
        for status in ['IsDraftProposal',
                       'IsDraft',
                       'IsEditedDraft',
                       'IsRoughDraft']:
            if status in self.statuses:
                return SpecificationStatus.DRAFT
        # otherwise ...
        return SpecificationStatus.PENDINGREVIEW

    @property
    def lpgoalstatus(self):
        # implemented and accepted specs => ACCEPTED
        for status in ['IsImplemented',
                       'IsImplementedProposal',
                       'IsAcceptedProposal']:
            if status in self.statuses:
                return SpecificationGoalStatus.ACCEPTED
        # rejected or retracted => DECLINED
        for status in ['IsRetractedProposal', 'IsRejectedProposal']:
            if status in self.statuses:
                return SpecificationGoalStatus.DECLINED

        # otherwise ...
        return SpecificationGoalStatus.PROPOSED

    @property
    def lpdelivery(self):
        for status in ['IsImplemented',
                       'IsImplementedProposal']:
            if status in self.statuses:
                return SpecificationDelivery.IMPLEMENTED
        # otherwise ...
        return SpecificationDelivery.UNKNOWN

    def syncSpec(self):
        zope = getUtility(IProductSet).getByName('zope')
        zope_dev = getUtility(IPersonSet).getByName('zope-dev')
        # has the spec been created?
        lpspec = getUtility(ISpecificationSet).getByURL(self.url)
        if not lpspec:
            lpspec = getUtility(ISpecificationSet).new(
                name=self.lpname,
                title=self.title,
                specurl=self.url,
                summary=self.summary,
                priority=SpecificationPriority.UNDEFINED,
                status=SpecificationStatus.NEW,
                owner=zope_dev,
                product=zope)

        # synchronise
        lpspec.title = self.title
        lpspec.summary = self.summary
        lpspec.status = self.lpstatus
        newgoalstatus = self.lpgoalstatus
        if newgoalstatus != lpspec.goalstatus:
            if newgoalstatus == SpecificationGoalStatus.PROPOSED:
                lpspec.proposeGoal(None, zope_dev)
            elif newgoalstatus == SpecificationGoalStatus.ACCEPTED:
                lpspec.acceptBy(zope_dev)
            elif newgoalstatus == SpecificationGoalStatus.DECLINED:
                lpspec.declineBy(zope_dev)
        lpspec.delivery = self.lpdelivery
        lpspec.updateLifecycleStatus(zope_dev)
            
        # set the assignee to the first author email with an LP account
        for author in sorted(self.authors):
            person = getUtility(IPersonSet).getByEmail(author)
            if person is not None:
                lpspec.assignee = person
                break


def iter_spec_urls(url=specroot):
    contents = urllib2.urlopen(url)
    soup = BeautifulSoup(contents)
    contentdivs = soup('div', {'class': 'content'})
    assert len(contentdivs) == 1
    contentdiv = contentdivs[0]
    listofspecs = contentdiv('ul')[0]

    for listitem in listofspecs('li', recursive=False):
        anchors = listitem('a')
        if not anchors:
            continue
        specanchor = anchors[0]
        href = specanchor['href']
        # broken wiki link => ignore
        if 'createform?page=' in href:
            continue
        title = getTextContent(specanchor)
        summary = ''.join([getTextContent(tag)
                               for tag in specanchor.nextSiblingGenerator()])
        yield ZopeSpec(href, title, summary.strip())

        
def main(argv):
    execute_zcml_for_scripts()
    ztm = initZopeless()

    for spec in itertools.chain(*[iter_spec_urls(WIKI_BASE + page)
                                  for page in PROPOSAL_LISTS]):
        # parse extra information from the spec body
        spec.parseSpec()
        # add its metadata to LP
        print 'Synchronising', spec.name
        ztm.begin()
        try:
            spec.syncSpec()
            ztm.commit()
        except:
            ztm.abort()
            raise

if __name__ == '__main__':
    sys.exit(main(sys.argv))
