DESTDIR?=/
PYTHONDIR?=$(shell python3 -c 'import sys; print(sys.path[-1])')

purge_pycache:
	@find -name '__pycache__' | xargs rm -rf

clean: purge_pycache
	@rm -rf build dist uchroma.egg-info
	make -C doc clean

install_library: purge_pycache
	python3 setup.py install --root=$(DESTDIR)

install_udev:
	install -m 644 -v -D udev/90-uchroma.rules $(DESTDIR)/etc/udev/rules.d/90-uchroma.rules
	$(eval HWDB := $(shell mktemp))
	python3 setup.py -q hwdb > $(HWDB)
	install -m 644 -v -D $(HWDB) $(DESTDIR)/etc/udev/hwdb.d/90-uchroma.hwdb
	@rm -v -f $(HWDB)

uninstall_library:
	$(eval UCPATH := $(shell find $(DESTDIR)/usr/local/lib/python3* -maxdepth 2 -name "uchroma"))
	$(eval EGGPATH := $(shell readlink -f $(UCPATH)-*.egg-info/))
	@rm -v -rf $(UCPATH)
	@rm -v -rf $(EGGPATH)
	@rm -v -f $(DESTDIR)/usr/local/bin/uchroma

uninstall_udev:
	@rm -v -f $(DESTDIR)/etc/udev/rules.d/90-uchroma.rules
	@rm -v -f $(DESTDIR)/etc/udev/hwdb.d/90-uchroma.hwdb

sphinx_clean:
	@rm -f doc/uchroma.*

sphinx: sphinx_clean
	sphinx-apidoc -o doc -M -f -e .

docs: sphinx
	make -C doc html

install: install_library install_udev

uninstall: uninstall_library uninstall_udev

debs:
	debuild -i -us -uc -b

all: install docs
