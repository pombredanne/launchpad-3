/* Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling form elements on the {Branch,GitRef}:+new-snap
 * and Snap:+edit pages.
 *
 * @module Y.lp.snappy.snap.edit
 * @requires node, DOM
 */
YUI.add('lp.snappy.snap.edit', function(Y) {
    Y.log('loading lp.snappy.snap.edit');
    var module = Y.namespace('lp.snappy.snap.edit');

    module.set_enabled = function(field_id, is_enabled) {
        var field = Y.DOM.byId(field_id);
        if (field !== null) {
            field.disabled = !is_enabled;
        }
    };

    module.onclick_vcs = function(e) {
        var selected_vcs = null;
        Y.all('input[name="field.vcs"]').each(function(node) {
            if (node.get('checked')) {
                selected_vcs = node.get('value');
            }
        });
        if (selected_vcs !== null) {
            module.set_enabled('field.branch', selected_vcs === 'BZR');
            module.set_enabled(
                'field.git_ref.repository', selected_vcs === 'GIT');
            module.set_enabled('field.git_ref.path', selected_vcs === 'GIT');
        }
    };

    module.onclick_auto_build = function(e) {
        var auto_build = Y.one(
            'input[name="field.auto_build"]').get('checked');
        module.set_enabled(
            'field.auto_build_archive.option.primary', auto_build);
        module.set_enabled('field.auto_build_archive.option.ppa', auto_build);
        module.set_enabled('field.auto_build_archive.ppa', auto_build);
        module.set_enabled('field.auto_build_pocket', auto_build);
    };

    module.setup = function() {
        Y.all('input[name="field.vcs"]').on('click', module.onclick_vcs);
        Y.all('input[name="field.auto_build"]').on(
            'click', module.onclick_auto_build);

        // Set the initial state.
        module.onclick_vcs();
        module.onclick_auto_build();
    };
}, '0.1', {'requires': ['node', 'DOM']});
