import os
import tempfile
import unittest
from pathlib import Path

import requests
from mockito import when, mock, unstub

from cwlkernel.git.CWLGitResolver import CWLGitResolver


class GitResolverTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def set_mock_github_responses(cls):
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev") \
            .thenReturn(mock({
            'status_code': 200,
            'json': lambda: {
                "name": "head.cwl",
                "path": "tests/cwl/head.cwl",
                "sha": "74e6680835a37ecc696279bd84495a4ec370c732",
                "size": 316,
                "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev",
                "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/head.cwl",
                "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/74e6680835a37ecc696279bd84495a4ec370c732",
                "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/head.cwl",
                "type": "file",
                "content": "Y2xhc3M6IENvbW1hbmRMaW5lVG9vbApjd2xWZXJzaW9uOiB2MS4wCmlkOiBo\nZWFkCmJhc2VDb21tYW5kOgogIC0gaGVhZAppbnB1dHM6CiAgLSBpZDogbnVt\nYmVyX29mX2xpbmVzCiAgICB0eXBlOiBpbnQ/CiAgICBpbnB1dEJpbmRpbmc6\nCiAgICAgIHBvc2l0aW9uOiAwCiAgICAgIHByZWZpeDogJy1uJwogIC0gaWQ6\nIGhlYWRpbnB1dAogICAgdHlwZTogRmlsZQogICAgaW5wdXRCaW5kaW5nOgog\nICAgICBwb3NpdGlvbjogMQpvdXRwdXRzOgogIC0gaWQ6IGhlYWRvdXRwdXQK\nICAgIHR5cGU6IHN0ZG91dApsYWJlbDogaGVhZApzdGRvdXQ6IGhlYWQub3V0\nCg==\n",
                "encoding": "base64",
                "_links": {
                    "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/head.cwl?ref=dev",
                    "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/74e6680835a37ecc696279bd84495a4ec370c732",
                    "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/head.cwl"
                }
            }
        }))
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev") \
            .thenReturn(mock(
            {
                'status_code': 200,
                'json': lambda: {
                    "name": "3stepWorkflow.cwl",
                    "path": "tests/cwl/3stepWorkflow.cwl",
                    "sha": "681de5be2005ab7258c33328140b33e0c42b891f",
                    "size": 810,
                    "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev",
                    "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl",
                    "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/681de5be2005ab7258c33328140b33e0c42b891f",
                    "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/3stepWorkflow.cwl",
                    "type": "file",
                    "content": "IyEvdXNyL2Jpbi9lbnYgY3dsdG9vbApjd2xWZXJzaW9uOiB2MS4wCmNsYXNz\nOiBXb3JrZmxvdwppZDogdGhyZWVzdGVwcwppbnB1dHM6CiAgLSBpZDogaW5w\ndXRmaWxlCiAgICB0eXBlOiBGaWxlCiAgLSBpZDogcXVlcnkKICAgIHR5cGU6\nIHN0cmluZwpvdXRwdXRzOgogIG91dHB1dGZpbGU6CiAgICB0eXBlOiBGaWxl\nCiAgICBvdXRwdXRTb3VyY2U6IGdyZXAyL2dyZXBvdXRwdXQKICBvdXRwdXRm\naWxlMjoKICAgIHR5cGU6IEZpbGUKICAgIG91dHB1dFNvdXJjZTogZ3JlcHN0\nZXAvZ3JlcG91dHB1dAoKc3RlcHM6CiAgaGVhZDoKICAgIHJ1bjogaGVhZC5j\nd2wKICAgIGluOgogICAgICBoZWFkaW5wdXQ6IGlucHV0ZmlsZQogICAgb3V0\nOiBbaGVhZG91dHB1dF0KCiAgZ3JlcHN0ZXA6CiAgICBydW46IGdyZXAuY3ds\nCiAgICBpbjoKICAgICAgZ3JlcGlucHV0OiBoZWFkL2hlYWRvdXRwdXQKICAg\nICAgcXVlcnk6IHF1ZXJ5CiAgICAgIGxpbmVzX2JlbGxvdzoKICAgICAgICB2\nYWx1ZUZyb206ICR7cmV0dXJuIDU7fQogICAgb3V0OiBbZ3JlcG91dHB1dF0K\nICBncmVwMjoKICAgIHJ1bjogZ3JlcC5jd2wKICAgIGluOgogICAgICBncmVw\naW5wdXQ6IGdyZXBzdGVwL2dyZXBvdXRwdXQKICAgICAgcXVlcnk6CiAgICAg\nICAgdmFsdWVGcm9tOiAncXVlcnknCiAgICAgIGxpbmVzX2Fib3ZlOgogICAg\nICAgIHZhbHVlRnJvbTogJHtyZXR1cm4gNTt9CiAgICBvdXQ6IFtncmVwb3V0\ncHV0XQpyZXF1aXJlbWVudHM6CiAgU3RlcElucHV0RXhwcmVzc2lvblJlcXVp\ncmVtZW50OiB7fQogIElubGluZUphdmFzY3JpcHRSZXF1aXJlbWVudDoge30K\n",
                    "encoding": "base64",
                    "_links": {
                        "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/3stepWorkflow.cwl?ref=dev",
                        "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/681de5be2005ab7258c33328140b33e0c42b891f",
                        "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl"
                    }
                }
            }))
        when(requests) \
            .get("https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev") \
            .thenReturn(mock(
            {
                'status_code': 200,
                'json': lambda: {
                    "name": "grep.cwl",
                    "path": "tests/cwl/grep.cwl",
                    "sha": "a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                    "size": 476,
                    "url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev",
                    "html_url": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/grep.cwl",
                    "git_url": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                    "download_url": "https://raw.githubusercontent.com/giannisdoukas/CWLJNIKernel/dev/tests/cwl/grep.cwl",
                    "type": "file",
                    "content": "Y2xhc3M6IENvbW1hbmRMaW5lVG9vbApjd2xWZXJzaW9uOiB2MS4wCmlkOiBn\ncmVwCmJhc2VDb21tYW5kOgogIC0gZ3JlcAppbnB1dHM6CiAgLSBpZDogcXVl\ncnkKICAgIHR5cGU6IHN0cmluZwogICAgaW5wdXRCaW5kaW5nOgogICAgICBw\nb3NpdGlvbjogMAogIC0gaWQ6IGxpbmVzX2JlbGxvdwogICAgdHlwZTogaW50\nPwogICAgaW5wdXRCaW5kaW5nOgogICAgICBwb3NpdGlvbjogMQogICAgICBw\ncmVmaXg6ICctQScKICAtIGlkOiBsaW5lc19hYm92ZQogICAgdHlwZTogaW50\nPwogICAgaW5wdXRCaW5kaW5nOgogICAgICBwb3NpdGlvbjogMgogICAgICBw\ncmVmaXg6ICctQicKICAtIGlkOiBncmVwaW5wdXQKICAgIHR5cGU6IEZpbGUK\nICAgIGlucHV0QmluZGluZzoKICAgICAgcG9zaXRpb246IDEwCm91dHB1dHM6\nCiAgLSBpZDogZ3JlcG91dHB1dAogICAgdHlwZTogc3Rkb3V0CmxhYmVsOiBo\nZWFkCnN0ZG91dDogZ3JlcG91dHB1dC5vdXQ=\n",
                    "encoding": "base64",
                    "_links": {
                        "self": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/contents/tests/cwl/grep.cwl?ref=dev",
                        "git": "https://api.github.com/repos/giannisdoukas/CWLJNIKernel/git/blobs/a0ce6c241f90eafd0b4c489a1880368f2ceca1d9",
                        "html": "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/grep.cwl"
                    }
                }
            }
        ))

    def test_resolve(self):
        git_dir = Path(tempfile.mkdtemp())
        self.set_mock_github_responses()
        git_resolver = CWLGitResolver(git_dir)
        self.assertListEqual(
            sorted([
                os.path.join(git_dir, f) for f in
                ['giannisdoukas/CWLJNIKernel/tests/cwl/3stepWorkflow.cwl',
                 'giannisdoukas/CWLJNIKernel/tests/cwl/head.cwl',
                 'giannisdoukas/CWLJNIKernel/tests/cwl/grep.cwl']
            ]),
            sorted(git_resolver.resolve(
                "https://github.com/giannisdoukas/CWLJNIKernel/blob/dev/tests/cwl/3stepWorkflow.cwl"))
        )
        unstub()


if __name__ == '__main__':
    unittest.main()
