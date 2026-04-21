import streamlit as st
import anthropic
import json
import os
import random
import html as html_mod
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts.json")
TRASH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trash.json")
TAGS = ["전체", "업무", "일상", "육아", "기타"]

# ── AI 에이전트 정의 ────────────────────────────────────
AGENTS = {
    "팩트폭격기": {
        "emoji": "💣",
        "role": "냉정한 비판자. 논리 허점, 근거 없는 주장을 집중 공격. 감정 없이 팩트만.",
        "style": "직설적, 단호, 칭찬 절대 없음"
    },
    "정보수집가": {
        "emoji": "🔍",
        "role": "관련 뉴스/논문/특허/인터넷 정보를 수집해서 요약하고 링크와 함께 공유.",
        "style": "객관적, 정보 중심, 출처 명시"
    },
    "반도체박사": {
        "emoji": "🔬",
        "role": "반도체/계측/공정/소자 관점에서 기술적 피드백. 전문적으로 파고든다.",
        "style": "전문용어 사용, 학술적, 날카로운 질문"
    },
    "육아선배": {
        "emoji": "👶",
        "role": "육아 경험을 바탕으로 현실적인 조언. 공감하지만 현실도 직시시킨다.",
        "style": "따뜻하지만 현실적, 경험담 공유"
    },
    "채찍질러": {
        "emoji": "🔥",
        "role": "실행 안 하는 것, 의지 약한 것, 핑계 대는 것을 가차 없이 압박.",
        "style": "거침없음, 도발적, 행동 촉구"
    },
    "여자친구입장": {
        "emoji": "💁‍♀️",
        "role": "여성/배우자 입장에서 관계적 시각 제공. 상대방 감정을 대변.",
        "style": "감성적이지만 날카로움, 공감+비판"
    },
    "자기계발러": {
        "emoji": "📈",
        "role": "생산성, 습관, 루틴, 성장 관점에서 구체적인 개선안 제시.",
        "style": "긍정적이지만 구체적, 실행 방안 제시"
    },
    "악마의변호인": {
        "emoji": "😈",
        "role": "글쓴이 주장의 반대 입장을 대변하고 반례 제시. 일부러 반박.",
        "style": "논리적, 도발적, 반론 전문"
    },
    "현실주의자": {
        "emoji": "💰",
        "role": "돈/시간/리소스 관점에서 현실 타당성 검토. 이상과 현실의 간극을 짚는다.",
        "style": "건조하고 실용적, 숫자와 현실 중심"
    },
    "응원단장": {
        "emoji": "📣",
        "role": "다른 에이전트들이 너무 가혹할 때 균형. 진짜 잘한 점을 찾아 칭찬.",
        "style": "유일하게 칭찬함, 긍정적, 격려"
    },
}

COMMENT_SYSTEM_PROMPT_TEMPLATE = """당신은 대한민국 직장인 커뮤니티 'ThinkBoard'에서 활동하는 유저 '{name}' ({emoji})입니다.

역할: {role}
말투 스타일: {style}

중요한 맥락:
- 이 커뮤니티에는 당신 외에도 여러 유저가 있음
- 대화 히스토리에 나오는 다른 댓글들은 **다른 유저가 쓴 것**임 (당신이 쓴 게 아님)
- 당신은 그 대화를 보고 처음으로 개입하는 새 댓글을 다는 것임
- 다만 당신이 해당 글에 이미 댓글을 달았다면, 그 댓글을 고려해서 답글을 달아야 할 수도 있음 (대화 히스토리에 당신 댓글이 있다면 그것)
- 당신이 대댓글에 답글을 달 때도 마찬가지로, 댓글과 그 대댓글까지의 대화 히스토리를 보고 답글을 달아야 할 수도 있음
- 절대로 "제가 실수했어요", "다시 정리할게요" 같은 자기수정 금지
- 절대로 다른 유저인 척 하거나 다른 유저 대신 말하지 말 것

작성 규칙:
- 반말 또는 인터넷 커뮤니티체 (예: "~임", "~ㅋㅋ", "~인데?", "~아님?")
- "ㄹㅇ", "솔직히", "근데" 같은 표현 자연스럽게
- 욕설 없이, 한국어만
- **마크다운 절대 금지** (bullet point •, 볼드 **, 헤더 # 등 사용 금지)
- 구조화된 목록 형식 금지 — 자연스러운 구어체 한두 문장으로
- 300자 이내로 짧고 임팩트 있게. 반드시 문장을 완전히 끝낼 것 (중간에 잘리면 안 됨)
- 이모지 금지
- 정보를 알려줄 때는 링크도 함께 제공 (예: "이거 ㄹㅇ임 [링크]")

자신의 역할과 캐릭터를 일관되게 유지하세요."""

