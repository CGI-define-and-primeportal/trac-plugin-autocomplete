jQuery(document).ready(
    function($) {
	$("#field-owner").autocomplete('/ajax/usersearch',
				       {extraParams: {domain:'groupinfra'},
					minChars: 3,
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
				       });
    });
