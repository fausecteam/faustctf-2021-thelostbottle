#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REMOTE=${1}

function pass() {
	echo -e "[${1}]\tOK" >&2
}

function fail() {
	echo -e "[${1}]\tFAIL" >&2
}

function check_equals() {
	if [ "${1}" = "$2" ]; then
		pass $3
	else
		fail $3
		echo "Got      ${1}"
		echo "Expected ${2}"
	fi
}

#####
# Checker
#####
function checker() {
	if [ "${REMOTE}" = "::1" ]; then
		systemctl --user start thelostbottle.socket
	fi
	for i in `seq 0 5`; do
		res=$(python3 ${SCRIPT_DIR}/../checker/checker.py ${REMOTE} 10 $i 2>/dev/null | tail -n 1)
		check_equals "$res" "Check result: OK" "check/tick${i}"
	done
	if [ "${REMOTE}" = "::1" ]; then
		systemctl --user stop thelostbottle.socket
	fi
}
checker

#### unittest ####
function unittest() {
	fn=${1}
	name=${2}
	systemctl --user start thelostbottle.socket
	a=$(python ${fn} 3>&1 1>&2 2>&3 1>/dev/null)
	ok=$(echo "${a}" | tail -n 1)
	check_equals "$ok" "OK" ${name}
}
unittest "test/player.py" "ut/player"
unittest "test/serverunit.py" "ut/srvunit"


#####
# Check that exploit is working
#####

function exploit() {
	expl=${1}
	map=${2}
	pushd ${SCRIPT_DIR}/../exploit > /dev/null
	flag=$(python ${expl} ${REMOTE} 5555 ${map} /tmp/a.json | tail -n 1)
	echo $flag
	popd > /dev/null
}

## Exploits ##
for expl in exploit.py exploit_bottle.py exploit_typechange.py; do
# samplemap
	flag=$(exploit ${expl} maps/smallmap.json)
	check_equals "$flag" ">> FAUST_AAAAAAABKl/MJ+kAAAAAMHITYPjsr9dJ" "${expl}samp"
	# map 0
	#flag=$(exploit ${expl} maps/map_0.json)
	#check_equals "$flag" ">> FLAG_AAAAAAAKKrw4/iIAAAAASw9IMSuHm/p3" "${expl}map0"
	# map 1
	#flag=$(exploit ${expl} maps/map_1.json)
	#check_equals "$flag" ">> FLAG_AAAAAQAKKgSEmUcAAAAAh6H2l+f1maFu" "${expl}map1"
done
