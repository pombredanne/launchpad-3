-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

-- Fix the missing account on validated and preferred email addresses.
-- Launchpad must be restarted; Storm will not see the changes.

SET client_min_messages=ERROR;

UPDATE
    EmailAddress
SET
    account = Person.account
FROM
    Person
WHERE
    Person.id = EmailAddress.person
    AND Person.account IS NOT NULL
    AND EmailAddress.status in (2, 4)
    AND EmailAddress.account IS NULL;


/*

-- Select all preferred email addresses for active accounts that
-- are missing their account.
SELECT
    Account.id AS account_id,
    Account.status AS account_status,
    Account.displayname AS account_displayname,
    EmailAddress.*
FROM
    Account,
    EmailAddress,
    Person
WHERE
    Account.id = Person.account
    AND Person.id = EmailAddress.person
    AND Account.status = 20
    AND EmailAddress.Status in (2, 4)
    AND EmailAddress.account is NULL;

*/
