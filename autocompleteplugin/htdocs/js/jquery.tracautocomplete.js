jQuery.fn.makeTracUserSearch = function(method, options) {
  method = method || 'select'
  if (method == 'text') {
    return this.each(function(){
        options = options || {
            addButtonLabel: 'Add cc',
            group: 1, // 0: project members, 1: ppl who've accessed project
          }
        var infield = $(this)
        var id = infield.attr('id')
        var name = infield.attr('name')
        function split(val) {
          return $.grep(val.split(/,\s*/), function(i) { return i && true })
        }
        var entries = split(infield.val())
        // Rename and empty the input so it won't be post:ed
        infield.attr('id', id + '-input').attr('name', '').val('')
        infield.parent().append(
          $('<button>').text(options.addButtonLabel).button().click(
            function(e) {
              $('#' + id).data('addEntry')(infield.val())
              return false
            }
          )
        )
        // Create a hidden input with the value
        var entry = $('<input type="hidden">').attr('id', id).attr('name', name).val(entries.join(', '))
        // Holder for the removal buttons
        var boxHolder = $('<div>').addClass(id + '-buttons')
        entry.data('updateBoxes', function() {
          boxHolder.empty()
          $.each(entries, function(idx, val) {
            boxHolder.append(
              $('<button>').text(val)
            )
          })
          $('.' + id + '-buttons button')
              .attr('title', 'Click to remove')
              .button()
              .css('float','left').css('margin','2px')
              .click(function(e) { 
                entry.data('removeEntry')($(this).text())
                return false 
              })
        })
        entry.data('addEntry', function(val) {
          if (val && $.inArray(val, entries) == -1) {
            // Don't add dups
            entries.push(val)
            infield.val('')
            entry.val(entries.join(', '))
            entry.data('updateBoxes')()
          }
        })
        entry.data('removeEntry', function(val) {
          entries = $.grep(entries, function(e, i) { return e != val })
          entry.val(entries.join(', '))
          entry.data('updateBoxes')()
        })
        infield.parent().append(entry).append(boxHolder)
        entry.data('updateBoxes')()
        infield.autocomplete({
          source: function(request, response) {
            var matches = []
            $.each(project_users, function(groupName) {
              $.each(project_users[groupName], function(i, user) {
                if (!user) { return }
                var s = user.sid.toLowerCase() + user.email.toLowerCase() + user.name.toLowerCase()
                if (s.indexOf(request.term.toLowerCase()) != -1) {
                  matches.push({label:user.name, value:user.sid})
                }
              })
            })
            response(matches)
          },
          search: function() {
            // custom minLength
            var term = this.value
            if (term.length < 3) {
              return false
            }
          },
          focus: function() {
            // prevent value inserted on focus
            return false
          },
          select: function(event, ui) {
            entry.data('addEntry')(ui.item.value)
            return false
          }
        })
      })
      return infield
  } else {
    // Handle 'select' case (default)
    return this.each(function(){
      var settings = options || {minChars: 3,
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

      var infield = this;
      var id = infield.id;
      var name = infield.name;
      var size = infield.size;
      var klass = $(infield).attr('class');
      var width = $(infield).width();
      var selectfield = $("<select id='" + id + "' name='" + name + "' class='" + klass + "'/>");
      if (width > 0) {
        selectfield.attr('style','width: ' + width + 'px');
      }
      var currentvalue = $(infield).val();
      $(infield).replaceWith(selectfield);
      var optgroup;
      var option;
      var n;
      optgroup = $('<optgroup label="Current Value"></optgroup>');
      selectfield.append(optgroup);
      // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
      option = document.createElement('OPTION');
      option.value = currentvalue;
      option.appendChild(document.createTextNode(currentvalue));
      optgroup.append(option);
      optgroup = $('<optgroup label="Search"></optgroup>');
      selectfield.append(optgroup);
      for ( n in username_completers ) {
        // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
        option = document.createElement('OPTION');
        option.value = username_completers[n].url;
        option.appendChild(document.createTextNode(username_completers[n].name));
        optgroup.append(option);
      };
      for ( n in project_users ) {
        optgroup = $('<optgroup label="' + n + '"></optgroup>');
        selectfield.append(optgroup);
        for ( var u in project_users[n] ) {
          // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
          option = document.createElement('OPTION');
          option.value = project_users[n][u].sid;
          if (project_users[n][u].email)
            option.appendChild(document.createTextNode(project_users[n][u].name + " <" + project_users[n][u].email + ">"));
          else
            option.appendChild(document.createTextNode(project_users[n][u].name));
          optgroup.append(option);
        };
      };
      optgroup = $('<optgroup label="Manual Entry"></optgroup>');
      selectfield.append(optgroup);
      // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
      option = document.createElement('OPTION');
      option.value = "";
      option.appendChild(document.createTextNode("Type manually..."));
      optgroup.append(option);

      selectfield.change(function() {
        if (selectfield[0].selectedIndex == 0)
          return;
        if ((selectfield[0].selectedIndex > username_completers.length) &&
            (selectfield[0].selectedIndex != selectfield[0].options.length - 1))
          return;
        var url = selectfield.val();
        var searchname = selectfield.find("option:selected").text();
        var inputfield = $("<input type='text' id='" + id + "' name='" + name + "' class='" + klass + "'/>");
        if (size > 0) {
          inputfield[0].size = size;
        }
        selectfield.replaceWith(inputfield);
        var searchnote;
        if (url == '') {
          searchnote = $("<div class='searchnote'>").text("Manual entry...");
        } else {
          inputfield.autocomplete(url, settings);
          searchnote = $("<div class='searchnote'>").text("Searching " + searchname);
        }
        var cancel = $("<img class=\"cancelsearch\" src='/chrome/common/parent.png'/>");
        cancel.click(function() {
          cancel.remove();
          searchnote.remove();
          inputfield.makeTracUserSearch();
        });
        inputfield.keydown(function(e) {
          if (e.keyCode == 27) {
            cancel.click();
          }
        });
        inputfield.after(searchnote);
        inputfield.after(cancel);
        inputfield.focus();
      });
      return selectfield;
    });
  }
};

