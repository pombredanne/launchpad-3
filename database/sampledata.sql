/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.  This requires the default
   data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/
 

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('schema', 'SCHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('trema', 'XCHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('enema', 'ENHEMA', 'description', (Select id from Person where displayname = 'Mark Shuttleworth'), true);


 -- Label
INSERT INTO Label (schema, name, title, description)
VALUES ((SELECT id FROM Schema WHERE name = 'Mark schema'),
         'blah', 'blah', 'blah');


-- Distribution
INSERT INTO Distribution (name, title, description, domainname, owner) values ('ubuntu', 'Ubuntu Distribution', 'text ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('redhat', 'Redhat Advanced Server', 'some text', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('debian', 'Debian Crazy-Unstable', 'text ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('gentoo', 'The Gentoo bits', 'another ...', 'domain', 1);
INSERT INTO Distribution (name, title, description, domainname, owner) values ('porkypigpolka', 'Porky Pig Polka Swine-oriented Distribution', 'blabla', 'domain', 1);

INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('warty', 'Warty', 'text ...', 1, 'PONG', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('6.0', 'Six Six Six', 'some text', 2, '12321.XX', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('hoary', 'Hoary Crazy-Unstable', 'text ...', 1, 'EWEpp##', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('7.0', 'Seven', 'another ...', 2, 'ACK ACK', 1, 1, 0, 1);
INSERT INTO Distrorelease (name, title, description, distribution, version, components, sections, releasestate, owner) values ('grumpy', 'G-R-U-M-P-Y', 'blabla', 1, 'PINKPY POLLY', 1, 1, 0, 1);


-- Binarypackage
INSERT INTO Binarypackage (name, title, description) values ('mozilla-firefox-0.8', 'Mozilla Firefox 0.8', 'some text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-thunderbird-1.5', 'Mozilla Thunderbird 1.5', 'text');
INSERT INTO Binarypackage (name, title, description) values ('python-twisted-1.3', 'Python-Twisted 1.3', 'text and so');
INSERT INTO Binarypackage (name, title, description) values ('bugzilla-2.18', 'Bugzilla 2.18r','bugs ??? where ??');
INSERT INTO Binarypackage (name, title, description) values ('arch-1.0', 'Arch 1.0', 'another data');
INSERT INTO Binarypackage (name, title, description) values ('kiwi-2.0', 'Kiwi 2.0', 'pygtk2 ...');
INSERT INTO Binarypackage (name, title, description) values ('plone-1.0', 'Plone 1.0', 'plone ??? zope ??');
 
 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
 
 -- BinarypackageBuild
INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-1'),
         (SELECT id FROM Binarypackage WHERE name = 'mozilla-firefox'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-1',
        timestamp '2004-06-28 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-2'),
         (SELECT id FROM Binarypackage WHERE name = 'mozilla-thunderbird-1.5'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-2',
        timestamp '2004-07-29 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-3'),
         (SELECT id FROM Binarypackage WHERE name = 'python-twisted-1.3'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-3',
        timestamp '2004-05-29 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-4'),
         (SELECT id FROM Binarypackage WHERE name = 'bugzilla-2.18'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-4',
        timestamp '2004-05-29 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-5'),
         (SELECT id FROM Binarypackage WHERE name = 'arch-1.0'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-5',
        timestamp '2004-06-29 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-6'),
         (SELECT id FROM Binarypackage WHERE name = 'kiwi-2.0'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-6',
        timestamp '2004-03-29 00:00');

INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-7'),
         (SELECT id FROM Binarypackage WHERE name = 'plone-1.0'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-7',
        timestamp '2004-06-23 00:00');


 -- DistroArchRelease
INSERT INTO DistroArchRelease (distrorelease, processorfamily, architecturetag, owner)
VALUES ((SELECT id FROM DistroRelease WHERE name = 'warty'),
         (SELECT id FROM ProcessorFamily WHERE name = 'x86'),
	'warty--x86--devel--0',
 	(SELECT id FROM Person WHERE displayname = 'Mark Shuttleworth'));
  

-- BinarypackageUpload

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-1'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-2'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-3'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-4'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-5'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-6'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);

INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-7'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'warty--x86--devel--0'),
 	4, -- Published
 	1, -- FIXME
 	1, -- FIXME
 	3 -- Standard
 	);
 
--SourcePackageUpload


INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'plone')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'kiwi2')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-firefox')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'warty'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'mozilla-thunderbird')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'python-twisted')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	 sourcepackage = (SELECT id from Sourcepackage where name = 'kiwi2')),
	1);
INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'hoary'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'bugzilla')),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'bugzilla')),
	1);

INSERT INTO Sourcepackageupload (distrorelease, sourcepackagerelease, 
				uploadstatus) 
VALUES ((SELECT id FROM Distrorelease WHERE name = 'grumpy'),
        (SELECT id FROM Sourcepackagerelease WHERE 
	sourcepackage = (SELECT id from Sourcepackage where name = 'arch')),
	1);

/*
 * Sample data for Rosetta
 */

INSERT INTO Person ( displayname, givenname, familyname ) VALUES ( 'Carlos Perelló Marín', 'Carlos', 'Perelló Marín' );
INSERT INTO Project ( owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Person WHERE displayname='Carlos Perelló Marín'),
	'gnome', 'GNOME', 'The GNOME Project', 'foo', 'bar', 'http://www.gnome.org/' );
INSERT INTO Product ( project, owner, name, displayname, title, shortdesc, description, homepageurl )
VALUES ((SELECT id FROM Project WHERE name='gnome'),
	(SELECT id FROM Person WHERE displayname='Carlos Perelló Marín'),
	'evolution', 'Evolution', 'The Evolution Groupware', 'foo', 'bar', 'http://www.novell.com/' );
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('gnome', 'GNOME', 'The GNOME Project', false);
INSERT INTO ArchNamespace (archarchive, category, branch, version, visible)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'gnome'), 'gnome', 'evolution',
	'2.0', false);
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchNamespace
	 WHERE category = 'gnome' AND
	       branch = 'evolution' AND
	       version = '2.0'),
	'Evolution 2.0', 'text',
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'));


INSERT INTO License (legalese) VALUES ('GPL-2');

/* Sample POTemplate file */

INSERT INTO POTemplate (product, branch, priority, name, title,
			description, copyright, license, datecreated,
			path, iscurrent, messagecount, owner)
