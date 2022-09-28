#!/usr/bin/env bash

script_dir=$(dirname $0)
workdir=$(pwd)

XVSA_IDIR=$(realpath $(dirname $(dirname ${CXX})))
echo "XVSA_IDIR: ${XVSA_IDIR}"
echo "Working in $(pwd)"

# Change the IFS
OLDIFS=$IFS
IFS=$'\n'

fileArray=($(find $(pwd) -name '*.o'))

# restore it
IFS=$OLDIFS

# get length of an array
tLen=${#fileArray[@]}

process_file() {
    file_name=$1
    inito_cnt=$(grep -n "INITOs:" "${file_name}" | awk -F: '{print $1}' | tail -n 1)
    tail -n "+${inito_cnt}" "${file_name}" > "${file_name}.inito"
    python3 ${script_dir}/file_transform.py -i "${file_name}.inito"  -o "${file_name}.list"
    if [ $RET -ne 0 ] ; then
	rm "${file_name}.list"
	echo "Failed to transform ${file_name}"
    else
	rm "${file_name}" "${file_name}.inito"
    fi
    
}

# use for loop read all filenames
for (( i=0; i<${tLen}; i++ ));
do
    one_prop=${fileArray[$i]}
    if [ -f "${one_prop}" ] ; then
	if [ -f "${XVSA_IDIR}/bin/ir_b2a" ] ; then
	    "${XVSA_IDIR}/bin/ir_b2a" -st2 "${one_prop}" "${one_prop}.W"
	    RET=$?
	else
	    ir_b2a -st2 "${one_prop}" "${one_prop}.W"
	    RET=$?
	fi
	if [ $RET -ne 0 ] ; then
	    echo "Fail to run ir_b2a on ${one_prop}, skipping ..."
	    rm "${one_prop}.W"
	    continue;
	fi
	process_file "${one_prop}.W"
    else
	echo "Failed to find file ${one_prop} ..."
	exit 2;
    fi
    echo "Completing ... ${one_prop}"
done
