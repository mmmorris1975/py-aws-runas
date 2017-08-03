package:
	python setup.py bdist_wheel

upload: package
	twine upload dist/*

clean:
	rm -rf build dist *.egg-info

distclean: clean
	rm -rf aws_runas/*.py[co] aws_runas/__pycache__
