SET client_min_messages TO error;

/*
 * names must be UNIQUE within their context, and all lower case
 */
ALTER TABLE Sourcepackage ADD UNIQUE (name);
ALTER TABLE Sourcepackage ADD CHECK (name = lower(name));

-- Project already UNIQUE
ALTER TABLE Project ADD CHECK (name = lower(name));

-- Product name unique within a Project, constraint already exists
ALTER TABLE Product ADD CHECK (name = lower(name));

ALTER TABLE Bug DROP CONSTRAINT bug_nickname_key;
ALTER TABLE Bug ADD UNIQUE (name);
ALTER TABLE Bug ADD CHECK (name = lower(name));

ALTER TABLE BinarypackageName ADD CHECK (name = lower(name));

/*
 * Email addresses must be UNIQUE regardless of case. We preserve case,
 * however, as many users like it that way and others don't realize
 * they are case insensitive.
 */
ALTER TABLE EmailAddress DROP CONSTRAINT emailaddress_email_key;
CREATE UNIQUE INDEX idx_EmailAddress_email ON EmailAddress (lower(email));

