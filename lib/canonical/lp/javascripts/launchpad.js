// Javascript code from Plone Solutions - http://www.plonesolutions.com, thanks! 

function registerLaunchpadFunction(func){
    // registers a function to fire onload. 
	// Turned out we kept doing this all the time
	// Use this for initilaizing any javascript that should fire once the page 
	// has been loaded. 
	// 
    if (window.addEventListener) window.addEventListener("load",func,false);
    else if (window.attachEvent) window.attachEvent("onload",func);   
  }

function getContentArea(){
	// to end all doubt on where the content sits. It also felt a bit silly doing 
	// this over and over in every
	// function, even if it is a tiny operation. Just guarding against someone 
	// changing the names again, in the name
	// of semantics or something.... ;)
	node =  document.getElementById('region-content')
	if (! node){
		node = document.getElementById('content')
		}
	return node
	}

function activateCollapsables(){
    // a script that searches for sections that can be (or are already) collapsed
    // - and enables the collapse-behavior      
    
    // usage : give the class "collapsible" to a fieldset
    // also , give it a <legend> with some descriptive text.
    // you can also add the class "collapsed" amounting to a total of <fieldset class="collapsible collapsed">
    // to make the section pre-collapsed 
    
    // terminate if we hit a non-compliant DOM implementation    
    if (! document.getElementsByTagName){return false};
    if (! document.getElementById){return false};
      
    // only search in the content-area
    contentarea = getContentArea()
    if (! contentarea){return false}
    
    // gather all objects that are to be collapsed
    // we only do fieldsets for now. perhaps DIVs later...
    collapsibles = contentarea.getElementsByTagName('fieldset');
      
    for (i=0; i < collapsibles.length; i++){    
        if (collapsibles[i].className.indexOf('collapsible')== -1 ){
            continue
            } 
        legends = collapsibles[i].getElementsByTagName('LEGEND')
        // get the legend
        // if there is no legend, we do not touch the fieldset at all. 
        // we assume that if there is a legend, there is only one. nothing else makes any sense
        if (! legends.length){continue}
        legend = legends[0]
        
        // add the icon/button with its functionality to the legend
        icon = document.createElement('img');
        icon.setAttribute('src','++resource++treeExpanded.gif')
        icon.setAttribute('class','collapseIcon')
        icon.setAttribute('heigth','9')
        icon.setAttribute('width','9')
        icon.style.marginRight='1em';
        
        //set up the legend to handle click-events
        if (window.addEventListener) legend.addEventListener("click",toggleCollapsible,false);
        else if (window.attachEvent) legend.attachEvent("onclick",toggleCollapsible);
        legend.style.cursor = 'pointer';
        
        
        // insert the icon icon at the start of the legend
        legend.insertBefore(icon,legend.firstChild)
        
        // wrap the contents inside a div to make turning them on and off simpler. 
        // unless something very strange happens, this new div should always be the last childnode
        // we'll give it a class to make sure.
                    
        hiderWrapper = document.createElement('div');
        hiderWrapper.setAttribute('class','collapseWrapper')
        
        // also add a new div describing that the element is collapsed.
        collapsedDescription = document.createElement('div');
        collapsedDescription.setAttribute('class','collapsedText') 
        collapsedDescription.style.display = 'none'
        
        // if the fieldset has the class of "collapsed", pre-collapse it. This can be used to preserve valuable UI-space 
        if (collapsibles[i].className.indexOf('collapsed')!= -1 ){
            icon.setAttribute('src','++resource++treeCollapsed.gif')
            collapsedDescription.style.display = 'block'
            hiderWrapper.style.display = 'none';
            }

        // now we have the wrapper div.. Stuff all the contents inside it
        nl = collapsibles[i].childNodes.length
        for (j=0; j < nl; j++){
            node = collapsibles[i].childNodes[0]
            if ( node.nodeName == 'LEGEND'){
                if (collapsibles[i].childNodes.length > 1 ){
                    hiderWrapper.appendChild(collapsibles[i].childNodes[1])
                    }
            }else{
                hiderWrapper.appendChild(collapsibles[i].childNodes[0])
                }
            }
        // and add it to the document
        collapsibles[i].appendChild(hiderWrapper)
        collapsibles[i].insertBefore(collapsedDescription, hiderWrapper) 
    }
}
registerLaunchpadFunction(activateCollapsables)   

