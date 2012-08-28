/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Base functionality for displaying Information Type data.
 */

YUI.add('lp.app.information_type', function(Y) {

var namespace = Y.namespace('lp.app.information_type');

var get_information_type_banner_text = function(value) {
    var text_template = "This page contains {info_type} information.";
    var info_type = namespace.information_type_value_from_key(
            value, 'value', 'name');
    return Y.Lang.sub(text_template, {'info_type': info_type});
};

/**
 * Lookup the information_type property, keyed on the named value.
 *
 * @param cache_key_value the key value to lookup
 * @param key_property_name the key property name used to access the key value
 * @param value_property_name the value property name
 * @return {*}
 */
namespace.information_type_value_from_key = function(cache_key_value,
                                                     key_property_name,
                                                     value_property_name) {
    var data = null;
    Y.Array.some(LP.cache.information_type_data, function(info_type) {
        if (info_type[key_property_name] === cache_key_value) {
            data = info_type[value_property_name];
            return true;
        }
        return false;
    });
    return data;
};

/**
 * Update the privacy portlet to display the specified information type value.
 *
 * @param value
 */
namespace.update_privacy_portlet = function(value) {
    var description = namespace.information_type_value_from_key(
        value, 'value', 'description');
    var desc_node = Y.one('#information-type-description');
    if (Y.Lang.isValue(desc_node)) {
        desc_node.set('text', description);
    }
    var summary = Y.one('#information-type-summary');
    var private_type =
            Y.Array.indexOf(LP.cache.private_types, value) >= 0;
    if (private_type) {
        summary.replaceClass('public', 'private');
    } else {
        summary.replaceClass('private', 'public');
    }
};

/**
 * Update the privacy banner to display the specified information type value.
 *
 * @param value
 */
namespace.update_privacy_banner = function(value) {
    var body = Y.one('body');
    var privacy_banner = Y.lp.app.banner.privacy.getPrivacyBanner();
    var private_type =
            Y.Array.indexOf(LP.cache.private_types, value) >= 0;
    if (private_type) {
        body.replaceClass('public', 'private');
        var banner_text = get_information_type_banner_text(value);
        privacy_banner.updateText(banner_text);
        privacy_banner.show();
    } else {
        body.replaceClass('private', 'public');
        privacy_banner.hide();
    }
};

}, "0.1", {"requires": ["base", "oop", "node", "lp.app.banner.privacy"]});
