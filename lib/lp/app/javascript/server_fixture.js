/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code to support full application server testing with YUI.
 *
 * @module Y.lp.testing.serverfixture
 */
YUI.add('lp.testing.serverfixture', function(Y) {

var module = Y.namespace('lp.testing.serverfixture');

/*
 * This function calls fixture on the appserver side.
 */
module.setup = function(testcase) {
    // self-post, get data, stash/merge on testcase
    var fixtures = Y.Array(arguments, 1);
    var data = Y.QueryString.stringify(
        {action: 'setup',
         fixtures: fixtures.join(',')
        })
    var config = {
        method: "POST",
        data: data,
        sync: true,
        headers: {Accept: 'application/json'}
        };
    var response = Y.io(window.location, config);
    if (response.status !== 200) {
        Y.error(response.responseText);
    }
    var data = Y.JSON.parse(response.responseText);
    if (!Y.Lang.isValue(testcase._lp_fixture_setups)) {
        testcase._lp_fixture_setups = [];
    }
    testcase._lp_fixture_setups = testcase._lp_fixture_setups.concat(
        fixtures);
    if (!Y.Lang.isValue(testcase._lp_fixture_data)) {
        testcase._lp_fixture_data = {};
    }
    testcase._lp_fixture_data = Y.merge(testcase._lp_fixture_data, data);
    return data;
};

module.teardown = function(testcase) {
    var fixtures = testcase._lp_fixture_setups;
    var data = Y.QueryString.stringify(
        {action: 'teardown',
         fixtures: fixtures.join(','),
         data: Y.JSON.stringify(testcase._lp_fixture_data)
        })
    var config = {
        method: "POST",
        data: data,
        sync: true
        };
    var response = Y.io(window.location, config);
    if (response.status !== 200) {
        Y.error(response.responseText);
    }
    delete testcase._lp_fixture_setups;
    delete testcase._lp_fixture_data;
};

  }, "0.1", {"requires": ["io", "json", "querystring"]});
