MAINDIR = ~/mjezersky-facerec

all:
	@echo all target not yet implemented

download:
	mkdir -p $(MAINDIR)
	cd $(MAINDIR) && wget https://raw.githubusercontent.com/mjezersky/facerec/master/deploy/sources.zip && unzip sources.zip
	
run:
	cd $(MAINDIR) && python main.py
