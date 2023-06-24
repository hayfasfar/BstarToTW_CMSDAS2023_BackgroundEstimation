#!/bin/bash

files=`ls -1 *root`


for file in $files
do
	newfile=`echo $file | sed -e s/16APV/16/`
	echo copying $file to $newfile

	cp $file $newfile
done

