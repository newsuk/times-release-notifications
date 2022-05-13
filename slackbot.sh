#!/bin/bash
# Script to notify slack when a release has been deployed.
#
# Expects the following environment variables to be available:
#  * GIT_REPO_URL      The git repository URL (e.g. git@github.com:newsuk/project.git)
#  * GIT_HASH          The commit hash of the build, must be tagged!
#  * PROJECT_NAME      The project name
#  * RELEASED_BY       The user who released
#  * RELEASE_BOT_TOKEN Slackbot token to access git api
#  * SLACK_URL_RELEASE One or more slack webhook urls for the appropriate channel to post to, split by comma
set -e

function usage()
{
    echo "News UK github release slack notification bot"
    echo ""
    echo "./slackbot.sh"
    echo "\t-h --help"
    echo "\tPrints this help"
    echo ""
    echo "\t--git-repo-url"
    echo "\tThe git repository URL (e.g. git@github.com:newsuk/project.git)"
    echo ""
    echo "\t--git-hash"
    echo "\tThe commit hash of the build, must be tagged!"
    echo ""
    echo "\t--project-name"
    echo "\tThe project name"
    echo ""
    echo "\t--released-by"
    echo "\tThe user who released"
    echo ""
    echo "\t--slack-url-release"
    echo "\tOne or more slack webhook urls for the appropriate channel to post to, split by comma"
    echo ""
    echo "\t--release"
    echo "\tPatches the github release status from prelrelease to release"
    echo ""
}

while [ "$1" != "" ]; do
    PARAM=`echo $1 | awk -F= '{print $1}'`
    VALUE=`echo $1 | awk -F= '{print $2}'`
    case $PARAM in
        -h | --help)
            usage
            exit
            ;;
        --release)
            GIT_STATUS_RELEASE=true
            ;;
        --git-repo-url)
            GIT_REPO_URL=$VALUE
            ;;
        --git-hash)
            GIT_HASH=$VALUE
            ;;
        --project-name)
            PROJECT_NAME=$VALUE
            ;;
        --released-by)
            RELEASED_BY=$VALUE
            ;;
        --slack-release-url)
            SLACK_URL_RELEASE=$VALUE
            ;;
        *)
            echo "ERROR: unknown parameter \"$PARAM\""
            usage
            exit 1
            ;;
    esac
    shift
done

# Extract the organisation/repository from the repository url
orgRepo=$(echo $GIT_REPO_URL | sed 's/https:\/\///g' | sed 's/github.com\///g' | sed 's/.git//g' | sed 's/github.com://g')

# Debug dump
echo "GIT_REPO_URL:      $GIT_REPO_URL"
echo "GIT_HASH:          $GIT_HASH"
echo "PROJECT_NAME:      $PROJECT_NAME"
echo "RELEASED_BY:       $RELEASED_BY"
echo "SLACK_URL_RELEASE: SLACK_URL_RELEASE"
echo "Organisation/Repo: $orgRepo"

# Lookup the tag from the git commit hash used
tag=$(git ls-remote "$GIT_REPO_URL" | grep "$GIT_HASH" | grep 'refs/tags/' | sed 's|.*refs/tags/||' | sed 's|\^{}||')

releaseId=$(curl -H "Accept: application/vnd.github.v3+json" -H "Authorization: token $RELEASE_BOT_TOKEN" https://api.github.com/repos/$orgRepo/releases/tags/$tag| jq .id)

if [ "$GIT_STATUS_RELEASE" = "true" ]; then
    echo "GIT_STATUS_RELEASE: $GIT_STATUS_RELEASE"
    changelog=$(curl -H "Accept: application/vnd.github.v3+json"  -H "Authorization: token  $RELEASE_BOT_TOKEN"  --data '{"prerelease": false}' -X PATCH https://api.github.com/repos/$orgRepo/releases/$releaseId | jq .body | sed -e 's/"//g')
else
    changelog=$(curl -H "Accept: application/vnd.github.v3+json"  -H "Authorization: token  $RELEASE_BOT_TOKEN" https://api.github.com/repos/$orgRepo/releases/tags/$tag | jq .body | sed -e 's/"//g')
fi

echo "Changelog: $changelog"

# Create a URL to the tag (or commit if no tag)
githubUrl=$(echo "$GIT_REPO_URL" | sed 's|^.*@\(.*\):\(.*\).git$|https://\1/\2|')
if [ -z "$tag" ]; then
    tag=$GIT_HASH
    releaseUrl="$githubUrl/commit/$GIT_HASH"
else
    releaseUrl="$githubUrl/releases/tag/$tag"
fi

# Format and send slack webhook
format='{"attachments":[{"author_name": "Released by: %s", "title": "%s", "text": "Version %s has been released\n%s\n\n%s"}]}'
data=$(printf "$format" "$RELEASED_BY" "$PROJECT_NAME" "$tag" "$releaseUrl" "$changelog")

urls=(${SLACK_URL_RELEASE//,/ })

for slack_url in "${urls[@]}"
do
      curl -X POST -H 'Content-type: application/json' --data "$data" "$slack_url"
done

