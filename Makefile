DESTDIR?=/
PYTHONDIR?=$(shell python3 -c 'import sys; print(sys.path[-1])')

purge_pycache:
	@find -name '__pycache__' | xargs rm -rf

clean: purge_pycache
	@rm -rf build dist uchroma.egg-info

install_library: purge_pycache
	python3 setup.py install --prefix=/usr --root=$(DESTDIR)

install_udev:
	install -m 644 -v -D udev/99-uchroma.rules $(DESTDIR)/lib/udev/rules.d/99-uchroma.rules

uninstall_library:
	$(eval UCPATH := $(shell find $(DESTDIR)/usr/lib/python3* -maxdepth 2 -name "uchroma"))
	$(eval EGGPATH := $(shell readlink -f $(UCPATH)-*.egg-info/))
	@rm -v -rf $(UCPATH)
	@rm -v -rf $(EGGPATH)
	@rm -v -f $(DESTDIR)/usr/bin/uchroma

uninstall_udev:
	@rm -v -f $(DESTDIR)/lib/udev/rules.d/99-uchroma.rules

install: install_library install_udev

uninstall: uninstall_library uninstall_udev
