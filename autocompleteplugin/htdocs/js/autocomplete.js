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
	    var id = infield[0].id;
	    var selectfield = $("<select id='" + id + "'/>");
	    var currentvalue = infield.val();
	    infield.replaceWith(selectfield);
	    var optgroup;
	    optgroup = $('<optgroup label="Current Value"></optgroup>');
	    selectfield.append(optgroup);
	    optgroup.append(new Option(currentvalue,currentvalue));	
	    optgroup = $('<optgroup label="Search"></optgroup>');
	    selectfield.append(optgroup);
	    for ( var n in username_completers ) {
		optgroup.append(new Option(username_completers[n].name, username_completers[n].url));
	    };
	    optgroup = $('<optgroup label="Project Users"></optgroup>');
	    selectfield.append(optgroup);
	    for ( var n in project_users ) {
		optgroup.append(new Option(project_users[n].name, 
					   project_users[n].sid));
	    };
	    selectfield.change(function() {
			     if (selectfield[0].selectedIndex == 0)
				 return;
			     if (selectfield[0].selectedIndex > username_completers.length)
				 return;
			     var url = selectfield.val();
			     var searchname = selectfield.find("option:selected").text();
			     var inputfield = $("<input id='" + id + "'/>");
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
	
	$("#field-cc").parent().append('<ul id="field-cc-ul">');
	$("#field-cc").autocomplete('/ajax/usersearch/adfs', settings).result(
	    function(e, item) {
		$("#field-cc-ul").append("<li>" + item.name + "</li>");
		$("#field-cc").val('');	
	    });
    });
