CREATE TABLE BugPerson (
    bug INTEGER NOT NULL,
    person INTEGER NOT NULL
);
ALTER TABLE BugPerson ADD CONSTRAINT "bug_fk" FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE BugPerson ADD CONSTRAINT "person_fk" FOREIGN KEY (person) REFERENCES person(id);
ALTER TABLE BugPerson ADD CONSTRAINT "bug_person_key" unique(bug, person);

COMMENT ON TABLE BugPerson IS 'A Person (which can be an individual or a group) linked to this bug. Can be used, for example, to assign a bug to a security team in a distro.';

ALTER TABLE BugTask ADD COLUMN private BOOLEAN NULL;

COMMENT ON COLUMN BugTask.private IS 'Is this task private? If so, only the BugPersons and administrator will be able to see it';
