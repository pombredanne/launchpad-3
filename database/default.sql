/*
   LAUNCHPAD INITIAL DATA

# arch-tag: 72b5bbef-19d6-4a07-b434-60f2a121ade2

this is initial data for launchpad. unlike the sample data, this will be loaded into our production install.

*/


-- Person
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Mark Shuttleworth', 'Mark', 'Shuttleworth' );     -- 1
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Dave Miller', 'David', 'Miller' );                -- 2
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Colin Watson', 'Colin', 'Watson' );               -- 3
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Steve Alexander', 'Steve', 'Alexander' );         -- 4
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Scott James Remnant', 'Scott James', 'Remnant' ); -- 5
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Robert Collins', 'Robert', 'Collins' );           -- 6
INSERT INTO Person ( presentationname, givenname, familyname ) VALUES ( 'Jeff Waugh', 'Jeff', 'Waugh' );                   -- 7


-- EmailAddress
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'mark@hbd.com', 1, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'marks@thawte.com', 1, 3 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'markshuttle@yahoo.co.uk', 1, 1 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'justdave@bugzilla.org', 2, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'colin.watson@canonical.com', 3, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'steve.alexander@canonical.com', 4, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'scott@netsplit.com', 5, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'robertc@cygwin.com', 6, 2 );
INSERT INTO EmailAddress ( email, person, status ) VALUES ( 'robert.collins@canonical.com', 6, 2 );


-- BugSystemType
INSERT INTO BugSystemType VALUES ( 1, 'bugzilla', 'BugZilla', 'Dave Miller\'s Labour of Love, the Godfather of Open Source project issue tracking.', 'http://www.bugzilla.org/', 2 );
INSERT INTO BugSystemType VALUES ( 2, 'debbugs', 'DebBugs', 'The Debian bug tracking system, ugly as sin but fast and productive as a rabbit in high heels.', 'http://bugs.debian.org/', 3 );
INSERT INTO BugSystemType VALUES ( 3, 'roundup', 'Round-Up', 'Python-based open source bug tracking system with an elegant design and reputation for cleanliness and usability.', 'http://www.roundup.org/', 4 );



-- Project
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 1, 'ubuntu', 'The Ubuntu Project', 'The Ubuntu Project aims to create a freely redistributable OS that is easy to customize and derive from. Ubuntu is released every six months with contributions from a large community. Ubuntu also includes work to unify the translation of common opens source desktop applications and the tracking of bugs across multiple distributions.', 'http://www.no-name-yet.com/' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 2, 'mozilla', 'The Mozilla Project', 'The Mozilla Project is the largest open source web browser collaborative project. The Mozilla Project produces several internet applications that are very widely used, and is also a center for collaboration on internet standards work by open source groups.', 'http://www.mozilla.org/' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 7, 'gnome', 'The Gnome Project', 'The Gnome project aims to create a desktop environment and core desktop applications that bring simplicity and ease of use to the open source desktop.', 'http://www.gnome.org/' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 6, 'arch', 'The Arch Revision Control System', 'Arch is a next-generation revision control system that allows anyone to create local branches of open source code, and makes merging between these branches easy.', 'http://www.gnuarch.org/' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 6, 'launchpad-mirrors', 'The launchpad mirroring Project', 'launchpad mirrors various revision control archives, that mirroring is managed here', '????' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 6, 'do-not-use-info-imports', 'DO NOT USE', 'TEMPORARY project till mirror jobs are assigned to correct project', '????' );
INSERT INTO Project ( owner, name, title, description, homepageurl ) VALUES ( 3, 'apache', 'The Apache Project', 'The Apache Project produces some of the worlds most widely used web and internet server software.', 'http://www.apache.org/' ); -- 5



-- Product
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 7, 3, 'apache', 'The Apache Web Server', 'The worlds most popular web server. Used on more than half of the worlds web servers, and most of the servers that carry heavy traffic, Apache is the undisputed champion of the web server business.', 'http://httpd.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 7, 3, 'tomcat', 'Tomcat Java Application Server', 'Tomcat description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://tomcat.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 7, 3, 'spamassassin', 'Spamassassin Spam Filter Daemon', 'Spamassassin description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://spamassassin.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 7, 3, 'apr', 'Apache Portable Runtime Library', 'APR description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://apr.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 7, 3, 'cocoon', 'XML Publishing Engine', 'Cocoon description goes here. A good description has at least a full paragraph of text, explaining what\'s unique about that product, why and when you would use it.', 'http://cocoon.apache.org/' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 5, 6, 'arch-mirrors', 'Arch archive mirrors', 'Arch archive full-archive mirror tasks', '????' );
INSERT INTO Product ( project, owner, name, title, description, homepageurl ) VALUES ( 6, 6, 'unassigned', 'unassigned syncs', 'unassigned syncs, will not be processed, to be moved to real proejcts ASAP.', '????' );



