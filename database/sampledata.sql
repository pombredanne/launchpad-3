/*
   LAUNCHPAD SAMPLE DATA
   
   This is some sample data for the launchpad system.  This requires the default
   data to be inserted first.
*/

/* 
 Sample data for Soyuz
*/

-- Schema
INSERT INTO schema (name, title, description, owner, extensible) VALUES('Mark schema', 'TITLE', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('schema', 'SCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('trema', 'XCHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);
INSERT INTO Schema (name, title, description, owner, extensible) values('enema', 'ENHEMA', 'description', (Select id from Person where presentationname = 'Mark Shuttleworth'), true);

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
INSERT INTO Binarypackage (name, title, description) values ('mozilla-firefox', 'Mozilla Firefox', 'some text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-thunderbird', 'Mozilla Thunderbird', 'text');
INSERT INTO Binarypackage (name, title, description) values ('mozilla-browser', 'Mozilla Browser', 'text and so');
INSERT INTO Binarypackage (name, title, description) values ('emacs21', 'Emacs21 Programming Editor', 'fofofof');
INSERT INTO Binarypackage (name, title, description) values ('bash-1.8', 'Bash', 'another data');

 
 -- ProcessorFamily
INSERT INTO ProcessorFamily (name, title, description, owner) 
VALUES ('x86', 'Intel 386 compatible chips', 'Bring back the 8086!', 
         (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Processor
INSERT INTO Processor (family, name, title, description, owner)
VALUES ((SELECT id FROM ProcessorFamily WHERE name = 'x86'),
         '386', 'Intel 386', 'Intel 386 and its many derivatives and clones, the basic 32-bit chip in the x86 family',
        (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- BinarypackageBuild
INSERT INTO BinarypackageBuild (sourcepackagerelease, binarypackage, processor,
                                 binpackageformat, version, datebuilt)
VALUES ((SELECT id FROM SourcepackageRelease WHERE version = '0.9.1-1'),
         (SELECT id FROM Binarypackage WHERE name = 'mozilla-firefox'),
 	(SELECT id FROM Processor WHERE name = '386'),
 	1, -- DEB
 	'0.9.1-1',
        timestamp '2004-06-29 00:00');
 
 -- DistroArchRelease
INSERT INTO DistroArchRelease (distrorelease, processorfamily, architecturetag, owner)
VALUES ((SELECT id FROM DistroRelease WHERE name = 'warty'),
         (SELECT id FROM ProcessorFamily WHERE name = 'x86'),
	'Foo',
 	(SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Schema
INSERT INTO Schema (name, title, description, owner)
VALUES ('blah', 'blah', 'blah',
         (SELECT id FROM Person WHERE presentationname = 'Mark Shuttleworth'));
 
 -- Label
INSERT INTO Label (schema, name, title, description)
VALUES ((SELECT id FROM Schema WHERE name = 'blah'),
         'blah', 'blah', 'blah');
 
-- BinarypackageUpload
INSERT INTO BinarypackageUpload (binarypackagebuild, distroarchrelease, uploadstatus, component, section, priority) 
VALUES ((SELECT id FROM BinarypackageBuild WHERE version = '0.9.1-1'),
 	(SELECT id FROM DistroArchRelease WHERE architecturetag = 'Foo'),
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


INSERT INTO License (legalese) VALUES ('GPL-2');

INSERT INTO POTemplate (product, branch, priority, name, title,
			description, copyright, license, datecreated,
			path, iscurrent, messagecount, owner)
VALUES ((SELECT id FROM Product WHERE name = 'evolution'),
        (SELECT id FROM Branch
	WHERE title = 'Evolution 1.5.90'),
	2, 'evolution-1.5.90',
	'Main POT file for the Evolution 2.0 development branch',
	'I suppose we should create a long description here....',
	'Copyright (C) 2003  Ximian Inc.',
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-07-13 00:00',
	'po/', TRUE, 3, 	
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'));

INSERT INTO POFile (potemplate, language, topcomment, header, fuzzyheader,
		    lasttranslator, currentcount, updatescount, rosettacount,
		    pluralforms)
VALUES ((SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
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
        'POT-Creation-Date: 2004-07-02 14:48-0400\n'
        'PO-Revision-Date: 2004-07-07 20:52+0200\n'
        'Last-Translator: Francisco Javier F. Serrador <serrador@cvs.gnome.org>\n'
        'Language-Team: Spanish <traductores@es.gnome.org>\n'
        'MIME-Version: 1.0\n'
        'Content-Type: text/plain; charset=UTF-8\n'
        'Content-Transfer-Encoding: 8bit\n'
        'Report-Msgid-Bugs-To: serrador@hispalinux.es\n'
        'X-Generator: KBabel 1.3.1\n'
        'Plural-Forms:  nplurals=2; plural=(n != 1);\n',
	FALSE,
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'),
	2, 0, 1, 2);

INSERT INTO POMsgID (msgid)
VALUES ('evolution addressbook %s');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment, flagscomment)
VALUES ((SELECT id FROM POMsgID WHERE msgid = 'evolution addressbook %s'),
	1, (SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	TRUE, FALSE, FALSE,
	'a11y/addressbook/ea-addressbook-view.c:94\n'
	'a11y/addressbook/ea-addressbook-view.c:103\n'
	'a11y/addressbook/ea-minicard-view.c:119',
	' This is an example comment generated from source code',
	'c-source');

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'evolution addressbook %s') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile IS NULL),
	(SELECT id FROM POMsgID WHERE msgid = 'evolution addressbook %s'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POTranslation (translation)
VALUES ('libreta de direcciones de Evolution %s');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete,
		      obsolete, fuzzy) 
VALUES ((SELECT id FROM POMsgID WHERE msgid = 'evolution addressbook %s'),
	1,
	(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	(SELECT id FROM POFile WHERE potemplate =
		(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90') AND
		language = (SELECT id FROM Language WHERE code = 'cy')),
	TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'evolution addressbook %s') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POMsgID WHERE msgid = 'evolution addressbook %s'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'evolution addressbook %s') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POTranslation
	 WHERE translation = 'libreta de direcciones de Evolution %s'),
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0,
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POMsgID (msgid)
VALUES ('current addressbook folder');

INSERT INTO POMsgSet (primemsgid, sequence,  potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES ((SELECT id FROM POMsgID WHERE msgid = 'current addressbook folder'),
	2, (SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	TRUE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:101',
	' This is an example comment generated from source code');

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'current addressbook folder') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile IS NULL),
	(SELECT id FROM POMsgID WHERE msgid = 'current addressbook folder'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POTranslation (translation)
VALUES ('carpeta de libretas de direcciones actual');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES ((SELECT id FROM POMsgID WHERE msgid = 'current addressbook folder'),
	2,
	(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	(SELECT id FROM POFile WHERE potemplate =
		(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90') AND
		language = (SELECT id FROM Language WHERE code = 'cy')),
	TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'current addressbook folder') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POMsgID WHERE msgid = 'current addressbook folder'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = 'current addressbook folder') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POTranslation
	 WHERE translation = 'carpeta de libretas de direcciones actual'),
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-07-12 00:00',
	timestamp '2004-07-14 00:00',
	TRUE,
	0,
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'),
	0);


INSERT INTO POComment (potemplate, pomsgid, commenttext, datecreated)
VALUES ((SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
        (SELECT id FROM POMsgID WHERE msgid = 'current addressbook folder'),
        ' This comment comes from Rosetta',
	now());

/* An example for plural forms */

/*
 * #: addressbook/gui/widgets/e-addressbook-model.c:151
 * #, c-format
 * msgid "%d contact"
 * msgid_plural "%d contacts"
 * msgstr[0] "%d contacto"
 * msgstr[1] "%d contactos"
 */
INSERT INTO POMsgID (msgid)
VALUES ('%d contact');
INSERT INTO POMsgID (msgid)
VALUES ('%d contacts');

INSERT INTO POMsgSet (primemsgid, sequence,  potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, flagscomment)
VALUES ((SELECT id FROM POMsgID WHERE msgid = '%d contact'),
	3, (SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	TRUE, FALSE, FALSE,
	'addressbook/gui/widgets/e-addressbook-model.c:151',
	'c-format');

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile IS NULL),
	(SELECT id FROM POMsgID WHERE msgid = '%d contact'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile IS NULL),
	(SELECT id FROM POMsgID WHERE msgid = '%d contacts'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	1);

INSERT INTO POTranslation (translation)
VALUES ('%d contacto');

INSERT INTO POTranslation (translation)
VALUES ('%d contactos');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES ((SELECT id FROM POMsgID WHERE msgid = '%d contact'),
	3,
	(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90'),
	(SELECT id FROM POFile WHERE potemplate =
		(SELECT id FROM POTemplate WHERE name = 'evolution-1.5.90') AND
		language = (SELECT id FROM Language WHERE code = 'cy')),
	TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POMsgID WHERE msgid = '%d contact'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	0);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, firstseen,
			      lastseen, inpofile, pluralform)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      potemplate = (SELECT id FROM POTemplate WHERE
	      			name = 'evolution-1.5.90') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POMsgID WHERE msgid = '%d contacts'),
	timestamp '2004-07-13 00:00',
	timestamp '2004-07-13 00:00',
	TRUE,
	1);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POTranslation
	 WHERE translation = '%d contacto'),
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-07-12 00:00',
	timestamp '2004-07-14 00:00',
	TRUE,
	0,
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, firstseen, lasttouched, 
				   inpofile, pluralform, person, origin)
VALUES ((SELECT id FROM POMsgSet
	WHERE primemsgid = (SELECT id FROM POMsgID WHERE
				msgid = '%d contact') AND
	      pofile = (SELECT id FROM POFile WHERE
	      			potemplate = (SELECT id FROM POTemplate
						WHERE name = 'evolution-1.5.90') AND
				language = (SELECT language FROM Language
		                           WHERE code = 'cy'))),
	(SELECT id FROM POTranslation
	 WHERE translation = '%d contactos'),
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-07-12 00:00',
	timestamp '2004-07-14 00:00',
	TRUE,
	1,
	(SELECT id FROM Person WHERE presentationname = 'Carlos Perelló Marín'),
	0);



