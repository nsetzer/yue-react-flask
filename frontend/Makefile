

.PHONY: serve

serve:
	export PYTHONPATH=../daedalus && python3.8 -c 'import sys; print(sys.path)'
	export PYTHONPATH=../daedalus && python3.8 -c 'import daedalus; print(daedalus.__file__)'
	export PYTHONPATH=../daedalus; python3.8 -m daedalus serve --env baseUrl='http://localhost:4200' --static ./resources src/app.js
