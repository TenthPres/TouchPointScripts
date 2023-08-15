const gulp = require('gulp'),
	zip = require('gulp-zip');

function buildEverything(cb) {

	// Mapify Only
	gulp.src(['Mapify/*.py', "Mapify/keyword"])
		.pipe(zip('Mapify.zip'))
		.pipe(gulp.dest('.Builds'));

	// Tuition Only
	gulp.src(['TuitionAutomation/*.py', "TuitionAutomation/keyword", "TuitionAutomation/*.sql"])
		.pipe(zip('TuitionAutomation.zip'))
		.pipe(gulp.dest('.Builds'));

	cb();
}

exports.default = buildEverything;