function toggleCollapsible(e){
    
    // this is the function that collapses/expands fieldsets. 
    
    var node = window.event ? window.event.srcElement : e.currentTarget;
    
    // node should be the legend, but this can change later on. 
    
    if (node.nodeName == 'IMG'){
        node = node.parentNode
        }
    var icon = node.firstChild
    var legend = node

       
    if( icon.getAttribute('src').indexOf('++resource++treeCollapsed.gif')!= -1 ){
        // that was an ugly check, but IE rewrites image sources to absolute urls from some sick reason....
        icon.setAttribute('src','++resource++treeExpanded.gif')
        legend.parentNode.lastChild.style.display = 'block'
        legend.parentNode.childNodes[1].style.display = 'none'

    }else{
        icon.setAttribute('src','++resource++treeCollapsed.gif')
        legend.parentNode.lastChild.style.display = 'none'
        legend.parentNode.childNodes[1].style.display = 'block'
        }
    }

/********* Table sorter script *************/
// Table sorter script, thanks to Geir Bækholt for this.
// DOM table sorter originally made by Paul Sowden 

function compare(a,b)
{
    au = new String(a);
    bu = new String(b);

    if (au.charAt(4) != '-' && au.charAt(7) != '-')
    {
    var an = parseFloat(au)
    var bn = parseFloat(bu)
    }
    if (isNaN(an) || isNaN(bn))
        {as = au.toLowerCase()
         bs = bu.toLowerCase()
        if (as > bs)
            {return 1;}
        else
            {return -1;}
        }
    else {
    return an - bn;
    }
}



function getConcatenedTextContent(node) {
    var _result = "";
	  if (node == null) {
		    return _result;
	  }
    var childrens = node.childNodes;
    var i = 0;
    while (i < childrens.length) {
        var child = childrens.item(i);
        switch (child.nodeType) {
            case 1: // ELEMENT_NODE
            case 5: // ENTITY_REFERENCE_NODE
                _result += getConcatenedTextContent(child);
                break;
            case 3: // TEXT_NODE
            case 2: // ATTRIBUTE_NODE
            case 4: // CDATA_SECTION_NODE
                _result += child.nodeValue;
                break;
            case 6: // ENTITY_NODE
            case 7: // PROCESSING_INSTRUCTION_NODE
            case 8: // COMMENT_NODE
            case 9: // DOCUMENT_NODE
            case 10: // DOCUMENT_TYPE_NODE
            case 11: // DOCUMENT_FRAGMENT_NODE
            case 12: // NOTATION_NODE
                // skip
                break;
        }
        i ++;
    }
  	return _result;
}

