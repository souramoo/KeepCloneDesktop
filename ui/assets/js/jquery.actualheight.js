jQuery(function( $ ){
  $.fn.actualHeight = function(){
        // find the closest visible parent and get it's hidden children
    var visibleParent = this.closest(':visible').children(),
        thisHeight;
    
    // set a temporary class on the hidden parent of the element
    visibleParent.addClass('temp-show');
    
    // get the height
    thisHeight = this.height();
    
    // remove the temporary class
    visibleParent.removeClass('temp-show');
    
    return thisHeight;
  };

  // get the hidden div's height and show what you got
  $('#height').text( $('.hidden').actualHeight() );

});
