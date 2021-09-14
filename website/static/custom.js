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

function sleep(milliseconds) {
	const date = Date.now();
	let currentDate = null;

	do {
		currentDate = Date.now();
	} while (currentDate - date < milliseconds);
}

$(window).on('load', function() {
	const obj = $('#get_all');
	const action = obj.attr('action');

	obj.submit(function( event ) {
		event.preventDefault();

		$.ajax({
			url: action,
			context: document.body,
			method: 'POST'
		}).done(function(result) {
			$.each(result['posts'], function( index, value ) {
				console.log('Downloading: ' + value);

				window.open(value);
			});
		});
	});
});
