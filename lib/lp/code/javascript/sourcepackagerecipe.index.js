/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Update the recipe page on context updates.
 *
 * @module Y.lp.code.sourcepackagerecipe.index
 */
YUI.add('lp.code.sourcepackagerecipe.index', function(Y) {

    var module = Y.namespace('lp.code.sourcepackagerecipe.index');

    function update_deb_version(e) {
      Y.lp.ui.update_field('#debian-version dd', e.new_value);
    }

    function update_base_branch(e) {
      Y.lp.ui.update_field('#base-branch dd', e.entry.getHTML(e.name));
    }

    module.setup = function() {
      Y.on('lp:context:deb_version_template:changed', update_deb_version);
      Y.on('lp:context:base_branch_link:changed', update_base_branch);
    };

  }, "0.1", {"requires": ["lp.ui"]}
);
