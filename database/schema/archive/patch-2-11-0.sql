SET client_min_messages TO error;

/* Argh bloody sqlobject uses the primary key sequences directly, calculated
    from the Table name. This is naughty but might be unfixable if SQLObject
    needs to know the ID before the row is inserted :-/

*/

ALTER TABLE projectbugsystem_id_seq RENAME TO projectbugtracker_id_seq;
ALTER TABLE ProjectBugTracker 
    ALTER COLUMN id SET DEFAULT nextval('projectbugtracker_id_seq');

ALTER TABLE bugsystem_id_seq RENAME TO bugtracker_id_seq;
ALTER TABLE BugTracker
    ALTER COLUMN id SET DEFAULT nextval('bugtracker_id_seq');

ALTER TABLE bugsystemtype_id_seq RENAME TO bugtrackertype_id_seq;
ALTER TABLE BugTrackerType
    ALTER COLUMN id SET DEFAULT nextval('bugtrackertype_id_seq');

