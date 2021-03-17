$( ".datetime" ).each(function( index ) {
	// Get the current value of the tag
	const t = $(this).text();

	// Make a moment object
	m = moment.utc(t);

	// Use the moment object as the new value
	$(this).text(m.fromNow());

	// Set the old value as a tooltip
	$(this).prop('title', t);
});