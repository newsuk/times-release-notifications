import unittest
from unittest.mock import patch, MagicMock
import subprocess
import requests

# Assuming the script is named `slackbot.py` and all functions are imported
from tool.slackbot import (
    execute_shell_command,
    get_tag_for_commit,
    get_release_info_by_tag,
    get_commit_info,
    send_slack_notification,
    build_message,
    notify_release
)


class TestSlackBotRelease(unittest.TestCase):

    @patch('subprocess.check_output')
    def test_execute_shell_command_success(self, mock_check_output):
        mock_check_output.return_value = b"output"
        result = execute_shell_command("ls")
        self.assertEqual(result, "output")

    @patch('subprocess.check_output')
    def test_execute_shell_command_failure(self, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'cmd')
        with self.assertRaises(RuntimeError):
            execute_shell_command("ls")

    @patch('subprocess.check_output')
    def test_get_tag_for_commit(self, mock_check_output):
        mock_check_output.return_value = b"abcdef refs/tags/v1.0.0\n123456 refs/tags/v1.1.0"
        result = get_tag_for_commit("https://github.com/example/repo.git", "abcdef")
        self.assertEqual(result, "v1.0.0")

    @patch('subprocess.check_output')
    def test_get_tag_for_commit_no_tag(self, mock_check_output):
        mock_check_output.return_value = b"123456 refs/tags/v1.1.0"
        result = get_tag_for_commit("https://github.com/example/repo.git", "abcdef")
        self.assertIsNone(result)

    @patch('requests.get')
    def test_get_release_info_by_tag_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "changelog", "author": {"login": "authorName"}}
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        result = get_release_info_by_tag("org/repo", "v1.0.0", "token")
        self.assertEqual(result['body'], "changelog")
        self.assertEqual(result['author']['login'], "authorName")

    @patch('requests.get')
    def test_get_release_info_by_tag_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            get_release_info_by_tag("org/repo", "v1.0.0", "token")

    @patch('requests.get')
    def test_get_commit_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"commit": {"author": {"name": "authorName"}, "message": "commit message"}}
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response

        result = get_commit_info("https://github.com/example/repo.git", "abcdef", "token")
        self.assertEqual(result['commit']['author']['name'], "authorName")
        self.assertEqual(result['commit']['message'], "commit message")

    @patch('requests.get')
    def test_get_commit_info_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException
        mock_get.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            get_commit_info("https://github.com/example/repo.git", "abcdef", "token")

    @patch('requests.post')
    def test_send_slack_notification_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_post.return_value = mock_response

        send_slack_notification("https://hooks.slack.com/services/XXX", "message")

        mock_post.assert_called_once_with(
            "https://hooks.slack.com/services/XXX",
            headers={'Content-Type': 'application/json'},
            data='{"text": "message"}'
        )

    @patch('requests.post')
    def test_send_slack_notification_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.RequestException):
            send_slack_notification("https://hooks.slack.com/services/XXX", "message")

    def test_build_message(self):
        result = build_message("ProjectX", "username", "abcdef", "authorName", ["change1", "change2"])
        expected_message = (
            "*Release Notification:*\n"
            "*Project:* ProjectX\n"
            "*Released by:* username\n"
            "*Commit:* abcdef\n"
            "*Author:* authorName\n"
            "*What's Changed:*\n"
            "```\n"
            "change1\n"
            "change2\n"
            "```"
        )
        self.assertEqual(result, expected_message)

    @patch('tool.slackbot.get_tag_for_commit')
    @patch('tool.slackbot.get_release_info_by_tag')
    @patch('tool.slackbot.send_slack_notification')
    @patch('tool.slackbot.get_commit_info')
    def test_slackbot(self, mock_get_commit_info, mock_send_slack_notification, mock_get_release_info_by_tag,
                            mock_get_tag_for_commit):
        mock_get_tag_for_commit.return_value = "v1.0.0"
        mock_get_release_info_by_tag.return_value = {"body": "changelog", "author": {"login": "authorName"}}
        mock_get_commit_info.return_value = {"commit": {"author": {"name": "authorName"}, "message": "commit message"}}

        notify_release("https://github.com/example/repo.git", "abcdef", "ProjectX", "username", "token",
                       ["https://hooks.slack.com/services/XXX"])

        mock_get_tag_for_commit.assert_called_once_with("https://github.com/example/repo.git", "abcdef")
        mock_get_release_info_by_tag.assert_called_once_with("example/repo", "v1.0.0", "token")
        mock_send_slack_notification.assert_called_once()


if __name__ == '__main__':
    unittest.main()
