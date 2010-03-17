jQuery(document).ready(function($) {
			   $("#field-owner").autocomplete('/ajax/usersearch',
							  {'extraParams': {'domain':'groupinfra'},
							   'minChars': 3,
							   'width': 300,
							   formatItem: function(data, value) {
							       return data[1] + "<br><em>"+ data[0] + " " + data[2] + "</em>";
							   }});
		       });