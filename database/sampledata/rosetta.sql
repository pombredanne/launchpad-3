/*
   Rosetta SAMPLE DATA
   
   This is some sample data for Rosetta.  This requires the default
   data to be inserted first.

   arch-tag: 5734820d-754e-4297-bb54-fbe33b88af4c
*/


INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('gnome', 'GNOME', 'The GNOME Project', false);
INSERT INTO ArchArchive (name, title, description, visible)
VALUES ('iso-codes', 'iso-codes', 'The iso-codes', false);
INSERT INTO ArchNamespace (archarchive, category, branch, version, visible)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'gnome'), 'gnome', 'evolution',
	'2.0', false);
INSERT INTO ArchNamespace (archarchive, category, branch, version, visible)
VALUES ((SELECT id FROM ArchArchive WHERE name = 'iso-codes'), 'iso-codes', 'iso-codes',
	'0.35', false);
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchNamespace
	 WHERE category = 'gnome' AND
	       branch = 'evolution' AND
	       version = '2.0'),
	'Evolution 2.0', 'text',
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'));
INSERT INTO Branch (archnamespace, title, description, owner)
VALUES ((SELECT id FROM ArchNamespace
	 WHERE category = 'iso-codes' AND
	       branch = 'iso-codes' AND
	       version = '0.35'),
	'Iso-codes 0.35', 'text',
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

INSERT INTO POTemplate (product, branch, priority, name, title,
			description, copyright, license, datecreated,
			path, iscurrent, messagecount, owner)
VALUES ((SELECT id FROM Product WHERE name = 'iso-codes'),
        (SELECT id FROM Branch
	WHERE title = 'Iso-codes 0.35'),
	2, 'languages',
	'POT file for the iso_639 strings',
	'I suppose we should create a long description here....',
	'Copyright',
	(SELECT id FROM License WHERE legalese = 'GPL-2'),
	timestamp '2004-08-17 09:10',
	'iso_639/', TRUE, 3, 	
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'));


--  1
INSERT INTO POMsgID (msgid) VALUES ('evolution addressbook');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (1, 1, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-addressbook-view.c:94\n'
	'a11y/addressbook/ea-addressbook-view.c:103\n'
	'a11y/addressbook/ea-minicard-view.c:119');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (1, 1, now(), now(), TRUE, 0);
--  2
INSERT INTO POMsgID (msgid) VALUES ('current addressbook folder');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (2, 2, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:101');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (2, 2, now(), now(), TRUE, 0);
--  3
INSERT INTO POMsgID (msgid) VALUES ('have ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (3, 3, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:102');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (3, 3, now(), now(), TRUE, 0);
--  4
INSERT INTO POMsgID (msgid) VALUES ('has ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (4, 4, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:102');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (4, 4, now(), now(), TRUE, 0);
--  5
INSERT INTO POMsgID (msgid) VALUES (' cards');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (5, 5, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:104');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (5, 5, now(), now(), TRUE, 0);
--  6
INSERT INTO POMsgID (msgid) VALUES (' card');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (6, 6, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:104');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (6, 6, now(), now(), TRUE, 0);
--  7
INSERT INTO POMsgID (msgid) VALUES ('contact\'s header: ');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (7, 7, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard-view.c:105');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (7, 7, now(), now(), TRUE, 0);
--  8
INSERT INTO POMsgID (msgid) VALUES ('evolution minicard');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences)
VALUES (8, 8, 1, FALSE, FALSE, FALSE,
	'a11y/addressbook/ea-minicard.c:166');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (8, 8, now(), now(), TRUE, 0);
--  9
INSERT INTO POMsgID (msgid) VALUES ('This addressbook could not be opened.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (9, 9, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:2',
	'addressbook:ldap-init primary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (9, 9, now(), now(), TRUE, 0);
-- 10
INSERT INTO POMsgID (msgid) VALUES ('This addressbook server might unreachable or the server name may be misspelled or your network connection could be down.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (10, 10, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:4',
	'addressbook:ldap-init secondary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (10, 10, now(), now(), TRUE, 0);
-- 11
INSERT INTO POMsgID (msgid) VALUES ('Failed to authenticate with LDAP server.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (11, 11, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:6',
	'addressbook:ldap-auth primary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (11, 11, now(), now(), TRUE, 0);
-- 12
INSERT INTO POMsgID (msgid) VALUES ('Check to make sure your password is spelled correctly and that you are using a supported login method. Remember that many passwords are case sensitive; your caps lock might be on.');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, sourcecomment)
VALUES (12, 12, 1, FALSE, FALSE, FALSE,
	'addressbook/addressbook-errors.xml.h:8',
	'addressbook:ldap-auth secondary');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
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
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
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
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
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
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (15, 93, now(), now(), TRUE, 0);
-- 94
INSERT INTO POMsgID (msgid) VALUES ('%d contacts');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (15, 94, now(), now(), TRUE, 0);
-- 95
INSERT INTO POMsgID (msgid) VALUES ('Opening %d contact will open %d new window as well.\nDo you really want to display this contact?');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, iscomplete, obsolete,
		      fuzzy, filereferences, flagscomment)
VALUES (95, 16, 1, FALSE, FALSE, FALSE,
	'addressbook/gui/widgets/eab-gui-util.c:275',
	'c-format');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (16, 95, now(), now(), TRUE, 0);
-- 96
INSERT INTO POMsgID (msgid) VALUES ('Opening %d contacts will open %d new windows as well.\nDo you really want to display all of these contacts?');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (16, 96, now(), now(), TRUE, 0);
-- 97
INSERT INTO POMsgID (msgid) VALUES ('_Add Group');


INSERT INTO POFile (potemplate, language, topcomment, header, fuzzyheader,
		    lasttranslator, currentcount, updatescount, rosettacount,
		    pluralforms)
VALUES ((SELECT id FROM POTemplate WHERE name = 'evolution-2.0'),
        (SELECT id FROM Language WHERE code = 'es'),
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
        'Plural-Forms: nplurals=2; plural=(n != 1);\n',
	FALSE,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	2, 0, 1, 2);

INSERT INTO POTranslation (translation)
VALUES ('libreta de direcciones de Evolution');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete,
		      obsolete, fuzzy) 
VALUES (1, 1, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (17, 1, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (17, 1, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslation (translation)
VALUES ('carpeta de libretas de direcciones actual');

INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (2, 2, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (18, 2, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (18, 2, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);
	
/* An example for a fuzzy string */
INSERT INTO POTranslation (translation)
VALUES ('tiene');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (3, 3, 1, 1, FALSE, FALSE, TRUE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (19, 3, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (19, 3, 1, now(), now(), TRUE, 0,
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

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (20, 93, now(), now(), TRUE, 0);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (20, 94, now(), now(), TRUE, 1);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (20, 4, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (20, 5, 1, now(), now(), TRUE, 1,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

/* A multiline example */
INSERT INTO POTranslation (translation)
VALUES ('La ubicación y jerarquía de las carpetas de contactos de Evolution ha cambiado desde Evolution 1.x.\n\nTenga paciencia mientras Evolution migra sus carpetas...');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy, commenttext)
VALUES (68, 5, 1, 1, TRUE, FALSE, FALSE,
	' This is an example of commenttext for a multiline msgset');
INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			     datelastseen, inlastrevision, pluralform)
VALUES (21, 68, now(), now(), TRUE, 0);
INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (21, 6, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

/* A plural form + multiline example */
INSERT INTO POTranslation (translation)
VALUES ('Abrir %d contacto abrirá %d ventanas nuevas también.\n¿Quiere realmente mostrar este contacto?');
INSERT INTO POTranslation (translation)
VALUES ('Abrir %d contactos abrirá %d ventanas nuevas también.\n¿Quiere realmente mostrar todos estos contactos?');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy) 
VALUES (95, 6, 1, 1, TRUE, FALSE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (22, 95, now(), now(), TRUE, 0);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (22, 96, now(), now(), TRUE, 1);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (22, 7, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (22, 8, 1, now(), now(), TRUE, 1,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);


/* An example for obsolete string */
INSERT INTO POTranslation (translation)
VALUES ('_Añadir grupo');
INSERT INTO POMsgSet (primemsgid, sequence, potemplate, pofile, iscomplete, obsolete,
		      fuzzy)
VALUES (97, 7, 1, 1, TRUE, TRUE, FALSE);

INSERT INTO POMsgIDSighting (pomsgset, pomsgid, datefirstseen,
			      datelastseen, inlastrevision, pluralform)
VALUES (23, 97, now(), now(), TRUE, 0);

INSERT INTO POTranslationSighting (pomsgset, potranslation, license, datefirstseen, datelastactive, 
				   inlastrevision, pluralform, person, origin)
VALUES (23, 9, 1, now(), now(), TRUE, 0,
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'),
	0);

INSERT INTO Schema (name, title, description, owner)
VALUES ('translation-languages', 'Translation Languages',
	'Languages that a person can translate into',
	(SELECT id FROM Person WHERE displayname = 'Carlos Perelló Marín'));

INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'aa', 'Translates into Afar', 'A person with this label says that knows how to translate into Afar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ab', 'Translates into Abkhazian', 'A person with this label says that knows how to translate into Abkhazian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ace', 'Translates into Achinese', 'A person with this label says that knows how to translate into Achinese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ach', 'Translates into Acoli', 'A person with this label says that knows how to translate into Acoli');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ada', 'Translates into Adangme', 'A person with this label says that knows how to translate into Adangme');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ady', 'Translates into Adyghe; Adygei', 'A person with this label says that knows how to translate into Adyghe; Adygei');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'afa', 'Translates into Afro-Asiatic (Other)', 'A person with this label says that knows how to translate into Afro-Asiatic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'afh', 'Translates into Afrihili', 'A person with this label says that knows how to translate into Afrihili');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'af', 'Translates into Afrikaans', 'A person with this label says that knows how to translate into Afrikaans');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'aka', 'Translates into Akan', 'A person with this label says that knows how to translate into Akan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ak', 'Translates into Akkadian', 'A person with this label says that knows how to translate into Akkadian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sq', 'Translates into Albanian', 'A person with this label says that knows how to translate into Albanian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ale', 'Translates into Aleut', 'A person with this label says that knows how to translate into Aleut');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'alg', 'Translates into Algonquian languages', 'A person with this label says that knows how to translate into Algonquian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'am', 'Translates into Amharic', 'A person with this label says that knows how to translate into Amharic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ang', 'Translates into English, Old (ca.450-1100)', 'A person with this label says that knows how to translate into English, Old (ca.450-1100)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'apa', 'Translates into Apache languages', 'A person with this label says that knows how to translate into Apache languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ar', 'Translates into Arabic', 'A person with this label says that knows how to translate into Arabic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'arc', 'Translates into Aramaic', 'A person with this label says that knows how to translate into Aramaic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'an', 'Translates into Aragonese', 'A person with this label says that knows how to translate into Aragonese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hy', 'Translates into Armenian', 'A person with this label says that knows how to translate into Armenian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'arn', 'Translates into Araucanian', 'A person with this label says that knows how to translate into Araucanian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'arp', 'Translates into Arapaho', 'A person with this label says that knows how to translate into Arapaho');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'art', 'Translates into Artificial (Other)', 'A person with this label says that knows how to translate into Artificial (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'arw', 'Translates into Arawak', 'A person with this label says that knows how to translate into Arawak');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'as', 'Translates into Assamese', 'A person with this label says that knows how to translate into Assamese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ast', 'Translates into Asturian; Bable', 'A person with this label says that knows how to translate into Asturian; Bable');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ath', 'Translates into Athapascan language', 'A person with this label says that knows how to translate into Athapascan language');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'aus', 'Translates into Australian languages', 'A person with this label says that knows how to translate into Australian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'av', 'Translates into Avaric', 'A person with this label says that knows how to translate into Avaric');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ae', 'Translates into Avestan', 'A person with this label says that knows how to translate into Avestan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'awa', 'Translates into Awadhi', 'A person with this label says that knows how to translate into Awadhi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ay', 'Translates into Aymara', 'A person with this label says that knows how to translate into Aymara');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'az', 'Translates into Azerbaijani', 'A person with this label says that knows how to translate into Azerbaijani');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bad', 'Translates into Banda', 'A person with this label says that knows how to translate into Banda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bai', 'Translates into Bamileke languages', 'A person with this label says that knows how to translate into Bamileke languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ba', 'Translates into Bashkir', 'A person with this label says that knows how to translate into Bashkir');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bal', 'Translates into Baluchi', 'A person with this label says that knows how to translate into Baluchi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bm', 'Translates into Bambara', 'A person with this label says that knows how to translate into Bambara');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ban', 'Translates into Balinese', 'A person with this label says that knows how to translate into Balinese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'eu', 'Translates into Basque', 'A person with this label says that knows how to translate into Basque');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bas', 'Translates into Basa', 'A person with this label says that knows how to translate into Basa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bat', 'Translates into Baltic (Other)', 'A person with this label says that knows how to translate into Baltic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bej', 'Translates into Beja', 'A person with this label says that knows how to translate into Beja');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'be', 'Translates into Belarusian', 'A person with this label says that knows how to translate into Belarusian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bem', 'Translates into Bemba', 'A person with this label says that knows how to translate into Bemba');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bn', 'Translates into Bengali', 'A person with this label says that knows how to translate into Bengali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ber', 'Translates into Berber (Other)', 'A person with this label says that knows how to translate into Berber (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bho', 'Translates into Bhojpuri', 'A person with this label says that knows how to translate into Bhojpuri');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bh', 'Translates into Bihari', 'A person with this label says that knows how to translate into Bihari');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bik', 'Translates into Bikol', 'A person with this label says that knows how to translate into Bikol');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bin', 'Translates into Bini', 'A person with this label says that knows how to translate into Bini');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bi', 'Translates into Bislama', 'A person with this label says that knows how to translate into Bislama');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bla', 'Translates into Siksika', 'A person with this label says that knows how to translate into Siksika');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bnt', 'Translates into Bantu (Other)', 'A person with this label says that knows how to translate into Bantu (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bs', 'Translates into Bosnian', 'A person with this label says that knows how to translate into Bosnian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bra', 'Translates into Braj', 'A person with this label says that knows how to translate into Braj');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'br', 'Translates into Breton', 'A person with this label says that knows how to translate into Breton');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'btk', 'Translates into Batak (Indonesia)', 'A person with this label says that knows how to translate into Batak (Indonesia)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bua', 'Translates into Buriat', 'A person with this label says that knows how to translate into Buriat');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bug', 'Translates into Buginese', 'A person with this label says that knows how to translate into Buginese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bg', 'Translates into Bulgarian', 'A person with this label says that knows how to translate into Bulgarian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'my', 'Translates into Burmese', 'A person with this label says that knows how to translate into Burmese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'byn', 'Translates into Blin; Bilin', 'A person with this label says that knows how to translate into Blin; Bilin');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cad', 'Translates into Caddo', 'A person with this label says that knows how to translate into Caddo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cai', 'Translates into Central American Indian (Other)', 'A person with this label says that knows how to translate into Central American Indian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'car', 'Translates into Carib', 'A person with this label says that knows how to translate into Carib');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ca', 'Translates into Catalan', 'A person with this label says that knows how to translate into Catalan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cau', 'Translates into Caucasian (Other)', 'A person with this label says that knows how to translate into Caucasian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ceb', 'Translates into Cebuano', 'A person with this label says that knows how to translate into Cebuano');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cel', 'Translates into Celtic (Other)', 'A person with this label says that knows how to translate into Celtic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ch', 'Translates into Chamorro', 'A person with this label says that knows how to translate into Chamorro');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chb', 'Translates into Chibcha', 'A person with this label says that knows how to translate into Chibcha');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ce', 'Translates into Chechen', 'A person with this label says that knows how to translate into Chechen');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chg', 'Translates into Chagatai', 'A person with this label says that knows how to translate into Chagatai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'zh', 'Translates into Chinese', 'A person with this label says that knows how to translate into Chinese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chk', 'Translates into Chukese', 'A person with this label says that knows how to translate into Chukese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chm', 'Translates into Mari', 'A person with this label says that knows how to translate into Mari');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chn', 'Translates into Chinook jargon', 'A person with this label says that knows how to translate into Chinook jargon');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cho', 'Translates into Choctaw', 'A person with this label says that knows how to translate into Choctaw');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chp', 'Translates into Chipewyan', 'A person with this label says that knows how to translate into Chipewyan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chr', 'Translates into Cherokee', 'A person with this label says that knows how to translate into Cherokee');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chu', 'Translates into Church Slavic', 'A person with this label says that knows how to translate into Church Slavic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cv', 'Translates into Chuvash', 'A person with this label says that knows how to translate into Chuvash');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'chy', 'Translates into Cheyenne', 'A person with this label says that knows how to translate into Cheyenne');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cmc', 'Translates into Chamic languages', 'A person with this label says that knows how to translate into Chamic languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cop', 'Translates into Coptic', 'A person with this label says that knows how to translate into Coptic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kw', 'Translates into Cornish', 'A person with this label says that knows how to translate into Cornish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'co', 'Translates into Corsican', 'A person with this label says that knows how to translate into Corsican');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cpe', 'Translates into English-based (Other)', 'A person with this label says that knows how to translate into English-based (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cpf', 'Translates into French-based (Other)', 'A person with this label says that knows how to translate into French-based (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cpp', 'Translates into Portuguese-based (Other)', 'A person with this label says that knows how to translate into Portuguese-based (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cr', 'Translates into Cree', 'A person with this label says that knows how to translate into Cree');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'crh', 'Translates into Crimean Turkish; Crimean Tatar', 'A person with this label says that knows how to translate into Crimean Turkish; Crimean Tatar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'crp', 'Translates into Creoles and pidgins (Other)', 'A person with this label says that knows how to translate into Creoles and pidgins (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'csb', 'Translates into Kashubian', 'A person with this label says that knows how to translate into Kashubian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cus', 'Translates into Cushitic (Other)', 'A person with this label says that knows how to translate into Cushitic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cs', 'Translates into Czech', 'A person with this label says that knows how to translate into Czech');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dak', 'Translates into Dakota', 'A person with this label says that knows how to translate into Dakota');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'da', 'Translates into Danish', 'A person with this label says that knows how to translate into Danish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dar', 'Translates into Dargwa', 'A person with this label says that knows how to translate into Dargwa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'del', 'Translates into Delaware', 'A person with this label says that knows how to translate into Delaware');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'den', 'Translates into Slave (Athapascan)', 'A person with this label says that knows how to translate into Slave (Athapascan)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dgr', 'Translates into Dogrib', 'A person with this label says that knows how to translate into Dogrib');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'din', 'Translates into Dinka', 'A person with this label says that knows how to translate into Dinka');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dv', 'Translates into Divehi', 'A person with this label says that knows how to translate into Divehi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'doi', 'Translates into Dogri', 'A person with this label says that knows how to translate into Dogri');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dra', 'Translates into Dravidian (Other)', 'A person with this label says that knows how to translate into Dravidian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dsb', 'Translates into Lower Sorbian', 'A person with this label says that knows how to translate into Lower Sorbian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dua', 'Translates into Duala', 'A person with this label says that knows how to translate into Duala');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dum', 'Translates into Dutch, Middle (ca. 1050-1350)', 'A person with this label says that knows how to translate into Dutch, Middle (ca. 1050-1350)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nl', 'Translates into Dutch', 'A person with this label says that knows how to translate into Dutch');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dyu', 'Translates into Dyula', 'A person with this label says that knows how to translate into Dyula');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'dz', 'Translates into Dzongkha', 'A person with this label says that knows how to translate into Dzongkha');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'efi', 'Translates into Efik', 'A person with this label says that knows how to translate into Efik');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'egy', 'Translates into Egyptian (Ancient)', 'A person with this label says that knows how to translate into Egyptian (Ancient)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'eka', 'Translates into Ekajuk', 'A person with this label says that knows how to translate into Ekajuk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'elx', 'Translates into Elamite', 'A person with this label says that knows how to translate into Elamite');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'en', 'Translates into English', 'A person with this label says that knows how to translate into English');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'enm', 'Translates into English, Middle (1100-1500)', 'A person with this label says that knows how to translate into English, Middle (1100-1500)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'eo', 'Translates into Esperanto', 'A person with this label says that knows how to translate into Esperanto');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'et', 'Translates into Estonian', 'A person with this label says that knows how to translate into Estonian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ee', 'Translates into Ewe', 'A person with this label says that knows how to translate into Ewe');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ewo', 'Translates into Ewondo', 'A person with this label says that knows how to translate into Ewondo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fan', 'Translates into Fang', 'A person with this label says that knows how to translate into Fang');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fo', 'Translates into Faroese', 'A person with this label says that knows how to translate into Faroese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fat', 'Translates into Fanti', 'A person with this label says that knows how to translate into Fanti');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fj', 'Translates into Fijian', 'A person with this label says that knows how to translate into Fijian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fi', 'Translates into Finnish', 'A person with this label says that knows how to translate into Finnish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fiu', 'Translates into Finno-Ugrian (Other)', 'A person with this label says that knows how to translate into Finno-Ugrian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fon', 'Translates into Fon', 'A person with this label says that knows how to translate into Fon');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fr', 'Translates into French', 'A person with this label says that knows how to translate into French');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'frm', 'Translates into French, Middle (ca.1400-1600)', 'A person with this label says that knows how to translate into French, Middle (ca.1400-1600)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fro', 'Translates into French, Old (842-ca.1400)', 'A person with this label says that knows how to translate into French, Old (842-ca.1400)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fy', 'Translates into Frisian', 'A person with this label says that knows how to translate into Frisian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ff', 'Translates into Fulah', 'A person with this label says that knows how to translate into Fulah');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fur', 'Translates into Friulian', 'A person with this label says that knows how to translate into Friulian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gaa', 'Translates into Ga', 'A person with this label says that knows how to translate into Ga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gay', 'Translates into Gayo', 'A person with this label says that knows how to translate into Gayo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gba', 'Translates into Gbaya', 'A person with this label says that knows how to translate into Gbaya');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gem', 'Translates into Germanic (Other)', 'A person with this label says that knows how to translate into Germanic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ka', 'Translates into Georgian', 'A person with this label says that knows how to translate into Georgian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'de', 'Translates into German', 'A person with this label says that knows how to translate into German');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gez', 'Translates into Geez', 'A person with this label says that knows how to translate into Geez');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gil', 'Translates into Gilbertese', 'A person with this label says that knows how to translate into Gilbertese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gd', 'Translates into Gaelic; Scottish', 'A person with this label says that knows how to translate into Gaelic; Scottish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ga', 'Translates into Irish', 'A person with this label says that knows how to translate into Irish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gl', 'Translates into Gallegan', 'A person with this label says that knows how to translate into Gallegan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gv', 'Translates into Manx', 'A person with this label says that knows how to translate into Manx');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gmh', 'Translates into German, Middle High (ca.1050-1500)', 'A person with this label says that knows how to translate into German, Middle High (ca.1050-1500)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'goh', 'Translates into German, Old High (ca.750-1050)', 'A person with this label says that knows how to translate into German, Old High (ca.750-1050)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gon', 'Translates into Gondi', 'A person with this label says that knows how to translate into Gondi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gor', 'Translates into Gorontalo', 'A person with this label says that knows how to translate into Gorontalo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'got', 'Translates into Gothic', 'A person with this label says that knows how to translate into Gothic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'grb', 'Translates into Grebo', 'A person with this label says that knows how to translate into Grebo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'grc', 'Translates into Greek, Ancient (to 1453)', 'A person with this label says that knows how to translate into Greek, Ancient (to 1453)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'el', 'Translates into Greek, Modern (1453-)', 'A person with this label says that knows how to translate into Greek, Modern (1453-)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gn', 'Translates into Guarani', 'A person with this label says that knows how to translate into Guarani');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gu', 'Translates into Gujarati', 'A person with this label says that knows how to translate into Gujarati');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'gwi', 'Translates into Gwichin', 'A person with this label says that knows how to translate into Gwichin');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hai', 'Translates into Haida', 'A person with this label says that knows how to translate into Haida');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ht', 'Translates into Haitian; Haitian Creole', 'A person with this label says that knows how to translate into Haitian; Haitian Creole');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ha', 'Translates into Hausa', 'A person with this label says that knows how to translate into Hausa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'haw', 'Translates into Hawaiian', 'A person with this label says that knows how to translate into Hawaiian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'he', 'Translates into Hebrew', 'A person with this label says that knows how to translate into Hebrew');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hz', 'Translates into Herero', 'A person with this label says that knows how to translate into Herero');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hil', 'Translates into Hiligaynon', 'A person with this label says that knows how to translate into Hiligaynon');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'him', 'Translates into Himachali', 'A person with this label says that knows how to translate into Himachali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hi', 'Translates into Hindi', 'A person with this label says that knows how to translate into Hindi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hit', 'Translates into Hittite', 'A person with this label says that knows how to translate into Hittite');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hmn', 'Translates into Hmong', 'A person with this label says that knows how to translate into Hmong');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ho', 'Translates into Hiri', 'A person with this label says that knows how to translate into Hiri');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hsb', 'Translates into Upper Sorbian', 'A person with this label says that knows how to translate into Upper Sorbian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hu', 'Translates into Hungarian', 'A person with this label says that knows how to translate into Hungarian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hup', 'Translates into Hupa', 'A person with this label says that knows how to translate into Hupa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'iba', 'Translates into Iban', 'A person with this label says that knows how to translate into Iban');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ig', 'Translates into Igbo', 'A person with this label says that knows how to translate into Igbo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'is', 'Translates into Icelandic', 'A person with this label says that knows how to translate into Icelandic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'io', 'Translates into Ido', 'A person with this label says that knows how to translate into Ido');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ii', 'Translates into Sichuan Yi', 'A person with this label says that knows how to translate into Sichuan Yi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ijo', 'Translates into Ijo', 'A person with this label says that knows how to translate into Ijo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'iu', 'Translates into Inuktitut', 'A person with this label says that knows how to translate into Inuktitut');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ie', 'Translates into Interlingue', 'A person with this label says that knows how to translate into Interlingue');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ilo', 'Translates into Iloko', 'A person with this label says that knows how to translate into Iloko');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ia', 'Translates into Interlingua', 'A person with this label says that knows how to translate into Interlingua');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'inc', 'Translates into Indic (Other)', 'A person with this label says that knows how to translate into Indic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'id', 'Translates into Indonesian', 'A person with this label says that knows how to translate into Indonesian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ine', 'Translates into Indo-European (Other)', 'A person with this label says that knows how to translate into Indo-European (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'inh', 'Translates into Ingush', 'A person with this label says that knows how to translate into Ingush');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ik', 'Translates into Inupiaq', 'A person with this label says that knows how to translate into Inupiaq');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ira', 'Translates into Iranian (Other)', 'A person with this label says that knows how to translate into Iranian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'iro', 'Translates into Iroquoian languages', 'A person with this label says that knows how to translate into Iroquoian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'it', 'Translates into Italian', 'A person with this label says that knows how to translate into Italian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'jv', 'Translates into Javanese', 'A person with this label says that knows how to translate into Javanese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'jbo', 'Translates into Lojban', 'A person with this label says that knows how to translate into Lojban');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ja', 'Translates into Japanese', 'A person with this label says that knows how to translate into Japanese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'jpr', 'Translates into Judeo-Persian', 'A person with this label says that knows how to translate into Judeo-Persian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'jrb', 'Translates into Judeo-Arabic', 'A person with this label says that knows how to translate into Judeo-Arabic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kaa', 'Translates into Kara-Kalpak', 'A person with this label says that knows how to translate into Kara-Kalpak');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kab', 'Translates into Kabyle', 'A person with this label says that knows how to translate into Kabyle');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kac', 'Translates into Kachin', 'A person with this label says that knows how to translate into Kachin');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kl', 'Translates into Greenlandic (Kalaallisut)', 'A person with this label says that knows how to translate into Greenlandic (Kalaallisut)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kam', 'Translates into Kamba', 'A person with this label says that knows how to translate into Kamba');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kn', 'Translates into Kannada', 'A person with this label says that knows how to translate into Kannada');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kar', 'Translates into Karen', 'A person with this label says that knows how to translate into Karen');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ks', 'Translates into Kashmiri', 'A person with this label says that knows how to translate into Kashmiri');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kr', 'Translates into Kanuri', 'A person with this label says that knows how to translate into Kanuri');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kaw', 'Translates into Kawi', 'A person with this label says that knows how to translate into Kawi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kk', 'Translates into Kazakh', 'A person with this label says that knows how to translate into Kazakh');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kbd', 'Translates into Kabardian', 'A person with this label says that knows how to translate into Kabardian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kha', 'Translates into Khazi', 'A person with this label says that knows how to translate into Khazi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'khi', 'Translates into Khoisan (Other)', 'A person with this label says that knows how to translate into Khoisan (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'km', 'Translates into Khmer', 'A person with this label says that knows how to translate into Khmer');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kho', 'Translates into Khotanese', 'A person with this label says that knows how to translate into Khotanese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ki', 'Translates into Kikuyu', 'A person with this label says that knows how to translate into Kikuyu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rw', 'Translates into Kinyarwanda', 'A person with this label says that knows how to translate into Kinyarwanda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ky', 'Translates into Kirghiz', 'A person with this label says that knows how to translate into Kirghiz');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kmb', 'Translates into Kimbundu', 'A person with this label says that knows how to translate into Kimbundu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kok', 'Translates into Konkani', 'A person with this label says that knows how to translate into Konkani');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kv', 'Translates into Komi', 'A person with this label says that knows how to translate into Komi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kg', 'Translates into Kongo', 'A person with this label says that knows how to translate into Kongo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ko', 'Translates into Korean', 'A person with this label says that knows how to translate into Korean');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kos', 'Translates into Kosraean', 'A person with this label says that knows how to translate into Kosraean');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kpe', 'Translates into Kpelle', 'A person with this label says that knows how to translate into Kpelle');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'krc', 'Translates into Karachay-Balkar', 'A person with this label says that knows how to translate into Karachay-Balkar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kro', 'Translates into Kru', 'A person with this label says that knows how to translate into Kru');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kru', 'Translates into Kurukh', 'A person with this label says that knows how to translate into Kurukh');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kj', 'Translates into Kuanyama', 'A person with this label says that knows how to translate into Kuanyama');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kum', 'Translates into Kumyk', 'A person with this label says that knows how to translate into Kumyk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ku', 'Translates into Kurdish', 'A person with this label says that knows how to translate into Kurdish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'kut', 'Translates into Kutenai', 'A person with this label says that knows how to translate into Kutenai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lad', 'Translates into Ladino', 'A person with this label says that knows how to translate into Ladino');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lah', 'Translates into Lahnda', 'A person with this label says that knows how to translate into Lahnda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lam', 'Translates into Lamba', 'A person with this label says that knows how to translate into Lamba');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lo', 'Translates into Lao', 'A person with this label says that knows how to translate into Lao');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'la', 'Translates into Latin', 'A person with this label says that knows how to translate into Latin');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lv', 'Translates into Latvian', 'A person with this label says that knows how to translate into Latvian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lez', 'Translates into Lezghian', 'A person with this label says that knows how to translate into Lezghian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'li', 'Translates into Limburgian', 'A person with this label says that knows how to translate into Limburgian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ln', 'Translates into Lingala', 'A person with this label says that knows how to translate into Lingala');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lt', 'Translates into Lithuanian', 'A person with this label says that knows how to translate into Lithuanian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lol', 'Translates into Mongo', 'A person with this label says that knows how to translate into Mongo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'loz', 'Translates into Lozi', 'A person with this label says that knows how to translate into Lozi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lb', 'Translates into Luxembourgish', 'A person with this label says that knows how to translate into Luxembourgish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lua', 'Translates into Luba-Lulua', 'A person with this label says that knows how to translate into Luba-Lulua');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lu', 'Translates into Luba-Katanga', 'A person with this label says that knows how to translate into Luba-Katanga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lg', 'Translates into Ganda', 'A person with this label says that knows how to translate into Ganda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lui', 'Translates into Luiseno', 'A person with this label says that knows how to translate into Luiseno');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lun', 'Translates into Lunda', 'A person with this label says that knows how to translate into Lunda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'luo', 'Translates into Luo (Kenya and Tanzania)', 'A person with this label says that knows how to translate into Luo (Kenya and Tanzania)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'lus', 'Translates into Lushai', 'A person with this label says that knows how to translate into Lushai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mk', 'Translates into Macedonian', 'A person with this label says that knows how to translate into Macedonian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mad', 'Translates into Madurese', 'A person with this label says that knows how to translate into Madurese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mag', 'Translates into Magahi', 'A person with this label says that knows how to translate into Magahi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mh', 'Translates into Marshallese', 'A person with this label says that knows how to translate into Marshallese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mai', 'Translates into Maithili', 'A person with this label says that knows how to translate into Maithili');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mak', 'Translates into Makasar', 'A person with this label says that knows how to translate into Makasar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ml', 'Translates into Malayalam', 'A person with this label says that knows how to translate into Malayalam');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'man', 'Translates into Mandingo', 'A person with this label says that knows how to translate into Mandingo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mi', 'Translates into Maori', 'A person with this label says that knows how to translate into Maori');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'map', 'Translates into Austronesian (Other)', 'A person with this label says that knows how to translate into Austronesian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mr', 'Translates into Marathi', 'A person with this label says that knows how to translate into Marathi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mas', 'Translates into Masai', 'A person with this label says that knows how to translate into Masai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ms', 'Translates into Malay', 'A person with this label says that knows how to translate into Malay');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mdf', 'Translates into Moksha', 'A person with this label says that knows how to translate into Moksha');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mdr', 'Translates into Mandar', 'A person with this label says that knows how to translate into Mandar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'men', 'Translates into Mende', 'A person with this label says that knows how to translate into Mende');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mga', 'Translates into Irish, Middle (900-1200)', 'A person with this label says that knows how to translate into Irish, Middle (900-1200)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mic', 'Translates into Micmac', 'A person with this label says that knows how to translate into Micmac');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'min', 'Translates into Minangkabau', 'A person with this label says that knows how to translate into Minangkabau');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mis', 'Translates into Miscellaneous languages', 'A person with this label says that knows how to translate into Miscellaneous languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mkh', 'Translates into Mon-Khmer (Other)', 'A person with this label says that knows how to translate into Mon-Khmer (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mg', 'Translates into Malagasy', 'A person with this label says that knows how to translate into Malagasy');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mt', 'Translates into Maltese', 'A person with this label says that knows how to translate into Maltese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mnc', 'Translates into Manchu', 'A person with this label says that knows how to translate into Manchu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mno', 'Translates into Manobo languages', 'A person with this label says that knows how to translate into Manobo languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'moh', 'Translates into Mohawk', 'A person with this label says that knows how to translate into Mohawk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mo', 'Translates into Moldavian', 'A person with this label says that knows how to translate into Moldavian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mn', 'Translates into Mongolian', 'A person with this label says that knows how to translate into Mongolian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mos', 'Translates into Mossi', 'A person with this label says that knows how to translate into Mossi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mul', 'Translates into Multiple languages', 'A person with this label says that knows how to translate into Multiple languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mun', 'Translates into Munda languages', 'A person with this label says that knows how to translate into Munda languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mus', 'Translates into Creek', 'A person with this label says that knows how to translate into Creek');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'mwr', 'Translates into Marwari', 'A person with this label says that knows how to translate into Marwari');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'myn', 'Translates into Mayan languages', 'A person with this label says that knows how to translate into Mayan languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'myv', 'Translates into Erzya', 'A person with this label says that knows how to translate into Erzya');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nah', 'Translates into Nahuatl', 'A person with this label says that knows how to translate into Nahuatl');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nai', 'Translates into North American Indian (Other)', 'A person with this label says that knows how to translate into North American Indian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nap', 'Translates into Neapolitan', 'A person with this label says that knows how to translate into Neapolitan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'na', 'Translates into Nauru', 'A person with this label says that knows how to translate into Nauru');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nv', 'Translates into Navaho', 'A person with this label says that knows how to translate into Navaho');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nr', 'Translates into Ndebele, South', 'A person with this label says that knows how to translate into Ndebele, South');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nd', 'Translates into Ndebele, North', 'A person with this label says that knows how to translate into Ndebele, North');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ng', 'Translates into Ndonga', 'A person with this label says that knows how to translate into Ndonga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nds', 'Translates into German, Low', 'A person with this label says that knows how to translate into German, Low');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ne', 'Translates into Nepali', 'A person with this label says that knows how to translate into Nepali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'new', 'Translates into Newari', 'A person with this label says that knows how to translate into Newari');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nia', 'Translates into Nias', 'A person with this label says that knows how to translate into Nias');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nic', 'Translates into Niger-Kordofanian (Other)', 'A person with this label says that knows how to translate into Niger-Kordofanian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'niu', 'Translates into Niuean', 'A person with this label says that knows how to translate into Niuean');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nn', 'Translates into Norwegian Nynorsk', 'A person with this label says that knows how to translate into Norwegian Nynorsk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nb', 'Translates into Bokmål, Norwegian', 'A person with this label says that knows how to translate into Bokmål, Norwegian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nog', 'Translates into Nogai', 'A person with this label says that knows how to translate into Nogai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'non', 'Translates into Norse, Old', 'A person with this label says that knows how to translate into Norse, Old');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'no', 'Translates into Norwegian', 'A person with this label says that knows how to translate into Norwegian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nso', 'Translates into Sotho, Northern', 'A person with this label says that knows how to translate into Sotho, Northern');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nub', 'Translates into Nubian languages', 'A person with this label says that knows how to translate into Nubian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nwc', 'Translates into Classical Newari; Old Newari', 'A person with this label says that knows how to translate into Classical Newari; Old Newari');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ny', 'Translates into Chewa; Chichewa; Nyanja', 'A person with this label says that knows how to translate into Chewa; Chichewa; Nyanja');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nym', 'Translates into Nyankole', 'A person with this label says that knows how to translate into Nyankole');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nyo', 'Translates into Nyoro', 'A person with this label says that knows how to translate into Nyoro');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'nzi', 'Translates into Nzima', 'A person with this label says that knows how to translate into Nzima');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'oc', 'Translates into Occitan (post 1500)', 'A person with this label says that knows how to translate into Occitan (post 1500)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'oj', 'Translates into Ojibwa', 'A person with this label says that knows how to translate into Ojibwa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'or', 'Translates into Oriya', 'A person with this label says that knows how to translate into Oriya');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'om', 'Translates into Oromo', 'A person with this label says that knows how to translate into Oromo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'osa', 'Translates into Osage', 'A person with this label says that knows how to translate into Osage');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'os', 'Translates into Ossetian', 'A person with this label says that knows how to translate into Ossetian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ota', 'Translates into Turkish, Ottoman (1500-1928)', 'A person with this label says that knows how to translate into Turkish, Ottoman (1500-1928)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'oto', 'Translates into Otomian languages', 'A person with this label says that knows how to translate into Otomian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'paa', 'Translates into Papuan (Other)', 'A person with this label says that knows how to translate into Papuan (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pag', 'Translates into Pangasinan', 'A person with this label says that knows how to translate into Pangasinan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pal', 'Translates into Pahlavi', 'A person with this label says that knows how to translate into Pahlavi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pam', 'Translates into Pampanga', 'A person with this label says that knows how to translate into Pampanga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pa', 'Translates into Panjabi', 'A person with this label says that knows how to translate into Panjabi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pap', 'Translates into Papiamento', 'A person with this label says that knows how to translate into Papiamento');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pau', 'Translates into Palauan', 'A person with this label says that knows how to translate into Palauan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'peo', 'Translates into Persian, Old (ca.600-400 B.C.)', 'A person with this label says that knows how to translate into Persian, Old (ca.600-400 B.C.)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'fa', 'Translates into Persian', 'A person with this label says that knows how to translate into Persian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'phi', 'Translates into Philippine (Other)', 'A person with this label says that knows how to translate into Philippine (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'phn', 'Translates into Phoenician', 'A person with this label says that knows how to translate into Phoenician');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pi', 'Translates into Pali', 'A person with this label says that knows how to translate into Pali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pl', 'Translates into Polish', 'A person with this label says that knows how to translate into Polish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pt', 'Translates into Portuguese', 'A person with this label says that knows how to translate into Portuguese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pon', 'Translates into Pohnpeian', 'A person with this label says that knows how to translate into Pohnpeian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pra', 'Translates into Prakrit languages', 'A person with this label says that knows how to translate into Prakrit languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'pro', 'Translates into Provençal, Old (to 1500)', 'A person with this label says that knows how to translate into Provençal, Old (to 1500)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ps', 'Translates into Pushto', 'A person with this label says that knows how to translate into Pushto');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'qu', 'Translates into Quechua', 'A person with this label says that knows how to translate into Quechua');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'raj', 'Translates into Rajasthani', 'A person with this label says that knows how to translate into Rajasthani');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rap', 'Translates into Rapanui', 'A person with this label says that knows how to translate into Rapanui');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rar', 'Translates into Rarotongan', 'A person with this label says that knows how to translate into Rarotongan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'roa', 'Translates into Romance (Other)', 'A person with this label says that knows how to translate into Romance (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rm', 'Translates into Raeto-Romance', 'A person with this label says that knows how to translate into Raeto-Romance');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rom', 'Translates into Romany', 'A person with this label says that knows how to translate into Romany');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ro', 'Translates into Romanian', 'A person with this label says that knows how to translate into Romanian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'rn', 'Translates into Rundi', 'A person with this label says that knows how to translate into Rundi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ru', 'Translates into Russian', 'A person with this label says that knows how to translate into Russian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sad', 'Translates into Sandawe', 'A person with this label says that knows how to translate into Sandawe');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sg', 'Translates into Sango', 'A person with this label says that knows how to translate into Sango');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sah', 'Translates into Yakut', 'A person with this label says that knows how to translate into Yakut');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sai', 'Translates into South American Indian (Other)', 'A person with this label says that knows how to translate into South American Indian (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sal', 'Translates into Salishan languages', 'A person with this label says that knows how to translate into Salishan languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sam', 'Translates into Samaritan Aramaic', 'A person with this label says that knows how to translate into Samaritan Aramaic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sa', 'Translates into Sanskrit', 'A person with this label says that knows how to translate into Sanskrit');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sas', 'Translates into Sasak', 'A person with this label says that knows how to translate into Sasak');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sat', 'Translates into Santali', 'A person with this label says that knows how to translate into Santali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sr', 'Translates into Serbian', 'A person with this label says that knows how to translate into Serbian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sco', 'Translates into Scots', 'A person with this label says that knows how to translate into Scots');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'hr', 'Translates into Croatian', 'A person with this label says that knows how to translate into Croatian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sel', 'Translates into Selkup', 'A person with this label says that knows how to translate into Selkup');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sem', 'Translates into Semitic (Other)', 'A person with this label says that knows how to translate into Semitic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sga', 'Translates into Irish, Old (to 900)', 'A person with this label says that knows how to translate into Irish, Old (to 900)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sgn', 'Translates into Sign languages', 'A person with this label says that knows how to translate into Sign languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'shn', 'Translates into Shan', 'A person with this label says that knows how to translate into Shan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sid', 'Translates into Sidamo', 'A person with this label says that knows how to translate into Sidamo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'si', 'Translates into Sinhalese', 'A person with this label says that knows how to translate into Sinhalese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sio', 'Translates into Siouan languages', 'A person with this label says that knows how to translate into Siouan languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sit', 'Translates into Sino-Tibetan (Other)', 'A person with this label says that knows how to translate into Sino-Tibetan (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sla', 'Translates into Slavic (Other)', 'A person with this label says that knows how to translate into Slavic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sk', 'Translates into Slovak', 'A person with this label says that knows how to translate into Slovak');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sl', 'Translates into Slovenian', 'A person with this label says that knows how to translate into Slovenian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sma', 'Translates into Southern Sami', 'A person with this label says that knows how to translate into Southern Sami');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'se', 'Translates into Northern Sami', 'A person with this label says that knows how to translate into Northern Sami');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'smi', 'Translates into Sami languages (Other)', 'A person with this label says that knows how to translate into Sami languages (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'smj', 'Translates into Lule Sami', 'A person with this label says that knows how to translate into Lule Sami');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'smn', 'Translates into Inari Sami', 'A person with this label says that knows how to translate into Inari Sami');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sm', 'Translates into Samoan', 'A person with this label says that knows how to translate into Samoan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sms', 'Translates into Skolt Sami', 'A person with this label says that knows how to translate into Skolt Sami');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sn', 'Translates into Shona', 'A person with this label says that knows how to translate into Shona');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sd', 'Translates into Sindhi', 'A person with this label says that knows how to translate into Sindhi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'snk', 'Translates into Soninke', 'A person with this label says that knows how to translate into Soninke');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sog', 'Translates into Sogdian', 'A person with this label says that knows how to translate into Sogdian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'so', 'Translates into Somali', 'A person with this label says that knows how to translate into Somali');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'son', 'Translates into Songhai', 'A person with this label says that knows how to translate into Songhai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'st', 'Translates into Sotho, Southern', 'A person with this label says that knows how to translate into Sotho, Southern');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'es', 'Translates into Spanish (Castilian)', 'A person with this label says that knows how to translate into Spanish (Castilian)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sc', 'Translates into Sardinian', 'A person with this label says that knows how to translate into Sardinian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'srr', 'Translates into Serer', 'A person with this label says that knows how to translate into Serer');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ssa', 'Translates into Nilo-Saharan (Other)', 'A person with this label says that knows how to translate into Nilo-Saharan (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ss', 'Translates into Swati', 'A person with this label says that knows how to translate into Swati');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'suk', 'Translates into Sukuma', 'A person with this label says that knows how to translate into Sukuma');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'su', 'Translates into Sundanese', 'A person with this label says that knows how to translate into Sundanese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sus', 'Translates into Susu', 'A person with this label says that knows how to translate into Susu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sux', 'Translates into Sumerian', 'A person with this label says that knows how to translate into Sumerian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sw', 'Translates into Swahili', 'A person with this label says that knows how to translate into Swahili');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'sv', 'Translates into Swedish', 'A person with this label says that knows how to translate into Swedish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'syr', 'Translates into Syriac', 'A person with this label says that knows how to translate into Syriac');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ty', 'Translates into Tahitian', 'A person with this label says that knows how to translate into Tahitian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tai', 'Translates into Tai (Other)', 'A person with this label says that knows how to translate into Tai (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ta', 'Translates into Tamil', 'A person with this label says that knows how to translate into Tamil');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ts', 'Translates into Tsonga', 'A person with this label says that knows how to translate into Tsonga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tt', 'Translates into Tatar', 'A person with this label says that knows how to translate into Tatar');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'te', 'Translates into Telugu', 'A person with this label says that knows how to translate into Telugu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tem', 'Translates into Timne', 'A person with this label says that knows how to translate into Timne');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ter', 'Translates into Tereno', 'A person with this label says that knows how to translate into Tereno');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tet', 'Translates into Tetum', 'A person with this label says that knows how to translate into Tetum');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tg', 'Translates into Tajik', 'A person with this label says that knows how to translate into Tajik');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tl', 'Translates into Tagalog', 'A person with this label says that knows how to translate into Tagalog');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'th', 'Translates into Thai', 'A person with this label says that knows how to translate into Thai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'bo', 'Translates into Tibetan', 'A person with this label says that knows how to translate into Tibetan');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tig', 'Translates into Tigre', 'A person with this label says that knows how to translate into Tigre');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ti', 'Translates into Tigrinya', 'A person with this label says that knows how to translate into Tigrinya');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tiv', 'Translates into Tiv', 'A person with this label says that knows how to translate into Tiv');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tlh', 'Translates into Klingon; tlhIngan-Hol', 'A person with this label says that knows how to translate into Klingon; tlhIngan-Hol');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tkl', 'Translates into Tokelau', 'A person with this label says that knows how to translate into Tokelau');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tli', 'Translates into Tlinglit', 'A person with this label says that knows how to translate into Tlinglit');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tmh', 'Translates into Tamashek', 'A person with this label says that knows how to translate into Tamashek');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tog', 'Translates into Tonga (Nyasa)', 'A person with this label says that knows how to translate into Tonga (Nyasa)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'to', 'Translates into Tonga (Tonga Islands)', 'A person with this label says that knows how to translate into Tonga (Tonga Islands)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tpi', 'Translates into Tok Pisin', 'A person with this label says that knows how to translate into Tok Pisin');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tsi', 'Translates into Tsimshian', 'A person with this label says that knows how to translate into Tsimshian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tn', 'Translates into Tswana', 'A person with this label says that knows how to translate into Tswana');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tk', 'Translates into Turkmen', 'A person with this label says that knows how to translate into Turkmen');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tum', 'Translates into Tumbuka', 'A person with this label says that knows how to translate into Tumbuka');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tup', 'Translates into Tupi languages', 'A person with this label says that knows how to translate into Tupi languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tr', 'Translates into Turkish', 'A person with this label says that knows how to translate into Turkish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tut', 'Translates into Altaic (Other)', 'A person with this label says that knows how to translate into Altaic (Other)');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tvl', 'Translates into Tuvalu', 'A person with this label says that knows how to translate into Tuvalu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tw', 'Translates into Twi', 'A person with this label says that knows how to translate into Twi');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'tyv', 'Translates into Tuvinian', 'A person with this label says that knows how to translate into Tuvinian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'udm', 'Translates into Udmurt', 'A person with this label says that knows how to translate into Udmurt');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'uga', 'Translates into Ugaritic', 'A person with this label says that knows how to translate into Ugaritic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ug', 'Translates into Uighur', 'A person with this label says that knows how to translate into Uighur');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'uk', 'Translates into Ukrainian', 'A person with this label says that knows how to translate into Ukrainian');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'umb', 'Translates into Umbundu', 'A person with this label says that knows how to translate into Umbundu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'und', 'Translates into Undetermined', 'A person with this label says that knows how to translate into Undetermined');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'urd', 'Translates into Urdu', 'A person with this label says that knows how to translate into Urdu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'uz', 'Translates into Uzbek', 'A person with this label says that knows how to translate into Uzbek');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'vai', 'Translates into Vai', 'A person with this label says that knows how to translate into Vai');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 've', 'Translates into Venda', 'A person with this label says that knows how to translate into Venda');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'vi', 'Translates into Vietnamese', 'A person with this label says that knows how to translate into Vietnamese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'vo', 'Translates into Volapuk', 'A person with this label says that knows how to translate into Volapuk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'vot', 'Translates into Votic', 'A person with this label says that knows how to translate into Votic');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'wak', 'Translates into Wakashan languages', 'A person with this label says that knows how to translate into Wakashan languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'wal', 'Translates into Walamo', 'A person with this label says that knows how to translate into Walamo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'war', 'Translates into Waray', 'A person with this label says that knows how to translate into Waray');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'was', 'Translates into Washo', 'A person with this label says that knows how to translate into Washo');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'cy', 'Translates into Welsh', 'A person with this label says that knows how to translate into Welsh');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'wen', 'Translates into Sorbian languages', 'A person with this label says that knows how to translate into Sorbian languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'wa', 'Translates into Walloon', 'A person with this label says that knows how to translate into Walloon');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'wo', 'Translates into Wolof', 'A person with this label says that knows how to translate into Wolof');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'xal', 'Translates into Kalmyk', 'A person with this label says that knows how to translate into Kalmyk');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'xh', 'Translates into Xhosa', 'A person with this label says that knows how to translate into Xhosa');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'yao', 'Translates into Yao', 'A person with this label says that knows how to translate into Yao');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'yap', 'Translates into Yapese', 'A person with this label says that knows how to translate into Yapese');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'yi', 'Translates into Yiddish', 'A person with this label says that knows how to translate into Yiddish');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'yo', 'Translates into Yoruba', 'A person with this label says that knows how to translate into Yoruba');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'ypk', 'Translates into Yupik languages', 'A person with this label says that knows how to translate into Yupik languages');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'zap', 'Translates into Zapotec', 'A person with this label says that knows how to translate into Zapotec');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'zen', 'Translates into Zenaga', 'A person with this label says that knows how to translate into Zenaga');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'za', 'Translates into Chuang; Zhuang', 'A person with this label says that knows how to translate into Chuang; Zhuang');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'znd', 'Translates into Zande', 'A person with this label says that knows how to translate into Zande');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'zu', 'Translates into Zulu', 'A person with this label says that knows how to translate into Zulu');
INSERT INTO label ("schema", name, title, description) VALUES ((SELECT id FROM Schema WHERE name='translation-languages'), 'zun', 'Translates into Zuni', 'A person with this label says that knows how to translate into Zuni');


INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Carlos Perelló Marín'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'es'));

INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Carlos Perelló Marín'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'ca'));

INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Dafydd Harries'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'cy'));

INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Dafydd Harries'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'ja'));

INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Dafydd Harries'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'en'));

/* Sorry Lalo, I need to improve the script that generates the Labels so it works with lang_country languages */
INSERT INTO PersonLabel (person, label)
VALUES ((SELECT id FROM Person Where displayname='Lalo Martins'),
	(SELECT id FROM Label
	 WHERE schema = (SELECT id FROM Schema WHERE name='translation-languages') AND
	       name = 'pt'));

