"""
Notify Slack when a release has been deployed.

This script is designed to send a release notification to Slack
using one or more provided webhook URLs. It gathers information about
the specified git commit, constructs a message, and sends it to the specified
Slack channels. Optionally, it can dump release information to a file.

Author: Yordan Borisov
Usage:
    python slackbot.py --git-repo-url=<repo_url> --git-hash=<commit_hash> \
--project-name=<project_name> --released-by=<released_by> \
--release-bot-token=<github_token> --slack-url-release=<slack_webhook_urls> \
[--dump-release-info=<file_path>]

Examples:
    python notify_release.py --git-repo-url=https://github.com/example/repo.git \
--git-hash=abc123 --project-name=ProjectX --released-by=username \
--release-bot-token=token123 --slack-url-release=https://hooks.slack.com/services/XXX,https://hooks.slack.com/services/YYY \
--dump-release-info=/path/to/release_info.json
"""

import os
import re
from urllib.parse import urlparse

import requests
import json
import subprocess
import argparse
import sys


def execute_shell_command(command):
    """
    Execute a shell command and return its output.

    Args:
        command (str): The command to execute.

    Returns:
        str: The output of the command.

    Raises:
        RuntimeError: If the command fails.
    """
    try:
        result = subprocess.check_output(command, shell=True)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to execute command: {e}")


def get_tag_for_commit(repo_url, commit_hash):
    """
    Get the tag associated with a given commit hash in a repository.

    Args:
        repo_url (str): The repository URL.
        commit_hash (str): The commit hash.

    Returns:
        str: The tag name if found, else None.
    """
    command = f"git ls-remote {repo_url}"
    result = execute_shell_command(command)

    lines = result.split('\n')
    for line in lines:
        if commit_hash in line and 'refs/tags/' in line:
            parts = line.split('refs/tags/')
            if len(parts) > 1:
                return parts[1].replace("^{}", "")
    return None


