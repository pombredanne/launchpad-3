ALTER TABLE Bug ADD COLUMN securityrelated BOOLEAN null;
ALTER TABLE Bug ALTER COLUMN securityrelated SET DEFAULT FALSE;
COMMENT ON COLUMN Bug.securityrelated IS 'Does this bug expose a security vulnerability in the software it affects?';
