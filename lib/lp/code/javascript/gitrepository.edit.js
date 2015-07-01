/* Copyright 2015 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling form elements on the GitRepository:+edit page.
 *
 * @module Y.lp.code.gitrepository.edit
 * @requires node, DOM
 */
YUI.add('lp.code.gitrepository.edit', function(Y) {
    Y.log('loading lp.code.gitrepository.edit');
    var module = Y.namespace('lp.code.gitrepository.edit');

    module.set_enabled = function(field_id, is_enabled) {
        var field = Y.DOM.byId(field_id);
        field.disabled = !is_enabled;
    };

    module.onclick_target = function(e) {
        var value = false;
        Y.all('input[name="field.target"]').each(function(node) {
            if (node.get('checked'))
                value = node.get('value');
        });
        module.set_enabled('field.owner_default', value !== 'personal');
    };

    module.setup = function() {
        Y.all('input[name="field.target"]').on('click', module.onclick_target);
        Y.all('input[name="field.target.package"]').on(
            'keypress', function(e) {
                Y.DOM.byId('field.target.option.package', e).checked = true;
                module.set_enabled('field.owner_default', true);
            });
        Y.all('input[name="field.target.project"]').on(
            'keypress', function(e) {
                Y.DOM.byId('field.target.option.project', e).checked = true;
                module.set_enabled('field.owner_default', true);
            });

        // Set the initial state.
        module.onclick_target();
    };
}, '0.1', {'requires': ['node', 'DOM']});
