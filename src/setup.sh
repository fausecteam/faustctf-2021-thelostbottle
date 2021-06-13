#!/bin/bash

# one-time secret key generation
SK=/srv/thelostbottle/secret.key

if ! [ -e ${SK} ]; then
	head -c 32 /dev/urandom > ${SK}
	chown root:thelostbottle ${SK}
	chmod 440 ${SK}
fi
