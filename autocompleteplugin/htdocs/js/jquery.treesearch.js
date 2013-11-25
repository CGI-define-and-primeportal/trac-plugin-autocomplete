
function treeSearch(settings)
{
	var x=null;
	$(settings.inputID).keyup(function(){
		if(x!=null) {
			clearTimeout(globalTimeout);            
		}
    x=setTimeout(defineTree(settings),0);
  });
}

// process tree
function defineTree(settings){
	var input_data = $(settings.inputID).val();
	// check if data starts with /
	if (!input_data.match('^/')){
			$(settings.root_id).hide();
			// display error
			console.log('error data');
			return false;
	}
	// check if data exists already
	$(settings.root_id).show();

	var prev_root = settings.root_id;
	var chk_data = $(settings.root_id).attr('id')+'-srch'+input_data.replace(/\//g,'-');
	console.log('chk-data',chk_data);
	var chk_id = $('#'+chk_data);

	// if data exist toggle child and set the node start
	if($(chk_id).length){
		console.log('data exists');
		settings.node_start = chk_id
		toggleChild(settings.node_start);
		//return false;
		}
	console.log('treeroot',settings.node_start);
	settings.data = data;
	res = createElement(settings);
	$(settings.node_start).html(res);
	
	// AJAX call 
	var ajx_resp = $.ajax({
                    url: settings.url,
                    type:'POST',
                    data:settings.data,
                    datatype:'json'
                    });

    ajx_resp.done(function(data){
      createElement(data,settings.node_start);
      });

    ajx_resp.fail(function(jqXHR,status){
      console.log('Request Failed:'+status);
      err_msg.html('Try again');
    });
    // scroll up the current element
	$(settings.root_id).animate({
				scrollTop: $(settings.node_start).offset().top
	}, 1000);
}

// show-hide children
function toggleChild(node){
	console.log('calling toggle',node);
	$(node).children('ul:first').toggleClass('collapse');
	var child = $(node).children('span:first');
	if (child.hasClass('fa-caret-right')){
		child.removeClass('fa-caret-right').addClass('fa-caret-down');
		return false;
	}
	else{
		child.removeClass('fa-caret-down').addClass('fa-caret-right');
		return false;
	}
}

// create ul elements
function createElement(args,prev_node='') {
	// clear html if root and div is same
	if(args.node_start == args.root_id){
		console.log('reset');
		$(args.root_id).html('');
	}
	var node_start = $(args.node_start);
	var ul = $('<ul>');
	var item = args.data; 
  // Make a <ul> to hold the current tree node's children (if any)
	$(node_start).append(ul);
	$.each(item,function(index,val){
    var li = $('<li>');
    cur_id = prev_node+ '-' + item[index].label; 
    $(li).attr({'id':$(args.root_id).attr('id')+'-srch-'+ cur_id.substr(1)});
    if(item[index].children.length > 0){
      $(li).append($('<span>').attr({'class':'expander fa fa-caret-right'}));
      $(li).append($('<span>').text(item[index].label).attr({'class':'expander fa fa-folder-o txt-data'}));       
      args={'node_start':li,'data':item[index].children,'root_id':args.root_id};
      createElement(args,cur_id);
    }
    else{
      $(li).append($('<span>').text(item[index].label).attr({'class':'expander fa fa-file-o txt-data'}));    
    }
    ul.append(li);
	});
}

//Populate text
$(document).on('click','span.txt-data',function(){
    var ele=$(this).parents('li').attr('id');
    var frmt_data = ele.split('-').slice(2);
    var txt='/'+frmt_data.join('/');
    console.log('data',txt);
    $('#txt-box').val(txt);
  });

// toggle arrow
$(document).on('click','span.fa-caret-right,span.fa-caret-down',function(){
	var node = $(this).parent('li');
	toggleChild(node);
  return false;
  });
