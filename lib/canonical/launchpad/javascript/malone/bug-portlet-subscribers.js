/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * Load the contents of the subscribers portlet of bugs after
 * the rest of the page is loaded.
 *
 * @requires io, node, LP
 */
YUI().use('io', 'node', 'LP', function(Y) {
  Y.on('contentready', function() {
    var portlet = Y.get('#portlet-subscribers');
    portlet.set('innerHTML',
      portlet.get('innerHTML') +
                  '<div id="subscribers-portlet-spinner"' +
                  '     style="text-align: center">' +
                  '<img src="/@@/spinner" /></div>');
  }, '#portlet-subscribers');

  Y.on('load', function() {
    var portlet = Y.get('#portlet-subscribers');

    function remove_spinner() {
      portlet.removeChild(Y.get('#subscribers-portlet-spinner'));
    }

    function on_success(transactionid, response, arguments) {
      remove_spinner();
      portlet.set('innerHTML',
                  portlet.get('innerHTML') + response.responseText);
    }

    var config = {on: {success: on_success,
                       failure: remove_spinner}};
    var url = LP.client.cache['context']['self_link'].replace('/api/beta', '') +
              '/+bug-portlet-subscribers-content';
    var request = Y.io(url, config);
  }, window);
});
