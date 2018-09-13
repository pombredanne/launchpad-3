/* Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
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

    module.update_date_built = function(node, build_summary) {
        node.set("text", build_summary.when_complete);
        if (build_summary.when_complete_estimate) {
            node.appendChild(document.createTextNode(' (estimated)'));
        }
        if (build_summary.build_log_url !== null) {
            var new_link = Y.Node.create(
                '<a class="sprite download">buildlog</a>');
            new_link.setAttribute('href', build_summary.build_log_url);
            node.appendChild(document.createTextNode(' '));
            node.appendChild(new_link);
            if (build_summary.build_log_size !== null) {
                node.appendChild(document.createTextNode(' '));
                node.append("(" + build_summary.build_log_size + " bytes)");
            }
        }
    };

    module.domUpdate = function(table, data_object) {
        var tbody = table.one('tbody');
        if (tbody === null) {
            return;
        }
        var tbody_changed = false;

        Y.each(data_object['requests'], function(request_summary, request_id) {
            var tr_elem = tbody.one('tr#request-' + request_id);
            if (tr_elem === null) {
                return;
            }

            if (request_summary['status'] === 'FAILED') {
                // XXX cjwatson 2018-06-18: Maybe we should show the error
                // message in this case, but we don't show non-pending
                // requests in the non-JS case, so it's not clear where
                // would be appropriate.
                tr_elem.remove();
                tbody_changed = true;
                return;
            } else if (request_summary['status'] === 'COMPLETED') {
                // Insert rows for the new builds.
                Y.Array.each(request_summary['builds'],
                             function(build_summary) {
                    // Construct the new row.
                    var new_row = Y.Node.create(
                        '<tr>' +
                        '<td class="build_status"><img/><a/></td>' +
                        '<td class="datebuilt"/>' +
                        '<td><a class="sprite distribution"/></td>' +
                        '<td><span class="archive-placeholder"/></td>' +
                        '</tr>');
                    new_row.set('id', 'build-' + build_summary.id);
                    new_row.one('td.build_status a')
                        .set('href', build_summary.self_link);
                    Y.lp.buildmaster.buildstatus.update_build_status(
                        new_row.one('td.build_status'), build_summary);
                    if (build_summary.when_complete !== null) {
                        module.update_date_built(
                            new_row.one('td.datebuilt'), build_summary);
                    }
                    new_row.one('td a.distribution')
                        .set('href', build_summary.distro_arch_series_link)
                        .set('text', build_summary.architecture_tag);
                    new_row.one('td .archive-placeholder')
                        .replace(build_summary.archive_link);

                    // Insert the new row, maintaining descending-ID sorted
                    // order.
                    var tr_next = null;
                    tbody.get('children').some(function(tr) {
                        var tr_id = tr.get('id');
                        if (tr_id !== null &&
                                tr_id.substr(0, 6) === 'build-') {
                            var build_id = parseInt(
                                tr_id.replace('build-', ''), 10);
                            if (!isNaN(build_id) &&
                                    build_id < build_summary.id) {
                                tr_next = tr;
                                return true;
                            }
                        }
                        return false;
                    });
                    tbody.insert(new_row, tr_next);
                });

                // Remove the completed build request row.
                tr_elem.remove();
                tbody_changed = true;
                return;
            }
        });

        if (tbody_changed) {
            var anim = Y.lp.anim.green_flash({node: tbody});
            anim.run();
        }

        Y.each(data_object['builds'], function(build_summary, build_id) {
            var ui_changed = false;

            var tr_elem = tbody.one("tr#build-" + build_id);
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
                module.update_date_built(td_datebuilt, build_summary);
            }

            if (ui_changed) {
                var anim = Y.lp.anim.green_flash({node: tr_elem});
                anim.run();
            }
        });
    };

    module.parameterEvaluator = function(table_node) {
        var td_request_list = table_node.all('td.request_status');
        var pending_requests = td_request_list.filter('.PENDING');
        var td_build_list = table_node.all('td.build_status');
        var pending_builds = td_build_list.filter(
            "." + module.pending_states.join(",."));
        if (pending_requests.size() === 0 && pending_builds.size() === 0) {
            return null;
        }

        var request_ids = [];
        Y.each(pending_requests, function(node) {
            var elem_id = node.ancestor().get('id');
            var request_id = elem_id.replace('request-', '');
            request_ids.push(request_id);
        });

        var build_ids = [];
        Y.each(pending_builds, function(node) {
            var elem_id = node.ancestor().get('id');
            var build_id = elem_id.replace('build-', '');
            build_ids.push(build_id);
        });

        return {request_ids: request_ids, build_ids: build_ids};
    };

    module.stopUpdatesCheck = function(table_node) {
        // Stop updating when there aren't any build requests or builds to
        // update.
        var td_request_list = table_node.all('td.request_status');
        var pending_requests = td_request_list.filter('.PENDING');
        var td_build_list = table_node.all('td.build_status');
        var pending_builds = td_build_list.filter(
            "." + module.pending_states.join(",."));
        return pending_requests.size() === 0 && pending_builds.size() === 0;
    };

    module.config = {
        uri: null,
        api_method_name: 'getBuildSummaries',
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
