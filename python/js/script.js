// When the user scrolls the page, execute myFunction 
window.onscroll = function() {myFunction()};

function myFunction() {
  var winScroll = document.body.scrollTop || document.documentElement.scrollTop;
  var height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  var scrolled = (winScroll / height) * 100;
  document.getElementById("myBar").style.width = scrolled + "%";
}


//Scrolls to the bottom of the page when the page loads
function updateScroll(){
    var element = document.getElementById("message-box");
    element.scrollTop = element.scrollHeight;
}


var time = new Date().getTime();
$(document.body).bind("mousemove keypress", function(e) {
	time = new Date().getTime();
});

function insertEmoji(emoji){
	document.getElementById("input-box").value += emoji;
}

function refresh() {
	if(new Date().getTime() - time >= 10000) 
		window.location.reload(true);
	else 
		setTimeout(refresh, 10000);
}

setTimeout(refresh, 10000);