/*
   SOYUZ SAMPLE DATA
   
   This is some sample data for the Soyuz App components.  
   This requires the default data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/


-- Component
INSERT INTO Component (name) VALUES ('default_component');

-- Section

INSERT INTO Section (name) VALUES ('default_section');

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES
	('Mark schema', 'TITLE', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES 
	('schema', 'SCHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES
	('trema', 'XCHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);

INSERT INTO Schema (name, title, description, owner, extensible) VALUES 
	('enema', 'ENHEMA', 'description', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'), 
	TRUE);
-- Sourcepackagename
INSERT INTO Sourcepackagename (name)
	VALUES('mozilla-firefox'); 
INSERT INTO Sourcepackagename (name)
	VALUES('mozilla-thunderbird'); 
INSERT INTO Sourcepackagename (name)
	VALUES('python-twisted'); 
INSERT INTO Sourcepackagename (name)
	VALUES('bugzilla'); 
INSERT INTO Sourcepackagename (name)
	VALUES('arch'); 
INSERT INTO Sourcepackagename (name)
	VALUES('kiwi2'); 
INSERT INTO Sourcepackagename (name)
	VALUES('plone'); 
INSERT INTO Sourcepackagename (name)
	VALUES('evolution'); 


-- Sourcepackage
INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'),
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        (SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'),
	'Mozilla Thunderbird Mail Reader', 
         'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        (SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'),
	'Python Twisted', 
         'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        (SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'),
	'Bugzilla', 
        'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        (SELECT id FROM Sourcepackagename WHERE name = 'arch'),
	'Arch(TLA)', 
        'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        (SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'),
	'Kiwi2', 
         ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk\'s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
        (SELECT id FROM Sourcepackagename WHERE name = 'plone'),
	'Plone', 
        'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.');

INSERT INTO Sourcepackage (maintainer, sourcepackagename, shortdesc, 
	description)
VALUES ((SELECT id FROM Person WHERE displayname = 'Jeff Waugh'),
        (SELECT id FROM Sourcepackagename WHERE name = 'evolution'),
	'Evolution', 
        'Evolution is the integrated mail, calendar, task and address book 
	distributed suite from Ximian, Inc.');


--SourcepackageRelease
INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM SOurcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-6',
        timestamp '2004-06-17 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-7',
        timestamp '2004-06-18 00:00',
        1);


INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-8',
        timestamp '2004-06-19 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.0-9',
        timestamp '2004-06-20 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'),
        '0.9.1-1',
        timestamp '2004-06-29 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Steve Alexander'),
        '0.9.1-2',
        timestamp '2004-06-30 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM SOurcepackagename WHERE name = 'python-twisted')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts'),
        '0.9.1-3',
        timestamp '2004-07-01 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Dave Miller'),
        '0.9.1-4',
        timestamp '2004-07-02 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'James Blackwell'),
        '0.9.1-5',
        timestamp '2004-07-03 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Christian Reis'),
        '0.9.1-6',
        timestamp '2004-07-04 00:00',
        1);

INSERT INTO SourcepackageRelease (sourcepackage, srcpackageformat, creator,
                                  version, dateuploaded, urgency)
VALUES ((SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone')),
 	1,
        (SELECT id FROM Person WHERE displayname = 'Alexander Limi'),
        '0.9.1-7',
        timestamp '2004-07-05 00:00',
        1);

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))
	;

UPDATE sourcepackagerelease set builddepends = 
	'mozilla-firefox  (>= 0.9.0-9), mozilla-thunderbird, arch'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'evolution'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))
	;

UPDATE sourcepackagerelease set builddependsindep = 
	'kiwi (>= 2.0),python-twisted , bugzilla, plone'
	where sourcepackage = 
	(SELECT id FROM Sourcepackage WHERE sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'evolution'))
	;

UPDATE sourcepackagerelease set changelog = 
'
mozilla-thunderbird (0.5-4) unstable; urgency=low

  * reenabled hppa patch, which apparently led to FTBFS on hppa

 -- Alexander Sack <asac@jwsdot.com>  Thu, 04 Mar 2004 21:30:20 +0100

mozilla-thunderbird (0.5-3) unstable; urgency=medium

  * preinst added to allow clean upgrade path to this
      (Closes: 234118, Closes: 234267)
  * added prerm script to allow a clean remove of package

 -- Alexander Sack <asac@jwsdot.com>  Sun, 29 Feb 2004 10:30:20 +0100

mozilla-thunderbird (0.5-2) unstable; urgency=low

  * new source package layout!! Now using orig.tar.gz with diff.gz
    (Closes: 232055)
  * moved arch-indep chrome stuff to /usr/share/mozilla-thunderbird/chrome
  * moved images to /usr/share/mozilla-thunderbird/res
      /usr/share/mozilla-thunderbird/icons
      /usr/share/mozilla-thunderbird/chrome/icons

 -- Alexander Sack <asac@jwsdot.com>  Thu, 19 Feb 2004 19:30:20 +0100

mozilla-thunderbird (0.5-1.1) unstable; urgency=low

  * new source package layout!! Now using orig.tar.gz with diff.gz

 -- Alexander Sack <asac@jwsdot.com>  Mon, 11 Feb 2003 19:30:20 +0100

mozilla-thunderbird (0.5-1) unstable; urgency=low

 Aggregated changes since 0.4-1:
  * new upstream release 0.5 included
  * added xprt-xprintorg to Recommends (Closes: 226626)
  * upgraded enigmail to 0.83.2 (Closes: 228678)
      + includes a workaround for mozilla bug
          leading to a crash in rare situations
          (fixed in 0.82.6)
  * improved package structure. Sources now are included as original archives
        & are extracted to build-dir. (Closes: 225033)
  * Minor wording changes in package description, pointed out by
      Mark Stevenson.
  * New debianization of appearance (branding)
  * added switches for pref.js config entries for
        individual doubleclick timeout & drag threshold
        settings in gtk2 (Closes: 229146)

 -- Alexander Sack <asac@jwsdot.com>  Mon, 09 Feb 2003 19:30:20 +0100
' 
WHERE  sourcepackage = (SELECT id from sourcepackage where sourcepackagename = 
	(select id from sourcepackagename where name = 'mozilla-thunderbird')
	);


UPDATE sourcepackagerelease set changelog = 
'
mozilla-firefox (0.8-12) unstable; urgency=low

  * The "Last Chance Before 0.9" release.
  * debian/mozilla-firefox-runner: Fix unescaped \n, thanks Olly
    Betts. (Closes: #252436)
  * debian/update-mozilla-firefox-chrome: Watch out for empty
    LD_LIBRARY_PATH. Thanks George Cristian Birzan. (Closes: #254142)
  * debian/README.Debian: Restructure and update a bit.
  * debian/presubj: Add bug information from README.Debian for reportbug.
  * debian/mozilla-firefox.install: Install the presubj.

 -- Eric Dorland <eric@debian.org>  Mon, 14 Jun 2004 19:39:27 -0400

mozilla-firefox (0.8-11) unstable; urgency=low

  * Apply amd64 fix from #249211.
  * debian/README.Debian: Shamelessly stole the java plugin installation
    instructions from the mozilla package. (Closes: #243513)
  * nsCommonWidget.cpp, nsCommonWidget.h, nsWindow.cpp: Apply patch (with
    some hand massaging) from upstream bugzilla bug #209342 to fix initial
    window placement. (Closes: #235209, 241519)
  * nsprpub/pr/src/misc/prnetdb.c: Apply patch from Miquel van Smoorenburg
    to prevent unless reverse DNS lookups. (Closes: #251978)
  * debian/mozilla-firefox-runner: Apply patch from Jasper Spaans to fix
    remote xprint printing. (Closes: #252072)

 -- Eric Dorland <eric@debian.org>  Tue,  1 Jun 2004 23:12:36 -0400

mozilla-firefox (0.8-10) unstable; urgency=low

  * debian/mozilla-firefox.install: Don\'t install uuencoded file. (Closes:
    #251441)
  * debian/mozilla-firefox-runner: unset AUDIODEV which can cause
    crashes. Thanks Christopher Armstrong. (Closes: #236231)
  * update-mozilla-firefox-chrome: Port security fix from #249613 to
    handle insecure tempfile creation.
  * debian/rules: Following the advice of #247585 I\'m disabling postscript
    printing. Perhaps this will alleviate some of the other printing
    problems.

 -- Eric Dorland <eric@debian.org>  Sun, 30 May 2004 01:47:52 -0400

mozilla-firefox (0.8-9) unstable; urgency=low

  * debian/control:
    - Suggest latex-xft-fonts for MathML fonts. Thanks Michael
      JasonSmith. (Closes: #216925)
    - Build depend on libx11-dev & libxp-dev instead of xlibs-dev to
      reflect new X packages.
  * widget/src/gtk2/nsWindow.cpp: Apply patch from Peter Colberg to ignore
    unused mouse buttons. (Closes: #244305)
  * debian/README.Debian: Document the fact that the loopback interface
    has to be up and unfiltered for things to work right.

 -- Eric Dorland <eric@debian.org>  Wed,  5 May 2004 23:30:42 -0400

'
WHERE  sourcepackage = (SELECT id from sourcepackage where sourcepackagename = 
	(select id from sourcepackagename where name = 'mozilla-firefox')
	);




--Manifest
INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-29 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-30 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Steve Alexander')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-01 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-02 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Dave Miller')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-03 00:00',  
 (SELECT id FROM Person WHERE displayname = 'James Blackwell')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-04 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Christian Reis')
 );

INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-07-05 00:00',  
 (SELECT id FROM Person WHERE displayname = 'Alexander Limi')
 );


--CodeRelease
INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-06-29 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-06-30 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-30 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-01 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-01 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-02 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-02 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-03 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-03 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-04 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-07-04 00:00'));

INSERT INTO CodeRelease (sourcepackagerelease, manifest) 
VALUES ((SELECT id FROM SourcepackageRelease WHERE 
	dateuploaded = timestamp '2004-07-05 00:00'),
 (SELECT id FROM Manifest WHERE datecreated = timestamp '2004-06-29 00:00'));


--ArchArchive
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('mozilla', 'Mozilla', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('thunderbird', 'Thunderbid', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('twisted', 'Twisted', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('bugzila', 'Bugzila', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('arch', 'Arch', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('kiwi2', 'Kiwi2', 'text', false);

INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('plone', 'Plone', 'text', false);


--Archnamespace
INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (1, 'mozilla', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (2, 'tunderbird', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (3, 'twisted', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (4, 'bugzila', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (5, 'arch', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (6, 'kiwi2', true);

INSERT INTO Archnamespace (archarchive, category, visible) 
VALUES (7, 'plone', true);


--Branch
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'mozilla'),
        'Mozilla Firefox 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'thunderbird'),
        'Mozilla Thunderbird 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Steve Alexander')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'twisted'),
        'Python Twisted 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Andrew Bennetts')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'bugzila'),
        'Bugzila 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Dave Miller')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'arch'),
        'Arch 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'James Blackwell')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'kiwi2'),
        'Kiwi2 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Christian Reis')); 

INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'plone'),
        'Plone 0.9.1', 'text',
 (SELECT id FROM Person WHERE displayname = 'Alexander Limi'));


 -- Label
INSERT INTO Label (schema, name, title, description)
VALUES ((SELECT id FROM Schema WHERE name = 'Mark schema'),
         'blah', 'blah', 'blah');
 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 
	'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));

-- Distribution
INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('ubuntu', 'Ubuntu', 
	'Ubuntu is a new concept of GNU/Linux Distribution based on Debian GNU/Linux.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('redhat', 'Redhat Advanced Server', 
	'Red Hat is a commercial distribution of GNU/Linux Operating System.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('debian', 'Debian GNU/Linux', 
	'Debian GNU/Linux is a non commercial distribution of a GNU/Linux Operating System for many platforms.', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('gentoo', 'The Gentoo Linux', 
	'Gentoo is a very customizeable GNU/Linux Distribution', 
	'domain', 1);

INSERT INTO Distribution (name, title, description, domainname, owner) 
	values ('porkypigpolka', 'Porky Pig Polka Distribution', 
	'Should be near the Spork concept of GNU/Linux Distribution',
	'domain', 1);



-- Distrorelease
INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	values 
	('warty', 'Warty', 'This is the first stable release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'), 
	'1.0.0', 
	'2004-08-20',
	1, 1, 3, 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('six', 'Six Six Six', 
	'some text to describe the whole 666 release of RH', 
	(SELECT id FROM Distribution WHERE name = 'redhat'), 
	'6.0.1', 
	'2004-03-21',
	1, 1, 4, 8);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease, 
	owner) 
	VALUES ('hoary', 'Hoary Crazy-Unstable', 
	'Hoary is the next release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'), 
	'0.0.1',
	'2004-08-25', 
	1, 1, 2, 
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('7.0', 'Seven', 
	'The release that we would not expect', 
	(SELECT id FROM Distribution WHERE name = 'redhat'), 
	'7.0.1', 
	'2004-04-01',
	1, 1, 3, 
	(SELECT id FROM Distrorelease WHERE name = 'six'),
	7);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('grumpy', 'G-R-U-M-P-Y', 
	'Grumpy is far far away, but should be the third release of Ubuntu', 
	(SELECT id FROM Distribution WHERE name = 'ubuntu'),
	'-0.0.1', 
	'2004-08-29',
	1, 1, 1, 
	(SELECT id FROM Distrorelease WHERE name = 'warty'),
	1);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, owner) 
	VALUES ('woody', 'WOODY', 
	'WOODY is the current stable verison of Debian GNU/Linux', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.0', 
	'2003-01-01',
	1, 1, 4, 2);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('sarge', 'Sarge', 
	'Sarge is the FROZEN unstable version of Debian GNU/Linux.', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.1', 
	'2004-09-29',
	1, 1, 3, 
	(SELECT id FROM Distrorelease WHERE name = 'woody'),
	5);

INSERT INTO Distrorelease (name, title, description, distribution, version, 
	datereleased, components, sections, releasestate, parentrelease,
	owner) 
	VALUES ('sid', 'Sid', 
	'Sid is the CRAZY unstable version of Debian GNU/Linux.', 
	(SELECT id FROM Distribution WHERE name = 'debian'),
	'3.2', 
	'2004-12-29',
	1, 1, 1, 
	(SELECT id FROM Distrorelease WHERE name = 'woody'),
	6);

--Distroreleaserole Persons ?!

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	1);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	1);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distrorelease WHERE name = 'grumpy'),
	1);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	2);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	2);
INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distrorelease WHERE name = 'grumpy'),
	3);

-- Distroreleaserole Teams ?!

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Warty Security Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Warty Gnome Team'),
	(SELECT id from Distrorelease WHERE name = 'warty'),
	4);

INSERT INTO Distroreleaserole (person, distrorelease, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Hoary Gnome Team'),
	(SELECT id from Distrorelease WHERE name = 'hoary'),
	4);


--Distributionrole Persons ?!

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Mark Shuttleworth'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Steve Alexander'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Alexander Limi'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Andrew Bennetts'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Scott James Remnant'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	1);

-- DistributionRole Teams ?!

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Ubuntu Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);

INSERT INTO Distributionrole (person, distribution, role) 
	VALUES(
	(SELECT id from Person WHERE displayname = 'Ubuntu Gnome Team'),
	(SELECT id from Distribution WHERE name = 'ubuntu'),
	3);


--DistroArchrelease
INSERT INTO Distroarchrelease(distrorelease, processorfamily, architecturetag, 
	owner) VALUES 
	((SELECT id FROM Distrorelease where name = 'warty'), 
	(SELECT id from Processorfamily where name = 'x86'), 
	'warty--x86--devel--0', 
	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth')
	);

-- Build

INSERT INTO Build (datecreated, processor, distroarchrelease, buildstate)
	VALUES
	('2004-08-24',
	(SELECT id FROM Processor where name = '386'),
	1, -- hardcoded ?!?! use query instead
	1  -- ??
	);	

--Binarypackagename
INSERT INTO Binarypackagename(name) VALUES ('mozilla-firefox');
INSERT INTO Binarypackagename(name) VALUES ('mozilla-thunderbird');
INSERT INTO Binarypackagename(name) VALUES ('python-twisted');
INSERT INTO Binarypackagename(name) VALUES ('bugzilla');
INSERT INTO Binarypackagename(name) VALUES ('arch');
INSERT INTO Binarypackagename(name) VALUES ('kiwi');
INSERT INTO Binarypackagename(name) VALUES ('plone');

-- Binarypackage
INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.1-1'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.9.1-1', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');	

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.0-9'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.9.0-9', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.0-8'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.9.0-8', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.0-7'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.9.0-7', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))  
	and version='0.9.0-6'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-firefox'), 
	'0.9.0-6', 
	'Mozilla Firefox Web Browser', 
        'Firefox is a redesign of the Mozilla browser component, similar to Galeon, 
	K-Meleon and Camino, but written using the XUL user interface language and 
	designed to lightweight and cross-platform.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-thunderbird'))
	and version='0.9.1-2'),
	(SELECT id from Binarypackagename WHERE name = 'mozilla-thunderbird'), 
	'0.9.1-2', 
	'Mozilla Thunderbird Mail Reader', 
        'Mozilla Thunderbird is a redesign of the Mozilla mail component. 
	The goal is to produce a cross platform stand alone mail application 
	using the XUL user interface language. Mozilla Thunderbird leaves a 
	somewhat smaller memory footprint than the Mozilla suite.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3 -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))
	and version = '0.9.1-3'),
	(SELECT id from Binarypackagename WHERE name = 'python-twisted'), 
	'0.9.1-3', 
	'Python Twisted', 
        'It includes a web server, a telnet server, a multiplayer RPG engine, 
	a generic client and server for remote object access, and APIs for 
	creating new protocols.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3); -- highest priority

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))
	and version = '0.9.1-4'),
	(SELECT id from Binarypackagename WHERE name = 'bugzilla'), 
	'0.9.1-4', 
	'Bugzilla',
        'Bugzilla is a "Defect Tracking System" or "Bug-Tracking System". 
	Defect Tracking Systems allow individual or groups of developers 
	to keep track of outstanding bugs in their product effectively.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))
	and version = '0.9.1-5'),
	(SELECT id from Binarypackagename WHERE name = 'arch'), 
	'0.9.1-5', 
	'ARCH',
        'arch is a revision control system with features that are ideal for 
	projects characterised by widely distributed development, concurrent 
	support of multiple releases, and substantial amounts of development
	on branches. It can be a replacement for CVS and corrects many 
	mis-features of that system.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))
	and version = '0.9.1-6'),
	(SELECT id from Binarypackagename WHERE name = 'kiwi'), 
	'0.9.1-6', 'Python Kiwi',
        ' Kiwi2 consists of a set of classes and wrappers for PyGTK-2 that were 
	developed to provide a sort of framework for applications. Fully object-oriented, 
	and roughly modeled after Smalltalk\'s MVC, Kiwi provides a simple, practical 
	way to build forms, windows and widgets that transparently access and display
	your object data. Kiwi was primarily designed to make implementing the UI for
	 Stoq easier, and it is released under the LGPL',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

INSERT INTO Binarypackage (sourcepackagerelease, binarypackagename, 
version, shortdesc, description, build, binpackageformat, component, 
section, priority, licence) 
	VALUES (
	(SELECT id from Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))
	and version = '0.9.1-7'),
	(SELECT id from Binarypackagename WHERE name = 'plone'), 
	'0.9.1-7', 'Plone', 
        'Plone is powerful and flexible. It is ideal as an intranet and extranet 
	server, as a document publishing system, a portal server and as a groupware
	 tool for collaboration between separately located entities.',
	1, -- hardcoded ?? use query instead
	1, -- DEB ?
	1, -- default component
	1, -- default section
	3, -- highest priority
	'GPL');

-- Packagepublishing

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox' and version = '0.9.1-1')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox' and version = '0.9.0-9')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox' and version = '0.9.0-8')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox' and version = '0.9.0-7')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'mozilla-firefox' and version = '0.9.0-6')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 
	     'mozilla-thunderbird')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'python-twisted')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
	   'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???

INSERT INTO Packagepublishing (binarypackage, distroarchrelease, component, 
	section, priority) 
	VALUES
	((SELECT id FROM Binarypackage where binarypackagename = 
	  (SELECT id FROM Binarypackagename where name = 'kiwi')
	),
	(SELECT id FROM Distroarchrelease WHERE architecturetag = 
           'warty--x86--devel--0'),
	1, -- default_component
	1, -- default_section
	3); -- ???


--SourcePackageUpload


INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'plone'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	 and version='0.9.0-6'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-7'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-8'),
	6);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox')) 
	and version='0.9.0-9'),
	4);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'mozilla-firefox'))
	 and version='0.9.1-1'),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name='mozilla-thunderbird'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'python-twisted'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'kiwi2'))),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'bugzilla'))),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE sourcepackage = 
	(SELECT id from Sourcepackage where sourcepackagename = 
	(SELECT id FROM Sourcepackagename WHERE name = 'arch'))),
	1);

UPDATE SourcePackage SET distro = 3 WHERE id < 4;

UPDATE SourcePackage SET distro = 1 WHERE id >= 4;
