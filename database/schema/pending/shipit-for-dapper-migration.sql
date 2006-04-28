
UPDATE RequestedCDs SET quantityapproved = 0 WHERE quantityapproved IS NULL;
ALTER TABLE RequestedCDs ALTER COLUMN quantityapproved SET NOT NULL;

INSERT INTO RequestedCDs (request, distrorelease, architecture, flavour,
quantity, quantityapproved) VALUES ((SELECT request, distrorelease,
architecture FROM RequestedCDs), 2, 0, 0);

-- All existing standard requests are for the Ubuntu flavour.
UPDATE StandardShipItRequest SET flavour = 1;

-- These ones may not be necessary, because when we move to production we
-- should have no standardrequests in order to make sure people can't make new
-- requests.
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (7, 1, 0, 0, true, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (8, 5, 0, 0, false, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (9, 10, 0, 0, false, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (10, 0, 0, 1, false, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (11, 0, 0, 5, false, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (12, 8, 0, 2, false, 2);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (13, 5, 0, 0, true, 3);
INSERT INTO standardshipitrequest (id, quantityx86, quantityppc, quantityamd64, isdefault, flavour) VALUES (14, 1, 0, 0, false, 3);

ALTER TABLE StandardShipItRequest ALTER COLUMN flavour SET NOT NULL;
