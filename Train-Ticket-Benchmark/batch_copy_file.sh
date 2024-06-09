#!/bin/bash

file_to_copy="apache-skywalking-java-agent-9.2.0.tgz"

if [[ ! -f "$file_to_copy" ]]; then
  echo "Error: File '$file_to_copy' does not exist."
  exit 1
fi

find . -type d | while read -r dir; do
  if [[ -f "$dir/pom.xml" ]]; then # only for Java projects
    echo "Copying $file_to_copy to $dir"
    cp "$file_to_copy" "$dir"
  fi
done

echo "Finished copying files."
