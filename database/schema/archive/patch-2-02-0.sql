SET client_min_messages TO error;

/* Rosetta changes for Carlos */
ALTER TABLE POTemplate DROP CONSTRAINT potemplate_name_key;

/*
CREATE INDEX idx_pomsgidsighting_inlastrevision ON POMsgIDSighting (pomsgset, pomsgid, inlastrevision);
CREATE INDEX idx_pomsgidsighting_pluralform ON POMsgIDSighting (pomsgset, pluralform);
CREATE INDEX idx_pomsgset_primemsgid ON POMsgSet (potemplate, pofile, primemsgid);
*/

CREATE INDEX pomsgidsighting_pomsgset_idx ON POMsgIDSighting(pomsgset);
CREATE INDEX pomsgidsighting_pomsgid_idx ON POMsgIDSighting(pomsgid);
CREATE INDEX pomsgidsighting_inlastrevision_idx ON 
    POMsgIDSighting(inlastrevision);
CREATE INDEX pomsgidsighting_pluralform_idx ON POMsgIDSighting (pluralform);
CREATE INDEX pomsgset_index_potemplate ON POMsgSet (potemplate);
CREATE INDEX pomsgset_index_pofile ON POMsgSet (pofile);
CREATE INDEX pomsgset_index_primemsgid ON POMsgSet (primemsgid);

/* Malone needs to allow NULL in SourcePackageBugAssignment.assignee and
   ProductBugAssignment.assignee. This allows us to differentiate between
   'not yet assigned' and 'assigned to the owner' */

ALTER TABLE SourcePackageBugAssignment ALTER COLUMN assignee DROP NOT NULL;
ALTER TABLE ProductBugAssignment ALTER COLUMN assignee DROP NOT NULL;

