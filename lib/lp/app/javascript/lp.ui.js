/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Launchpad helper methods for generic UI stuff.
 *
 * @module Y.lp.ui
 */
YUI.add('lp.ui', function(Y) {

    var module = Y.namespace('lp.ui');

    module.update_field = function(selector, content)
    {
      var element = Y.one(selector);
      element.set('innerHTML', content);
      Y.lazr.anim.green_flash({node:element}).run();
    }

  }, "0.1", {"requires": ["node", "lazr.anim"]}
);
