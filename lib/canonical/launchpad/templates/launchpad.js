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
        icon.setAttribute('src','/++resource++treeExpanded.gif')
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
            icon.setAttribute('src','/++resource++treeCollapsed.gif')
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

       
    if( icon.getAttribute('src').indexOf('/++resource++treeCollapsed.gif')!= -1 ){
        // that was an ugly check, but IE rewrites image sources to absolute urls from some sick reason....
        icon.setAttribute('src','/++resource++treeExpanded.gif')
        legend.parentNode.lastChild.style.display = 'block'
        legend.parentNode.childNodes[1].style.display = 'none'

    }else{
        icon.setAttribute('src','/++resource++treeCollapsed.gif')
        legend.parentNode.lastChild.style.display = 'none'
        legend.parentNode.childNodes[1].style.display = 'block'
        }
    }


// Add/remove items between selection lists by double clicking:

function addSelectedKeywords(fromlist,tolist) 
	{
	predefSubjects=document.getElementById(fromlist);
	for (var x=0; x < predefSubjects.length; x++) 
		{
		if (predefSubjects[x].selected) 
			{
			addNewKeyword(tolist, predefSubjects[x].text);
			}
		}
	}

function addNewKeyword(tolist, newWord)
	{
	selSubjects=document.getElementById(tolist);
	for (var x=0; x < selSubjects.length; x++) 
		{
		if (selSubjects[x].text == newWord) 
			{
			return false;
			}
		}
	ssl = selSubjects.length	
	selSubjects[ssl] = new Option(newWord)   
	}
	 
function selectAllWords()
    {
    var keyword = document.getElementsByTagName('select')
    
    for (var i=0; i < keyword.length; i++)
        {if (keyword[i].multiple)
            {
    	        for (var x=0; x < keyword[i].options.length; x++) 
    		    {
                keyword[i].options[x].selected = true
        	    }
            }
         }
    }

function removeWords(thelist)
	{
	selSubjects=document.getElementById(thelist);
    
	for (var x=selSubjects.length-1; x >= 0 ; x--) 
		{
		if (selSubjects[x].selected) 
			{
			selSubjects[x] = null;
			}
		}
	
	}

// Focus on error or tabindex=1 
function setFocus() {
    var xre = new RegExp(/\berror\b/);
    // Search only forms to avoid spending time on regular text
    for (var f = 0; (formnode = document.getElementsByTagName('form').item(f)); f++) {
        // Search for errors first, focus on first error if found
        for (var i = 0; (node = formnode.getElementsByTagName('div').item(i)); i++) {
            if (xre.exec(node.className)) {
                for (var j = 0; (inputnode = node.getElementsByTagName('input').item(j)); j++) {
                    inputnode.focus();
                    return;   
                }
            }
        }
        // If no error, focus on input element with tabindex 1
        
        
        for (var i = 0; (node = formnode.getElementsByTagName('input').item(i)); i++) {
           if (node.getAttribute('tabindex') == 1) {
               node.focus();
                return;   
           }
        }
    }
}

registerLaunchpadFunction(setFocus)

function popup_window(url, width, height) {
    LaunchpadPopupWindow = window.open(url, 'LaunchpadPopupWindow',
        'scrollbars=yes,resizable=yes,toolbar=no,height='
        +height+',width='+width);
}

// from richard braine for the source import forms
function morf(x){
      //    morf morphs form. it takes a radio choice as argument
      //    and shows and hides given divs as a result
      function showdiv(){
          for(i=0; i<arguments.length; i++){
              //document.all[arguments[i]].style.visibility='visible'
              document.getElementById(arguments[i]).style.visibility='visible'
          }
      }
      function hidediv(){
          for(i=0; i<arguments.length; i++){
              //document.all[arguments[i]].style.visibility='hidden'
              document.getElementById(arguments[i]).style.visibility='hidden'
          }
      }
  switch(true){
      case x=='cvs':
          showdiv('cvsdetails')
          hidediv('svndetails')
          break
      case x=='svn':
          showdiv('svndetails')
          hidediv('cvsdetails')
          break
   //   case x=='arch':
   //       showdiv('archdetails')
   //       hidediv('cvsdetails', 'svndetails')
   //       break
  }
}
