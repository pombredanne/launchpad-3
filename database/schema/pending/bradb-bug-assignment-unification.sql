/* migrate existing product assignments */
INSERT INTO bugassignment (
    bug, product, status, priority, severity,
    assignee, dateassigned, datecreated, owner)
SELECT bug, product, bugstatus, priority, severity, assignee,
       dateassigned, datecreated, owner 
FROM productbugassignment;

/* migrate existing package assignments */
INSERT INTO bugassignment (
    bug, sourcepackagename, distro, status, priority, 
    severity, binarypackagename, assignee, dateassigned, 
    datecreated, owner)
SELECT bug, sourcepackagename, distro, bugstatus, priority, severity,
       binarypackagename, assignee, dateassigned, datecreated, owner
FROM sourcepackagebugassignment spba, sourcepackage sp, sourcepackagename spn
WHERE spba.sourcepackage = sp.id and sp.sourcepackagename = spn.id;
