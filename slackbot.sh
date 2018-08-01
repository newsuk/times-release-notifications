#!/bin/bash
# Script to notify slack when a release has been deployed.
#
# Expects the following environment variables to be available:
#  * GIT_REPO_URL      The git repository URL (e.g. git@github.com:newsuk/project.git)
#  * GIT_HASH          The commit hash of the build, must be tagged!
#  * PROJECT_NAME      The project name
#  * RELEASED_BY       The user who released
#  * SLACK_URL_RELEASE The slack webhook url for the appropriate channel to post to
set -e

# Debug dump
echo "GIT_REPO_URL:      $GIT_REPO_URL"
echo "GIT_HASH:          $GIT_HASH"
echo "PROJECT_NAME:      $PROJECT_NAME"
echo "RELEASED_BY:       $RELEASED_BY"
echo "SLACK_URL_RELEASE: $SLACK_URL_RELEASE"

# Lookup the tag & release url from the git commit hash used
tag=$(git ls-remote "$GIT_REPO_URL" | grep "$GIT_HASH" | grep 'refs/tags/' | sed 's|.*refs/tags/||')
releaseUrl=$(echo "$GIT_REPO_URL" | sed 's|^.*@\(.*\):\(.*\).git$|https://\1/\2/releases/tag/|')

# Format and send slack webhook
format='{"attachments":[{"author_name": "Released by: %s", "title": "%s", "text": "Version %s has been released\n%s"}]}'
data=$(printf "$format" "$RELEASED_BY" "$PROJECT_NAME" "$tag" "$releaseUrl/$tag")
curl -X POST -H 'Content-type: application/json' --data "$data" "$SLACK_URL_RELEASE"
