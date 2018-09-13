/* Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE). */

YUI.add('lp.snappy.snap.update_build_statuses.test', function (Y) {
    var tests = Y.namespace('lp.snappy.snap.update_build_statuses.test');
    var module = Y.lp.snappy.snap.update_build_statuses;
    tests.suite = new Y.Test.Suite('lp.snappy.snap.update_build_status Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'lp.snappy.snap.update_build_statuses_tests',

        setUp: function () {
            // Clone the table from the test data so that we can reliably
            // restore it.
            this.table = Y.one('table#latest-builds-listing').cloneNode(true);
            this.tbody = this.table.one('tbody');
            this.tr_request_1 = this.tbody.one('tr#request-1');
            this.tr_build_1 = this.tbody.one('tr#build-1');
            this.td_status = this.tr_build_1.one('td.build_status');
            this.td_datebuilt = this.tr_build_1.one("td.datebuilt");
        },

        assert_node_matches: function(expected, node) {
            Y.each(expected, function(value, key) {
                if (key === "tag") {
                    Y.Assert.areEqual(
                        value, node.get("tagName").toLowerCase());
                } else if (key === "attrs") {
                    Y.each(value, function(attr_value, attr_key) {
                        Y.Assert.areEqual(
                            attr_value, node.getAttribute(attr_key));
                    });
                } else if (key === "text") {
                    Y.Assert.areEqual(value, node.get("text").trim());
                } else if (key === "children") {
                    var children = [];
                    node.get("children").each(function(child) {
                        children.push(child);
                    });
                    Y.Array.each(Y.Array.zip(value, children), function(item) {
                        Y.Assert.isObject(item[0]);
                        Y.Assert.isObject(item[1]);
                        this.assert_node_matches(item[0], item[1]);
                    }, this);
                } else {
                    Y.Assert.fail("unhandled key " + key);
                }
            }, this);
        },

        test_dom_updater_plugin_attached: function() {
            Y.Assert.isUndefined(this.table._plugins.updater);
            module.setup(this.table);
            var updater = Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater;
            Y.Assert.areEqual(updater, this.table._plugins.updater);
            // Unplug plugin to prevent DOM autorefresh during testing.
            // DOM autorefresh should be tested in DynamicDomUpdater testsuite.
            this.table.unplug(updater);
            Y.Assert.isUndefined(this.table._plugins.updater);
        },

        test_parameter_evaluator: function() {
            // parameterEvaluator should return an object with the ids of
            // build requests and builds in pending states.
            var params = module.parameterEvaluator(this.table);
            Y.lp.testing.assert.assert_equal_structure(
                {request_ids: ["1"], build_ids: ["1"]}, params);
        },

        test_parameter_evaluator_empty: function() {
            // parameterEvaluator should return empty if no builds remaining
            // in pending states.
            this.tr_request_1.remove();
            this.td_status.setAttribute("class", "build_status FULLYBUILT");
            var params = module.parameterEvaluator(this.table);
            Y.Assert.isNull(params);
        },

        test_stop_updates_check: function() {
            // stopUpdatesCheck should return false if pending build
            // requests or pending builds exist.
            Y.Assert.isFalse(module.stopUpdatesCheck(this.table));
            this.tr_request_1.one('td.request_status')
                .setAttribute('class', 'request_status COMPLETED');
            Y.Assert.isFalse(module.stopUpdatesCheck(this.table));
            // stopUpdatesCheck should return true if no pending build
            // requests or pending builds exist.
            this.td_status.setAttribute("class", "build_status FULLYBUILT");
            Y.Assert.isTrue(module.stopUpdatesCheck(this.table));
            this.tr_request_1.remove();
            Y.Assert.isTrue(module.stopUpdatesCheck(this.table));
            for (var i = 0; i < module.pending_states.length; i++) {
                this.td_status.setAttribute(
                    "class", "build_status " + module.pending_states[i]);
                Y.Assert.isFalse(module.stopUpdatesCheck(this.table));
            }
        },

        test_update_build_request_status_dom_completed: function() {
            var data = {
                "requests": {
                    "1": {
                        "status": "COMPLETED",
                        "error_message": null,
                        "builds": [
                            {
                                "self_link": "/~max/+snap/snap/+build/3",
                                "id": 3,
                                "distro_arch_series_link":
                                    "/ubuntu/hoary/amd64",
                                "architecture_tag": "amd64",
                                "archive_link":
                                    '<a href="/ubuntu" ' +
                                    'class="sprite distribution">Primary ' +
                                    'Archive for Ubuntu Linux</a>',
                                "status": "NEEDSBUILD",
                                "build_log_url": null,
                                "when_complete_estimate": false,
                                "buildstate": "Needs building",
                                "build_log_size": null,
                                "when_complete": null
                            },
                            {
                                "self_link": "/~max/+snap/snap/+build/4",
                                "id": 4,
                                "distro_arch_series_link":
                                    "/ubuntu/hoary/i386",
                                "architecture_tag": "i386",
                                "archive_link":
                                    '<a href="/ubuntu" ' +
                                    'class="sprite distribution">Primary ' +
                                    'Archive for Ubuntu Linux</a>',
                                "status": "BUILDING",
                                "build_log_url": null,
                                "when_complete_estimate": true,
                                "buildstate": "Currently building",
                                "build_log_size": null,
                                "when_complete": "in 1 minute"
                            }
                        ]
                    }
                },
                "builds": {}
            };
            module.domUpdate(this.table, data);
            Y.ArrayAssert.itemsAreEqual(
                ["build-4", "build-3", "build-2", "build-1"],
                this.tbody.get("children").get("id"));
            this.assert_node_matches({
                "tag": "tr",
                "attrs": {"id": "build-3"},
                "children": [
                    {
                        "tag": "td",
                        "attrs": {"class": "build_status NEEDSBUILD"},
                        "children": [
                            {
                                "tag": "img",
                                "attrs": {
                                    "alt": "[NEEDSBUILD]",
                                    "title": "Needs building",
                                    "src": "/@@/build-needed",
                                    "width": "14"
                                }
                            },
                            {
                                "tag": "a",
                                "attrs": {"href": "/~max/+snap/snap/+build/3"},
                                "text": "Needs building"
                            }
                        ]
                    },
                    {
                        "tag": "td",
                        "attrs": {"class": "datebuilt"},
                        "text": "",
                        "children": []
                    },
                    {
                        "tag": "td",
                        "children": [{
                            "tag": "a",
                            "attrs": {
                                "class": "sprite distribution",
                                "href": "/ubuntu/hoary/amd64"
                            },
                            "text": "amd64"
                        }]
                    },
                    {
                        "tag": "td",
                        "children": [{
                            "tag": "a",
                            "attrs": {
                                "class": "sprite distribution",
                                "href": "/ubuntu"
                            },
                            "text": "Primary Archive for Ubuntu Linux"
                        }]
                    }
                ]
            }, this.tbody.one("tr#build-3"));
            this.assert_node_matches({
                "tag": "tr",
                "attrs": {"id": "build-4"},
                "children": [
                    {
                        "tag": "td",
                        "attrs": {"class": "build_status BUILDING"},
                        "children": [
                            {
                                "tag": "img",
                                "attrs": {
                                    "alt": "[BUILDING]",
                                    "title": "Currently building",
                                    "src": "/@@/processing",
                                    "width": "14"
                                }
                            },
                            {
                                "tag": "a",
                                "attrs": {"href": "/~max/+snap/snap/+build/4"},
                                "text": "Currently building"
                            }
                        ]
                    },
                    {
                        "tag": "td",
                        "attrs": {"class": "datebuilt"},
                        "text": "in 1 minute (estimated)",
                        "children": []
                    },
                    {
                        "tag": "td",
                        "children": [{
                            "tag": "a",
                            "attrs": {
                                "class": "sprite distribution",
                                "href": "/ubuntu/hoary/i386"
                            },
                            "text": "i386"
                        }]
                    },
                    {
                        "tag": "td",
                        "children": [{
                            "tag": "a",
                            "attrs": {
                                "class": "sprite distribution",
                                "href": "/ubuntu"
                            },
                            "text": "Primary Archive for Ubuntu Linux"
                        }]
                    }
                ]
            }, this.tbody.one("tr#build-4"));
        },

        test_update_build_request_status_dom_failed: function() {
            var data = {
                "requests": {
                    "1": {
                        "status": "FAILED",
                        "error_message": "Something went wrong",
                        "builds": []
                    }
                },
                "builds": {}
            };
            module.domUpdate(this.table, data);
            Y.ArrayAssert.itemsAreEqual(
                ["build-2", "build-1"], this.tbody.get("children").get("id"));
        },

        test_update_build_status_dom_building: function() {
            var original_a_href = this.td_status.one("a").getAttribute("href");
            var data = {
                "requests": {},
                "builds": {
                    "1": {
                        "status": "BUILDING",
                        "build_log_url": null,
                        "when_complete_estimate": true,
                        "buildstate": "Currently building",
                        "build_log_size": null,
                        "when_complete": "in 1 minute"
                    }
                }
            };
            module.domUpdate(this.table, data);
            this.assert_node_matches({
                "attrs": {"class": "build_status BUILDING"},
                "text": "Currently building",
                "children": [
                    {
                        "tag": "img",
                        "attrs": {
                            "alt": "[BUILDING]",
                            "title": "Currently building",
                            "src": "/@@/processing",
                            "width": "14"
                        }
                    },
                    {
                        "tag": "a",
                        "attrs": {"href": original_a_href}
                    }
                ]
            }, this.td_status);
        },

        test_update_build_status_dom_failedtobuild: function() {
            var original_a_href = this.td_status.one("a").getAttribute("href");
            var data = {
                "requests": {},
                "builds": {
                    "1": {
                        "status": "FAILEDTOBUILD",
                        "build_log_url": null,
                        "when_complete_estimate": false,
                        "buildstate": "Failed to build",
                        "build_log_size": null,
                        "when_complete": "1 minute ago"
                    }
                }
            };
            module.domUpdate(this.table, data);
            this.assert_node_matches({
                "attrs": {"class": "build_status FAILEDTOBUILD"},
                "text": "Failed to build",
                "children": [
                    {
                        "tag": "img",
                        "attrs": {
                            "alt": "[FAILEDTOBUILD]",
                            "title": "Failed to build",
                            "src": "/@@/build-failed",
                            "width": "16"
                        }
                    },
                    {
                        "tag": "a",
                        "attrs": {"href": original_a_href}
                    }
                ]
            }, this.td_status);
        },

        test_update_build_status_dom_chrootwait: function() {
            var original_a_href = this.td_status.one("a").getAttribute("href");
            var data = {
                "requests": {},
                "builds": {
                    "1": {
                        "status": "CHROOTWAIT",
                        "build_log_url": null,
                        "when_complete_estimate": false,
                        "buildstate": "Chroot problem",
                        "build_log_size": null,
                        "when_complete": "1 minute ago"
                    }
                }
            };
            module.domUpdate(this.table, data);
            this.assert_node_matches({
                "attrs": {"class": "build_status CHROOTWAIT"},
                "text": "Chroot problem",
                "children": [
                    {
                        "tag": "img",
                        "attrs": {
                            "alt": "[CHROOTWAIT]",
                            "title": "Chroot problem",
                            "src": "/@@/build-chrootwait",
                            "width": "14"
                        }
                    },
                    {
                        "tag": "a",
                        "attrs": {"href": original_a_href}
                    }
                ]
            }, this.td_status);
        },

        test_update_build_date_dom: function() {
            var data = {
                "requests": {},
                "builds": {
                    "1": {
                        "status": "NEEDSBUILD",
                        "build_log_url": "/+build/1/+files/build1.txt.gz",
                        "when_complete_estimate": true,
                        "buildstate": "Needs building",
                        "build_log_size": 12345,
                        "when_complete": "in 30 seconds"
                    }
                }
            };
            module.domUpdate(this.table, data);
            this.assert_node_matches({
                "text": "in 30 seconds (estimated) buildlog (12345 bytes)",
                "children": [{
                    "tag": "a",
                    "attrs": {
                        "class": "sprite download",
                        "href": data["builds"]["1"].build_log_url
                    },
                    "text": "buildlog"
                }]
            }, this.td_datebuilt);
        }
    }));

}, '0.1', {
    requires: ['test', 'console', 'lp.testing.assert',
               'lp.snappy.snap.update_build_statuses']
});
