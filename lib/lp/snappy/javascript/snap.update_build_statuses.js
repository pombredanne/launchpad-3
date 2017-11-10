/* Copyright 2016 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * The lp.snappy.snap.update_build_statuses module uses the
 * LP DynamicDomUpdater plugin for updating the latest builds table of a snap.
 *
 * @module Y.lp.snappy.snap.update_build_statuses
 * @requires anim, node, lp.anim, lp.buildmaster.buildstatus,
 *           lp.soyuz.dynamic_dom_updater
 */
YUI.add('lp.snappy.snap.update_build_statuses', function(Y) {
    Y.log('loading lp.snappy.snap.update_build_statuses');
    var module = Y.namespace('lp.snappy.snap.update_build_statuses');

    module.pending_states = [
        "NEEDSBUILD", "BUILDING", "UPLOADING", "CANCELLING"];

    module.domUpdate = function(table, data_object) {
        Y.each(data_object, function(build_summary, build_id) {
            var ui_changed = false;

            var tr_elem = Y.one("tr#build-" + build_id);
            if (tr_elem === null) {
                return;
            }

            var td_build_status = tr_elem.one("td.build_status");
            var td_datebuilt = tr_elem.one("td.datebuilt");

            if (td_build_status === null || td_datebuilt === null) {
                return;
            }

            if (Y.lp.buildmaster.buildstatus.update_build_status(
                    td_build_status, build_summary)) {
                ui_changed = true;
            }

            if (build_summary.when_complete !== null) {
                ui_changed = true;
                td_datebuilt.set("innerHTML", build_summary.when_complete);
                if (build_summary.when_complete_estimate) {
                    td_datebuilt.appendChild(
                        document.createTextNode(' (estimated)'));
                }
                if (build_summary.build_log_url !== null) {
                    var new_link = Y.Node.create(
                        '<a class="sprite download">buildlog</a>');
                    new_link.setAttribute(
                        'href', build_summary.build_log_url);
                    td_datebuilt.appendChild(document.createTextNode(' '));
                    td_datebuilt.appendChild(new_link);
                    if (build_summary.build_log_size !== null) {
                        td_datebuilt.appendChild(
                            document.createTextNode(' '));
                        td_datebuilt.append(
                            "(" + build_summary.build_log_size + " bytes)");
                    }
                }
            }

            if (ui_changed) {
                var anim = Y.lp.anim.green_flash({node: tr_elem});
                anim.run();
            }
        });
    };

    module.parameterEvaluator = function(table_node) {
        var td_list = table_node.all('td.build_status');
        var pending = td_list.filter("." + module.pending_states.join(",."));
        if (pending.size() === 0) {
            return null;
        }

        var snap_build_ids = [];
        Y.each(pending, function(node) {
            var elem_id = node.ancestor().get('id');
            var snap_build_id = elem_id.replace('build-', '');
            snap_build_ids.push(snap_build_id);
        });

        return {snap_build_ids: snap_build_ids};
    };

    module.stopUpdatesCheck = function(table_node) {
        // Stop updating when there aren't any builds to update
        var td_list = table_node.all('td.build_status');
        var pending = td_list.filter("." + module.pending_states.join(",."));
        return (pending.size() === 0);
    };

    module.config = {
        uri: null,
        api_method_name: 'getBuildSummariesForSnapBuildIds',
        lp_client: null,
        domUpdateFunction: module.domUpdate,
        parameterEvaluatorFunction: module.parameterEvaluator,
        stopUpdatesCheckFunction: module.stopUpdatesCheck
    };

    module.setup = function(node, uri) {
        module.config.uri = uri;
        node.plug(Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater,
                  module.config);
    };
}, "0.1", {"requires":["anim",
                       "node",
                       "lp.anim",
                       "lp.buildmaster.buildstatus",
                       "lp.soyuz.dynamic_dom_updater"]});
