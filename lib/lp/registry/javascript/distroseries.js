/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Distroseries related stuff.
 *
 * @module Y.lp.registry.distroseries
 * @requires node, DOM
 */
YUI.add('lp.registry.distroseries.initialize', function(Y) {
    Y.log('loading lp.registry.distroseries.initialize');
    var module = Y.namespace('lp.registry.distroseries.initialize');

    set_enabled = function(fields, is_enabled) {
       var buttons = document.getElementsByName(fields);
       for (var i = 0; i < buttons.length; i++) {
           buttons[i].disabled = !is_enabled;
       }
    };

    onclick_arch_type = function(e) {
       /* Which architecture initialization type radio button has been
        * selected? */
       var selected = document.getElementById(
          'field.all_architectures.0').checked;
       set_enabled('field.architectures', !selected);
    };

    onclick_packagesets_type = function(e) {
       /* Which packageset initialization type radio button has been
        * selected? */
       var selected = document.getElementById(
          'field.all_packagesets.0').checked;
       set_enabled('field.packagesets', !selected);
    };

    module.setup = function() {
       Y.all('input[name=field.all_architectures]').on(
          'click', onclick_arch_type);
       Y.all('input[name=field.all_packagesets]').on(
          'click', onclick_packagesets_type);
       // Set the initial state.
       onclick_arch_type();
       onclick_packagesets_type();
    };

   }, "0.1", {"requires": ["node", "dom"]}
);
