#!/bin/bash

echo "Masstest"
rm -f testmaps/*re*
for i in testmaps/*.json; do
	../binformat j2m $i testmaps/`basename $i .json`.bin
	../binformat m2j testmaps/`basename $i .json`.bin testmaps/`basename $i .json`.re.json
	../binformat j2m testmaps/`basename $i .json`.re.json testmaps/`basename $i .json`.re.bin
	diff  testmaps/`basename $i .json`.bin testmaps/`basename $i .json`.re.bin
done
