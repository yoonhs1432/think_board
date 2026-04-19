import streamlit as st
import anthropic
import random
import os
import json
from datetime import datetime
from github_storage import GitHubStorage

GITHUB_REPO = "yoonhs1432/think_board"
TAGS = ["업무", "일상", "아이디어", "기타"]

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
글 유형 (랜덤): 1.관련 뉴스/트렌드(링크포함) 2.비슷한 경험 3.반대의견 4.실용적인 팁
말투: 블라인드/클리앙 스타일
출력 형식 (반드시 JSON만):
{"title":"글 제목","tag":"업무|일상|아이디어|기타","body":"글 본문(200자 내외)","link":"URL또는null","link_title":"링크제목또는null"}"""

def now_str():
    return datetime.now().strftime("%Y/%m/%d %H:%M")

def time_ago(time_str):
    try:
        if len(time_str) <= 11:
            t = datetime.strptime(time_str, "%m/%d %H:%M").replace(year=datetime.now().year)
        else:
            t = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
        diff = datetime.now() - t
        mins = int(diff.total_seconds() / 60)
        if mins < 1: return "방금"
        if mins < 60: return f"{mins}분 전"
        if mins < 1440: return f"{mins//60}시간 전"
        return f"{mins//1440}일 전"
    except:
        return time_str

def pick_reviewer():
    return random.choice(REVIEWER_NAMES)

def get_clients():
    gh_token = os.getenv("GITHUB_TOKEN") or st.session_state.get("gh_token", "")
    ant_key  = os.getenv("ANTHROPIC_API_KEY") or st.session_state.get("ant_key", "")
    storage = GitHubStorage(gh_token, GITHUB_REPO) if gh_token else None
    ai      = anthropic.Anthropic(api_key=ant_key) if ant_key else None
    return storage, ai

def generate_ai_comment(ai, thread, post_body):
    messages = [{"role": "user", "content": f"원글:\n{post_body}"}]
    for item in thread:
        role = "assistant" if item["is_ai"] else "user"
        messages.append({"role": role, "content": item["text"]})
    if messages[-1]["role"] == "assistant":
        messages.append({"role": "user", "content": "계속 리뷰해주세요."})
    resp = ai.messages.create(model="claude-opus-4-5", max_tokens=300,
                               system=COMMENT_SYSTEM_PROMPT, messages=messages)
    return resp.content[0].text.strip(), pick_reviewer()

def generate_ai_post(ai, posts):
    context = "\n\n".join([f"제목: {p['title']}\n내용: {p['body'][:200]}" for p in posts[:5]])
    resp = ai.messages.create(model="claude-opus-4-5", max_tokens=600,
                               system=POST_SYSTEM_PROMPT,
                               messages=[{"role": "user", "content": f"기존 글들:\n{context}\n\n관련 새 글을 작성해주세요."}])
    text = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(text)

st.set_page_config(page_title="ThinkBoard", page_icon="💬", layout="centered")
st.markdown("""
<style>
.block-container { padding: 0.5rem 0.6rem 4rem !important; max-width: 480px !important; }
.stButton button { border-radius: 8px !important; }
.board-title { font-size: 1.1rem; font-weight: 700; color: #333; line-height: 2; }
.post-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.42rem 0.3rem; border-bottom: 1px solid #eee;
}
.post-row.unread { background: #f0eeff; border-radius: 4px; }
.post-list-title { font-size: 0.88rem; color: #222; flex: 1; line-height: 1.3; }
.ai-badge { font-size: 0.65rem; background: #fbe9e7; color: #bf360c; padding: 1px 4px; border-radius: 3px; margin-right: 3px; }
.post-list-right { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; margin-left: 6px; min-width: 50px; }
.post-list-count { font-size: 0.72rem; color: #6c63ff; font-weight: 600; }
.post-list-time { font-size: 0.66rem; color: #aaa; }
.unread-dot { width: 6px; height: 6px; background: #6c63ff; border-radius: 50%; display: inline-block; margin-right: 4px; }
/* 열기 버튼 숨김 */
div[data-testid="stButton"] > button[kind="secondary"] { display: none !important; }
.post-box { background: #f9f9f9; border-left: 3px solid #6c63ff; padding: 0.9rem 1rem; border-radius: 6px; margin-bottom: 0.5rem; font-size: 0.92rem; }
.post-box.ai-post { border-left-color: #ff7043; }
.post-link { display: block; background: #fff3e0; border: 1px solid #ffcc80; border-radius: 6px; padding: 0.5rem 0.75rem; margin-top: 8px; font-size: 0.82rem; color: #e65100; text-decoration: none; }
.comment-ai { background: #f5f5f5; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.3rem 0 0.3rem 1rem; font-size: 0.85rem; }
.comment-me { background: #eef6ff; border: 1px solid #c8dfff; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.3rem 0 0.3rem 1rem; font-size: 0.85rem; }
.comment-new { border-color: #a59bff !important; background: #f0eeff !important; }
.reviewer-name { font-size: 0.73rem; font-weight: 600; color: #555; margin-bottom: 2px; }
.my-name { font-size: 0.73rem; font-weight: 600; color: #2a6dd9; margin-bottom: 2px; }
.meta { color: #bbb; font-size: 0.68rem; margin-top: 3px; }
.tag { display: inline-block; background: #ede9ff; color: #5a52c7; padding: 1px 7px; border-radius: 99px; font-size: 0.7rem; margin-bottom: 3px; }
.tag.ai-tag { background: #fbe9e7; color: #bf360c; }
/* 글쓰기 버튼만 보이게 - primary 버튼 */
div[data-testid="stButton"] > button[kind="primary"] { display: block !important; }
</style>
""", unsafe_allow_html=True)

for key, val in [("page","list"), ("selected_id",None), ("read_posts",set()), ("read_comments",{})]:
    if key not in st.session_state:
        st.session_state[key] = val

with st.sidebar:
    st.markdown("### ⚙️ 설정")
    gh_token = os.getenv("GITHUB_TOKEN") or ""
    ant_key  = os.getenv("ANTHROPIC_API_KEY") or ""
    if gh_token:
        st.success("✅ GitHub 토큰 로드됨")
    else:
        v = st.text_input("GitHub Token", type="password", placeholder="ghp_...")
        if v: st.session_state["gh_token"] = v
    if ant_key:
        st.success("✅ Anthropic 키 로드됨")
    else:
        v = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
        if v: st.session_state["ant_key"] = v
    st.markdown("---")
    st.markdown("**수동 AI 실행**")
    if st.button("🤖 AI 새 글 생성"):
        storage, ai = get_clients()
        if storage and ai:
            posts = storage.load()
            if posts:
                with st.spinner("AI가 글 작성 중..."):
                    try:
                        data = generate_ai_post(ai, posts)
                        posts.insert(0, {"id": int(datetime.now().timestamp()), "title": data.get("title","AI 글"),
                                         "tag": data.get("tag","기타"), "body": data.get("body",""),
                                         "link": data.get("link"), "link_title": data.get("link_title"),
                                         "created": now_str(), "is_ai_post": True, "author": pick_reviewer(), "thread": []})
                        storage.save(posts)
                        st.success("완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    if st.button("💬 AI 댓글 달기"):
        storage, ai = get_clients()
        if storage and ai:
            posts = storage.load()
            my_posts = [p for p in posts if not p.get("is_ai_post")]
            if my_posts:
                target = random.choice(my_posts)
                with st.spinner("AI가 댓글 작성 중..."):
                    try:
                        comment, reviewer = generate_ai_comment(ai, target["thread"], target["body"])
                        for p in posts:
                            if p["id"] == target["id"]:
                                p["thread"].append({"is_ai": True, "text": comment,
                                                    "time": now_str(), "reviewer": reviewer, "is_new": True})
                                break
                        storage.save(posts)
                        st.success(f"'{target['title'][:15]}'에 댓글 추가!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

storage, ai = get_clients()
if not storage or not ai:
    st.warning("사이드바에 GitHub Token과 Anthropic API Key를 입력해주세요.")
    st.stop()

posts = storage.load()

# ══════════════════════════════════════════════════════
# 글쓰기 페이지
# ══════════════════════════════════════════════════════
if st.session_state.page == "write":
    if st.button("← 목록", key="back_write", type="primary"):
        st.session_state.page = "list"
        st.rerun()
    st.markdown("### ✏️ 새 글 쓰기")
    title = st.text_input("제목", placeholder="제목을 입력하세요")
    tag   = st.selectbox("태그", TAGS)
    body  = st.text_area("내용", placeholder="자유롭게 써주세요.", height=180)
    if st.button("게시하기", type="primary"):
        if title.strip() and body.strip():
            with st.spinner("리뷰어가 읽는 중..."):
                first_comment, reviewer = generate_ai_comment(ai, [], body)
            new_post = {"id": int(datetime.now().timestamp()), "title": title.strip(),
                        "tag": tag, "body": body.strip(), "created": now_str(), "is_ai_post": False,
                        "thread": [{"is_ai": True, "text": first_comment,
                                    "time": now_str(), "reviewer": reviewer, "is_new": False}]}
            posts.insert(0, new_post)
            storage.save(posts)
            st.session_state.page = "list"
            st.rerun()
        else:
            st.warning("제목과 내용을 입력해주세요.")

# ══════════════════════════════════════════════════════
# 글 상세 페이지
# ══════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    post = next((p for p in posts if p["id"] == st.session_state.selected_id), None)
    if not post:
        st.session_state.page = "list"
        st.rerun()

    pid = str(post["id"])
    thread = post.get("thread", [])
    st.session_state.read_posts.add(pid)
    st.session_state.read_comments[pid] = len(thread)
    for c in thread:
        c["is_new"] = False
    storage.save(posts)

    if st.button("← 목록", key="back_detail", type="primary"):
        st.session_state.page = "list"
        st.rerun()

    is_ai = post.get("is_ai_post", False)
    link_html = ""
    if post.get("link"):
        link_html = f'<a href="{post["link"]}" target="_blank" class="post-link">🔗 {post.get("link_title") or post["link"]}</a>'

    st.markdown(f"""
    <div class="post-box {'ai-post' if is_ai else ''}">
        <span class="tag {'ai-tag' if is_ai else ''}">{post['tag']}</span>
        {"<span style='font-size:0.72rem;color:#ff7043;margin-left:4px;'>🤖 AI 작성</span>" if is_ai else ""}
        <br><strong style="font-size:1rem;">{post['title']}</strong>
        <p style="margin-top:6px;font-size:0.9rem;color:#333;line-height:1.6;">{post['body']}</p>
        {link_html}
        <div class="meta">{"🤖 " + post.get("author","AI") if is_ai else "✍️ 나"} · {time_ago(post['created'])}</div>
    </div>
    """, unsafe_allow_html=True)

    if thread:
        st.markdown(f"<div style='font-size:0.78rem;color:#888;margin:0.4rem 0 0.2rem;'>댓글 {len(thread)}개</div>",
                    unsafe_allow_html=True)
        for c in thread:
            new_cls = "comment-new" if c.get("is_new") else ""
            if c["is_ai"]:
                st.markdown(f"""
                <div class="comment-ai {new_cls}">
                    <div class="reviewer-name">👤 {c.get('reviewer','익명')} {"🆕" if c.get('is_new') else ""}</div>
                    {c['text']}
                    <div class="meta">{time_ago(c['time'])} · 추천 {random.randint(1,12)}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="comment-me">
                    <div class="my-name">✍️ 글쓴이</div>
                    {c['text']}
                    <div class="meta">{time_ago(c['time'])}</div>
                </div>""", unsafe_allow_html=True)

    reply = st.text_area("댓글 입력", placeholder="댓글을 입력하세요...",
                          height=80, label_visibility="collapsed")
    if st.button("답변 달기 ↩", type="primary"):
        if reply.strip():
            idx = next((i for i, p in enumerate(posts) if p["id"] == post["id"]), None)
            if idx is not None:
                posts[idx]["thread"].append({"is_ai": False, "text": reply.strip(), "time": now_str()})
                with st.spinner("리뷰어가 읽는 중..."):
                    ai_reply, reviewer = generate_ai_comment(ai, posts[idx]["thread"], post["body"])
                posts[idx]["thread"].append({"is_ai": True, "text": ai_reply,
                                             "time": now_str(), "reviewer": reviewer, "is_new": False})
                st.session_state.read_comments[pid] = len(posts[idx]["thread"])
                storage.save(posts)
                st.rerun()

    if st.button("🗑️ 글 삭제"):
        posts = [p for p in posts if p["id"] != post["id"]]
        storage.save(posts)
        st.session_state.page = "list"
        st.rerun()

# ══════════════════════════════════════════════════════
# 목록 페이지
# ══════════════════════════════════════════════════════
else:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("<div class='board-title'>💬 ThinkBoard</div>", unsafe_allow_html=True)
    with col2:
        if st.button("✏️ 글쓰기", key="write_btn", type="primary", use_container_width=True):
            st.session_state.page = "write"
            st.rerun()

    st.markdown("<hr style='margin:0.2rem 0 0.3rem;border:none;border-top:2px solid #6c63ff'>",
                unsafe_allow_html=True)

    if not posts:
        st.markdown("<div style='text-align:center;color:#aaa;margin-top:3rem;'>첫 글을 써보세요!</div>",
                    unsafe_allow_html=True)
    else:
        for post in posts:
            pid = str(post["id"])
            thread = post.get("thread", [])
            cnt = len(thread)
            is_ai = post.get("is_ai_post", False)

            # 수정 5: 세션 기반 읽음 상태 (새로고침 후에도 세션 내 유지)
            never_read   = pid not in st.session_state.read_posts
            new_comments = (pid in st.session_state.read_comments and
                            cnt > st.session_state.read_comments[pid])
            has_new_flag = any(c.get("is_new") for c in thread)
            is_unread    = never_read or new_comments or has_new_flag

            dot      = "<span class='unread-dot'></span>" if is_unread else ""
            ai_badge = "<span class='ai-badge'>AI</span>" if is_ai else ""
            cnt_str  = f"[{cnt}]" if cnt else ""

            # 수정 3: 간격 줄인 리스트 행
            st.markdown(f"""
            <div class="post-row {'unread' if is_unread else ''}">
                <div class="post-list-title">{dot}{ai_badge}{post['title']}</div>
                <div class="post-list-right">
                    <span class="post-list-count">{cnt_str}</span>
                    <span class="post-list-time">{time_ago(post['created'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 수정 2: 제목 클릭으로 이동 (버튼은 CSS로 숨기고 위 HTML 행과 겹침)
            if st.button(post['title'], key=f"open_{post['id']}"):
                st.session_state.read_posts.add(pid)
                st.session_state.read_comments[pid] = cnt
                st.session_state.selected_id = post["id"]
                st.session_state.page = "detail"
                st.rerun()
