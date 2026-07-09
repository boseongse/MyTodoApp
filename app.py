import json
import os
import re
import uuid
from datetime import datetime, timezone

import streamlit as st

TODOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")
CATEGORIES = ["업무", "개인", "공부"]
CATEGORY_ACCENT = {
    "업무": "#2563eb",
    "개인": "#16a34a",
    "공부": "#ea8a1f",
}

AUTO_LABEL = "자동 분류"
DEFAULT_CATEGORY = "개인"

TIME_SLOTS = [f"{h:02d}:00" for h in range(24)]
DEFAULT_TIME = "09:00"

# 텍스트에 아래 키워드가 포함되면 해당 카테고리로 자동 분류한다.
# CATEGORIES 순서대로 검사해서, 여러 카테고리 키워드가 동시에 있으면 앞쪽 카테고리를 우선한다.
KEYWORD_RULES = {
    "업무": [
        "회의", "미팅", "보고서", "발표", "업무", "프로젝트", "기획서",
        "이메일", "메일", "출장", "계약", "클라이언트", "고객", "마감", "회사", "결재",
    ],
    "개인": [
        "장보기", "청소", "빨래", "운동", "산책", "병원", "약속", "가족",
        "친구", "여행", "취미", "쇼핑", "은행", "생일", "약",
    ],
    "공부": [
        "공부", "시험", "과제", "강의", "수업", "독서", "복습", "예습",
        "자격증", "논문", "스터디", "학원", "단어",
    ],
}


def classify_by_keyword(text):
    """텍스트에 포함된 키워드를 보고 카테고리를 추론한다. 일치하는 키워드가 없으면 None."""
    for cat in CATEGORIES:
        for keyword in KEYWORD_RULES.get(cat, []):
            if keyword in text:
                return cat
    return None

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!~])")


def md_escape(text: str) -> str:
    """마크다운 특수문자를 이스케이프해서 할 일 텍스트가 서식으로 오해석되지 않게 한다."""
    return _MD_SPECIAL.sub(r"\\\1", text)


