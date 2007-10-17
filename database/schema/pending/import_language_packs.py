#!/usr/bin/python2.4
# Copyright 2007 Canonical Ldt.  All rights reserved.

"""Script to upload existing language packs into Launchpad."""

from urllib2 import urlopen
from zope.component import getUtility

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import (
    IDistributionSet, ILanguagePackSet, LanguagePackType)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp import initZopeless

language_packs_dates = {
    'dapper': '2007-08-03',
    'edgy': '2006-10-19',
    'feisty': '2007-04-12',
    'gutsy': '2007-08-02',
    }


def get_langpack_url(distroseries_name, export_date):
    filename = 'rosetta-%s-%s.tar.gz' % (distroseries_name, export_date)
    return 'http://people.ubuntu.com/~carlos/language-packs/%s/%s' % (
        distroseries_name, filename)


def main():
    # setup a transaction manager to LPDB
    tm = initZopeless()

    # load the zcml configuration
    execute_zcml_for_scripts()

    # get an librarian client instance
    client = getUtility(ILibrarianClient)

    for distroseries_name, langpack_date in language_packs_dates.iteritems():
        # Open the language pack file.
        langpack = urlopen(get_langpack_url(distroseries_name, langpack_date))

        # Get some metadata information.
        flen = int(langpack.info()['Content-Length'])
        filename = 'ubuntu-%s-translations.tar.gz' % distroseries_name
        ftype = 'application/x-gtar'

        # Add it to Librarian
        file_alias = client.addFile(
            filename, flen, langpack, contentType=ftype)

        # Register it in the LanguagePack table.
        distribution = getUtility(IDistributionSet)['ubuntu']
        distroseries = distribution.getSeries(distroseries_name)
        language_pack_set = getUtility(ILanguagePackSet)
        lang_pack_type = LanguagePackType.FULL

        # And set it as the base one.
        distroseries.language_pack_base = language_pack_set.addLanguagePack(
            distroseries, file_alias, lang_pack_type)

        # Store the changes.
        tm.commit()


if __name__ == '__main__':
    main()
