-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Drop everything in the authdb replication set.
DROP TABLE IF EXISTS Account CASCADE;
DROP TABLE IF EXISTS AccountPassword CASCADE;
DROP TABLE IF EXISTS AuthToken CASCADE;
DROP TABLE IF EXISTS EmailAddress CASCADE;
DROP TABLE IF EXISTS OpenIDAssociation CASCADE;
DROP TABLE IF EXISTS OpenIDAuthorization CASCADE;
DROP TABLE IF EXISTS OpenIDNonce CASCADE;
DROP TABLE IF EXISTS OpenIDRPSummary;
