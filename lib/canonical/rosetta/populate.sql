/* Script to populate soyuz with some dummy rosetta data.
 *
 *
 * Expected use of this script is something like:
 *    psql --file launchpad.sql launchpad && psql --file default.sql launchpad
 *    && psql --file languages.sql && psql --file populate.sql launchpad
 * (where launchpad.sql, default.sql and languages.sql are scripts located
 * at launchpad/database)
 *
 * This file is updated with the v0.99-dev version of the scheme
 *
 */


/* XXX the following is sample data for Soy.  Replace with sample data
   for rosetta. */

/* Create a dummy person */
INSERT INTO Person (presentationname)
VALUES ('Joe Example');

/* Create a product */
INSERT INTO Product (project, owner, name, title, description, datecreated)
VALUES ((SELECT id FROM Project WHERE name = 'mozilla'),
        (SELECT id FROM Person WHERE presentationname = 'Joe Example'),
        'gecko', 'Gecko HTML Layout Engine',
	'The Gecko HTML Layout Engine', now());
        
INSERT INTO Product (project, owner, name, title, description, datecreated)
VALUES ((SELECT id FROM Project WHERE name = 'gnome'),
        (SELECT id FROM Person WHERE presentationname = 'Joe Example'),
        'evolution', 'Evolution',
	'The Evolution groupware client', now());
        
/* Create an upstream release */
INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES ((SELECT id FROM Product WHERE name = 'firefox'),
        timestamp '2004-06-28 00:00',
        '0.9.1',
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'));

INSERT INTO ProductRelease (product, datereleased, version, owner)
VALUES ((SELECT id FROM Product WHERE name = 'evolution'),
        timestamp '2004-07-5 14:46',
        '1.5.90',
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'));

/* Create a source package */
INSERT INTO Sourcepackage (maintainer, name, title, description)
VALUES ((SELECT id FROM Person WHERE presentationname = 'Joe Example'),
        'evolution', 'Ubuntu Evolution Source Package', 
        'text');

/* Create a manifest */
-- FIXME: This needs to be connected to the release somehow.
INSERT INTO Manifest (datecreated, owner)
VALUES (timestamp '2004-06-29 00:00',
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'));

/* Create an arch archive */
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('mozilla', 'Mozilla', 'text', false);
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('gnome', 'GNOME', 'The GNOME Project', false);

INSERT INTO ArchNamespace (archarchive, category, branch, version, visible)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'gnome'),
	'gnome',
	'evolution',
	'1.5.90',
	false);

INSERT INTO Branch (archnamespace, title, description)
VALUES ((SELECT id FROM ArchNamespace
	WHERE category = 'gnome' AND
	      branch = 'evolution' AND
	      version = '1.5.90'),
	'Evolution 1.5.90', 'text');

INSERT INTO License (legalese) VALUES ('GPL-2');

/* Rosetta data */

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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'));

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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'),
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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'),
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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'),
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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'),
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
	(SELECT id FROM Person WHERE presentationname = 'Joe Example'),
	0);

/* arch-tag: a6661b62-7351-4868-8a92-ceb5883f0c92 */
