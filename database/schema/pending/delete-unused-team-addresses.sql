-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

--SELECT person.name, email, status
--FROM EmailAddress
--    JOIN Person ON EmailAddress.person = Person.id
--        AND Person.teamowner IS NOT NULL
--WHERE
--    EmailAddress.status in (1, 2)
--    AND EmailAddress.email not in (
--        person.name || '@lists.launchpad.net',
--        person.name || '@lists.staging.launchpad.net')
--;

-- Delete all the unused team email addresses that Launchpad claims to have
-- removed. Status 1 (NEW, meaning merged) or 2 (VALID, meaning not used)
-- and email not the team's mailing list address.
DELETE
FROM EmailAddress
USING Person
WHERE
    EmailAddress.person = Person.id
    AND Person.teamowner IS NOT NULL
    AND EmailAddress.status in (1, 2)
    AND EmailAddress.email not in (
        person.name || '@lists.launchpad.net',
        person.name || '@lists.staging.launchpad.net')
;
