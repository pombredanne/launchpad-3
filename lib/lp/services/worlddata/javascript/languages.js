/* Copyright 2009 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @module Languages
 * @requires oop, event, node
 */

YUI.add('languages', function(Y) {

var languages = Y.namespace('languages');

var hide_and_show = function(searchstring) {
    var all_languages = Y.all('#all-languages li');
    all_languages.each(function(element, index, list) {
        if(index < 10) {
            alert(element);
        }
    });
    
};


var init_filter_form = function() {
    var heading = Y.get('.searchform h2');
    heading.setContent('Filter languages in Launchpad');
    var button = Y.get('.searchform input.submit');
    button.set('value', 'Filter languages');
    button.on('click', function(e){
        e.preventDefault();
        hide_and_show('de');
    });
};


languages.initialize_languages_page = function(Y) {
    init_filter_form();

};


// "oop" and "event" are required to fix known bugs in YUI, which
// are apparently fixed in a later version.
}, "0.1", {"requires": ["oop", "event", "node"]});
