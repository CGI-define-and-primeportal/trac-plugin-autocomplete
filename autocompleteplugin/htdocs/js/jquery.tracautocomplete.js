/*
#
# Copyright (c) 2010, Logica
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
*/
jQuery.fn.makeAutocompleteSearch = function(method, options) {
  method = method || 'select';
  if (method == 'text') {
    return this.each(function(){
        options = $.extend({
          // Default option values
          // Button with label and attributes
          button: {text:'Add', attr:{}},
          // Delimeter expected
          delimiter: /\s*(?:\s|[,;])\s*/,
          // Autocomplete source
          source: function(request, response) {
            var matches = [];
            $.each(project_users, function(groupName) {
              $.each(project_users[groupName], function(i, user) {
                var s = user.sid.toLowerCase() + user.email.toLowerCase() + user.name.toLowerCase();
                if (s.indexOf(request.term.toLowerCase()) != -1) {
                  var label = user.name || user.sid;
                  if (user.email) {
                    label += $.format(' <$1>', user.email);
                  }
                  matches.push({label: label, value: user.sid});
                }
              });
            });
            response(matches);
          },
          // Autocomplete search
          search: function() {
            // custom minLength
            var term = this.value;
            if (term.length < 2) {
              return false;
            }
            return true;
          },
          // Autocomplete focus
          // http://jqueryui.com/demos/autocomplete/#event-focus
          focus: function() {
            // prevent value inserted on focus
            return false;
          },
          // Autocomplete select
          // http://jqueryui.com/demos/autocomplete/#event-select
          select: function(event, ui) {
            entry.data('addEntry')(ui.item.value);
            return false;
          }
        }, options);
        var infield = $(this);
        var id = infield.attr('id');
        var name = infield.attr('name');
        function split(val) {
          return $.grep(val.split(options.delimiter), function(i) { return i && true });
        }
        var entries = split(infield.val());
        // Rename and empty the input so it won't be post:ed
        infield.attr({id: id + '-input', name: name +'-input'}).val('');
        // For jquery validator
        infield.addClass('text-autocomplete') // Marker for validate plugin (not currently used)
        infield.after(
          $('<button>').attr(options.button.attr)
                       .text(options.button.text)
                       .click(function(e) {
                         $('#' + id).data('addEntry')(infield.val());
                         return false;
                       })
        );
        infield.keyup(function(e) {
          // Add keyword on enter-key
          if (e.which == 13) {
            $('#' + id).data('addEntry')(infield.val());
          }
        })
        // Create a hidden input with the value
        var entry = $($.format('<input type="hidden" id="$1" name="$2">', id, name)).val(entries.join(', '));
        // Move jquery.validate "required" marker to the hidden value field if applicable
        if (infield.hasClass('required')) {
          infield.removeClass('required')
          entry.addClass('required')
        }
        // Holder for the removal buttons
        var boxHolder = $('<div>').addClass(id + '-buttons');
        entry.data('updateBoxes', function() {
          boxHolder.empty();
          $.each(entries, function(idx, val) {
            boxHolder.append(
              $('<button>').text(val)
            );
          });
          $('.' + id + '-buttons button')
              .attr('title', 'Click to remove')
//              .button()
              .css('float','left').css('margin','2px')
              .click(function(e) {
                entry.data('removeEntry')($(this).text());
                return false;
              });
        });
        entry.data('addEntry', function(val) {
          var values = split(val)
          $(values).each(function(i, v){
            if (v && $.inArray(v, entries) == -1) {
              // Don't add dups
              entries.push(v);
              infield.val('');
              entry.val(entries.join(', '));
              entry.data('updateBoxes')();
            }
          })
        });
        entry.data('removeEntry', function(val) {
          entries = $.grep(entries, function(e, i) { return e != val });
          entry.val(entries.join(', '));
          entry.data('updateBoxes')();
        });
        infield.parent().append(entry).append(boxHolder);
        entry.data('updateBoxes')();
        infield.autocomplete({
          source: options.source,
          search: options.search,
          focus: options.focus,
          select: options.select
        });
      });
      return infield;
  } else {
    // Handle 'select' case (default)
    return this.each(function(){
      // Merge default settings with options
      var settings = $.extend({
        minLength: 3,
        delay: 500,
        source: function(request, response) {
          $.ajax({
            url: settings.url,
            data: {q: request.term, limit: 20},
            success: function(data) {
              // Map the response to the autocomplete dropdown
              response($.map(data, function(row) {
                return {data: row, value: row.sid,
                  label: $.format('$1 <$2>', row.name, row.email)};
              }));
            }
          });
        }
      }, options);

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
      selectfield.attr('disabled',$(infield).attr('disabled'));
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
          if (option.value == currentvalue)
            option.selected = true;
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
      option.appendChild(document.createTextNode("Type username..."));
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
          settings.url = url;
          inputfield.autocomplete(settings);
          searchnote = $("<div class='searchnote'>").text("Searching " + searchname);
        }
        var cancel = $('<img class="cancelsearch" alt="cancel" title="Cancel Search"/>');
        cancel.attr('src',autocomplete_cancel_image_url);
        cancel.click(function() {
          cancel.remove();
          searchnote.remove();
          inputfield.makeAutocompleteSearch();
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

/* Local Variables:   */
/* js-indent-level: 2 */
/* End:               */
