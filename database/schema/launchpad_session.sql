-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

-- Create the standard session tables.

\i session.sql

-- Grant required permissions on these tables to the 'session' user.
GRANT SELECT, INSERT, UPDATE, DELETE ON SessionData TO session;
GRANT SELECT, INSERT, UPDATE, DELETE oN SessionPkgData TO session;
GRANT SELECT ON Secret TO session;

GRANT EXECUTE ON FUNCTION ensure_session_client_id(text) TO session;
GRANT EXECUTE ON FUNCTION
    set_session_pkg_data(text, text, text, bytea) TO session;

