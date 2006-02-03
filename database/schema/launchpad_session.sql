-- Create the standard session tables.
\i session.sql

-- Grant required permissions on these tables to the 'session' user.
GRANT SELECT, INSERT, UPDATE, DELETE ON SessionData TO session;
GRANT SELECT, INSERT, UPDATE, DELETE oN SessionPkgData TO session;
GRANT SELECT ON Secret TO session;

