SET client_min_messages TO error;

/* Add Person.name

    This is a traversable unique identifier, also suitable for use as
    a login name if we decide to implement that in the future.

 */

ALTER TABLE Person ADD COLUMN name text;
UPDATE Person SET name = 'name' || id;
ALTER TABLE Person ALTER COLUMN name SET NOT NULL;
CREATE UNIQUE INDEX person_name_key ON Person(name);
ALTER TABLE Person ADD CHECK (name = lower(name));

/* Schema.name must be UNIQUE and lowercase */
CREATE UNIQUE INDEX schema_name_key ON Schema(name);
ALTER TABLE Schema ADD CHECK (name = lower(name));

