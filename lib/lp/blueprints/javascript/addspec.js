/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Provide functionality for the file bug pages.
 *
 * @module blueprints
 * @submodule addspec
 */
YUI.add('lp.blueprints.addspec', function(Y) {

var namespace = Y.namespace('lp.blueprints.addspec');
var to_choice = Y.lp.app.information_type.cache_to_choicesource;

namespace.set_up = function () {
    var choice_data = to_choice(LP.cache.information_type_data);
    Y.lp.app.choice.addPopupChoiceForRadioButtons('information_type',
                                                  choice_data);
};

}, "0.1", {"requires": ['lp.app.information_type', 'lp.app.choice']});
