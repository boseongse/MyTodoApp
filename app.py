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
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


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
    category = st.session_state.get("new_todo_category", CATEGORIES[0])
    st.session_state.todos.append(
        {
            "id": str(uuid.uuid4()),
            "text": text,
            "category": category,
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


def start_edit(todo_id, current_text):
    st.session_state[f"edit_input_{todo_id}"] = current_text
    st.session_state.editing_id = todo_id


def save_edit(todo_id):
    new_text = st.session_state.get(f"edit_input_{todo_id}", "").strip()
    if new_text:
        for todo in st.session_state.todos:
            if todo["id"] == todo_id:
                todo["text"] = new_text
                break
        save_todos(st.session_state.todos)
    st.session_state.editing_id = None
    st.session_state.pop(f"edit_input_{todo_id}", None)


def cancel_edit(todo_id):
    st.session_state.editing_id = None
    st.session_state.pop(f"edit_input_{todo_id}", None)


def set_filter(value):
    st.session_state.filter = value


def get_filtered_todos():
    todos = st.session_state.todos
    if st.session_state.filter == "전체":
        return todos
    return [t for t in todos if t["category"] == st.session_state.filter]


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
        display: inline-flex; align-items: center; gap: 5px; font-size: 12px;
        font-weight: 600; padding: 4px 10px; border-radius: 999px;
        background: #f1f3f8; margin-right: 6px;
    }
    .cat-chip .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
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
        dot_color = CATEGORY_ACCENT[cat]
        chip_html += (
            f'<span class="cat-chip"><span class="dot" style="background:{dot_color}"></span>'
            f"{cat} {cat_completed}/{len(cat_todos)}</span>"
        )
    st.markdown(chip_html, unsafe_allow_html=True)

    st.divider()

    # 입력 폼 (Enter 또는 버튼으로 추가)
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.text_input(
                "할 일",
                key="new_todo_text",
                placeholder="할 일을 입력하세요",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "카테고리",
                CATEGORIES,
                key="new_todo_category",
                label_visibility="collapsed",
            )
        with c3:
            st.form_submit_button(
                "추가", use_container_width=True, on_click=add_todo
            )

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
            row = st.columns([0.08, 0.5, 0.16, 0.13, 0.13])

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
                if st.session_state.editing_id == todo["id"]:
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

            with row[2]:
                accent = CATEGORY_ACCENT[todo["category"]]
                st.markdown(
                    f'<span class="category-badge" style="background:{accent};'
                    f'color:#ffffff">{todo["category"]}</span>',
                    unsafe_allow_html=True,
                )

            with row[3]:
                if st.session_state.editing_id == todo["id"]:
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
                        args=(todo["id"], todo["text"]),
                    )

            with row[4]:
                if st.session_state.editing_id == todo["id"]:
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
