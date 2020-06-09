import base64
import os.path
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict
from urllib.parse import urlparse

import requests
import ruamel.yaml as yaml
from requests.compat import urljoin


class CWLGitResolver:
    """CWLGitResolver fetches the required cwl files from a remote git url."""

    def __init__(self, local_directory: Path):
        self._local_root_directory = local_directory
        self._local_root_directory.mkdir(exist_ok=True)

    def resolve(self, github_url: str) -> List[str]:
        github_path = urlparse(github_url).path.split('/')
        git_owner = github_path[1]
        git_repo = github_path[2]
        git_branch = github_path[4]
        git_path = '/'.join(github_path[5:])
        workflow_files = set()
        root_path = git_path[:git_path.rfind('/')]
        search_stack = {git_path}
        while len(search_stack) > 0:
            current_path = search_stack.pop()
            if current_path not in workflow_files:
                workflow_filename, workflow = self._resolve_file(current_path, git_owner, git_repo, git_branch)
                workflow_files.add(workflow_filename)
                if 'steps' in workflow:
                    for step in workflow['steps']:
                        if isinstance(workflow['steps'][step]['run'], str):
                            file = '/'.join([root_path, workflow['steps'][step]['run']])
                            if file not in workflow_files and file not in search_stack:
                                search_stack.add(file)
        return list(workflow_files)

    def _resolve_file(self, path: str, git_owner: str, git_repo: str, git_branch: str) -> Tuple[str, Dict]:
        url = urljoin(f"https://api.github.com/repos/{git_owner}/{git_repo}/contents/",
                      f"{path}?ref={git_branch}")
        github_response = requests.get(url)
        if github_response.status_code != 200:
            raise RuntimeError(
                f"Error on github api call for: {url}: {github_response.status_code}: {github_response.text}")
        github_response = github_response.json()
        workflow = yaml.load(BytesIO(base64.b64decode(github_response['content'])), yaml.Loader)
        workflow_filename = os.path.join(str(self._local_root_directory), git_owner, git_repo, path)
        Path(os.path.dirname(workflow_filename)).mkdir(exist_ok=True, parents=True)
        with open(workflow_filename, 'w') as f:
            yaml.dump(workflow, f)
        return workflow_filename, workflow
