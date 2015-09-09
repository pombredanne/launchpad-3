/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling form elements on the Snap:+edit page.
 *
 * @module Y.lp.snappy.snap.edit
 * @requires node, DOM
 */
YUI.add('lp.snappy.snap.edit', function(Y) {
    Y.log('loading lp.snappy.snap.edit');
    var module = Y.namespace('lp.snappy.snap.edit');

    module.set_enabled = function(field_id, is_enabled) {
        var field = Y.DOM.byId(field_id);
        field.disabled = !is_enabled;
    };

    module.onclick_vcs = function(e) {
        var selected_vcs = null;
        Y.all('input[name="field.vcs"]').each(function(node) {
            if (node.get('checked')) {
                selected_vcs = node.get('value');
            }
        });
        module.set_enabled('field.branch', selected_vcs === 'BZR');
        module.set_enabled('field.git_ref.repository', selected_vcs === 'GIT');
        module.set_enabled('field.git_ref.path', selected_vcs === 'GIT');
    };

    module.setup = function() {
        Y.all('input[name="field.vcs"]').on('click', module.onclick_vcs);

        // Set the initial state.
        module.onclick_vcs();
    };
}, '0.1', {'requires': ['node', 'DOM']});
