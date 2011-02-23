/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Update the recipe page on context updates.
 *
 * @module Y.lp.code.sourcepackagerecipe.index
 */
YUI.add('lp.code.sourcepackagerecipe.index', function(Y) {

    var module = Y.namespace('lp.code.sourcepackagerecipe.index');

    function recipe_changed(fields_changed, entry) {
      if (Y.Array.indexOf(fields_changed, "deb_version_template") >= 0) {
        Y.lp.ui.update_field(
          '#debian-version dd', entry.get('deb_version_template'));
      }
      if (Y.Array.indexOf(fields_changed, "base_branch_link") >= 0) {
        Y.lp.ui.update_field(
          '#base-branch dd', entry.getHTML('base_branch_link'));
      }
    }

    module.setup = function() {
      Y.on('lp:context:changed', recipe_changed);
    };

  }, "0.1", {"requires": ["lp.ui"]}
);
