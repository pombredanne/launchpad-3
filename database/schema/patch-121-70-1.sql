SET client_min_messages=ERROR;

CREATE OR REPLACE VIEW ValidPersonOrTeamCache AS
    SELECT Person.id
    FROM Person
    LEFT OUTER JOIN EmailAddress ON Person.id = EmailAddress.person
    LEFT OUTER JOIN Account ON EmailAddress.account = Account.id
    WHERE teamowner IS NOT NULL
        OR (account.status = 20 AND EmailAddress.status = 4);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 70, 1);
