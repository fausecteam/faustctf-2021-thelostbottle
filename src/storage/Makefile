.PHONY: test

all: ../binformat

release_simple: storage.cpp storage.h json.hpp
	echo "Compiling binary ..."
	clang++ -O3 storage.cpp -o storage \
		-ftrapv \
		-static
	echo "Stripping binary"
	strip storage
	mv storage ../binformat

debug: storage.cpp storage.h json.hpp
	g++ -g -fsanitize=address,undefined storage.cpp -o storage-debug
	mv storage-debug ../binformat

test:
	cd .. && ./binformat j2m storage/testflagmap.json storage/testflagmap.bin
	cd .. && ./binformat m2j storage/testflagmap.bin storage/testflagmap.re.json
	cd .. && ./binformat j2m storage/testflagmap.re.json storage/testflagmap.re.bin
	diff testflagmap.bin testflagmap.re.bin
	bash masstest.sh

storage.s: storage.cpp storage.h json.hpp
	clang++ -O3 -S storage.cpp -o storage.s \
		-ftrapv
obftest: ../binformat
	bash masstest.sh

../binformat: storage_obf
	cp storage_obf ../binformat
	strip ../binformat

storage_obf: storage_obf.s
	clang++ storage_obf.s -o storage_obf -static

storage_obf.s: storage.s
	# the real ctf did more stuff here
	cp storage.s storage_obf.s
