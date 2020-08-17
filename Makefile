DIR=htmlcov

coverage: coverage-run coverage-html coverage-pdf

coverage-run:
	coverage run --source cwlkernel --omit cwlkernel/__main__.py -m unittest discover tests

coverage-html:
	coverage html

coverage-pdf:
	wkhtmltopdf --title 'Coverage Report' --enable-local-file-access $(DIR)/index.html $(DIR)/cwlkernel*.html $(DIR)/report.pdf

clean:
	rm -rf $(DIR)