def load_todos():
    if not os.path.exists(TODOS_FILE):
        return []
    try:
        with open(TODOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
    except (json.JSONDecodeError, OSError):
        return []

    # 시간 필드가 도입되기 전에 저장된 할 일에는 기본 시간을 채워준다.
    for todo in data:
        todo.setdefault("time", DEFAULT_TIME)
    return data


def save_todos(todos):
    with open(TODOS_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def init_state():
    if "todos" not in st.session_state:
        st.session_state.todos = load_todos()
    if "filter" not in st.session_state:
        st.session_state.filter = "전체"
    if "editing_id" not in st.session_state:
        st.session_state.editing_id = None


def add_todo():
    text = st.session_state.get("new_todo_text", "").strip()
    if not text:
        return

    selected = st.session_state.get("new_todo_category", AUTO_LABEL)
    if selected == AUTO_LABEL:
        matched = classify_by_keyword(text)
        category = matched or DEFAULT_CATEGORY
        if matched:
            st.toast(f"'{text}' → {matched}(으)로 자동 분류했습니다", icon="🏷️")
    else:
        category = selected

    time_slot = st.session_state.get("new_todo_time", DEFAULT_TIME)

    st.session_state.todos.append(
        {
            "id": str(uuid.uuid4()),
            "text": text,
            "category": category,
            "time": time_slot,
            "completed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_todos(st.session_state.todos)


def toggle_complete(todo_id):
    for todo in st.session_state.todos:
        if todo["id"] == todo_id:
            todo["completed"] = st.session_state[f"chk_{todo_id}"]
            break
    save_todos(st.session_state.todos)


def delete_todo(todo_id):
    st.session_state.todos = [t for t in st.session_state.todos if t["id"] != todo_id]
    save_todos(st.session_state.todos)
    if st.session_state.editing_id == todo_id:
        st.session_state.editing_id = None
    st.session_state.pop(f"edit_input_{todo_id}", None)
    st.session_state.pop(f"edit_time_{todo_id}", None)


def start_edit(todo_id, current_text, current_time):
    st.session_state[f"edit_input_{todo_id}"] = current_text
    st.session_state[f"edit_time_{todo_id}"] = current_time
    st.session_state.editing_id = todo_id


def save_edit(todo_id):
    new_text = st.session_state.get(f"edit_input_{todo_id}", "").strip()
    new_time = st.session_state.get(f"edit_time_{todo_id}", DEFAULT_TIME)
    if new_text:
        for todo in st.session_state.todos:
            if todo["id"] == todo_id:
                todo["text"] = new_text
                todo["time"] = new_time
                break
        save_todos(st.session_state.todos)
    st.session_state.editing_id = None
    st.session_state.pop(f"edit_input_{todo_id}", None)
    st.session_state.pop(f"edit_time_{todo_id}", None)


def cancel_edit(todo_id):
    st.session_state.editing_id = None
    st.session_state.pop(f"edit_input_{todo_id}", None)
    st.session_state.pop(f"edit_time_{todo_id}", None)


def set_filter(value):
    st.session_state.filter = value


def get_filtered_todos():
    todos = st.session_state.todos
    if st.session_state.filter != "전체":
        todos = [t for t in todos if t["category"] == st.session_state.filter]
    return sorted(todos, key=lambda t: t["time"])


st.set_page_config(page_title="My Todo", page_icon="✅", layout="centered")
init_state()

st.markdown(
    """
    <style>
    .block-container { max-width: 560px; padding-top: 2.5rem; }
    .category-badge {
        display: inline-block; font-size: 12px; font-weight: 700;
        padding: 3px 10px; border-radius: 999px; white-space: nowrap;
    }
    .cat-chip {
        display: inline-flex; align-items: center; font-size: 12px;
        font-weight: 700; padding: 4px 11px; border-radius: 999px;
        color: #ffffff; margin-right: 6px;
    }
    .time-badge {
        display: inline-block; font-size: 12px; font-weight: 700;
        padding: 3px 8px; border-radius: 6px; white-space: nowrap;
        background: #eef1f6; color: #475569;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.title("My Todo")
    st.caption("오늘 할 일을 가볍게 정리해보세요")

    # 진행률
    todos = st.session_state.todos
    total = len(todos)
    completed_count = sum(1 for t in todos if t["completed"])
    percent = round(completed_count / total * 100) if total else 0

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("진행률", f"{percent}%")
    with col2:
        st.write("")
        st.progress(percent / 100)
        st.caption(f"완료 {completed_count} / 전체 {total}")

    chip_html = ""
    for cat in CATEGORIES:
        cat_todos = [t for t in todos if t["category"] == cat]
        cat_completed = sum(1 for t in cat_todos if t["completed"])
        accent = CATEGORY_ACCENT[cat]
        chip_html += (
            f'<span class="cat-chip" style="background:{accent}">'
            f"{cat} {cat_completed}/{len(cat_todos)}</span>"
        )
    st.markdown(chip_html, unsafe_allow_html=True)

    st.divider()

    # 입력 폼 (Enter 또는 버튼으로 추가)
    with st.form("add_form", clear_on_submit=True):
        st.text_input(
            "할 일",
            key="new_todo_text",
            placeholder="할 일을 입력하세요",
            label_visibility="collapsed",
        )
        c2, c3, c4 = st.columns([1.2, 1.2, 0.8])
        with c2:
            st.selectbox(
                "카테고리",
                [AUTO_LABEL] + CATEGORIES,
                key="new_todo_category",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "시간",
                TIME_SLOTS,
                index=datetime.now().hour,
                key="new_todo_time",
                label_visibility="collapsed",
            )
        with c4:
            st.form_submit_button(
                "추가", use_container_width=True, on_click=add_todo
            )
        st.caption("카테고리를 '자동 분류'로 두면 문장 속 키워드로 자동으로 정해드려요. 시간은 1시간 단위로 선택합니다.")

    # 필터
    filter_options = ["전체"] + CATEGORIES
    filter_cols = st.columns(len(filter_options))
    for col, label in zip(filter_cols, filter_options):
        with col:
            btn_type = "primary" if st.session_state.filter == label else "secondary"
            st.button(
                label,
                key=f"filter_{label}",
                use_container_width=True,
                type=btn_type,
                on_click=set_filter,
                args=(label,),
            )

    st.write("")

    filtered = get_filtered_todos()

    if not filtered:
        msg = "할 일을 추가해보세요" if total == 0 else "해당 카테고리에 할 일이 없습니다"
        st.info(msg)
    else:
        for todo in filtered:
            is_editing = st.session_state.editing_id == todo["id"]
            row = st.columns([0.07, 0.19, 0.31, 0.14, 0.14, 0.15])

            with row[0]:
                st.checkbox(
                    "완료",
                    value=todo["completed"],
                    key=f"chk_{todo['id']}",
                    label_visibility="collapsed",
                    on_change=toggle_complete,
                    args=(todo["id"],),
                )

            with row[1]:
                if is_editing:
                    st.selectbox(
                        "시간",
                        TIME_SLOTS,
                        key=f"edit_time_{todo['id']}",
                        label_visibility="collapsed",
                    )
                else:
                    st.markdown(
                        f'<span class="time-badge">{todo["time"]}</span>',
                        unsafe_allow_html=True,
                    )

            with row[2]:
                if is_editing:
                    st.text_input(
                        "수정",
                        key=f"edit_input_{todo['id']}",
                        label_visibility="collapsed",
                    )
                else:
                    display_text = md_escape(todo["text"])
                    if todo["completed"]:
                        st.markdown(f":gray[~~{display_text}~~]")
                    else:
                        st.markdown(display_text)

            with row[3]:
                accent = CATEGORY_ACCENT[todo["category"]]
                st.markdown(
                    f'<span class="category-badge" style="background:{accent};'
                    f'color:#ffffff">{todo["category"]}</span>',
                    unsafe_allow_html=True,
                )

            with row[4]:
                if is_editing:
                    st.button(
                        "저장",
                        key=f"save_{todo['id']}",
                        use_container_width=True,
                        on_click=save_edit,
                        args=(todo["id"],),
                    )
                else:
                    st.button(
                        "✏️",
                        key=f"edit_{todo['id']}",
                        use_container_width=True,
                        on_click=start_edit,
                        args=(todo["id"], todo["text"], todo["time"]),
                    )

            with row[5]:
                if is_editing:
                    st.button(
                        "취소",
                        key=f"cancel_{todo['id']}",
                        use_container_width=True,
                        on_click=cancel_edit,
                        args=(todo["id"],),
                    )
                else:
                    st.button(
                        "🗑️",
                        key=f"del_{todo['id']}",
                        use_container_width=True,
                        on_click=delete_todo,
                        args=(todo["id"],),
                    )
