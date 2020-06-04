import base64
import json
import os.path
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict
from urllib.parse import urlparse

import requests
import ruamel.yaml as yaml
from requests.compat import urljoin


class CWLGitResolver:
    """CWLGitResolver fetches the required cwl files from a remote git url"""

    def __init__(self, local_directory: Path, github_url: str):
        self._local_directory = local_directory
        self._local_directory.mkdir(exist_ok=True)
        github_path = urlparse(github_url).path.split('/')
        self._git_owner = github_path[1]
        self._git_repo = github_path[2]
        self._git_branch = github_path[4]
        self._git_path = '/'.join(github_path[5:])

    def resolve(self) -> List[str]:
        workflow_files = set()
        root_path = self._git_path[:self._git_path.rfind('/')]
        search_stack = [self._git_path]
        while len(search_stack) > 0:
            current_path = search_stack.pop()
            if current_path not in workflow_files:
                workflow_filename, workflow = self._resolve_file(current_path)
                workflow_files.add(workflow_filename)
                if 'steps' in workflow:
                    for step in workflow['steps']:
                        if isinstance(workflow['steps'][step]['run'], str):
                            search_stack.append('/'.join([root_path, workflow['steps'][step]['run']]))
        return list(workflow_files)

    def _resolve_file(self, path: str) -> Tuple[str, Dict]:
        url = urljoin(f"https://api.github.com/repos/{self._git_owner}/{self._git_repo}/contents/",
                      f"{path}?ref={self._git_branch}")
        github_response = requests.get(url)
        github_response = json.loads(github_response.text)
        if github_response.status_code != 200:
            raise RuntimeError(f"Error on github api call: {github_response.status_code}: {github_response.text}")
        workflow = yaml.load(BytesIO(base64.b64decode(github_response['content'])), yaml.Loader)
        workflow_filename = os.path.join(str(self._local_directory), path)
        Path(os.path.dirname(workflow_filename)).mkdir(exist_ok=True, parents=True)
        with open(workflow_filename, 'w') as f:
            yaml.dump(workflow, f)
        return workflow_filename, workflow
