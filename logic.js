var searchResultFormat = '<tr><td>$machine</td><td>$line</td><td><a href="$link">Open Link</a></td></tr>';
var linkTemplate = 'https://youtube.com/watch?v=$video&start=$time';

$(document).ready(() => {
	$results = $('div#results');
	$query = $('#query');
	$searchValue = $('input#search').first();
	$form = $('form#searchForm');
	$resultsTable = $('tbody#results').first();

	controls = {
		displayResults: function(){
			$query.hide();
			$results.show();
		},
		hideResults: function(){
			$results.hide();
			$query.show();
		},
		doSearch: function(match){
			results = [];
			regex = match.toLowerCase();
			window.dataset.forEach((e) => {
				if (e.line.toLowerCase().match(regex) || e.machine.toLowerCase().match(regex)) results.push(e);
			});
			return results;
		},
		updateResults: function($loc, results){
			$loc.empty();

			results.forEach((r) => {
				//Not the fastest but it makes for easier to read code :>

				timeInSeconds = r.timestamp.minutes * 60 + r.timestamp.seconds;
				el = searchResultFormat
					.replace('$machine', r.machine)
					.replace('$line', r.line)
					.replace('$link', linkTemplate.replace('$video', r.videoId).replace('$time', timeInSeconds));

				$loc.append(el);
			});
		}
	};
	window.controls = controls;

	$.getJSON('./dataset.json', (data) => {
		window.dataset = data;
		controls.updateResults($resultsTable, window.dataset);
	});

	$form.submit((event) => {
		controls.displayResults();
		//Dont send the form
		if ($resultsTable.children().length == 0) {
			val = $searchValue.val();
			found = controls.doSearch(val);
			controls.updateResults($resultsTable, found);
		}

		event.preventDefault();
	});

	$searchValue.on('input', function(){
		val = $searchValue.val();
		found = controls.doSearch(val);
		controls.updateResults($resultsTable, found);
	});
});