def get_release_info_by_tag(org_repo, tag, token):
    """
    Get release information from GitHub for a specific tag.

    Args:
        org_repo (str): The organization and repository name in the form 'org/repo'.
        tag (str): The tag name.
        token (str): The GitHub token for authentication.

    Returns:
        dict: The release information.
    """
    headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
    api_url = f"https://api.github.com/repos/{org_repo}/releases/tags/{tag}"

    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_commit_info(repo_url, commit_hash, token):
    """
    Get commit information from GitHub.

    Args:
        repo_url (str): The repository URL.
        commit_hash (str): The commit hash.
        token (str): The GitHub token for authentication.

    Returns:
        dict: The commit information.
    """
    headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': f'token {token}'}
    api_url = f"https://api.github.com/repos/{repo_url.split(':')[1].replace('.git', '')}/commits/{commit_hash}"

    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def send_slack_notification(webhook_url, message):
    """
    Send a notification to Slack.

    Args:
        webhook_url (str): The Slack webhook URL.
        message (str): The message to send.

    Raises:
        requests.exceptions.RequestException: If the request fails.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {'text': message}

    response = requests.post(webhook_url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()


def build_message(project_name, released_by, git_hash, commit_author, changelog):
    """
    Build the Slack notification message.

    Args:
        project_name (str): The project name.
        released_by (str): The user who released.
        git_hash (str): The git commit hash.
        commit_author (str): The author of the commit.
        changelog (list): The list of changes.

    Returns:
        str: The formatted Slack message.
    """
    message = (
        f"*Release Notification:*\n"
        f"*Project:* {project_name}\n"
        f"*Released by:* {released_by}\n"
        f"*Commit:* {git_hash}\n"
        f"*Author:* {commit_author}\n"
        f"*What's Changed:*\n"
        "```\n"
    )

    if changelog:
        for change in changelog:
            if "What's Changed" in change:
                continue
            message += f"{change}\n"

    message += "```"  # Close the code block

    return message

def extract_org_repo(git_repo_url):
    """
    Extracts the organization and repository name from the given git URL.
    Handles both SSH and HTTPS URLs.
    """
    parsed_url = urlparse(git_repo_url)

    if parsed_url.scheme in ['http', 'https']:
        org_repo = parsed_url.path.lstrip('/')
    else:  # handling git@github.com:org/repo.git
        match = re.match(r'git@(.*):(.*)', git_repo_url)
        if match:
            org_repo = match.group(2)
        else:
            raise ValueError("Invalid git repository URL format")

    return org_repo.replace('.git', '')

def notify_release(git_repo_url, git_hash, project_name, released_by, release_bot_token, slack_urls):
    """
    Notify Slack about a release.

    Args:
        git_repo_url (str): The git repository URL.
        git_hash (str): The commit hash of the build.
        project_name (str): The project name.
        released_by (str): The user who released.
        release_bot_token (str): The Slackbot token for accessing GitHub API.
        slack_urls (list): List of Slack webhook URLs.

    Raises:
        requests.exceptions.RequestException: If the request fails.
    """
    org_repo = extract_org_repo(git_repo_url)

    tag = get_tag_for_commit(git_repo_url, git_hash)
    changelog = []
    commit_author = ""

    if tag:
        release_info = get_release_info_by_tag(org_repo, tag, release_bot_token)
        changelog = release_info['body'].split('\n')
        commit_author = release_info['author']['login']

    if not changelog:
        commit_info = get_commit_info(git_repo_url, git_hash, release_bot_token)
        changelog = [commit_info['commit']['message']]
        commit_author = commit_info['commit']['author']['name']

    message = build_message(project_name, released_by, git_hash, commit_author, changelog)

    for url in slack_urls:
        send_slack_notification(url, message)


def dump_release_info(git_repo_url, git_hash, release_bot_token, output_file):
    """
    Dump the release information to a file.

    Args:
        git_repo_url (str): The git repository URL.
        git_hash (str): The commit hash of the build.
        release_bot_token (str): The GitHub token for authentication.
        output_file (str): The file path to dump the release information.
    """
    org_repo = git_repo_url.split(':')[1].replace('.git', '')

    tag = get_tag_for_commit(git_repo_url, git_hash)
    release_info = get_release_info_by_tag(org_repo, tag, release_bot_token) if tag else {}

    if not release_info:
        commit_info = get_commit_info(git_repo_url, git_hash, release_bot_token)
        release_info = {
            'commit': commit_info,
            'message': commit_info['commit']['message'],
            'author': commit_info['commit']['author']['name']
        }

    with open(output_file, 'w') as file:
        json.dump(release_info, file, indent=4)


def main():
    """
    Main function to parse arguments and trigger Slack notification and (optional) info dump.
    """
    parser = argparse.ArgumentParser(description='Notify Slack when a release has been deployed.')
    parser.add_argument('--git-repo-url', default=os.getenv('GIT_REPO_URL'), help='The git repository URL')
    parser.add_argument('--git-hash', default=os.getenv('GIT_HASH'),
                        help='The commit hash of the build. Must be tagged.')
    parser.add_argument('--project-name', default=os.getenv('PROJECT_NAME'), help='The project name')
    parser.add_argument('--released-by', default=os.getenv('RELEASED_BY'), help='The user who released')
    parser.add_argument('--release-bot-token', default=os.getenv('RELEASE_BOT_TOKEN'),
                        help='Slackbot token for accessing GitHub API')
    parser.add_argument('--slack-url-release', default=os.getenv('SLACK_URL_RELEASE'),
                        help='One or more Slack webhook URLs, separated by commas')
    parser.add_argument('--dump-release-info', help='File path to dump the release information', type=str)

    args = parser.parse_args()

    if not all([args.git_repo_url, args.git_hash, args.project_name, args.released_by, args.release_bot_token,
                args.slack_url_release]):
        parser.error('All arguments must be provided either as command-line parameters or environment variables.')

    slack_urls = args.slack_url_release.split(',')

    notify_release(args.git_repo_url, args.git_hash, args.project_name, args.released_by, args.release_bot_token,
                   slack_urls)

    if args.dump_release_info:
        dump_release_info(args.git_repo_url, args.git_hash, args.release_bot_token, args.dump_release_info)


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except requests.exceptions.RequestException as e:
        print(f"Network Error: {str(e)}")
    except ValueError as e:
        print(f"Value Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
    sys.exit(1)
