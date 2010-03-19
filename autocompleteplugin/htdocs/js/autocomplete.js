jQuery(document).ready(
    function($) {
	var settings = {minChars: 3,
					width: 500,
					dataType: "json",
					parse: function(data) {
					    return $.map(data, function(row) {
							     return {data: row,
								     value: row.sid,
								     result: row.sid};
							 });
					},
					formatItem: function(row) {
					    return "<span class=\"username\">" + row.name + "</span><br/>" + 
						"<span class=\"detail\">" + row.sid + " &lt;" + row.email + "&gt</span>";
					}
				       };
	
        var build_control = function(infield) {
	    if (infield.length == 0) return;
	    var id = infield[0].id;
	    var name = infield[0].name;
	    var size = infield[0].size;
	    var klass = infield.attr('class');
	    var width = infield.width();
	    var selectfield = $("<select id='" + id + "' name='" + name + "' class='" + klass + "'/>");
	    selectfield.attr('style','width: ' + width + 'px');
	    var currentvalue = infield.val();
	    infield.replaceWith(selectfield);
	    var optgroup;
	    optgroup = $('<optgroup label="Current Value"></optgroup>');
	    selectfield.append(optgroup);
	    // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
	    var option = document.createElement('OPTION');
	    option.value = currentvalue;
	    option.appendChild(document.createTextNode(currentvalue));
	    optgroup.append(option);
	    optgroup = $('<optgroup label="Search"></optgroup>');
	    selectfield.append(optgroup);
	    for ( var n in username_completers ) {
		// http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
		var option = document.createElement('OPTION');
		option.value = username_completers[n].url;
		option.appendChild(document.createTextNode(username_completers[n].name));
		optgroup.append(option);
	    };
	    optgroup = $('<optgroup label="Project Users"></optgroup>');
	    selectfield.append(optgroup);
	    for ( var n in project_users ) {
		// http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
		var option = document.createElement('OPTION');
		option.value = project_users[n].sid;
		option.appendChild(document.createTextNode(project_users[n].name));
		optgroup.append(option);
	    };
	    selectfield.change(function() {
			     if (selectfield[0].selectedIndex == 0)
				 return;
			     if (selectfield[0].selectedIndex > username_completers.length)
				 return;
			     var url = selectfield.val();
			     var searchname = selectfield.find("option:selected").text();
			     var inputfield = $("<input type='text' id='" + id + "' name='" + name + "' class='" + klass + "'/>");
			     if (size > 0) {
				 inputfield[0].size = size;
			     }
			     selectfield.replaceWith(inputfield);
			     inputfield.autocomplete(url, settings);
			     var searchnote = $("<div class='searchnote'>").text("Searching " + searchname);
			     var cancel = $("<img class=\"cancelsearch\" src='/chrome/common/parent.png'/>");
			     cancel.click(function() {
					      cancel.remove();
					      searchnote.remove();
					      build_control(inputfield);
					  });
			     inputfield.after(searchnote);
			     inputfield.after(cancel);
			     inputfield.focus();
			     
			 });
	};
	build_control($("#field-owner"));
	build_control($("#field-reporter"));
	build_control($("#action_reassign_reassign_owner"));
	
	$("#field-cc").parent().append('<ul id="field-cc-ul">');
	$("#field-cc").autocomplete('/ajax/usersearch/adfs', settings).result(
	    function(e, item) {
		$("#field-cc-ul").append("<li>" + item.name + "</li>");
		$("#field-cc").val('');	
	    });
    });
