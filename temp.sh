#!/bin/bash

# Ensure the script is run from the directory containing .gitignore
if [ ! -f .gitignore ]; then
  echo ".gitignore file not found in the current directory."
  exit 1
fi

# Read ignored files from .gitignore
IGNORED_FILES=$(cat .gitignore | grep -v '^#' | grep -v '^$')

# Apply ACL restrictions to ignored files
for file in $IGNORED_FILES; do
  # Remove any leading/trailing whitespace
  file=$(echo $file | xargs)
  
  # Apply ACL to the file or directory
  if [ -e "/store/droptracker/disc/$file" ]; then
    sudo setfacl -m u:git_dev:--- "/store/droptracker/disc/$file"
  else
    echo "Warning: $file not found in /store/droptracker/disc"
  fi
done

echo "ACL restrictions applied based on .gitignore"