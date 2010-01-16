-- Repair sequences in the authdb replication set. We need to do this because
-- we cannot restore the sequence values from the dump when restoring the
-- data using pg_restore --data-only.

SELECT setval('account_id_seq', max(id)) AS Account
FROM Account;

SELECT setval('accountpassword_id_seq', max(id)) AS AccountPassword
FROM AccountPassword;

SELECT setval('authtoken_id_seq', max(id)) AS AuthToken
FROM AuthToken;

SELECT setval('emailaddress_id_seq', max(id)) AS EmailAddress
FROM EmailAddress;

SELECT setval('openidauthorization_id_seq', max(id)) AS OpenIDAuthorization
FROM OpenIDAuthorization;

SELECT setval('openidrpsummary_id_seq', max(id)) AS OpenIDRPSummary
FROM OpenIDRPSummary;

