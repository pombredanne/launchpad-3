SET client_min_messages=ERROR;

CREATE OR REPLACE VIEW ValidPersonOrTeamCache AS
    SELECT Person.id
    FROM Person
    LEFT OUTER JOIN EmailAddress ON Person.id = EmailAddress.person
    LEFT OUTER JOIN Account ON EmailAddress.account = Account.id
    WHERE teamowner IS NOT NULL
        OR (account.status = 20 AND EmailAddress.status = 4);

CREATE INDEX revision__revision_author__idx ON Revision(revision_author);
CREATE INDEX revision__revision_date__idx ON Revision(revision_date);
CREATE INDEX revision__gpgkey__idx ON Revision(gpgkey)
    WHERE gpgkey IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 70, 1);
