-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

--SELECT 
--    Account.displayname,
--    Account.openid_identifier,
--    'merged-' || Account.openid_identifier
--FROM Account
--    JOIN Person ON Account.id = Person.account
--WHERE
--    Person.merged IS NOT NULL
--;

-- Change the openid_identifier of merged Persons to prevent the merged
-- person from being selected during login.
UPDATE Account
SET openid_identifier = 'merged-' || openid_identifier
FROM Person
WHERE
    Account.id = Person.account
    AND Person.merged IS NOT NULL
;
