/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Control enabling/disabling of complex form on the
 * productseries/+setbranch page.
 *
 * @module Y.registry.productseries_setbranch
 * @requires node
 */
YUI.add('registry.productseries_setbranch', function(Y) {
    Y.log('loading registry.productseries_setbranch');
    var module = Y.namespace('registry.productseries_setbranch');

    module._getRcsType = function() {
       var rcs_types = module._rcs_types();
       var rcs_type = 'None';
       for (var i = 0; i < rcs_types.length; i++) {
          if (rcs_types[i].checked) {
             rcs_type = rcs_types[i].value;
             break;
          }
       }
       return rcs_type;
    };


    module.__rcs_types = null;

    module._rcs_types = function() {
       if (module.__rcs_types === null) {
          //module.__rcs_types = document.getElementsByName('field.rcs_type');
          module.__rcs_types = Y.get('*[name="field.rcs_type"]');
       }
       return module.__rcs_types;
    };

    module.setEnabled = function(field_id, is_enabled) {
       var field = Y.DOM.byId(field_id);
       field.disabled = !is_enabled;
    };

    module.updateWidgets = function() {
       /* Which rcs type radio button has been selected? */
       // CVS
       var rcs_types = module._rcs_types();
       var rcs_type = module._getRcsType();
       module.setEnabled('field.cvs_module', rcs_type == 'CVS');
    };

    module.updateBranchType = function() {
       /* Which branch type radio button was selected? */
       var rcs_types = module._rcs_types();
       var rcs_type = module._getRcsType();
       var types = document.getElementsByName('field.branch_type');
       var type = 'None';
       var i;
       for (i = 0; i < types.length; i++) {
          if (types[i].checked) {
             type = types[i].value;
             break;
          }
       }
       // Linked
       module.setEnabled('field.branch_location', type == 'link-lp-bzr');
       // New, empty branch -- do nothing
       // Import
       var is_external = (type == 'import-external');
       module.setEnabled('field.repo_url', is_external);
       module.setEnabled('field.cvs_module',
                   (is_external & rcs_type == 'CVS'));
       for (i = 0; i < rcs_types.length; i++) {
          rcs_types[i].set('disabled', !is_external);
       }
    };


    Y.on('domready', function() {
       var branch_types = document.getElementsByName('field.branch_type');
       var i;
       for (i = 0; i < branch_types.length; i++) {
          branch_types[i].onclick = module.updateBranchType;
       }
       var rcs_types = document.getElementsByName('field.rcs_type');
       for (i = 0; i < rcs_types.length; i++) {
          rcs_types[i].onclick = module.updateWidgets;
       }
       // Set the initial state.
       module.updateWidgets();
       module.updateBranchType();
    });

   }, "0.1", {"requires": ["node", "DOM"]}
);