VALUES ((SELECT id FROM Product WHERE name = 'evolution'),
        (SELECT id FROM Branch
	WHERE title = 'Evolution 2.0'),
	2, 'evolution-2.0',
	'Main POT file for the Evolution 2.0 development branch',
	'I suppose we should create a long description here....',
	'Copyright (C) 2003  Ximian Inc.',
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-08-17 09:10',
	'po/', TRUE, 3, 	
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'));

--  1
INSERT INTO POMsgID (msgid) VALUES ('evolution addressbook');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (1, 1, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-addressbook-view.c:94\n'
	'a11y/addressbook/ea-addressbook-view.c:103\n'
	'a11y/addressbook/ea-minicard-view.c:119');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (1, 1, now(), now(), TRUE, 0);
--  2
INSERT INTO POMsgID (msgid) VALUES ('current addressbook folder');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (2, 2, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:101');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (2, 2, now(), now(), TRUE, 0);
--  3
INSERT INTO POMsgID (msgid) VALUES ('have ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (3, 3, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:102');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (3, 3, now(), now(), TRUE, 0);
--  4
INSERT INTO POMsgID (msgid) VALUES ('has ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (4, 4, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:102');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (4, 4, now(), now(), TRUE, 0);
--  5
INSERT INTO POMsgID (msgid) VALUES (' cards');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (5, 5, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:104');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (5, 5, now(), now(), TRUE, 0);
--  6
INSERT INTO POMsgID (msgid) VALUES (' card');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (6, 6, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:104');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (6, 6, now(), now(), TRUE, 0);
--  7
INSERT INTO POMsgID (msgid) VALUES ('contact\'s header: ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (7, 7, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:105');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (7, 7, now(), now(), TRUE, 0);
--  8
INSERT INTO POMsgID (msgid) VALUES ('evolution minicard');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (8, 8, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard.c:166');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (8, 8, now(), now(), TRUE, 0);
--  9
INSERT INTO POMsgID (msgid) VALUES ('This addressbook could not be opened.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (9, 9, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:2',
	'addressbook:ldap-init primary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (9, 9, now(), now(), TRUE, 0);
-- 10
INSERT INTO POMsgID (msgid) VALUES ('This addressbook server might unreachable or the server name may be misspelled or your network connection could be down.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (10, 10, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:4',
	'addressbook:ldap-init secondary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (10, 10, now(), now(), TRUE, 0);
-- 11
INSERT INTO POMsgID (msgid) VALUES ('Failed to authenticate with LDAP server.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (11, 11, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:6',
	'addressbook:ldap-auth primary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (11, 11, now(), now(), TRUE, 0);
-- 12
INSERT INTO POMsgID (msgid) VALUES ('Check to make sure your password is spelled correctly and that you are using a supported login method. Remember that many passwords are case sensitive; your caps lock might be on.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (12, 12, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:8',
	'addressbook:ldap-auth secondary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (12, 12, now(), now(), TRUE, 0);
-- 13
INSERT INTO POMsgID (msgid) VALUES ('This addressbook server does not have any suggested search bases.');
-- 14
INSERT INTO POMsgID (msgid) VALUES ('This LDAP server may use an older version of LDAP, which does not support this functionality or it may be misconfigured. Ask your administrator for supported search bases.');
-- 15
INSERT INTO POMsgID (msgid) VALUES ('This server does not support LDAPv3 schema information.');
-- 16
INSERT INTO POMsgID (msgid) VALUES ('Could not get schema information for LDAP server.');
-- 17
INSERT INTO POMsgID (msgid) VALUES ('LDAP server did not respond with valid schema information.');
-- 18
INSERT INTO POMsgID (msgid) VALUES ('Could not remove addressbook.');
-- 19
INSERT INTO POMsgID (msgid) VALUES ('{0}');
-- 20
INSERT INTO POMsgID (msgid) VALUES ('Category editor not available.');
-- 21
INSERT INTO POMsgID (msgid) VALUES ('{1}');
-- 22
INSERT INTO POMsgID (msgid) VALUES ('Unable to open addressbook');
-- 23
INSERT INTO POMsgID (msgid) VALUES ('Error loading addressbook.');
-- 24
INSERT INTO POMsgID (msgid) VALUES ('Unable to perform search.');
-- 25
INSERT INTO POMsgID (msgid) VALUES ('Would you like to save your changes?');
-- 26
INSERT INTO POMsgID (msgid) VALUES ('You have made modifications to this contact. Do you want to save these changes?');
-- 27
INSERT INTO POMsgID (msgid) VALUES ('_Discard');
-- 28
INSERT INTO POMsgID (msgid) VALUES ('Cannot move contact.');
-- 29
INSERT INTO POMsgID (msgid) VALUES ('You are attempting to move a contact from one addressbook to another but it cannot be removed from the source. Do you want to save a copy instead?');
-- 30
INSERT INTO POMsgID (msgid) VALUES ('Unable to save contact(s).');
-- 31
INSERT INTO POMsgID (msgid) VALUES ('Error saving contacts to {0}: {1}');
-- 32
INSERT INTO POMsgID (msgid) VALUES ('The Evolution addressbook has quit unexpectedly.');
-- 33
INSERT INTO POMsgID (msgid) VALUES ('Your contacts for {0} will not be available until Evolution is restarted.');
-- 34
INSERT INTO POMsgID (msgid) VALUES ('Default Sync Address:');
-- 35
INSERT INTO POMsgID (msgid) VALUES ('Could not load addressbook');
-- 36
INSERT INTO POMsgID (msgid) VALUES ('Could not read pilot\'s Address application block');
-- 37
INSERT INTO POMsgID (msgid) VALUES ('*Control*F2');
-- 38
INSERT INTO POMsgID (msgid) VALUES ('Autocompletion');
-- 39
INSERT INTO POMsgID (msgid) VALUES ('C_ontacts');
-- 40
INSERT INTO POMsgID (msgid) VALUES ('Certificates');
-- 41
INSERT INTO POMsgID (msgid) VALUES ('Configure autocomplete here');
-- 42
INSERT INTO POMsgID (msgid) VALUES ('Contacts');
-- 43
INSERT INTO POMsgID (msgid) VALUES ('Evolution Addressbook');
-- 44
INSERT INTO POMsgID (msgid) VALUES ('Evolution Addressbook address pop-up');
-- 45
INSERT INTO POMsgID (msgid) VALUES ('Evolution Addressbook address viewer');
-- 46
INSERT INTO POMsgID (msgid) VALUES ('Evolution Addressbook card viewer');
-- 47
INSERT INTO POMsgID (msgid) VALUES ('Evolution Addressbook component');
-- 48
INSERT INTO POMsgID (msgid) VALUES ('Evolution S/Mime Certificate Management Control');
-- 49
INSERT INTO POMsgID (msgid) VALUES ('Evolution folder settings configuration control');
-- 50
INSERT INTO POMsgID (msgid) VALUES ('Manage your S/MIME certificates here');
-- 51
INSERT INTO POMsgID (msgid) VALUES ('New Contact');
-- 52
INSERT INTO POMsgID (msgid) VALUES ('_Contact');
-- 53
INSERT INTO POMsgID (msgid) VALUES ('Create a new contact');
-- 54
INSERT INTO POMsgID (msgid) VALUES ('New Contact List');
-- 55
INSERT INTO POMsgID (msgid) VALUES ('Contact _List');
-- 56
INSERT INTO POMsgID (msgid) VALUES ('Create a new contact list');
-- 57
INSERT INTO POMsgID (msgid) VALUES ('New Address Book');
-- 58
INSERT INTO POMsgID (msgid) VALUES ('Address _Book');
-- 59
INSERT INTO POMsgID (msgid) VALUES ('Create a new address book');
-- 60
INSERT INTO POMsgID (msgid) VALUES ('Failed upgrading Addressbook settings or folders.');
-- 61
INSERT INTO POMsgID (msgid) VALUES ('Migrating...');
-- 62
INSERT INTO POMsgID (msgid) VALUES ('Migrating \`%s\':');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, flagscomment)
VALUES (62, 13, 1, FALSE, FALSE, FALSE,
	'addressbook/gui/component/addressbook-migrate.c:124\n'
	'calendar/gui/migration.c:188 mail/em-migrate.c:1201',
	'c-format');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (13, 62, now(), now(), TRUE, 0);
-- 63
INSERT INTO POMsgID (msgid) VALUES ('On This Computer');
-- 64
INSERT INTO POMsgID (msgid) VALUES ('Personal');
-- 65
INSERT INTO POMsgID (msgid) VALUES ('On LDAP Servers');
-- 66
INSERT INTO POMsgID (msgid) VALUES ('LDAP Servers');
-- 67
INSERT INTO POMsgID (msgid) VALUES ('Autocompletion Settings');
-- 68
INSERT INTO POMsgID (msgid) VALUES ('The location and hierarchy of the Evolution contact folders has changed since Evolution 1.x.\n\nPlease be patient while Evolution migrates your folders...');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (68, 14, 1, FALSE, FALSE, FALSE,
	'addressbook/gui/component/addressbook-migrate.c:1123');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (14, 68, now(), now(), TRUE, 0);
-- 69
INSERT INTO POMsgID (msgid) VALUES ('The format of mailing list contacts has changed.\n\nPlease be patient while Evolution migrates your folders...');
-- 70
INSERT INTO POMsgID (msgid) VALUES ('The way Evolution stores some phone numbers has changed.\n\nPlease be patient while Evolution migrates your folders...');
-- 71
INSERT INTO POMsgID (msgid) VALUES ('Evolution\'s Palm Sync changelog and map files have changed.\n\nPlease be patient while Evolution migrates your Pilot Sync data...');
-- 72
INSERT INTO POMsgID (msgid) VALUES ('Address book \'%s\' will be removed. Are you sure you want to continue?');
-- 73
INSERT INTO POMsgID (msgid) VALUES ('Delete');
-- 74
INSERT INTO POMsgID (msgid) VALUES ('Properties...');
-- 75
INSERT INTO POMsgID (msgid) VALUES ('Accessing LDAP Server anonymously');
-- 76
INSERT INTO POMsgID (msgid) VALUES ('Failed to authenticate.\n');
-- 77
INSERT INTO POMsgID (msgid) VALUES ('%sEnter password for %s (user %s)');
-- 78
INSERT INTO POMsgID (msgid) VALUES ('EFolderList xml for the list of completion uris');
-- 79
INSERT INTO POMsgID (msgid) VALUES ('Position of the vertical pane in main view');
-- 80
INSERT INTO POMsgID (msgid) VALUES ('The number of characters that must be typed before evolution will attempt to autocomplete');
-- 81
INSERT INTO POMsgID (msgid) VALUES ('URI for the folder last used in the select names dialog');
-- 82
INSERT INTO POMsgID (msgid) VALUES ('*');
-- 83
INSERT INTO POMsgID (msgid) VALUES ('1');
-- 84
INSERT INTO POMsgID (msgid) VALUES ('3268');
-- 85
INSERT INTO POMsgID (msgid) VALUES ('389');
-- 86
INSERT INTO POMsgID (msgid) VALUES ('5');
-- 87
INSERT INTO POMsgID (msgid) VALUES ('636');
-- 88
INSERT INTO POMsgID (msgid) VALUES ('<b>Authentication</b>');
-- 89
INSERT INTO POMsgID (msgid) VALUES ('<b>Display</b>');
-- 90
INSERT INTO POMsgID (msgid) VALUES ('<b>Downloading</b>');
-- 91
INSERT INTO POMsgID (msgid) VALUES ('<b>Searching</b>');
-- 92
INSERT INTO POMsgID (msgid) VALUES ('<b>Server Information</b>');
/* A plural form: */
-- 93
INSERT INTO POMsgID (msgid) VALUES ('%d contact');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, flagscomment)
VALUES (93, 15, 1, FALSE, FALSE, FALSE,
	'addressbook/gui/widgets/e-addressbook-model.c:151',
	'c-format');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (15, 93, now(), now(), TRUE, 0);
-- 94
INSERT INTO POMsgID (msgid) VALUES ('%d contacts');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			     lastseen, inpofile, pluralform)
VALUES (15, 94, now(), now(), TRUE, 0);
-- 95
INSERT INTO POMsgID (msgid) VALUES ('_Add Group');


INSERT INTO POFile (potemplate, language, topcomment, header, fuzzyheader,
		    lasttranslator, currentcount, updatescount, rosettacount,
		    pluralforms)
VALUES ((SELECT id FROM POTemplate WHERE name = 'evolution-2.0'),
        (SELECT id FROM Language WHERE code = 'cy'),
	' traducción de es.po al Spanish\n'
        ' translation of es.po to Spanish\n'
        ' translation of evolution.HEAD to Spanish\n'
        ' Copyright © 2000-2002 Free Software Foundation, Inc.\n'
        ' This file is distributed under the same license as the evolution package.\n'
        ' Carlos Perelló Marín <carlos@gnome-db.org>, 2000-2001.\n'
        ' Héctor García Álvarez <hector@scouts-es.org>, 2000-2002.\n'
        ' Ismael Olea <Ismael@olea.org>, 2001, (revisiones) 2003.\n'
        ' Eneko Lacunza <enlar@iname.com>, 2001-2002.\n'
        ' Héctor García Álvarez <hector@scouts-es.org>, 2002.\n'
        ' Pablo Gonzalo del Campo <pablodc@bigfoot.com>,2003 (revisión).\n'
        ' Francisco Javier F. Serrador <serrador@cvs.gnome.org>, 2003, 2004.\n'
        '\n'
        '\n',
        'Project-Id-Version: es\n'
        'POT-Creation-Date: 2004-08-17 11:10+0200\n'
        'PO-Revision-Date: 2004-08-15 19:32+0200\n'
        'Last-Translator: Francisco Javier F. Serrador <serrador@cvs.gnome.org>\n'
        'Language-Team: Spanish <traductores@es.gnome.org>\n'
        'MIME-Version: 1.0\n'
        'Content-Type: text/plain; charset=UTF-8\n'
        'Content-Transfer-Encoding: 8bit\n'
        'Report-Msgid-Bugs-To: serrador@hispalinux.es\n'
        'X-Generator: KBabel 1.3.1\n'
        'Plural-Forms:  nplurals=2; plural=(n != 1);\n',
	FALSE,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	2, 0, 1, 2);

INSERT INTO POTranslation (translation)
VALUES ('libreta de direcciones de Evolution');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete,
		      obsolete, fuzzy) 
VALUES (1, 1, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (16, 1, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (16, 1, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslation (translation)
VALUES ('carpeta de libretas de direcciones actual');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (2, 2, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (17, 2, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (17, 2, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);
	
/* An example for a fuzzy string */
INSERT INTO POTranslation (translation)
VALUES ('tiene');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (3, 3, 1, 1, FALSE, FALSE, TRUE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (18, 3, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (18, 3, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

/* An example for plural forms */
INSERT INTO POTranslation (translation)
VALUES ('%d contacto');

INSERT INTO POTranslation (translation)
VALUES ('%d contactos');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (93, 4, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (19, 93, now(), now(), TRUE, 0);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (19, 94, now(), now(), TRUE, 1);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (19, 4, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (19, 5, 1, now(), now(), TRUE, 1,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

/* An example for obsolete string */
INSERT INTO POTranslation (translation)
VALUES ('_Añadir grupo');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (95, 5, 1, 1, TRUE, TRUE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES (20, 95, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES (20, 6, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

