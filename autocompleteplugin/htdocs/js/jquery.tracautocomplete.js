/*
#
# Copyright (c) 2010, Logica
# Copyright (c) 2013, CGI
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

  /**
   * Produce modified autocomplete functionality in which buttons appear
   * representing the selected values (essentially tags)
   */
  if(method == 'text') {

    return this.each(function() {

      // Combine explictly set and default options
      var combinedOptions = $.extend({
        show_button: true,
        button: {
          text:'Add',
          attr:{
            'class':'btn btn-mini btn-primary margin-left'
          }
        },

        delimiter: /\s*(?:\s|[,;])\s*/,

        // Return all members matching a request
        source: function(request, response) {
          var matches = [],
              found_sids = [];
          $.each(window.project_users, function(groupName) {
            $.each(window.project_users[groupName]["members"], function(i, user) {
              var s = (user.sid + user.email + user.name).toLowerCase();
              if(s.indexOf(request.term.toLowerCase()) != -1) {
                var label = user.name || user.sid;
                if(user.email) {
                  label += $.format(' <$1>', user.email);
                }
                // Only add each member once, even if in multiple groups
                if($.inArray(user.sid, found_sids) < 0) {
                  matches.push({label: label, value: user.sid});
                  found_sids.push(user.sid);
                }
              }
            });
          });
          response(matches);
        },

        // Minimum query length required for search
        search: function() {
          return this.value.length > 1;
        },

        // Prevent value from being inserted on focus
        focus: function() {
          return false;
        },

        // When selecting a suggestion
        select: function(event, ui) {
          $proxy.val(ui.item.value);
          submit_entries();
          return false;
        }
      }, options);

      /**
       * Apply jQuery UI autocomplete functionality to a clone of the selected element
       * using the combined options above.
       */
      var $original    = $(this),
          $proxy       = $original.clone().insertAfter($original),
          $entriesBox  = $("<div class='autocomplete-entries cf'></div>").insertAfter($proxy),
          entries      = [];

      // Hide our original element
      // TODO actually change the type when IE8 support is dropped
      $original.addClass("hidden");

      // Assign our proxy a unique ID, remove it's name
      $proxy.attr({
        id: $original.attr("id") + "-input",
        name: ""
      });

      $entriesBox.attr("id", $original.attr("id") + "-entries");

      // Prevent our proxy from being validated
      $proxy.removeClass("required").addClass("text-autocomplete");

      // Populate our entries box with the default values
      submit_entries();

      // Instantiate the vanilla autocomplete functionality for the proxy
      $proxy.autocomplete({
        source: combinedOptions.source,
        search: combinedOptions.search,
        select: combinedOptions.select,
        focus:  combinedOptions.focus,
      });

      // If specified, add a button to our autocomplete
      if(combinedOptions.show_button) {
        var $btn = $("<button></button>");
        $btn.attr(combinedOptions.button.attr)
            .text(combinedOptions.button.text)
            .on("click", submit_entries)
            .insertAfter($proxy);
      }

      /**
       * Return all non-empty values split by a delimiter.
       * Whilst the default delimeter excepts whitespace, commas, and colons
       * the delimiter used in the final input is always a comma
       */
      function split_by_delimiter(val) {
        return $.map(val.split(combinedOptions.delimiter), function(x) { return x && $.trim(x) || null; });
      }

      /**
       * Get a users real name, falling back to their sid
       */
      function get_name(sid) {
        var name;
        $.each(window.project_users, function(groupName) {
          $.each(window.project_users[groupName]["members"], function(i, user) {
            if(user.sid == sid) {
              name = user.name || user.sid;
              return;
            }
          });
          if(name) return;
        });
        return name || sid;
      }

      /**
       * Split up the current value of the proxy, and add all entries
       */
      function submit_entries(e) {
        // Prevent the form from submitting from an entry key press
        if(e) e.preventDefault();

        var newEntries = split_by_delimiter($proxy.val()),
            newLength  = newEntries.length;

        for(var i = 0; i < newLength; i ++) add_entry(newEntries[i]);

        $proxy.val("");
      }

      /**
       * Add and remove entries
       * Entries are both stored in the original input, and represented by
       * buttons in the DOM which, when clicked, remove the entry.
       * The add and remove methods manipulate the entries array as well as the DOM
       * and then call the refresh method, which iterates over the entries, and
       * sets the original input's value as each of the entries joined by a comma
       */
      function add_entry(entry) {
        if($.inArray(entry, entries) == -1) {
          // Add button to represent entry in DOM
          var $entry = $("<button></button");
          $entry.text(get_name(entry))
                .data("value", entry)
                .appendTo($entriesBox);

          // Add entry to array
          entries.push(entry);
          refresh_entries();
        }
      }

      // Doesn't take any arguments as only ran when clicking a button
      function remove_entry() {
        var entry = $(this).data("value"),
            index = $.inArray(entry, entries);

        if(index != -1) {
          entries.splice(index, 1);
          $(this).remove();
          refresh_entries();
        }
      }

      function refresh_entries() {
        $original.val(entries.join(", "));
      }

      /**
       * Events
       */
      $proxy.on("keyup", function(e) {
        if(e.which == 13) submit_entries();
      });

      $entriesBox.on("click", "button", remove_entry);


    });
  }
  else {
    // Handle 'select' case (default)
    return this.each(function(){
      // Merge default settings with options
      settings = $.extend({
        minLength: 3,
        delay: 500,
        order: ["currentValue", "search", "groups", "manual"],
        source: function(request, response) {
          $.ajax({
            url: settings.url,
            data: {
              q: request.term, 
              limit: 20
            },
            success: function(data) {
              // Map the response to the autocomplete dropdown
              response($.map(data, function(row) {
                if(row.email) {
                  return {
                    data: row,
                    value: row.sid,
                    label: $.format('$1 <$2>', row.name, row.email)
                  };
                }
                else {
                  return {
                    data: row, 
                    value: row.sid,
                    label: $.format('$1', row.name)
                  };
                }
              }));
            }
          });
        }
      }, options);

      var infield = this,
          id = infield.id,
          name = infield.name,
          size = infield.size,
          klass = $(infield).attr('class'),
          width = $(infield).width(),
          selectfield = $("<select id='" + id + "' name='" + name + "' class='" + klass + "'/>"),
          currentvalue = $(infield).val();

      selectfield.attr('disabled',$(infield).attr('disabled'));
      $(infield).replaceWith(selectfield);
      var option;
      var n;

      function currentValueOptGroup() {
        var optgroup = $('<optgroup label="Current value"></optgroup>');
        // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
        option = document.createElement('OPTION');
        option.value = currentvalue;
        option.className = 'currentValue';
        option.appendChild(document.createTextNode(currentvalue));
        optgroup.append(option);
        return optgroup;
      }

      function searchOptGroup() {
        var optgroup = $('<optgroup label="Search"></optgroup>');
        for ( n in username_completers ) {
          // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
          option = document.createElement('OPTION');
          option.value = username_completers[n].url;
          option.className = 'search';
          option.appendChild(document.createTextNode(username_completers[n].name));
          optgroup.append(option);
        };
        return optgroup;
      }

      // Create an <optgroup> for the named group of users `n`
      function groupOptGroup(n) {
        var optgroup = $('<optgroup label="' + n + '"></optgroup>');
        // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
        option = document.createElement('OPTION');
        option.value = n;
        option.className = 'group';
        if (option.value == currentvalue) {
            option.selected = true;
        }
        option.appendChild(document.createTextNode("Set to group: " + window.project_users[n]['name']));
	optgroup.append(option);
        for (var u in window.project_users[n]["members"]) {
          // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
          option = document.createElement('OPTION');
          option.value = window.project_users[n]["members"][u].sid;
          option.className = 'group';
          if (option.value == currentvalue) {
            option.selected = true;
          }
          if (window.project_users[n]["members"][u].email) {
            option.appendChild(document.createTextNode(window.project_users[n]["members"][u].name + " <" + window.project_users[n]["members"][u].email + ">"));
          }
          else {
            option.appendChild(document.createTextNode(window.project_users[n]["members"][u].name));
          }
          optgroup.append(option);
        };
        return optgroup;
      }

      function groupsOptGroups() {
        var optgroups = [];
        for(n in window.project_users) {
          optgroups.push(groupOptGroup(n).get(0));
        }
        return optgroups;
      }

      function manualOptGroup(selectfield) {
        var optgroup = $('<optgroup label="Manual Entry"></optgroup>');
        // http://timplode.com/wp-content/uploads/2009/07/ie_test.html :-(
        option = document.createElement('OPTION');
        option.value = "";
        option.className = 'manual';
        option.appendChild(document.createTextNode("Type username..."));
        optgroup.append(option);
        return optgroup;
      }

      // Populate the select list
      var optGroups_fns = {
        currentValue: currentValueOptGroup,
        search: searchOptGroup,
        groups: groupsOptGroups,
        manual: manualOptGroup
      };

      for(var i = 0; i < settings.order.length; i++) {
        var fn = optGroups_fns[settings.order[i]];
        selectfield.append(fn());
      }

      selectfield.on("change", function() {
        var selected = selectfield.find('option:selected');
        if(selected.hasClass('currentValue')) {
          if($("#username")) {
            $("#username").text('');
          }
          return;
        }
        if(selected.hasClass('group')) {
          if($("#username")) {
            $("#username").text("Username:"+$(this).val());
          }
          return;
        }

        if($("#username")) {
          $("#username").text('');
        }

        var url = selectfield.val(),
            searchname = selected.text(),
            inputclasses = "",
            inputfield = $("<input type='text' id='" + id + "' name='" + name + "' class='" + klass + "'/>");

        if(size > 0) {
          inputfield[0].size = size;
        }

        selectfield.replaceWith(inputfield);
        var searchnote;

        if(url == '') {
          searchnote = $("<div class='annotation'>").html("Manual entry, type <code>domain\\username</code>...");
          inputfield.addClass("manual-entry")
        }
        else {
          settings.url = url;
          inputfield.removeClass("manual-entry").autocomplete(settings);
          searchnote = $("<div class='annotation'>").text("Searching " + searchname);
        }

        var cancel = $("<button class='btn btn-mini btn-primary margin-left' type='button' alt='Cancel' title='Close Manual Entry'><i class='icon-remove'></i></button>");
        cancel.tooltip({placement: "bottom"});
        cancel.on("click", function() {
          searchnote.remove();
          inputfield.makeAutocompleteSearch(method, settings);
          cancel.tooltip("destroy").remove();
        });

        inputfield.keydown(function(e) {
          if(e.keyCode == 27) {
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