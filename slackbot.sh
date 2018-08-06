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

# Lookup the tag from the git commit hash used
tag=$(git ls-remote "$GIT_REPO_URL" | grep "$GIT_HASH" | grep 'refs/tags/' | sed 's|.*refs/tags/||')

# Create a URL to the tag (or commit if no tag)
githubUrl=$(echo "$GIT_REPO_URL" | sed 's|^.*@\(.*\):\(.*\).git$|https://\1/\2|')
if [ -z "$tag" ]; then
    tag=$GIT_HASH
    releaseUrl="$githubUrl/commit/$GIT_HASH"
else
    releaseUrl="$githubUrl/releases/tag/$tag"
fi

# Format and send slack webhook
format='{"attachments":[{"author_name": "Released by: %s", "title": "%s", "text": "Version %s has been released\n%s"}]}'
data=$(printf "$format" "$RELEASED_BY" "$PROJECT_NAME" "$tag" "$releaseUrl")
curl -X POST -H 'Content-type: application/json' --data "$data" "$SLACK_URL_RELEASE"
