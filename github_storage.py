"""
github_storage.py — GitHub API로 posts.json을 읽고 씁니다.
저장소의 posts.json이 DB 역할을 합니다.
"""

import json
import base64
import requests
from datetime import datetime

GITHUB_API = "https://api.github.com"

class GitHubStorage:
    def __init__(self, token: str, repo: str, branch: str = "main"):
        self.token = token
        self.repo = repo          # "yoonhs1432/think_board"
        self.branch = branch
        self.file_path = "posts.json"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _get_file_info(self):
        """파일의 현재 SHA와 내용을 가져옵니다."""
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.file_path}"
        r = requests.get(url, headers=self.headers,
                         params={"ref": self.branch})
        if r.status_code == 404:
            return None, None
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

    def load(self) -> list:
        """posts.json 불러오기. 없으면 빈 리스트 반환."""
        posts, _ = self._get_file_info()
        return posts if posts is not None else []

    def save(self, posts: list):
        """posts.json 저장 (없으면 생성, 있으면 업데이트)."""
        _, sha = self._get_file_info()

        content = base64.b64encode(
            json.dumps(posts, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")

        url = f"{GITHUB_API}/repos/{self.repo}/contents/{self.file_path}"
        payload = {
            "message": f"update posts {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": content,
            "branch": self.branch
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(url, headers=self.headers, json=payload)
        r.raise_for_status()
