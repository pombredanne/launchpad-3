////////// JS theme file for PopCalendarXP 9.0 /////////
// This file is totally configurable. You may remove all the comments in this file to minimize the download size.
// Since the plugins are loaded after theme config, sometimes we would redefine(override) some theme options there for convenience.
////////////////////////////////////////////////////////

// Fetch and eval datepicker.js so we start with is declared there
var request = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("MSXML2.XMLHTTP.3.0");

request.open("GET", 'datepicker.js', false);
request.send(null);
eval(request.responseText);