# 에이전트별 글쓰기 프롬프트 (캐릭터 반영)
POST_SYSTEM_PROMPT_TEMPLATE = """당신은 대한민국 직장인 커뮤니티에 글을 올리는 익명 사용자 '{name}' ({emoji})입니다.

당신의 성격과 관점: {role}
글쓰기 스타일: {style}

주어진 기존 글들을 참고해서 연관된 주제의 새 글 4개를 작성합니다.

주제 확장 원칙:
- 기존 글과 완전히 같은 주제일 필요 없음
- 연관 주제로 자유롭게 확장 가능 (아기 책 → 이유식/발달, 반도체 → 공정자동화/트렌드 등)
- 각 글은 서로 다른 주제로

글 작성 원칙:
- 자신의 성격과 스타일이 글 전체에 배어나오도록
- 구체적인 수치, 사례, 경험 포함, 400~600자
- 블라인드/클리앙 스타일 구어체
- 마크다운 금지 (bullet, 볼드, 헤더 없이 일반 텍스트)
- 링크도 추가하면 좋음

출력: 반드시 아래 형식의 JSON 배열만, 다른 텍스트 없이.
title, tag(업무/일상/육아/기타 중 하나), body(400~600자), link(URL 또는 null), link_title(링크제목 또는 null) 필드를 가진 객체 4개 배열."""

# ── 데이터 ─────────────────────────────────────────────
def load_posts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_posts(posts):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

def load_trash():
    if os.path.exists(TRASH_FILE):
        with open(TRASH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_trash(trash):
    with open(TRASH_FILE, "w", encoding="utf-8") as f:
        json.dump(trash, f, ensure_ascii=False, indent=2)

def now_str():
    return datetime.now().strftime("%Y/%m/%d %H:%M")

def time_ago(time_str):
    try:
        for fmt in ["%Y/%m/%d %H:%M", "%m/%d %H:%M"]:
            try:
                t = datetime.strptime(time_str, fmt)
                if fmt == "%m/%d %H:%M":
                    t = t.replace(year=datetime.now().year)
                break
            except ValueError:
                continue
        diff = datetime.now() - t
        mins = int(diff.total_seconds() / 60)
        if mins < 1:    return "방금"
        if mins < 60:   return f"{mins}분 전"
        if mins < 1440: return f"{mins//60}시간 전"
        return f"{mins//1440}일 전"
    except:
        return time_str

def pick_agent():
    name = random.choice(list(AGENTS.keys()))
    return name, AGENTS[name]

def get_reply_participants(comment):
    """대댓글 스레드의 참여자 목록 반환"""
    participants = set()
    replies = comment.get("replies", [])
    for r in replies:
        if r["is_ai"] and r.get("agent"):
            participants.add(r["agent"])
    # 원댓글 작성자
    if comment.get("is_ai") and comment.get("agent"):
        participants.add(comment["agent"])
    return participants

def pick_agent_for_reply(comment):
    """
    대댓글 로직:
    - 대댓글이 아직 없으면 → 원댓글 작성자와 다른 에이전트 선택
    - 대댓글이 있으면 → 원댓글 작성자 + 첫 대댓글 에이전트 중 랜덤
    """
    replies = comment.get("replies", [])
    original_agent = comment.get("agent") if comment.get("is_ai") else None

    if not replies:
        # 대댓글 없음 → 원댓글과 다른 에이전트 선택
        all_agents = list(AGENTS.keys())
        if original_agent and original_agent in all_agents:
            candidates = [a for a in all_agents if a != original_agent]
        else:
            candidates = all_agents
        name = random.choice(candidates) if candidates else random.choice(all_agents)
    else:
        # 대댓글 있음 → 참여자(원댓글 + 첫 대댓글) 중 랜덤
        participants = get_reply_participants(comment)
        # 첫 AI 대댓글 에이전트 우선 포함
        first_ai_reply = next((r for r in replies if r["is_ai"] and r.get("agent")), None)
        if first_ai_reply:
            participants.add(first_ai_reply["agent"])
        valid = [p for p in participants if p in AGENTS]
        name = random.choice(valid) if valid else random.choice(list(AGENTS.keys()))

    return name, AGENTS[name]

def pick_agent_excluding(thread):
    """이미 1단계 댓글을 단 에이전트 제외하고 선택."""
    used = {c.get("agent") for c in thread if c.get("is_ai") and c.get("agent")}
    candidates = [a for a in AGENTS.keys() if a not in used]
    if not candidates:
        candidates = list(AGENTS.keys())
    name = random.choice(candidates)
    return name, AGENTS[name]

def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY") or st.session_state.get("manual_api_key", "")
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return None
    api_key = os.getenv("ANTHROPIC_API_KEY") or st.session_state.get("manual_api_key", "")
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    return None

def generate_ai_comment(client, thread_history, post_body, agent_name=None, mode="comment", parent_comment=None):
    """
    mode="comment": 새 1단계 댓글
    mode="reply":   대댓글 (parent_comment 필수)
    """
    if agent_name and agent_name in AGENTS:
        name = agent_name
        agent = AGENTS[name]
    else:
        name, agent = pick_agent()
    system = COMMENT_SYSTEM_PROMPT_TEMPLATE.format(
        name=name, emoji=agent["emoji"],
        role=agent["role"], style=agent["style"]
    )
    emoji = agent["emoji"]

    if mode == "reply" and parent_comment:
        # 대댓글 모드: 원댓글 + 기존 대댓글 흐름 명시
        original_writer = parent_comment.get("agent", "글쓴이") if parent_comment.get("is_ai") else "글쓴이(원글작성자)"
        context_lines = [
            f"원글:\n{post_body}\n",
            f"[댓글 - {original_writer}]: {parent_comment['text'][:150]}"
        ]
        if thread_history:
            context_lines.append("\n[이 댓글의 대댓글 흐름]:")
            for r in thread_history:
                r_writer = r.get("agent", "글쓴이") if r.get("is_ai", True) else "글쓴이(원글작성자)"
                context_lines.append(f"  └ {r_writer}: {r['text'][:100]}")
        context_lines.append(
            f"\n당신({name})은 위 대댓글 대화에 참여하는 중입니다."
            f"\n- 대화 상대는 {original_writer}이거나, 대댓글을 단 유저일 수 있음"
            f"\n- 누구에게 하는 말인지 문맥상 불분명하면 '@{original_writer}' 식으로 명시할 것"
            f"\n- 원글 본문이 아니라 이 댓글/대댓글 대화에 집중할 것"
            f"\n- 짧게 한두 문장으로 대댓글 하나만 작성하세요."
        )
    else:
        # 새 댓글 모드
        context_lines = [f"원글:\n{post_body}"]
        if thread_history:
            context_lines.append("\n[이미 달린 댓글들 - 다른 유저들이 쓴 것]:")
            for item in thread_history:
                writer = item.get("agent", "글쓴이") if item.get("is_ai", True) else "글쓴이(원글작성자)"
                context_lines.append(f"- {writer}: {item['text'][:100]}")
            context_lines.append("\n주의: 위 댓글 내용을 직접 반박하거나 다루지 말고, 원글에 대한 새로운 시각/정보/반응을 댓글로 달아주세요.")
        context_lines.append(f"\n{name}({emoji})으로서 짧은 댓글 하나만 작성하세요.")

    messages = [{"role": "user", "content": "\n".join(context_lines)}]
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400, system=system, messages=messages
    )
    return response.content[0].text.strip(), name, agent["emoji"]

