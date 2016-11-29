#!/usr/bin/env bash

PR_NUM=$1
PR_REPO=$2
PR_BRANCH=$3

REF_REPO=git@github.com:NGEET/ed-clm.git

PR_DIR=pr${PR_NUM}
mkdir ${PR_DIR}

cd ${PR_DIR}
git clone ${REF_REPO}

cd ed-clm
git remote add pr ${PR_REPO}
git fetch pr
git checkout ${PR_BRANCH}
git checkout master
git merge --no-ff ${PR_BRANCH}
