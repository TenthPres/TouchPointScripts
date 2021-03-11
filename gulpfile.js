const gulp = require('gulp'),
	zip = require('gulp-zip');

exports.default = () => (

	// Mapify Only
	gulp.src(['Mapify/*.py', "Mapify/keyword"])
		.pipe(zip('Mapify.zip'))
		.pipe(gulp.dest('.Builds'))
);
