# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""A set of functions related to the ability to parse the XML CVE database,
extract details of known CVE entries, and ensure that all of the known
CVE's are fully registered in Launchpad."""

__metaclass__ = type

from zope.component import getUtility
from zope.event import notify

from zope.app.event.objectevent import ObjectModifiedEvent

from canonical.lp.dbschema import CveStatus
from canonical.launchpad.interfaces import ICveSet


CVEDB_NS = '{http://cve.mitre.org/cve/downloads/xml_schema_info.html}'

def getText(elem):
    """Get the text content of the given element"""
    text = elem.text or ""
    for e in elem:
        text += getText(e)
        if e.tail:
            text += e.tail
    return text.strip()


def handle_references(cve_node, cve, log):
    """Handle the references on the given CVE xml DOM.

    This function is passed an XML dom representing a CVE, and a CVE
    database object. It looks for Refs in the XML data structure and ensures
    that those are correctly represented in the database.

    It will try to find a relevant reference, and if so, update it. If
    not, it will create a new reference.  Finally, it removes any old
    references that it no longer sees in the official CVE database.
    It will return True or False, indicating whether or not the cve was
    modified in the process.
    """
    modified = False
    # we make a copy of the references list because we will be removing
    # items from it, to see what's left over
    old_references = set(cve.references)
    new_references = set()

    # work through the refs in the xml dump
    for ref_node in cve_node.findall('.//%sref' % CVEDB_NS):
        refsrc = ref_node.get("source")
        refurl = ref_node.get("url")
        reftxt = getText(ref_node)
        # compare it to each of the known references
        was_there_previously = False
        for ref in old_references:
            if ref.source == refsrc and ref.url == refurl and \
               ref.content == reftxt:
                # we have found a match, remove it from the old list
                was_there_previously = True
                new_references.add(ref)
                break
        if not was_there_previously:
            log.info("Creating new %s reference for %s" % (refsrc,
                cve.sequence))
            ref = cve.createReference(refsrc, reftxt, url=refurl)
            new_references.add(ref)
            modified = True
    # now, if there are any refs in old_references that are not in
    # new_references, then we need to get rid of them
    for ref in sorted(old_references,
        key=lambda a: (a.source, a.content, a.url)):
        if ref not in new_references:
            log.info("Removing %s reference for %s" % (ref.source,
                cve.sequence))
            cve.removeReference(ref)
            modified = True

    return modified


def update_one_cve(cve_node, log):
    """Update the state of a single CVE item."""
    # get the sequence number
    sequence = cve_node.get('seq')
    # establish its status
    status = cve_node.get('type')
    # get the description
    description = getText(cve_node.find(CVEDB_NS + 'desc'))
    if not description:
        log.debug('No description for CVE-%s' % sequence)
    if status == 'CAN':
        new_status = CveStatus.CANDIDATE
    elif status == 'CVE':
        new_status = CveStatus.ENTRY
    else:
        log.error('Unknown status %s for CVE-%s' % (status, sequence))
        return
    # find or create the CVE entry in the db
    cveset = getUtility(ICveSet)
    cve = cveset[sequence]
    if cve is None:
        cve = cveset.new(sequence, description, new_status)
        log.info('CVE-%s created' % sequence)
    # update the CVE if needed
    modified = False
    if cve.status <> new_status:
        log.info('CVE-%s changed from %s to %s' % (cve.sequence,
            cve.status.title, new_status.title))
        cve.status = new_status
        modified = True
    if cve.description <> description:
        log.info('CVE-%s updated description' % cve.sequence)
        cve.description = description
        modified = True
    # make sure we have copies of all the references.
    if handle_references(cve_node, cve, log):
        modified = True
    # trigger an event if modified
    if modified:
        notify(ObjectModifiedEvent(cve))
    return


