SET client_min_messages=ERROR;

UPDATE SourcePackageBugAssignment SET bugstatus = 10 WHERE bugstatus = 1;
UPDATE SourcePackageBugAssignment SET bugstatus = 20 WHERE bugstatus = 2;
UPDATE SourcePackageBugAssignment SET bugstatus = 30 WHERE bugstatus = 3;
UPDATE SourcePackageBugAssignment SET bugstatus = 40 WHERE bugstatus = 4;

UPDATE ProductBugAssignment SET bugstatus = 10 WHERE bugstatus = 1;
UPDATE ProductBugAssignment SET bugstatus = 20 WHERE bugstatus = 2;
UPDATE ProductBugAssignment SET bugstatus = 30 WHERE bugstatus = 3;
UPDATE ProductBugAssignment SET bugstatus = 40 WHERE bugstatus = 4;
