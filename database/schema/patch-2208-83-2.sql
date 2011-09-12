SET client_min_messages=ERROR;

-- Remove interdependencies. upgrade.py drops replicated tables in
-- undefined order.
ALTER TABLE bountymessage DROP CONSTRAINT bountymessage_bounty_fk;
ALTER TABLE bountymessage DROP CONSTRAINT bountymessage_message_fk;
ALTER TABLE bountysubscription DROP CONSTRAINT bountysubscription_bounty_fk;
ALTER TABLE distributionbounty DROP CONSTRAINT distributionbounty_bounty_fk;
ALTER TABLE productbounty DROP CONSTRAINT productbounty_bounty_fk;
ALTER TABLE projectbounty DROP CONSTRAINT projectbounty_bounty_fk;
ALTER TABLE requestedcds DROP CONSTRAINT requestedcds_request_fk;
ALTER TABLE shipitsurveyresult DROP CONSTRAINT shipitsurveyresult_answer_fkey;
ALTER TABLE shipitsurveyresult DROP CONSTRAINT shipitsurveyresult_question_fkey;
ALTER TABLE shipitsurveyresult DROP CONSTRAINT shipitsurveyresult_survey_fkey;
ALTER TABLE shipment DROP CONSTRAINT shipment_shippingrun_fk;
ALTER TABLE shippingrequest DROP CONSTRAINT shippingrequest_shipment_fk;

-- And now actually dispose of all the tables.
DROP TABLE authtoken;
DROP TABLE bounty;
DROP TABLE bountymessage;
DROP TABLE bountysubscription;
DROP TABLE bugpackageinfestation;
DROP TABLE bugproductinfestation;
DROP TABLE distributionbounty;
DROP TABLE distrocomponentuploader;
DROP TABLE mailinglistban;
DROP TABLE mentoringoffer;
DROP TABLE openidassociation;
DROP TABLE packagebugsupervisor;
DROP TABLE packageselection;
DROP TABLE posubscription;
DROP TABLE productbounty;
DROP TABLE productcvsmodule;
DROP TABLE productseriescodeimport;
DROP TABLE productsvnmodule;
DROP TABLE projectbounty;
DROP TABLE projectrelationship;
DROP TABLE pushmirroraccess;
DROP TABLE requestedcds;
DROP TABLE shipitreport;
DROP TABLE shipitsurvey;
DROP TABLE shipitsurveyanswer;
DROP TABLE shipitsurveyquestion;
DROP TABLE shipitsurveyresult;
DROP TABLE shipment;
DROP TABLE shippingrequest;
DROP TABLE shippingrun;
DROP TABLE standardshipitrequest;
DROP TABLE webserviceban;
DROP TABLE openidrpconfig;
DROP TABLE openidrpsummary;
DROP TABLE staticdiff;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 83, 2);
