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

    module._getSelectedRCS = function() {
       var rcs_types = module._rcs_types();
       var selected = 'None';
       for (var i = 0; i < rcs_types.length; i++) {
          if (rcs_types[i].checked) {
             selected = rcs_types[i].value;
             break;
          }
       }
       return selected;
    };


    module.__rcs_types = null;

    module._rcs_types = function() {
       if (module.__rcs_types === null) {
          module.__rcs_types = document.getElementsByName('field.rcs_type');
       }
       return module.__rcs_types;
    };

    module.setEnabled = function(field_id, is_enabled) {
       var field = Y.DOM.byId(field_id);
       field.disabled = !is_enabled;
    };

    module.onclickRcsType = function() {
       /* Which rcs type radio button has been selected? */
       // CVS
       var rcs_types = module._rcs_types();
       var selectedRCS = module._getSelectedRCS();
       module.setEnabled('field.cvs_module', selectedRCS == 'CVS');
    };

    module.onclickBranchType = function() {
       /* Which branch type radio button was selected? */
       var selectedRCS = module._getSelectedRCS();
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
                   (is_external & selectedRCS == 'CVS'));
       var rcs_types = module._rcs_types();
       for (j = 0; j < rcs_types.length; j++) {
          rcs_types[j].disabled = !is_external;
       }
    };


    Y.on('domready', function() {
       var branch_types = document.getElementsByName('field.branch_type');
       var i;
       for (i = 0; i < branch_types.length; i++) {
          branch_types[i].onclick = module.onclickBranchType;
       }
       var rcs_types = document.getElementsByName('field.rcs_type');
       var rcs_types = module._rcs_types();
       for (i = 0; i < rcs_types.length; i++) {
          rcs_types[i].onclick = module.onclickRcsType;
       }
       // Set the initial state.
       module.onclickRcsType();
       module.onclickBranchType();
    });

   }, "0.1", {"requires": ["node", "DOM"]}
);
