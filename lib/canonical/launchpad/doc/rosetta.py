Scripts helper functions for Rosetta
====================================

get_domains_from_tarball
------------------------


>>> from canonical.launchpad import helpers
>>> from canonical.launchpad.scripts import rosetta
>>> sourcepackage_name = 'uberfrob'
>>> distrorelease_name = 'hoary'

A case with only Debconf translations.

>>> tarball = helpers.make_tarball({
...     'source/debian/po/templates.pot': 'whatever',
...     'source/debian/po/cy.po': 'whatever',
...     'source/debian/po/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, [], tarball)
>>> len(domains)
1
>>> domains[0].name
'pkgconf-uberfrob'
>>> domains[0].pot_contents
'whatever'
>>> domains[0].pot_filename
'templates.pot'
>>> domains[0].domain_paths
['source/debian/po']
>>> domains[0].binary_packages
[]
>>> po_files = domains[0].po_files
>>> po_files['es']
'whatever2'
>>> po_files['cy']
'whatever'

We have only one translation domain, a .pot file and a set of .po files.

>>> tarball = helpers.make_tarball({
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob.mo':
...         'binary content for cy translation of uberfrob',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob.mo':
...         'binary content for es translation of uberfrob',
...     'source/po/template.pot': 'whatever',
...     'source/po/cy.po': 'whatever',
...     'source/po/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, [], tarball)
>>> len(domains)
1
>>> domains[0].name
'uberfrob'
>>> domains[0].pot_contents
'whatever'
>>> domains[0].pot_filename
'template.pot'
>>> domains[0].domain_paths
['source/po']
>>> domains[0].binary_packages
['uberfrob-package']
>>> po_files = domains[0].po_files
>>> po_files['es']
'whatever2'
>>> po_files['cy']
'whatever'

Now pass in some previously existing PO templates which match ones in the
tarball. The code should use the existing PO templates from the database.

>>> class DummyPOTemplateName:
...     def __init__(self, name):
...         self.name = name
...
>>> class DummyPOTemplate:
...     def __init__(self, name, path, filename):
...         self.potemplatename = DummyPOTemplateName(name)
...         self.path = path
...         self.filename = filename

>>> potemplateset = [
...     DummyPOTemplate(
...         name='uberfrob',
...         path='po',
...         filename='uberfrob-splat.pot'),
...     DummyPOTemplate(
...         name='uberfrob-x',
...         path='po-x',
...         filename='uberfrob-xyzzy.pot'),
... ]
>>> tarball = helpers.make_tarball({
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob.mo':
...         'binary content for cy translation of uberfrob',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob.mo':
...         'binary content for es translation of uberfrob',
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob-x.mo':
...         'binary content for cy translation of uberfrob x domain',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob-x.mo':
...         'binary content for es translation of uberfrob x domain',
...     'source/po/uberfrob-splat.pot': 'whatever',
...     'source/po/cy.po': 'whatever',
...     'source/po/es.po': 'whatever2',
...     'source/po-x/uberfrob-xyzzy.pot': 'whatever',
...     'source/po-x/cy.po': 'whatever',
...     'source/po-x/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, potemplateset, tarball)
>>> len(domains)
2

First domain:

>>> domains[0].name
'uberfrob-x'
>>> domains[0].pot_filename
'uberfrob-xyzzy.pot'

Second domain:

>>> domains[1].name
'uberfrob'
>>> domains[1].pot_filename
'uberfrob-splat.pot'

We have multiple domains and the filenames of the PO templates in the
source match the names of the MO files in the binary packages. Note that
there are no existing PO templates in this case which could be used.

>>> tarball = helpers.make_tarball({
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob.mo':
...         'binary content for cy translation of uberfrob',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob.mo':
...         'binary content for es translation of uberfrob',
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob-x.mo':
...         'binary content for cy translation of uberfrob x domain',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob-x.mo':
...         'binary content for es translation of uberfrob x domain',
...     'source/po/uberfrob.pot': 'whatever',
...     'source/po/cy.po': 'whatever',
...     'source/po/es.po': 'whatever2',
...     'source/po-x/uberfrob-x.pot': 'whatever',
...     'source/po-x/cy.po': 'whatever',
...     'source/po-x/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, [], tarball)
>>> len(domains)
2

First domain:

>>> domains[0].name
'uberfrob-x'
>>> domains[0].pot_contents
'whatever'
>>> domains[0].pot_filename
'uberfrob-x.pot'
>>> domains[0].domain_paths
['source/po-x']
>>> domains[0].binary_packages
['uberfrob-package']
>>> po_files = domains[0].po_files
>>> po_files['es']
'whatever2'
>>> po_files['cy']
'whatever'

Second domain:

>>> domains[1].name
'uberfrob'
>>> domains[1].pot_contents
'whatever'
>>> domains[1].pot_filename
'uberfrob.pot'
>>> domains[1].domain_paths
['source/po']
>>> domains[1].binary_packages
['uberfrob-package']
>>> po_files = domains[1].po_files
>>> po_files['es']
'whatever2'
>>> po_files['cy']
'whatever'

The fallback case, when we can't match a PO template to a domain in the
tarball, or an existing PO template from the database, and it's not a
Debconf template.

>>> potemplateset = []
>>> tarball = helpers.make_tarball({
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob.mo':
...         'binary content for cy translation of uberfrob',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob.mo':
...         'binary content for es translation of uberfrob',
...     'source/po/uberfrob-splat.pot': 'whatever',
...     'source/po/cy.po': 'whatever',
...     'source/po/es.po': 'whatever2',
...     'source/po-x/uberfrob-xyzzy.pot': 'whatever',
...     'source/po-x/cy.po': 'whatever',
...     'source/po-x/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, potemplateset, tarball)
>>> len(domains)
2

First domain:

>>> domains[0].name
'review-potemplate-hoary-uberfrob-1'
>>> domains[0].pot_filename
'uberfrob-xyzzy.pot'

Second domain:

>>> domains[1].name
'review-potemplate-hoary-uberfrob-2'
>>> domains[1].pot_filename
'uberfrob-splat.pot'

This is a combination case, when we have both a Debconf template and two
unidentifiable templates.

>>> potemplateset = []
>>> tarball = helpers.make_tarball({
...     'uberfrob-package/usr/share/locale/cy/LC_MESSAGES/uberfrob.mo':
...         'binary content for cy translation of uberfrob',
...     'uberfrob-package/usr/share/locale/es/LC_MESSAGES/uberfrob.mo':
...         'binary content for es translation of uberfrob',
...     'source/debian/po/templates.pot': 'whatever',
...     'source/debian/po/cy.po': 'whatever',
...     'source/debian/po/es.po': 'whatever2',
...     'source/po/uberfrob-splat.pot': 'whatever',
...     'source/po/cy.po': 'whatever',
...     'source/po/es.po': 'whatever2',
...     'source/po-x/uberfrob-xyzzy.pot': 'whatever',
...     'source/po-x/cy.po': 'whatever',
...     'source/po-x/es.po': 'whatever2',
...     })
>>> domains = rosetta.get_domains_from_tarball(
...     distrorelease_name, sourcepackage_name, [], tarball)
>>> len(domains)
3

First domain:

>>> domains[0].name
'pkgconf-uberfrob'
>>> domains[0].pot_filename
'templates.pot'

Second domain:

>>> domains[1].name
'review-potemplate-hoary-uberfrob-1'
>>> domains[1].pot_filename
'uberfrob-xyzzy.pot'

Third domain:

>>> domains[2].name
'review-potemplate-hoary-uberfrob-2'
>>> domains[2].pot_filename
'uberfrob-splat.pot'

