/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling of complex form on the
 * productseries/+setbranch page.
 *
 * @module Y.lp.code.productseries_setbranch
 * @requires node, DOM
 */
YUI.add('lp.code.productseries_setbranch', function(Y) {
    Y.log('loading lp.code.productseries_setbranch');
    var module = Y.namespace('lp.code.productseries_setbranch');

    module._get_selected_rcs = function() {
        var rcs_types = module._rcs_types();
        var selected = 'None';
        var i;
        for (i = 0; i < rcs_types.length; i++) {
            if (rcs_types[i].checked) {
                selected = rcs_types[i].value;
                break;
            }
        }
        return selected;
    };

    module._get_selected_default_vcs = function () {
        var vcs = document.getElementsByName('field.default_vcs');
        var i;
        for (i = 0; i < vcs.length; i++) {
            if (vcs[i].checked) {
                return vcs[i].value;
            } 
        }
        return null;
    };


    module.__rcs_types = null;

    module._rcs_types = function() {
        if (module.__rcs_types === null) {
            module.__rcs_types = document.getElementsByName('field.rcs_type');
        }
        return module.__rcs_types;
    };

    module.set_enabled = function(field_id, is_enabled) {
        var field = Y.DOM.byId(field_id);
        field.disabled = !is_enabled;
    };

    module.setup_expanders = function() {
        var git_expander = new Y.lp.app.widgets.expander.Expander(
            Y.one('#git-expander-icon'), Y.one('#git-expander-content')
        );

        var bzr_expander = new Y.lp.app.widgets.expander.Expander(
            Y.one('#bzr-expander-icon'), Y.one('#bzr-expander-content')
        );
        module.git_expander = git_expander.setUp();
        module.bzr_expander = bzr_expander.setUp();
    };

    module.onclick_default_vcs = function(e) {
        /* Which project vcs was selected? */
        var selectedDefaultVCS =
                module._get_selected_default_vcs();

        if (selectedDefaultVCS === 'GIT') {
            module.git_expander.render(true);
            module.bzr_expander.render(false);
        } else {
            module.bzr_expander.render(true);
            module.git_expander.render(false);
        }
    };

    module.onclick_rcs_type = function(e) {
        /* Which rcs type radio button has been selected? */
        // CVS
        var selectedRCS = module._get_selected_rcs();
        module.set_enabled('field.cvs_module', selectedRCS === 'CVS');
    };

    module.onclick_branch_type = function(e) {
        /* Which branch type radio button was selected? */
        var selectedRCS = module._get_selected_rcs();
        var type_node = Y.one('input[name="field.branch_type"]:checked');
        var type = (type_node === null) ? 'None' : type_node.get('value');
        // Linked
        module.set_enabled('field.branch_location', type === 'link-lp');
        module.set_enabled('field.branch_name', type !== 'link-lp');
        module.set_enabled('field.branch_owner', type !== 'link-lp');
        // Import
        var is_external = (type === 'import-external');
        module.set_enabled('field.repo_url', is_external);
        module.set_enabled('field.cvs_module',
                           (is_external & selectedRCS === 'CVS'));
        var rcs_types = module._rcs_types();
        var i;
        for (i = 0; i < rcs_types.length; i++) {
            rcs_types[i].disabled = !is_external;
        }
    };

    module.onclick_git_repository_type = function(e) {
        /* Which Git repository type radio button was selected? */
        var type_node = Y.one(
            'input[name="field.git_repository_type"]:checked');
        var type = (type_node === null) ? 'None' : type_node.get('value');
        // Linked
        module.set_enabled(
            'field.git_repository_location', type === 'link-lp');
        module.set_enabled('field.git_repository_name', type !== 'link-lp');
        module.set_enabled('field.git_repository_owner', type !== 'link-lp');
        // Import
        var is_external = (type === 'import-external');
        module.set_enabled('field.git_repository_url', is_external);
    };

    module.setup = function() {
        Y.all('input[name="field.rcs_type"]').on(
            'click', module.onclick_rcs_type);
        Y.all('input[name="field.branch_type"]').on(
            'click', module.onclick_branch_type);
        Y.all('input[name="field.default_vcs"]').on(
            'click', module.onclick_default_vcs);
        Y.all('input[name="field.git_repository_type"]').on(
            'click', module.onclick_git_repository_type);

        // Set the initial state.
        module.onclick_rcs_type();
        module.onclick_branch_type();
        // Only setup handlers for +configure-code
        if (document.getElementById('default_vcs')) {
            module.setup_expanders();
            module.onclick_default_vcs();
            module.onclick_git_repository_type();
        }
    };

}, "0.1", {"requires": ["node", "DOM"]});
