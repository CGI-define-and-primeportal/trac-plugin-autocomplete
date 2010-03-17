jQuery(document).ready(function($) {
			   $("#field-owner").autocomplete('/ajax/usersearch',
							  {'extraParams': {'domain':'project'},
							   'minChars': 3,
							   formatItem: function(data, value) {
							       return data[0] + "<br><em>"+ data[1] + " " + data[2] + "</em>";
							   }});
		       });