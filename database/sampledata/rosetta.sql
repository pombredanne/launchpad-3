/*
   Rosetta SAMPLE DATA
*/

INSERT INTO POTemplateName(name, title, description)
VALUES ('evolution-2.2',
        'Main translation domain for the Evolution 2.2',
        'This is a description about Evolution 2.2 POTemplateName'
);

INSERT INTO POTemplate (distrorelease, sourcepackagename, potemplatename,
                        title, description, datecreated, path, iscurrent,
                        messagecount, owner)
VALUES ((SELECT id FROM DistroRelease WHERE name = 'hoary'),
        (SELECT id FROM SourcepackageName WHERE name = 'evolution'),
        (SELECT id FROM POTemplateName WHERE name = 'evolution-2.2'),
        'Main POT file for the Hoary\'s Evolution',
        'This is a description about Hoary\'s Evolution POTemplate',
        timestamp '2005-03-02 11:20',
        'po',
        TRUE,
        3,
        (SELECT id FROM Person WHERE displayname = 'Sample Person')
);

INSERT INTO ProductRelease (product, datereleased, version, changelog, owner)
VALUES ((SELECT id FROM Product WHERE name = 'evolution'),
        timestamp '2005-02-28 00:00',
        '2.1.6',
        'Bugzilla bugs fixed (see http://bugzilla.ximian.com/show_bug.cgi):

 * Addressbook
   #73005 - Cannot cancel \'Contact List Editor\' (Siva)
   #73005 - offline - setting/unsetting folder offline property is not working (Sushma)
   #70371 - Evolution crashes when adding contact list (Siva)
   #67724 - When unix user name, callendar points to old username (Siva)
   #54825 - Freeze on .vcf import from MacOS X AddressBook (Christophe Fergeau)
   #73013 - \'Right\' click on a \'Contact\' cannot select \'Cut\' (Siva)

 * Calendar
   #72958 - Unable to send delayed meeting (Chen)
   #72006 - Opened existing appointments with attachment - press cancel - popup info with save / discard / cancel changes (Chen)
   #63866 - Same name can be entered twice in invitations tab (JP)
   #67714 - Invitations Tab Allows Entry Of Empty Line (JP)
   #62089 - adding contact lists to meetings impossible (JP)
   #47747 - Changes to attendee not updated until click on different row (JP)
   #61495 - Existing text is placed off screen when editing attendee field (JP)
   #28947 - adding contact list to attendee list should expand it (JP)
   #67724 - When unix user name, callendar points to old username (Siva)
   #72038 - Changes meeting to appoinment after throwing warning invalid mail id (Rodrigo)
   #69556 - Crash attaching mime parts to calendar events (Harish)

 * Mail
   #66126 - attach File Chooser is modal (Michael)
   #68549 - Answering to Usenet article doesn\'t consider the "Followup-To:" field (Michael)
   #71003 - threads still running at exit (Michael)
   #62109 - Inconsistent ways of determining 8-bit Subject: and From: header charsets (Jeff)
   #34153 - Confusing Outbox semantics for deleted outgoing messages (Michael)
   #71528 - Search Selection Widget Has Repeated Items (Michael)
   #71967 - Evolution delete mail from POP3 server even is checked the option "leave the mail on server (Michael)
   #40515 - Signature scripts do not allow switches (Michael)
   #68866 - Forward button doesn\'t put newline between headers and body (Michael)
   #35219 - flag-for-followup crufting (Michael)
   #64987 - Go to next unread message doesn\'t work when multiple messages are selected (Michael)
   #72337 - Evolution crashes if I click OK/Cancel on the password dialog after disabling the IMAP account (Michael)
   #70718 - Next and previous buttons don\'t realize there\'s new mail (Michael)
   #61363 - Setup wizard, IMAP for receiving server, sending default GW (Michael)
   #70795 - Next/Previous Message Should Only Display Listed Emails (Michael)
   #23822 - no copy text option when right-clicking on marked mail text (Rodney)
   #72266 - You shouldn\'t be able to open more than one \'Select Folder\' dialog in the mail filters (Michael)
   #71429 - on NLD, menus in wrong order (Michae)l
   #72228 - cannot store into groupwise sent folder (Michael)
   #72209 - Evolution is crashing when you move a VFolder to a folder \'on this computer\' (Michael)
   #72275 - Can\'t use Shift+F10 to popup context menu for link in message (Harry Lu)
   #54503 - "New" dropdown menu on toolbar has wrong widget style (Rodney)
   #72676 - Saved filter rule can\'t be modified if it is selected with GOK. (Harry Lu)

 * SMIME
   #68592 - "Backup" buttons in certificate settings does nothing - work around (Michael)

 * Shell
   #33287 - "send/receive" button not greyed out when starting offline (JP)
   #48868 - Status bar changes its height when fonts are large (William Jon McCann)

 * Plugins
   #71527 - Save Calendar widget mixup between directory and file (Rodrigo)

Other bugs

 * Addressbook
   - Use new categories dialog in contact editor (Rodrigo)
   - HIG spacing fixes (Rodney)
   - Display warning dialog when GW server is old (Vivek)

 * Calendar
   - Always ensure default sources are available (Siva)
   - Don\'t look up free/busy unless we need to (Harish)
   - Make sure new events don\'t display twice (Chen)
   - Make sure double click opens attachments (Chen)

 * Mail
   - a11y fixes for composer (Harry Lu)
   - Use gnome-vfs API to launch external applications (Marco Pesenti Gritti)
   - New mailer context menus for messages (Rodney)

 * Shell
   - Fix leak (JP)
   - Use gnome-vfs API to open quick reference (Marco Pesenti Gritti)

 * Plugins
   - Make e-popup more robust (Michael)
   - Cleanup authors/descriptions (Björn Torkelsson)
   - out of office exchange fixes (Sushma)
   - retry send options if invalid session string (Chen)
   - set proper default port for shared folders (Vivek)

 * Miscellaneous
   - BSD runtime linking fixes (Hans)
   - distclean fixes (Björn Torkelsson)

Updated translations:
   - et (Priit Laes)
   - el (Kostas Papadimas, Nikos Charonitakis)
   - sv (Christian Rose)
   - es (Francisco Javier F. Serrador)
   - it (Luca Ferretti, Marco Ciampa)
   - da (Martin Willemoes Hansen)
   - ca (Josep Puigdemont, Xavi Conde)
   - nb (Kjartan Maraas)
   - no (Kjartan Maraas)
   - ru (Leonid Kanter)
   - gu (Ankit Patel)
   - cs (Miloslav Trmac)
   - nl (Vincent van Adrighem)
   - fi (Ilkka Tuohela)
   - pt (Duarte Loreto)
   - uk (Maxim Dziumanenko)
   - ko (Changwoo Ryu)
   - de (Frank Arnold)
   - fr (Vincent Carriere)
   - en_CA (Adam Weinberger)
   - cs (Miloslav Trmac)
   - pl (Artur Flinta)
   - bg (Vladimir Petkov)
   - ja (Takeshi AIHANA)
   - en_GB (David Lodge)
   - en_CA (Adam Weinberger)
   - lt (Zygimantas Berucka)',
        (SELECT id FROM Person WHERE displayname = 'Sample Person')
);

INSERT INTO POTemplate (productrelease, potemplatename, title, description,
                        datecreated, path, iscurrent, messagecount, owner)
VALUES ((SELECT pr.id
         FROM Product p, ProductRelease pr
         WHERE
             p.name = 'evolution' AND
             p.id = pr.product AND
             pr.version = '2.1.6'),
        (SELECT id FROM POTemplateName WHERE name = 'evolution-2.2'),
        'Main POT file for the Evolution 2.1.6 release',
        'This is a description about Evolution 2.1.6 POTemplate',
        timestamp '2005-03-02 12:37',
        'po',
        TRUE,
        3,
        (SELECT id FROM Person WHERE displayname = 'Sample Person')
);
