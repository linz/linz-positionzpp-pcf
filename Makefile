# Script to install the PositioNZ-PP PCF file
#
# Installs the PCF and options files and scripts needed to run it.
#
# Also installs an executable run_positionzpp_pcf
#

# Version of software
VERSION=1.0

all: 

# Seem to need a dependency in install for debuild to work

install: all
	mkdir -p ${DESTDIR}/opt/bernese52
	mkdir -p ${DESTDIR}/usr/bin
	cp -r bernese/* ${DESTDIR}/opt/bernese52
	cp bin/* ${DESTDIR}/usr/bin

package:
	debuild -uc -us
