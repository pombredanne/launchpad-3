
set client_min_messages=ERROR;

CREATE TABLE KarmaCategory (
  id                serial PRIMARY KEY,
  name              text NOT NULL,
  title             text NOT NULL,
  summary           text NOT NULL
);


/* let's capture the old dbschema.KarmaActioNCategory data */

 -- this part is omitted from the version used by the autobuild system. see
 -- initial-karma-data.sql for the updates and inserts

/* now all the actions should point at karma categories and we should be 
   able to enforce that in the db */

ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_category_fk 
    FOREIGN KEY (category) REFERENCES KarmaCategory(id);

/* we need to transition the karmaaction table to use a text name and have a
   title and summary */

ALTER TABLE KarmaAction ADD COLUMN textname text;
ALTER TABLE KarmaAction ADD COLUMN title text;
ALTER TABLE KarmaAction ADD COLUMN summary text;

ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_name_uniq
    UNIQUE (name);

/* let's capture the old details from dbschema.KarmaActionName */

 -- this part is omitted from the version used by the autobuild system. see
 -- initial-karma-data.sql for the updates and inserts

/* now we can get rid of the old name column and make it the textual one */

ALTER TABLE KarmaAction DROP COLUMN name;
ALTER TABLE KarmaAction RENAME COLUMN textname TO name;

/* and we can make name unique, and all text attributes not null */

ALTER TABLE KarmaAction ALTER COLUMN name SET NOT NULL;
ALTER TABLE KarmaAction ADD CONSTRAINT karmaaction_name_uniq UNIQUE (name);

ALTER TABLE KarmaAction ALTER COLUMN title SET NOT NULL;
ALTER TABLE KarmaAction ALTER COLUMN summary SET NOT NULL;

/* and finally, lets add some new karma actions for the spec system and
   support systems */

INSERT INTO LaunchpadDatabaseRevision VALUES (25,50,0);
