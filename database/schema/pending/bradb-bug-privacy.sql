ALTER TABLE Bug ADD COLUMN private BOOLEAN;
COMMENT ON COLUMN Bug.private IS 'Is this bug private? If so, only explicit subscribers will be able to see it';

UPDATE Bug
SET private = FALSE;

ALTER TABLE Bug ALTER COLUMN private SET NOT NULL;
ALTER TABLE Bug ALTER COLUMN private SET DEFAULT FALSE;
