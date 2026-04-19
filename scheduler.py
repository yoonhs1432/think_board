"""
scheduler.py — GitHub Actions에서 실행되는 백그라운드 스케줄러
posts.json을 GitHub API로 읽고 AI 댓글/새 글을 추가합니다.
"""

import anthropic
import json
import os
import random
from datetime import datetime
from github_storage import GitHubStorage

GITHUB_REPO = "yoonhs1432/think_board"

REVIEWER_NAMES = [
    "달빛산책로", "새벽감성", "커피한잔해요", "조용한바람",
    "퇴근후맥주", "공대생김씨", "생각많은직장인", "현실주의자박씨",
    "밤새우는사람", "논리충", "팩트폭격기", "냉정한시선",
    "디테일왕", "까다로운리뷰어", "지나가던엔지니어"
]

COMMENT_SYSTEM_PROMPT = """당신은 대한민국 직장인 커뮤니티(블라인드, 클리앙)에서 댓글 다는 현실적인 직장인입니다.
허점을 찾아 날카롭게 지적하거나 현실적인 질문을 던집니다.
말투: 반말/커뮤니티체, "~임", "ㄹㅇ", "솔직히" 등 자연스럽게.
규칙: 칭찬 없이 질문/지적만, 80자 내외, 이모지 1개."""

POST_SYSTEM_PROMPT = """당신은 대한민국 직장인 커뮤니티에 글을 올리는 익명 사용자입니다.
기존 글들을 참고해서 관련 새 글을 작성합니다.

글 유형 (랜덤):
1. 관련 뉴스/트렌드 공유 (링크 포함)
2. 비슷한 경험 공유
3. 반대 의견/다른 시각
4. 실용적인 팁

말투: 블라인드/클리앙 스타일, 자연스러운 구어체

출력 형식 (반드시 JSON만, 다른 텍스트 없이):
{
  "title": "글 제목",
  "tag": "업무|일상|아이디어|기타",
  "body": "글 본문 (200자 내외)",
  "link": "관련 URL 또는 null",
  "link_title": "링크 제목 또는 null"
}"""

def now_str():
    return datetime.now().strftime("%m/%d %H:%M")

def pick_reviewer():
    return random.choice(REVIEWER_NAMES)

def add_comment(storage, client, posts):
    my_posts = [p for p in posts if not p.get("is_ai_post", False)]
    if not my_posts:
        print("  → 내 글 없음, 스킵")
        return

    target = random.choice(my_posts)
    thread = target.get("thread", [])

    messages = [{"role": "user", "content": f"원글:\n{target['body']}"}]
    for item in thread:
        role = "assistant" if item["is_ai"] else "user"
        messages.append({"role": role, "content": item["text"]})
    if messages[-1]["role"] == "assistant":
        messages.append({"role": "user", "content": "계속 리뷰해주세요."})

    resp = client.messages.create(
        model="claude-opus-4-5", max_tokens=300,
        system=COMMENT_SYSTEM_PROMPT, messages=messages
    )
    comment  = resp.content[0].text.strip()
    reviewer = pick_reviewer()

    for p in posts:
        if p["id"] == target["id"]:
            p.setdefault("thread", []).append({
                "is_ai": True, "text": comment,
                "time": now_str(), "reviewer": reviewer, "is_new": True
            })
            break

    storage.save(posts)
    print(f"  ✅ 댓글 → '{target['title'][:20]}' / {reviewer}: {comment[:40]}...")

def add_post(storage, client, posts):
    context = "\n\n".join([
        f"제목: {p['title']}\n내용: {p['body'][:200]}"
        for p in posts[:5]
    ])
    resp = client.messages.create(
        model="claude-opus-4-5", max_tokens=600,
        system=POST_SYSTEM_PROMPT,
        messages=[{"role": "user",
                   "content": f"기존 글들:\n{context}\n\n위 글들과 관련된 새 글을 작성해주세요."}]
    )
    text = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
    data = json.loads(text)

    new_post = {
        "id": int(datetime.now().timestamp()),
        "title": data.get("title","AI 글"),
        "tag": data.get("tag","기타"),
        "body": data.get("body",""),
        "link": data.get("link"),
        "link_title": data.get("link_title"),
        "created": now_str(),
        "is_ai_post": True,
        "author": pick_reviewer(),
        "thread": []
    }
    posts.insert(0, new_post)
    storage.save(posts)
    print(f"  ✅ 새 글 → '{new_post['title']}'")

def main():
    gh_token = os.environ.get("GITHUB_TOKEN")
    ant_key  = os.environ.get("ANTHROPIC_API_KEY")

    if not gh_token or not ant_key:
        print("❌ GITHUB_TOKEN 또는 ANTHROPIC_API_KEY 없음")
        return

    storage = GitHubStorage(gh_token, GITHUB_REPO)
    client  = anthropic.Anthropic(api_key=ant_key)
    posts   = storage.load()

    if not posts:
        print("글 없음, 종료")
        return

    # GitHub Actions workflow에서 어떤 작업을 할지 환경변수로 결정
    action = os.environ.get("SCHEDULER_ACTION", "comment")  # comment | post

    print(f"[{now_str()}] 실행: {action}")
    if action == "post":
        add_post(storage, client, posts)
    else:
        add_comment(storage, client, posts)

if __name__ == "__main__":
    main()
