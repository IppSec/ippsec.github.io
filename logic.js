var searchResultFormat = '<tr><td>$machine</td><td>$line</td><td><a href="$link">YouTube</a></td></tr>';
var linkTemplate = 'https://youtube.com/watch?v=$video&start=$time';

var controls = {
	oldColor: '',
	displayResults: function(){
		$results.show();
	},
	hideResults: function(){
		$results.hide();
	},
	doSearch: function(match, dataset){
		results = [];

		regex = match.toLowerCase();
		dataset.forEach((e) => {
			if (e.line.toLowerCase().match(regex) || e.machine.toLowerCase().match(regex)) results.push(e);
		});
		return results;
	},
	updateResults: function($loc, results){
		if (results.length == 0) {
			$noResults.show();
			$noResults.text('No Results Found');
			$resultsTableHideable.hide();
		}
		else if (results.length > 150) {
			$noResults.show();
			$resultsTableHideable.hide();
			$noResults.text('Error: ' + results.length + ' results were found, try being more specific');
			this.setColor($colorUpdate, 'too-many-results');
		}
		else {
			$loc.empty();
			$noResults.hide();
			$resultsTableHideable.show();

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
	},
	setColor: function($loc, indicator){
		if (this.oldColor == indicator) return;
		var colorTestRegex = /^color-/i;

		$loc[0].classList.forEach((cls) => {
			//we cant use class so we use cls instead :>
			if (cls.match(colorTestRegex)) $loc.removeClass(cls);
		});
		$loc.addClass('color-' + indicator);
		if (this.oldColor != '') {
			var fc = 'color-fade-from-' + this.oldColor + '-to-' + indicator;
			$loc.addClass(fc);
		}
		this.oldColor = indicator;
	}
};
window.controls = controls;

$(document).ready(() => {
	$results = $('div#results');
	$query = $('#query');
	$searchValue = $('input#search').first();
	$form = $('form#searchForm');
	$resultsTableHideable = $('table#results');
	$resultsTable = $('tbody#results').first();
	$noResults = $('div.noResults');
	$colorUpdate = $('body');

	controls.setColor($colorUpdate, 'no-search');
	controls.hideResults();
	var currentSet = [];
	var oldSearchValue = '';

	function doSearch(event){
		var val = $searchValue.val();

		if (val != '') {
			controls.displayResults();
			if (val.length < oldSearchValue.length) currentSet = window.dataset;
			oldSearchValue = val;

			currentSet = window.controls.doSearch(val, currentSet);
			if (currentSet.length < 150)
				window.controls.setColor($colorUpdate, currentSet.length == 0 ? 'no-results' : 'results-found');

			window.controls.updateResults($resultsTable, currentSet);
		}
		else {
			controls.hideResults();
			window.controls.setColor($colorUpdate, 'no-search');
		}

		if (event.type == 'submit') event.preventDefault();
	}

	$.getJSON('./dataset.json', (data) => {
		window.dataset = data;
		currentSet = window.dataset;
		window.controls.updateResults($resultsTable, window.dataset);
		doSearch({ type: 'none' });
	});

	$form.submit(doSearch);

	$searchValue.on('input', doSearch);
});
