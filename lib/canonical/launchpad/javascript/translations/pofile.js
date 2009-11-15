/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module lp.pofile
 * @requires event, node
 */

YUI.add('lp.pofile', function(Y) {

Y.log('loading lp.pofile');
var self = Y.namespace('lp.pofile');

/**
 * Function to disable/enable all suggestions as they are marked/unmarked
 * for dismission.
 */
self.setupSuggestionDismissal = function(e) {
    Y.all('.dismiss_action').each(function(checkbox) {
        var classbase = checkbox.get('id');
        var current_class = classbase.replace(/dismiss/, 'current');
        var current_radios = Y.all('.' + current_class);
        var dismissables = Y.all('.' + classbase+'able');
        // The button and textarea cannot be fetched beforehand
        // because they are or may be created dynamically.
        var dismissable_inputs_class = [
            '.', classbase, 'able_button input, ',
            '.', classbase, 'able_button button, ',
            '.', classbase, 'able_button textarea'].join("")
        checkbox.on('click', function(e) {
              if(checkbox.get('checked')) {
                  dismissables.addClass('dismissed');
                  Y.all(dismissable_inputs_class).set('disabled', true);
                  current_radios.set('checked', true);
              } else {
                  dismissables.removeClass('dismissed');
                  Y.all(dismissable_inputs_class).set('disabled', false);
              }
          });
      });
  };

}, '0.1', {
    requires: ['event', 'node']});
