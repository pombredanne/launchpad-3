/* Copyright 2016 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.snappy.snap.update_build_statuses.test', function (Y) {
    var tests = Y.namespace('lp.snappy.snap.update_build_statuses.test');
    var module = Y.lp.snappy.snap.update_build_statuses;
    tests.suite = new Y.Test.Suite('lp.snappy.snap.update_build_status Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.snappy.snap.update_build_statuses_tests',

        setUp: function () {
            this.table = Y.one('table#latest-builds-listing');
            this.tr_build_1 = Y.one('tr#build-1');
            this.td_status = this.tr_build_1.one('td.build_status');
            this.td_datebuilt = this.tr_build_1.one("td.datebuilt");
            this.td_status_class = this.td_status.getAttribute("class");
            this.td_status_img = this.td_status.one("img");
            this.td_status_a = this.td_status.one("a");
        },

        test_dom_updater_plugin_attached: function() {
            Y.Assert.isUndefined(this.table._plugins.updater);
            module.setup(this.table);
            updater = Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater;
            Y.Assert.areEqual(updater, this.table._plugins.updater);
            // Unplug plugin to prevent DOM autorefresh during testing.
            // DOM autorefresh should be tested in DynamicDomUpdater testsuite.
            this.table.unplug(updater);
            Y.Assert.isUndefined(this.table._plugins.updater);
        },

        test_parameter_evaluator: function() {
            // parameterEvaluator should return an object with the ids of
            // builds in pending states.
            params = module.parameterEvaluator(this.table);
            Y.lp.testing.assert.assert_equal_structure(
                {snap_build_ids: ["1"]}, params);
        },

        test_parameter_evaluator_empty: function() {
            // parameterEvaluator should return empty if no builds remaining
            // in pending states.
            this.td_status.setAttribute("class", "build_status FULLYBUILT");
            params = module.parameterEvaluator(this.table);
            Y.Assert.isNull(params);
            // reset td class to the original value
            this.td_status.setAttribute("class", this.td_status_class);
        },

        test_stop_updates_check: function() {
            // stopUpdatesCheck should return false if pending builds exist.
            Y.Assert.isFalse(module.stopUpdatesCheck(this.table));
            // stopUpdatesCheck should return true if no pending builds exist.
            this.td_status.setAttribute("class", "build_status FULLYBUILT");
            Y.Assert.isTrue(module.stopUpdatesCheck(this.table));
            for (i = 0; i < module.pending_states.length; i++) {
                this.td_status.setAttribute(
                    "class", "build_status " + module.pending_states[i]);
                Y.Assert.isFalse(module.stopUpdatesCheck(this.table));
            }
            // reset td class to the original value
            this.td_status.setAttribute("class", this.td_status_class);
        },

        test_update_build_status_dom: function() {
            var original_a_href = this.td_status_a.get("href");
            data = {"1": {
                    "status": "BUILDING",
                    "build_log_url": null,
                    "when_complete_estimate": true,
                    "buildstate": "Currently building",
                    "build_log_size": null,
                    "when_complete": "in 1 minute"
                }};
            module.domUpdate(this.table, data);
            Y.Assert.areEqual(
                "build_status BUILDING", this.td_status.getAttribute("class"));
            Y.Assert.areEqual(
                "Currently building", this.td_status.get("text").trim());
            Y.Assert.areEqual("[BUILDING]", this.td_status_img.get("alt"));
            Y.Assert.areEqual(
                "Currently building", this.td_status_img.get("title"));
            Y.Assert.areEqual(
                "file:///@@/processing", this.td_status_img.get("src"));
            Y.Assert.areEqual(original_a_href, this.td_status_a.get("href"));
        },

        test_update_build_date_dom: function() {
            data = {"1": {
                    "status": "NEEDSBUILD",
                    "build_log_url": "/+build/1/+files/build1.txt.gz",
                    "when_complete_estimate": true,
                    "buildstate": "Needs building",
                    "build_log_size": 12345,
                    "when_complete": "in 30 seconds"
                }};
            module.domUpdate(this.table, data);
            Y.Assert.areEqual(
                "in 30 seconds (estimated) buildlog (12345 bytes)",
                this.td_datebuilt.get("text").trim());
            var td_datebuilt_a = this.td_datebuilt.one("a");
            Y.Assert.isNotNull(td_datebuilt_a);
            Y.Assert.areEqual("buildlog", td_datebuilt_a.get("text").trim());
            Y.Assert.areEqual(
                "sprite download", td_datebuilt_a.getAttribute("class"));
            Y.Assert.areEqual(
                "file://" + data["1"].build_log_url,
                td_datebuilt_a.get("href"));
        }
    }));

}, '0.1', {
    requires: ['test', 'console', 'lp.testing.assert',
               'lp.snappy.snap.update_build_statuses']
});
