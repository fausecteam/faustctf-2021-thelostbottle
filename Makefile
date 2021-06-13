SERVICE := thelostbottle
DESTDIR ?= dist_root
SERVICEDIR ?= /srv/$(SERVICE)

.PHONY: build install test

build:
	$(MAKE) -C src/storage

install: build
	mkdir -p $(DESTDIR)$(SERVICEDIR)
	mkdir -p $(DESTDIR)$(SERVICEDIR)/maps
	cp src/binformat $(DESTDIR)$(SERVICEDIR)/
	cp -r src/ffserver $(DESTDIR)$(SERVICEDIR)/
	cp -r src/client $(DESTDIR)$(SERVICEDIR)/
	cp -r src/common $(DESTDIR)$(SERVICEDIR)/
	cp -r src/maps/smallmap.json $(DESTDIR)$(SERVICEDIR)/maps/
	cp -r src/NOTE.md $(DESTDIR)$(SERVICEDIR)/
	cp -r src/ServiceReadme $(DESTDIR)$(SERVICEDIR)/
	cp src/setup.sh $(DESTDIR)$(SERVICEDIR)/
	cp src/run_server.sh $(DESTDIR)$(SERVICEDIR)/
	rm $(DESTDIR)$(SERVICEDIR)/client/assets/*.xcf
	rm $(DESTDIR)$(SERVICEDIR)/client/assets/*.svg
	mkdir -p $(DESTDIR)/etc/systemd/system
	cp src/thelostbottle@.service $(DESTDIR)/etc/systemd/system/
	cp src/thelostbottle.socket $(DESTDIR)/etc/systemd/system/
	cp src/system-thelostbottle.slice $(DESTDIR)/etc/systemd/system/
	cp src/thelostbottlesetup.service $(DESTDIR)/etc/systemd/system/

test:
	test/test.sh ::1 > /dev/null

testremote:
	test/test.sh fd66:666:995::2 > /dev/null