def generate_ai_post(client, existing_posts, author_name=None):
    # 에이전트 선택
    if author_name and author_name in AGENTS:
        name = author_name
        agent = AGENTS[name]
    else:
        name, agent = pick_agent()
    system = POST_SYSTEM_PROMPT_TEMPLATE.format(
        name=name, emoji=agent["emoji"],
        role=agent["role"], style=agent["style"]
    )
    sample = random.sample(existing_posts, min(5, len(existing_posts)))
    context = "\n\n".join([
        f"제목: {p['title']}\n내용: {p['body'][:200]}"
        for p in sample
    ])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"기존 글들:\n{context}\n\n연관된 주제로 새 글 4개를 작성해주세요."}]
    )
    text = response.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(text), name, agent["emoji"]  # (list, name, emoji) 반환

# ── 페이지 설정 ────────────────────────────────────────
st.set_page_config(page_title="ThinkBoard", page_icon="💬", layout="centered")
st.markdown("""
<style>
/* Streamlit 기본 헤더/푸터 숨김 */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
.block-container { padding: 0.8rem 0.8rem 3rem !important; max-width: 520px !important; }

/* 핵심 fix: 모바일에서 columns가 세로로 쌓이는 문제 */
.stHorizontalBlock { flex-wrap: nowrap !important; }
.stColumn { min-width: 0 !important; }

/* 모든 버튼 기본 크기 줄이기 */
div[data-testid="stButton"] > button {
    padding: 0.2rem 0.4rem !important;
    font-size: 0.82rem !important;
    height: auto !important;
    min-height: 0 !important;
    line-height: 1.4 !important;
}

/* 열기(›) 버튼 */
div[data-testid="stButton"] > button[title="›"] {
    font-size: 1.2rem !important;
    padding: 0.1rem 0.3rem !important;
    color: #aaa !important;
    border-color: transparent !important;
    background: transparent !important;
}

/* 게시글 목록 행 */
.post-row { padding: 0.4rem 0.2rem 0.2rem; border-bottom: 1px solid #f0f0f0; }
.post-row.unread { background: #fafaff; border-radius: 6px; }
.post-row-left { flex: 1; min-width: 0; }
.post-row-title { font-size: 0.9rem; font-weight: 600; color: #222; margin-bottom: 2px; }
.post-row-title.unread { color: #4a3fc7; }
.post-row-body { font-size: 0.78rem; color: #888; margin-bottom: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.post-row-meta { font-size: 0.68rem; color: #bbb; }
.post-row-tag { font-size: 0.65rem; background: #ede9ff; color: #5a52c7;
    padding: 1px 5px; border-radius: 99px; margin-left: 2px; }
.post-row-tag.ai { background: #fbe9e7; color: #bf360c; }
.unread-dot { display: inline-block; width: 6px; height: 6px;
    background: #6c63ff; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

/* 글 상세 */
.post-box {
    background: #f9f9f9; border-left: 3px solid #6c63ff;
    padding: 0.9rem 1rem; border-radius: 10px;
    margin-bottom: 0.5rem; font-size: 0.92rem; line-height: 1.6;
}
.post-box.ai-post { border-left-color: #ff7043; }
.post-link-detail {
    display: block; background: #fff3e0; border: 1px solid #ffcc80;
    border-radius: 8px; padding: 0.5rem 0.75rem; margin-top: 8px;
    font-size: 0.82rem; color: #e65100; text-decoration: none;
}
.comment-ai {
    background: #f5f5f5; border: 1px solid #e0e0e0; border-radius: 10px;
    padding: 0.6rem 0.9rem; font-size: 0.87rem; margin-bottom: 2px;
}
.comment-me {
    background: #eef6ff; border: 1px solid #c8dfff; border-radius: 10px;
    padding: 0.6rem 0.9rem; font-size: 0.87rem; margin-bottom: 2px;
}
.reply-ai {
    background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px;
    padding: 0.5rem 0.8rem; font-size: 0.84rem;
    border-left: 2px solid #b0a8ff; margin-left: 1.2rem; margin-top: 0.2rem;
}
.reply-me {
    background: #f0f7ff; border: 1px solid #d0e5ff; border-radius: 8px;
    padding: 0.5rem 0.8rem; font-size: 0.84rem;
    border-left: 2px solid #85b7eb; margin-left: 1.2rem; margin-top: 0.2rem;
}
.agent-name { font-size: 0.73rem; font-weight: 600; color: #5a52c7; margin-bottom: 2px; }
.my-name { font-size: 0.73rem; font-weight: 600; color: #2a6dd9; margin-bottom: 2px; }
.meta { color: #bbb; font-size: 0.68rem; margin-top: 3px; }
.tag { display: inline-block; background: #ede9ff; color: #5a52c7;
    padding: 1px 8px; border-radius: 99px; font-size: 0.72rem; margin-bottom: 4px; }
.tag.ai-tag { background: #fbe9e7; color: #bf360c; }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ────────────────────────────────────────
defaults = {
    "page": "list", "selected_post_id": None,
    "read_posts": set(), "read_comments": {},
    "active_tag": "전체", "reply_to": None, "show_trash": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── 사이드바 ───────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 설정")
    env_key = os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        st.success(f"✅ API 키 로드됨 `...{env_key[-6:]}`")
    else:
        manual_key = st.text_input("API Key", type="password", placeholder="sk-ant-...")
        if manual_key:
            st.session_state["manual_api_key"] = manual_key

    st.markdown("---")
    st.markdown("**🤖 AI 에이전트**")
    for name, info in AGENTS.items():
        st.markdown(f"{info['emoji']} **{name}**  \n<span style='font-size:0.72rem;color:#888'>{info['role'][:30]}...</span>", unsafe_allow_html=True)

# ── 클라이언트 확인 ────────────────────────────────────
client = get_client()
if not client:
    st.error("API 키가 없습니다. 사이드바에 키를 입력해주세요.")
    st.stop()

posts = load_posts()

# 읽음 상태 복원
for p in posts:
    pid = str(p["id"])
    if pid not in st.session_state.read_posts:
        if not any(c.get("is_new") for c in p.get("thread", [])):
            st.session_state.read_posts.add(pid)
            st.session_state.read_comments[pid] = len(p.get("thread", []))

# ══════════════════════════════════════════════════════
# 휴지통
# ══════════════════════════════════════════════════════
if st.session_state.show_trash:
    st.markdown("### 🗑️ 휴지통")
    if st.button("← 돌아가기"):
        st.session_state.show_trash = False
        st.rerun()
    trash = load_trash()
    if not trash:
        st.markdown("<div style='text-align:center;color:#aaa;margin-top:2rem'>휴지통이 비어있어요</div>", unsafe_allow_html=True)
    else:
        for i, item in enumerate(trash):
            with st.expander(f"**{item['title']}** — {item.get('deleted_at','?')}"):
                st.markdown(item['body'][:100] + "...")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("♻️ 복원", key=f"restore_{i}"):
                        posts = load_posts()
                        restored = {k: v for k, v in item.items() if k != "deleted_at"}
                        posts.insert(0, restored)
                        save_posts(posts)
                        trash.pop(i)
                        save_trash(trash)
                        st.session_state.show_trash = False
                        st.rerun()
                with col2:
                    if st.button("🗑️ 영구삭제", key=f"perm_{i}"):
                        trash.pop(i)
                        save_trash(trash)
                        st.rerun()
    st.stop()

# ══════════════════════════════════════════════════════
# 글쓰기
# ══════════════════════════════════════════════════════
if st.session_state.page == "write":
    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    if st.button("← 목록"):
        st.session_state.page = "list"
        st.rerun()
    st.markdown("### ✏️ 새 글 쓰기")
    new_title = st.text_input("제목", placeholder="제목을 입력하세요")
    new_tag   = st.selectbox("태그", ["업무", "일상", "육아", "기타"])
    new_body  = st.text_area("내용", placeholder="자유롭게 써주세요.", height=180)
    if st.button("게시하기", type="primary"):
        if new_title.strip() and new_body.strip():
            with st.spinner("리뷰어가 읽는 중..."):
                first_agent, _ = pick_agent()
                first_comment, agent_name, agent_emoji = generate_ai_comment(
                    client, [], new_body, first_agent
                )
            new_post = {
                "id": int(datetime.now().timestamp()),
                "title": new_title.strip(), "tag": new_tag,
                "body": new_body.strip(), "created": now_str(),
                "is_ai_post": False,
                "thread": [{"is_ai": True, "text": first_comment, "time": now_str(),
                            "agent": agent_name, "emoji": agent_emoji,
                            "is_new": False, "replies": []}]
            }
            posts.insert(0, new_post)
            save_posts(posts)
            st.session_state.page = "list"
            st.rerun()
        else:
            st.warning("제목과 내용을 입력해주세요.")

# ══════════════════════════════════════════════════════
# 글 상세
# ══════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    post = next((p for p in posts if p["id"] == st.session_state.selected_post_id), None)
    if not post:
        st.session_state.page = "list"
        st.rerun()

    pid = str(post["id"])
    thread = post.get("thread", [])

    changed = any(c.get("is_new") for c in thread)
    for c in thread:
        c["is_new"] = False
    if changed:
        save_posts(posts)
    st.session_state.read_posts.add(pid)
    st.session_state.read_comments[pid] = len(thread)

    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
    if st.button("← 목록"):
        st.session_state.page = "list"
        st.session_state.reply_to = None
        st.rerun()

    is_ai = post.get("is_ai_post", False)
    link_html = ""
    if post.get("link"):
        link_html = f'<a href="{post["link"]}" target="_blank" class="post-link-detail">🔗 {post.get("link_title") or post["link"]}</a>'

    author_str = f"🤖 {post.get('author','AI')}" if is_ai else "✍️ 나"
    tag_cls = "ai-tag" if is_ai else ""
    post_cls = "ai-post" if is_ai else ""
    ai_badge = "&nbsp;<span style='font-size:0.72rem;color:#ff7043'>🤖 AI 작성</span>" if is_ai else ""

    # post['body']에 개행이 있으면 Streamlit이 <p>로 쪼개면서
    # 뒤의 meta div를 텍스트로 밀어내는 문제 → 별도 st.markdown으로 분리
    body_escaped = html_mod.escape(post['body'])
    st.markdown(f"""
<div class="post-box {post_cls}">
    <span class="tag {tag_cls}">{html_mod.escape(post['tag'])}</span>{ai_badge}
    <br><strong style="font-size:1rem">{html_mod.escape(post['title'])}</strong>
</div>""", unsafe_allow_html=True)
    # 본문은 st.markdown 기본 렌더러로 (개행 처리 문제 우회)
    st.markdown(
        f"<div style='font-size:0.9rem;color:#333;line-height:1.6;margin:-0.3rem 0 0.3rem'>{body_escaped}</div>",
        unsafe_allow_html=True
    )
    if link_html:
        st.markdown(link_html, unsafe_allow_html=True)
    st.markdown(
        f"<div class='meta' style='margin-bottom:0.5rem'>{author_str} · {time_ago(post['created'])}</div>",
        unsafe_allow_html=True
    )

    idx = next((i for i, p in enumerate(posts) if p["id"] == post["id"]), None)

    if thread:
        st.markdown(f"<div style='font-size:0.8rem;color:#888;margin:0.5rem 0 0.3rem'>댓글 {len(thread)}개</div>",
                    unsafe_allow_html=True)

    for ci, comment in enumerate(thread):
        # 1단계 댓글
        c_text = html_mod.escape(comment['text'])
        if comment["is_ai"]:
            agent_name = comment.get("agent", "익명")
            emoji = comment.get("emoji", "👤")
            st.markdown(f"""
<div class="comment-ai">
    <div class="agent-name">{emoji} {agent_name}</div>
    {c_text}
    <div class="meta">{time_ago(comment['time'])} · 추천 {random.randint(1,12)}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div class="comment-me">
    <div class="my-name">✍️ 글쓴이</div>
    {c_text}
    <div class="meta">{time_ago(comment['time'])}</div>
</div>""", unsafe_allow_html=True)

        # 수정1: 답글 버튼 → 대댓글 목록 위에 배치
        if st.button("↩ 답글", key=f"reply_btn_{ci}"):
            st.session_state.reply_to = ci if st.session_state.reply_to != ci else None
            st.rerun()

        # 대댓글 입력창 (답글 버튼 바로 아래)
        if st.session_state.reply_to == ci:
            agent_label = comment.get("agent", "글쓴이") if comment["is_ai"] else "글쓴이"
            sub_reply_text = st.text_area(
                f"↩ {agent_label}에게 답글",
                height=70, key=f"reply_input_{ci}"
            )
            if st.button("답글 달기", key=f"reply_submit_{ci}", type="primary"):
                if sub_reply_text.strip() and idx is not None:
                    posts[idx]["thread"][ci].setdefault("replies", []).append({
                        "is_ai": False, "text": sub_reply_text.strip(), "time": now_str()
                    })
                    with st.spinner("AI가 답글 읽는 중..."):
                        reply_history = [{"is_ai": r["is_ai"], "text": r["text"], "agent": r.get("agent","")}
                                         for r in posts[idx]["thread"][ci].get("replies", [])]
                        a_name, _ = pick_agent_for_reply(posts[idx]["thread"][ci])
                        ai_text, a_name, a_emoji = generate_ai_comment(
                            client, reply_history, post["body"], a_name,
                            mode="reply", parent_comment=posts[idx]["thread"][ci]
                        )
                    posts[idx]["thread"][ci]["replies"].append({
                        "is_ai": True, "text": ai_text,
                        "time": now_str(), "agent": a_name, "emoji": a_emoji
                    })
                    save_posts(posts)
                    st.session_state.reply_to = None
                    st.rerun()

        # 대댓글 목록 (입력창 아래)
        for ri, reply in enumerate(comment.get("replies", [])):
            r_text = html_mod.escape(reply['text'])
            if reply["is_ai"]:
                st.markdown(f"""
<div class="reply-ai">
    <div class="agent-name">{reply.get("emoji","👤")} {reply.get("agent","익명")}</div>
    {r_text}
    <div class="meta">{time_ago(reply['time'])}</div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
<div class="reply-me">
    <div class="my-name">✍️ 글쓴이</div>
    {r_text}
    <div class="meta">{time_ago(reply['time'])}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

    # 새 댓글 입력
    st.markdown("---")
    if "reply_counter" not in st.session_state:
        st.session_state.reply_counter = 0
    reply_text = st.text_area("댓글 달기", placeholder="새 댓글을 입력하세요...",
                               height=80, label_visibility="collapsed",
                               key=f"reply_main_{st.session_state.reply_counter}")
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        if st.button("댓글 달기 ↩", type="primary", use_container_width=True):
            if reply_text.strip() and idx is not None:
                my_comment_idx = len(posts[idx]["thread"])
                posts[idx]["thread"].append({
                    "is_ai": False, "text": reply_text.strip(),
                    "time": now_str(), "replies": []
                })
                with st.spinner("리뷰어가 읽는 중..."):
                    # 이미 댓글 단 에이전트 제외하고 선택
                    a_name, _ = pick_agent_excluding(posts[idx]["thread"])
                    my_comment = posts[idx]["thread"][my_comment_idx]
                    ai_reply, agent_name, agent_emoji = generate_ai_comment(
                        client, [], post["body"], a_name,
                        mode="reply", parent_comment=my_comment
                    )
                posts[idx]["thread"][my_comment_idx]["replies"].append({
                    "is_ai": True, "text": ai_reply, "time": now_str(),
                    "agent": agent_name, "emoji": agent_emoji
                })
                st.session_state.read_comments[pid] = len(posts[idx]["thread"])
                st.session_state.reply_counter += 1
                save_posts(posts)
                st.rerun()
    with col2:
        if st.button("🤖 AI댓글", use_container_width=True):
            if idx is not None:
                with st.spinner("AI 댓글 달성 중..."):
                    try:
                        n = random.randint(1, 5)
                        for _ in range(n):
                            # 매 루프마다 최신 thread 참조
                            thread_now = posts[idx].get("thread", [])
                            ai_comments = [(i, c) for i, c in enumerate(thread_now) if c.get("is_ai")]

                            if ai_comments and random.random() < 0.6:
                                # 이미 대댓글 있는 댓글 우선 (70%)
                                has_replies = [(i, c) for i, c in ai_comments if c.get("replies")]
                                no_replies  = [(i, c) for i, c in ai_comments if not c.get("replies")]

                                if has_replies and random.random() < 0.7:
                                    parent_idx, parent = random.choice(has_replies)
                                elif no_replies:
                                    parent_idx, parent = random.choice(no_replies)
                                else:
                                    parent_idx, parent = random.choice(ai_comments)

                                a_name, _ = pick_agent_for_reply(parent)
                                reply_hist = [
                                    {"is_ai": r["is_ai"], "text": r["text"], "agent": r.get("agent", "")}
                                    for r in parent.get("replies", [])
                                ]
                                cmt, a_n, a_e = generate_ai_comment(
                                    client, reply_hist, post["body"], a_name,
                                    mode="reply", parent_comment=parent
                                )
                                posts[idx]["thread"][parent_idx].setdefault("replies", []).append({
                                    "is_ai": True, "text": cmt,
                                    "time": now_str(), "agent": a_n, "emoji": a_e
                                })
                            else:
                                a_name, _ = pick_agent_excluding(posts[idx].get("thread", []))
                                cmt, a_n, a_e = generate_ai_comment(
                                    client, thread_now, post["body"], a_name, mode="comment"
                                )
                                posts[idx]["thread"].append({
                                    "is_ai": True, "text": cmt, "time": now_str(),
                                    "agent": a_n, "emoji": a_e,
                                    "is_new": False, "replies": []
                                })
                        st.session_state.read_comments[pid] = len(posts[idx]["thread"])
                        save_posts(posts)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col3:
        if st.button("🗑️", use_container_width=True):
            if idx is not None:
                trash = load_trash()
                deleted = dict(posts[idx])
                deleted["deleted_at"] = now_str()
                trash.insert(0, deleted)
                save_trash(trash)
                posts.pop(idx)
                save_posts(posts)
                st.session_state.page = "list"
                st.rerun()

# ══════════════════════════════════════════════════════
# 목록
# ══════════════════════════════════════════════════════
else:
    active_tag = st.session_state.active_tag
    filtered = posts if active_tag == "전체" else [p for p in posts if p.get("tag") == active_tag]

    # ── 헤더 타이틀
    st.markdown("### 💬 ThinkBoard")

    # ── 툴바: st.columns + st.button (4개 가로 배치)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("✏️ 쓰기", key="tb_write", use_container_width=True):
            st.session_state.page = "write"
            st.rerun()
    with c2:
        if st.button("🤖 AI글", key="tb_ai_post", use_container_width=True):
            with st.spinner("AI 글 4개 + 댓글 작성 중..."):
                try:
                    data_list, author_name, author_emoji = generate_ai_post(client, posts)
                    if not isinstance(data_list, list):
                        data_list = [data_list]
                    new_posts = []
                    for data in data_list:
                        post_author, _ = pick_agent()
                        new_post = {
                            "id": int(datetime.now().timestamp()) + random.randint(0, 9999),
                            "title": data.get("title","AI 글"),
                            "tag": data.get("tag","기타"),
                            "body": data.get("body",""),
                            "link": data.get("link"),
                            "link_title": data.get("link_title"),
                            "created": now_str(),
                            "is_ai_post": True,
                            "author": post_author,
                            "thread": []
                        }
                        # 글마다 1~5개 랜덤 초기 댓글 (중복 에이전트 제외)
                        n_comments = random.randint(1, 5)
                        for _ in range(n_comments):
                            try:
                                a_name, _ = pick_agent_excluding(new_post["thread"])
                                cmt, a_n, a_e = generate_ai_comment(
                                    client, new_post["thread"], new_post["body"], a_name, mode="comment"
                                )
                                new_post["thread"].append({
                                    "is_ai": True, "text": cmt, "time": now_str(),
                                    "agent": a_n, "emoji": a_e,
                                    "is_new": False, "replies": []
                                })
                            except:
                                pass
                        new_posts.append(new_post)
                    for np in new_posts:
                        posts.insert(0, np)
                    save_posts(posts)
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")
    with c3:
        if st.button("💬 댓글", key="tb_ai_cmt", use_container_width=True):
            all_targets = posts if posts else []
            if all_targets:
                with st.spinner("AI 댓글 10개 작성 중..."):
                    try:
                        count = 0
                        attempts = 0
                        while count < 10 and attempts < 30:
                            attempts += 1
                            # 매 루프마다 posts에서 최신 상태 참조
                            target_id = random.choice(all_targets)["id"]
                            target_p = next((p for p in posts if p["id"] == target_id), None)
                            if not target_p:
                                continue
                            thread = target_p.get("thread", [])

                            # 대댓글 달 수 있는 댓글 목록 (AI 댓글 중 선택)
                            ai_comments = [(i, c) for i, c in enumerate(thread) if c.get("is_ai")]

                            # 60% 확률로 대댓글 시도 (댓글이 있을 때만)
                            if ai_comments and random.random() < 0.6:
                                # 이미 대댓글 있는 댓글 우선 선택 (70%), 없으면 랜덤
                                has_replies = [(i, c) for i, c in ai_comments if c.get("replies")]
                                no_replies  = [(i, c) for i, c in ai_comments if not c.get("replies")]

                                if has_replies and random.random() < 0.7:
                                    parent_idx, parent = random.choice(has_replies)
                                elif no_replies:
                                    parent_idx, parent = random.choice(no_replies)
                                else:
                                    parent_idx, parent = random.choice(ai_comments)

                                a_name, _ = pick_agent_for_reply(parent)
                                reply_history = [
                                    {"is_ai": r["is_ai"], "text": r["text"], "agent": r.get("agent", "")}
                                    for r in parent.get("replies", [])
                                ]
                                cmt, a_n, a_e = generate_ai_comment(
                                    client, reply_history, target_p["body"], a_name,
                                    mode="reply", parent_comment=parent
                                )
                                target_p["thread"][parent_idx].setdefault("replies", []).append({
                                    "is_ai": True, "text": cmt,
                                    "time": now_str(), "agent": a_n, "emoji": a_e
                                })
                            else:
                                # 새 1단계 댓글: 이미 댓글 단 에이전트 제외
                                a_name, _ = pick_agent_excluding(thread)
                                cmt, a_n, a_e = generate_ai_comment(
                                    client, thread, target_p["body"], a_name, mode="comment"
                                )
                                target_p["thread"].append({
                                    "is_ai": True, "text": cmt, "time": now_str(),
                                    "agent": a_n, "emoji": a_e, "is_new": True, "replies": []
                                })
                            count += 1
                        save_posts(posts)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with c4:
        if st.button("🗑️", key="tb_trash", use_container_width=True):
            st.session_state.show_trash = True
            st.rerun()

    # ── 카테고리 필터
    tag_cols = st.columns(len(TAGS))
    for i, tag in enumerate(TAGS):
        with tag_cols[i]:
            is_active = st.session_state.active_tag == tag
            label = f"**{tag}**" if is_active else tag
            if st.button(label, key=f"tag_{tag}", use_container_width=True):
                st.session_state.active_tag = tag
                st.rerun()

    st.markdown("<hr style='margin:0.2rem 0 0.4rem;border:none;border-top:1px solid #eee'>",
                unsafe_allow_html=True)

    if not filtered:
        st.markdown("<div style='text-align:center;color:#aaa;margin-top:3rem'>글이 없어요!</div>",
                    unsafe_allow_html=True)
    else:
        for post in filtered:
            pid = str(post["id"])
            thread = post.get("thread", [])
            cnt = len(thread)
            is_ai = post.get("is_ai_post", False)

            has_new  = any(c.get("is_new") for c in thread)
            new_cmts = (pid in st.session_state.read_comments and
                        cnt > st.session_state.read_comments[pid])
            is_unread = has_new or new_cmts or pid not in st.session_state.read_posts

            dot      = "<span class='unread-dot'></span>" if is_unread else ""
            tag_cls  = "ai" if is_ai else ""
            row_cls  = "post-row unread" if is_unread else "post-row"
            t_cls    = "post-row-title unread" if is_unread else "post-row-title"
            body_prev = html_mod.escape(post['body'][:55] + "..." if len(post['body']) > 55 else post['body'])
            cnt_str  = f"💬 {cnt}" if cnt else ""
            tag_badge = f"<span class='post-row-tag {tag_cls}'>{post['tag']}</span>"
            # 작성자 표시: AI 글은 에이전트 이름, 내 글은 "나"
            author_disp = post.get("author", "AI") if is_ai else "나"

            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(f"""
<div class="{row_cls}" style="padding:0.4rem 0.2rem 0.2rem">
  <div class="{t_cls}">{dot}{html_mod.escape(post['title'])}&nbsp;{tag_badge}</div>
  <div class="post-row-body">{body_prev}</div>
  <div class="post-row-meta">{author_disp} · {time_ago(post['created'])} {cnt_str}</div>
</div>""", unsafe_allow_html=True)
            with col_btn:
                if st.button("›", key=f"open_{post['id']}", use_container_width=True):
                    st.session_state.read_posts.add(pid)
                    st.session_state.read_comments[pid] = cnt
                    st.session_state.selected_post_id = post["id"]
                    st.session_state.page = "detail"
                    st.session_state.reply_to = None
                    st.rerun()
            st.markdown("<hr style='margin:0.05rem 0;border:none;border-top:1px solid #f0f0f0'>",
                        unsafe_allow_html=True)
