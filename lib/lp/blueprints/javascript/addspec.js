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

namespace.dom_ready = function(){
    var information_type_data = [{"description_css_class": "choice-description", "description": "Everyone can see this information.\n", "value": "PUBLIC", "name": "Public"}, {"description_css_class": "choice-description", "description": "Only shared with users permitted to see proprietary information.\n", "value": "PROPRIETARY", "name": "Proprietary"}, {"description_css_class": "choice-description", "description": "Only shared with users permitted to see embargoed information.\n", "value": "EMBARGOED", "name": "Embargoed"}]
    Y.lp.app.choice.addPopupChoiceForRadioButtons(
        'information_type', information_type_data, true);
};

}, "0.1", {"requires": []});
