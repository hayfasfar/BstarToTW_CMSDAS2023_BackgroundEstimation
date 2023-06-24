#!/bin/bash

files=`ls -1 *root`


for file in $files
do
	newfile=`echo $file | sed -e s/16all/16_/`
	echo copying $file to $newfile

	cp $file $newfile
done