function sort(e) {
    var el = window.event ? window.event.srcElement : e.currentTarget;

    // a pretty ugly sort function, but it works nonetheless
    var a = new Array();
    // check if the image or the th is clicked. Proceed to parent id it is the image
    // NOTE THAT nodeName IS UPPERCASE
    if (el.nodeName == 'IMG') el = el.parentNode;
    //var name = el.firstChild.nodeValue;
    // This is not very robust, it assumes there is an image as first node then text
    var name = el.childNodes.item(1).nodeValue;
    var dad = el.parentNode;
    var node;
    
    // kill all arrows
    for (var im = 0; (node = dad.getElementsByTagName("th").item(im)); im++) {
        // NOTE THAT nodeName IS IN UPPERCASE
        if (node.lastChild.nodeName == 'IMG')
        {
            lastindex = node.getElementsByTagName('img').length - 1;
            node.getElementsByTagName('img').item(lastindex).setAttribute('src', '/++resource++arrowBlank.gif');
        }
    }
    
    for (var i = 0; (node = dad.getElementsByTagName("th").item(i)); i++) {
        var xre = new RegExp(/\bnosort\b/);
        // Make sure we are not messing with nosortable columns, then check second node.
        if (!xre.exec(node.className) && node.childNodes.item(1).nodeValue == name) 
        {
            //window.alert(node.childNodes.item(1).nodeValue;
            lastindex = node.getElementsByTagName('img').length -1;
            node.getElementsByTagName('img').item(lastindex).setAttribute('src', '/++resource++arrowUp.gif');
            break;
        }
    }

    var tbody = dad.parentNode.parentNode.getElementsByTagName("tbody").item(0);
    for (var j = 0; (node = tbody.getElementsByTagName("tr").item(j)); j++) {

        // crude way to sort by surname and name after first choice
        a[j] = new Array();
        a[j][0] = getConcatenedTextContent(node.getElementsByTagName("td").item(i));
        a[j][1] = getConcatenedTextContent(node.getElementsByTagName("td").item(1));
        a[j][2] = getConcatenedTextContent(node.getElementsByTagName("td").item(0));		
        a[j][3] = node;
    }

    if (a.length > 1) {
	
        a.sort(compare);

        // not a perfect way to check, but hell, it suits me fine
        if (a[0][0] == getConcatenedTextContent(tbody.getElementsByTagName("tr").item(0).getElementsByTagName("td").item(i))
	       && a[1][0] == getConcatenedTextContent(tbody.getElementsByTagName("tr").item(1).getElementsByTagName("td").item(i))) 
        {
            a.reverse();
            lastindex = el.getElementsByTagName('img').length - 1;
            el.getElementsByTagName('img').item(lastindex).setAttribute('src', '/++resource++arrowDown.gif');
        }

    }
	
    for (var j = 0; j < a.length; j++) {
        tbody.appendChild(a[j][3]);
    }
}
    
function initalizeTableSort(e) {
    var tbls = document.getElementsByTagName('table');
    for (var t = 0; t < tbls.length; t++)
        {
        // elements of class="listing" can be sorted
        var re = new RegExp(/\blisting\b/)
        // elements of class="nosort" should not be sorted
        var xre = new RegExp(/\bnosort\b/)
        if (re.exec(tbls[t].className) && !xre.exec(tbls[t].className))
        {
            try {
                var tablename = tbls[t].getAttribute('id');
                var thead = document.getElementById(tablename).getElementsByTagName("thead").item(0);
                var node;
                // set up blank spaceholder gifs
                blankarrow = document.createElement('img');
                blankarrow.setAttribute('src', '/++resource++arrowBlank.gif');
                blankarrow.setAttribute('height',6);
                blankarrow.setAttribute('width',9);
                // the first sortable column should get an arrow initially.
                initialsort = false;
                for (var i = 0; (node = thead.getElementsByTagName("th").item(i)); i++) {
                    // check that the columns does not have class="nosort"
                    if (!xre.exec(node.className)) {
                        node.insertBefore(blankarrow.cloneNode(1), node.firstChild);
                        if (!initialsort) {
                            initialsort = true;
                            uparrow = document.createElement('img');
                            uparrow.setAttribute('src', '/++resource++arrowUp.gif');
                            uparrow.setAttribute('height',6);
                            uparrow.setAttribute('width',9);
                            node.appendChild(uparrow);
                        } else {
                            node.appendChild(blankarrow.cloneNode(1));
                        }
    
                        if (node.addEventListener) node.addEventListener("click",sort,false);
                        else if (node.attachEvent) node.attachEvent("onclick",sort);
                    }
                }
            } catch(er) {}
        }
    }
}   
// **** End table sort script ***
registerLaunchpadFunction(initalizeTableSort)   
