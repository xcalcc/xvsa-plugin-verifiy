#!/usr/bin/env bash

cd $(dirname $0)
echo "Workdir $(pwd)"

testware=${testware:-~/xc5/opencti-testware}
XVSA_HOME=${XVSA_HOME:-~/xc5/install}

if [ ! -d ${testware} ] || [ ! -d ${XVSA_HOME} ] ; then
    echo 'Please configure ${testware} and ${XVSA_HOME}'
fi


echo "Testware: ${testware}, XVSA_HOME: ${XVSA_HOME}"

echo "Testing with app mode"

# python3 run-jfe-with-lib-lists.py -l ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/z.study-java-lib-gzip.lib.list -d ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/z.study-java-lib-gzip.dir.list -j ${XVSA_HOME}/lib/1.0/mapfej  || exit 1

echo "Testing with app mode.. cleanup"

rm ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/z.study-java-lib-gzip.o

echo "Testing with library mode"

# python3 run-jfe-with-lib-lists.py -l ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/z.study-java-lib-gzip.lib.list -d ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/z.study-java-lib-gzip.dir.list -j ${XVSA_HOME}/lib/1.0/mapfej -library || exit 2

echo "Testing with library mode .. cleanup"
rm ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/*.o


echo "Testing with whole-dir mode"
python3 run-jfe-with-lib-lists.py -j ${XVSA_HOME}/lib/1.0/mapfej -w ${testware}/application/jfe/plugin-maven/make-gzip/workdir/xvsa-out/ || exit 3

echo "Testing with whole-dir mode completed"
