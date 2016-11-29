#!/usr/bin/env bash
BATCH_FILE=env_batch.xml


if [ -f ./${BATCH_FILE} ]; then
    perl -w -i -p -e 's/regular/premium/g' ${BATCH_FILE}
    perl -w -i -p -e 's/[\d]+:00/00:10/g' ${BATCH_FILE}
else
    echo "ERROR: no ${BATCH_FILE} file in current directory."
    exit 1
fi

exit 0
