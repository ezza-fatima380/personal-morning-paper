import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from ai_features import make_insights
from config import TOPICS
from database import init_db
from fetcher import fetch_all
from pdf_builder import build_pdf
from ranker import build_edition, get_edition, list_editions, save_edition
from reader_profile import (
    get_feedback_ids,
    get_or_create_user,
    get_topic_weights,
    get_users,
    init_profile_tables,
    record_feedback,
    save_interests,
)

st.set_page_config(page_title="My Morning Paper", page_icon="📰", layout="wide")
init_db()
init_profile_tables()


def handle_feedback(user_id: int, article: dict, action: str) -> None:
    record_feedback(user_id, article, action)
    st.session_state["toast"] = (
        "Noted: more stories like this." if action == "like"
        else "Skipped: fewer stories like this."
    )


def onboarding() -> None:
    st.title("📰 Build your personal morning paper")
    st.write("Tell us what you care about. The paper learns from every like and skip.")

    users = get_users()
    if users:
        with st.expander("Already have a paper? Open it"):
            names = {name: uid for uid, name in users}
            choice = st.selectbox("Reader", list(names))
            if st.button("Open my paper"):
                st.session_state["user_id"] = names[choice]
                st.session_state["user_name"] = choice
                st.rerun()

    name = st.text_input("Your name")
    topics = st.multiselect("Pick at least 3 topics", TOPICS)
    keywords = st.text_input(
        "Specific interests (comma separated)", placeholder="e.g. cricket, AI, startups, climate"
    )
    if st.button("Create my paper", type="primary"):
        if not name.strip():
            st.error("Please enter your name.")
        elif len(topics) < 3:
            st.error("Please pick at least 3 topics.")
        else:
            user_id = get_or_create_user(name.strip())
            save_interests(user_id, topics, keywords)
            st.session_state["user_id"] = user_id
            st.session_state["user_name"] = name.strip()
            st.rerun()


def render_article(article: dict, user_id: int, prefix: str, interactive: bool,
                   liked: set, lead: bool = False) -> None:
    if article.get("image_url"):
        try:
            st.image(article["image_url"])
        except Exception:
            pass
    st.markdown(f"## {article['title']}" if lead else f"#### {article['title']}")
    st.caption(f"{article['source']} · {article['topic']}")
    if article.get("summary") and not article["summary"].startswith("http"):
        st.write(article["summary"])
    st.caption("💡 " + article["reason"])

    columns = st.columns([1, 1, 2])
    if interactive:
        if article["id"] in liked:
            columns[0].markdown("✅ Liked")
        else:
            columns[0].button("👍 Like", key=f"{prefix}_like_{article['id']}",
                              on_click=handle_feedback, args=(user_id, article, "like"))
        columns[1].button("🚫 Skip", key=f"{prefix}_skip_{article['id']}",
                          on_click=handle_feedback, args=(user_id, article, "skip"))
    columns[2].link_button("Read original ↗", article["link"])


def render_grid(articles: list, user_id: int, prefix: str, interactive: bool, liked: set) -> None:
    for start in range(0, len(articles), 2):
        columns = st.columns(2)
        for column, article in zip(columns, articles[start:start + 2]):
            with column:
                render_article(article, user_id, prefix, interactive, liked)
                st.divider()


# ---------------- Main flow ----------------
user_id = st.session_state.get("user_id")
if not user_id:
    onboarding()
    st.stop()

user_name = st.session_state.get("user_name", "Reader")
if "toast" in st.session_state:
    st.toast(st.session_state.pop("toast"))

today = date.today().isoformat()
if get_edition(user_id, today) is None:
    save_edition(user_id, build_edition(user_id), today)

# Sidebar
st.sidebar.title(f"📰 {user_name}")
dates = list_editions(user_id)
choice = st.sidebar.selectbox(
    "Edition", dates, format_func=lambda d: "Today's paper" if d == today else d
)
if st.sidebar.button("Fetch latest news"):
    with st.spinner("Fetching news from all sources..."):
        added = fetch_all()
    st.sidebar.success(f"{added} new stories fetched.")
if st.sidebar.button("Rebuild today's paper"):
    save_edition(user_id, build_edition(user_id), today)
    st.rerun()
st.sidebar.caption("Like or skip stories, then rebuild to see the paper learn.")

st.sidebar.subheader("What the paper has learned")
weights = get_topic_weights(user_id)
if weights:
    st.sidebar.bar_chart(pd.DataFrame({"interest": weights}).sort_values("interest", ascending=False))

if st.sidebar.button("Switch reader"):
    for key in ("user_id", "user_name"):
        st.session_state.pop(key, None)
    st.rerun()

# Masthead
label = datetime.strptime(choice, "%Y-%m-%d").strftime("%A, %d %B %Y")
st.markdown(
    f"<h1 style='text-align:center;font-family:Georgia,serif;margin-bottom:0'>"
    f"The {html.escape(user_name)} Morning Paper</h1>"
    f"<p style='text-align:center;color:gray'>{label}</p>",
    unsafe_allow_html=True,
)
st.divider()

articles = get_edition(user_id, choice) or []
interactive = choice == today
if interactive:
    skipped = get_feedback_ids(user_id, "skip")
    articles = [article for article in articles if article["id"] not in skipped]
liked = get_feedback_ids(user_id, "like")

if not articles:
    st.info("No stories yet. Click 'Fetch latest news' in the sidebar, then 'Rebuild today's paper'.")
    st.stop()

# Gemini insights: created once per edition, cached in the session
insights_key = f"insights_{user_id}_{choice}_{articles[0]['id']}"
if insights_key not in st.session_state:
    with st.spinner("Writing today's takeaways..."):
        st.session_state[insights_key] = make_insights(user_name, articles)
insights = st.session_state[insights_key]

# PDF export (same edition as the web page)
st.sidebar.divider()
if st.sidebar.button("Prepare PDF"):
    with st.spinner("Typesetting your newspaper..."):
        st.session_state["pdf"] = (choice, build_pdf(
            user_name, label, articles,
            takeaways=insights["takeaways"] if insights else None,
            editor_note=insights.get("note") if insights else None,
        ))
ready = st.session_state.get("pdf")
if ready and ready[0] == choice:
    st.sidebar.download_button(
        "Download PDF", data=ready[1], file_name=f"morning-paper-{choice}.pdf",
        mime="application/pdf",
    )

# Takeaways box
if insights:
    st.markdown("### Today's 3 takeaways")
    for number, text in enumerate(insights["takeaways"], 1):
        st.markdown(f"**{number}.** {text}")
    if insights["note"]:
        st.caption("Editor's note: " + insights["note"])
    st.divider()

lead, rest = articles[0], articles[1:]
wild = [a for a in rest if a.get("wildcard")]
regular = [a for a in rest if not a.get("wildcard")]

st.markdown("### Lead story")
render_article(lead, user_id, "lead", interactive, liked, lead=True)
st.divider()

if regular[:4]:
    st.markdown("### Top stories")
    render_grid(regular[:4], user_id, "top", interactive, liked)

by_topic = {}
for article in regular[4:]:
    by_topic.setdefault(article["topic"], []).append(article)
for topic, items in by_topic.items():
    st.markdown(f"### {topic}")
    render_grid(items, user_id, f"sec_{topic}", interactive, liked)

if wild:
    st.markdown("### 🎲 Wildcards")
    render_grid(wild, user_id, "wild", interactive, liked)