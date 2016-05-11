/* Copyright 2016 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * The lp.snappy.snap.update_build_statuses module uses the
 * LP DynamicDomUpdater plugin for updating the latest builds table of a snap.
 *
 * @module Y.lp.snappy.snap.update_build_statuses
 * @requires anim, node, lp.anim, lp.client, lp.soyuz.dynamic_dom_updater
 */
YUI.add('lp.snappy.snap.update_build_statuses', function(Y) {
    Y.log('loading lp.snappy.snap.update_build_statuses');

    var lp_client = new Y.lp.client.Launchpad();
    var config = {

        uri: null,
        api_method_name: 'getBuildSummariesForSnapBuildIds',
        lp_client: lp_client,

        domUpdateFunction: function(table, data_object) {
            Y.each(data_object, function(build_summary, build_id) {
                var ui_changed = false;

                var tr_elem = Y.one("tr#build-" + build_id)
                if (tr_elem === null) {
                    return;
                }

                var td_build_status = tr_elem.one("td.build_status")
                var td_datebuilt = tr_elem.one("td.datebuilt")

                if (td_build_status === null || td_datebuilt === null) {
                    return;
                }

                var link_node = td_build_status.one("a")
                var img_node = td_build_status.one("img")

                if (link_node === null || img_node === null) {
                    return;
                }

                if (!td_build_status.hasClass(build_summary.status)) {
                    ui_changed = true
                    var new_src = null;
                    switch(build_summary.status) {
                    case 'BUILDING':
                    case 'UPLOADING':
                        new_src = '/@@/processing';
                        break;
                    case 'NEEDSBUILD':
                        new_src = '/@@/build-needed';
                        break;
                    case 'FAILEDTOBUILD':
                        new_src = '/@@/build-failed';
                        break;
                    case 'FULLYBUILT_PENDING':
                        new_src = '/@@/build-success-publishing';
                        break;
                    default:
                        new_src = '/@@/build-success';
                    }

                    td_build_status.setAttribute("class", "build_status");
                    td_build_status.addClass(build_summary.status);
                    link_node.set("innerHTML", build_summary.buildstate)
                    img_node.setAttribute("src", new_src);
                    img_node.setAttribute("title", build_summary.buildstate)
                    img_node.setAttribute("alt",
                                          "[" + build_summary.status + "]");
                }

                if (build_summary.when_complete !== null) {
                    ui_changed = true
                    td_datebuilt.set("innerHTML", build_summary.when_complete)
                    if (build_summary.when_complete_estimate) {
                        td_datebuilt.appendChild(
                            document.createTextNode(' (estimated)'));
                    }
                    if (build_summary.build_log_url !== null) {
                        var new_link = Y.Node.create(
                            '<a class="sprite download">buildlog</a>')
                        new_link.setAttribute(
                            'href', build_summary.build_log_url)
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
            })
        },

        parameterEvaluatorFunction: function(table_node){
            var td_list = table_node.all('td.build_status');
            var pending = td_list.filter(
                ".NEEDSBUILD, .BUILDING, .UPLOADING, .CANCELLING")
            if (pending.size() === 0) {
                return null;
            }

            var snap_build_ids = [];
            Y.each(pending, function(node){
                var elem_id = node.ancestor().get('id');
                var snap_build_id = elem_id.replace('build-', '');
                snap_build_ids.push(snap_build_id);
            });

            return {snap_build_ids: snap_build_ids};
        },

        stopUpdatesCheckFunction: function(table_node){
            // Stop updating when there aren't any builds to update
            var td_list = table_node.all('td.build_status');
            var pending = td_list.filter(
                ".NEEDSBUILD, .BUILDING, .UPLOADING, .CANCELLING")
            return (pending.size() === 0);
        }
    }

    Y.on("domready", function(){
        var table = Y.one('table#latest-builds-listing');
        if (table !== null) {
            config.uri = LP.cache.context.self_link
            table.plug(Y.lp.soyuz.dynamic_dom_updater.DynamicDomUpdater,
                       config);
        }
    });
}, "0.1", {"requires":["anim",
                       "node",
                       "lp.anim",
                       "lp.client",
                       "lp.soyuz.dynamic_dom_updater"]});
