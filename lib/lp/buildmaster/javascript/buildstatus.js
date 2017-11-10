/* Copyright 2017 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Build status handling.
 *
 * @module Y.lp.buildmaster.buildstatus
 */
YUI.add('lp.buildmaster.buildstatus', function(Y) {
    var module = Y.namespace('lp.buildmaster.buildstatus');

    // Keep this in sync with
    // lib/lp/app/browser/tales.py:BuildImageDisplayAPI.
    var icon_map = {
        NEEDSBUILD: { src: '/@@/build-needed' },
        FULLYBUILT: { src: '/@@/build-success' },
        FAILEDTOBUILD: {
            src: '/@@/build-failed',
            width: 16
        },
        MANUALDEPWAIT: { src: '/@@/build-depwait' },
        CHROOTWAIT: { src: '/@@/build-chrootwait' },
        SUPERSEDED: { src: '/@@/build-superseded' },
        BUILDING: { src: '/@@/processing' },
        FAILEDTOUPLOAD: { src: '/@@/build-failedtoupload' },
        UPLOADING: { src: '/@@/processing' },
        CANCELLING: { src: '/@@/processing' },
        CANCELLED: { src: '/@@/build-failed' }
    };

    module.update_build_status = function(node, build_summary) {
        var link_node = node.one('a');
        var img_node = node.one('img');

        if (link_node === null || img_node === null) {
            return false;
        }

        if (node.hasClass(build_summary.status)) {
            return false;
        }
        if (!(build_summary.status in icon_map)) {
            return false;
        }
        icon_props = icon_map[build_summary.status];

        node.setAttribute('class', 'build_status');
        node.addClass(build_summary.status);
        link_node.set('innerHTML', build_summary.buildstate);
        img_node.setAttribute('alt', '[' + build_summary.status + ']');
        img_node.setAttribute('title', build_summary.buildstate);
        img_node.setAttribute('src', icon_props.src);
        img_node.setAttribute('width', icon_props.width || 14);
    };
}, '0.1', {'requires': []});
