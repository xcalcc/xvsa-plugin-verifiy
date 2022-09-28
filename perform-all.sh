#!/usr/bin/env bash

#echo "Enabling output."
#set -x

script_dir=$(dirname $0)
workdir=$(pwd)
echo "Working in $(pwd)"

if [ ! -f ${script_dir}/build/libs/verifier.jar ] ; then
    cd ${script_dir}
    ./gradlew build
    cd ${workdir}
fi

${script_dir}/generate-irb2a.sh
java -jar ${script_dir}/build/libs/verifier.jar $(pwd)
RET=$?
echo "Verifier returned ${RET}"
exit ${RET}
