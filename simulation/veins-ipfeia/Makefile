#
# Top-level Makefile of the IPFE-IA Veins simulation.
# Run ./configure first (in an OMNeT++ shell).
#

all: makefiles
	$(MAKE) -C src all

# absolute path to the Veins tree: opp_makemake resolves -I/-L relative to its
# CWD (src/), so a relative path would wrongly point at veins-ipfeia/veins-src
VEINS_DIR := $(abspath ../veins-src)

makefiles:
	cd src && opp_makemake -f --deep --no-deep-includes --make-so -I . -I $(VEINS_DIR)/src -L $(VEINS_DIR)/src -lveins$(D) -o ipfeia -O out -p IPFEIA

clean:
	$(MAKE) -C src cleanall
	rm -rf src/out
	rm -rf results

.PHONY: all makefiles clean
