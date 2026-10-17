import html
from datetime import date, datetime

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

TOPIC_EMOJI = {
    "World": "🌍", "Pakistan": "🇵🇰", "Business": "💼", "Technology": "💻",
    "Science": "🔬", "Health": "🩺", "Sports": "🏏", "Entertainment": "🎬",
}

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }

    /* Masthead */
    .mast-title {
        text-align: center; font-family: Georgia, 'Times New Roman', serif;
        font-weight: 900; font-size: clamp(1.8rem, 4.2vw, 3rem); white-space: nowrap;
        line-height: 1.1; color: #1A1A1A; padding: 6px 0 4px 0;
    }
    .dateline {
        display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
        border-top: 3px double #1A1A1A; border-bottom: 1px solid #1A1A1A;
        padding: 6px 2px; margin: 8px 0 14px 0; font-size: 0.8rem;
        text-transform: uppercase; letter-spacing: 0.08em; color: #1A1A1A;
    }

    /* Section headings */
    .section-head {
        text-align: center; text-transform: uppercase; letter-spacing: 0.18em;
        font-family: Georgia, serif; font-weight: 700; font-size: 1.05rem;
        color: #8B1A1A; border-top: 3px solid #1A1A1A; border-bottom: 1px solid #1A1A1A;
        padding: 5px 0; margin: 22px 0 14px 0;
    }

    /* Lead story */
    .lead-title {
        font-family: Georgia, serif; font-weight: 900; font-size: 2.3rem;
        line-height: 1.15; margin: 0 0 6px 0; color: #1A1A1A;
    }
    .dropcap::first-letter {
        float: left; font-size: 3.6rem; line-height: 0.85; padding: 4px 8px 0 0;
        font-weight: 900; color: #8B1A1A; font-family: Georgia, serif;
    }
    .lead-summary { text-align: justify; font-size: 1.05rem; line-height: 1.55; }

    /* Images: same height, newsprint tone */
    [data-testid="stImage"] img {
        width: 100%; height: 200px; object-fit: cover; border-radius: 2px;
        filter: grayscale(30%) sepia(12%);
    }

    /* Newspaper column rules */
    [data-testid="stColumn"] + [data-testid="stColumn"],
    [data-testid="column"] + [data-testid="column"] {
        border-left: 1px solid #CFC5AE; padding-left: 1rem;
    }
    [data-testid="stColumn"] [data-testid="stColumn"],
    [data-testid="column"] [data-testid="column"] {
        border-left: none; padding-left: 0;
    }

    /* Text */
    .stMarkdown h4 { font-weight: 700; line-height: 1.2; margin-bottom: 0.2rem; }
    [data-testid="stMarkdownContainer"] p { text-align: justify; }
    .stButton button, .stLinkButton a {
        padding: 0.15rem 0.6rem; font-size: 0.85rem; min-height: 0;
    }

    /* Takeaways */
    .takeaways {
        background: #F3EDE0; border: 1px solid #1A1A1A; border-left: 6px solid #8B1A1A;
        padding: 14px 18px; margin: 8px 0 18px 0; font-family: Georgia, serif;
    }
    .takeaways h4 { color: #8B1A1A; margin: 0 0 8px 0; letter-spacing: 1px; }
    .takeaways p { margin: 4px 0; color: #1A1A1A; }
    .takeaways .note { color: #666; font-style: italic; font-size: 0.9rem; margin-top: 8px; }

    /* Sidebar chart */
    .bar-row { display: flex; align-items: center; margin: 4px 0; font-size: 0.85rem; }
    .bar-label { width: 105px; }
    .bar-track { flex: 1; background: #E4DAC5; height: 12px; border-radius: 6px; }
    .bar-fill { background: #8B1A1A; height: 12px; border-radius: 6px; }
    .bar-value { width: 38px; text-align: right; color: #555; }
    </style>
    """,
    unsafe_allow_html=True,
)


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
    topics = st.multiselect(
        "Pick at least 3 topics", TOPICS,
        format_func=lambda t: f"{TOPIC_EMOJI.get(t, '📰')} {t}",
    )
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


def section_head(text: str) -> None:
    st.markdown(f"<div class='section-head'>{html.escape(text)}</div>", unsafe_allow_html=True)


def short_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def render_actions(article: dict, user_id: int, prefix: str, interactive: bool, liked: set) -> None:
    columns = st.columns(3)
    if interactive:
        if article["id"] in liked:
            columns[0].markdown("✅ Liked")
        else:
            columns[0].button("👍 Like", key=f"{prefix}_like_{article['id']}",
                              on_click=handle_feedback, args=(user_id, article, "like"))
        columns[1].button("🚫 Skip", key=f"{prefix}_skip_{article['id']}",
                          on_click=handle_feedback, args=(user_id, article, "skip"))
    columns[2].link_button("Read ↗", article["link"])


def render_article(article: dict, user_id: int, prefix: str, interactive: bool,
                   liked: set) -> None:
    if article.get("image_url"):
        try:
            st.image(article["image_url"])
        except Exception:
            pass
    st.markdown(f"#### {article['title']}")
    st.caption(f"{article['source']} · {article['topic']}")
    if article.get("summary") and not article["summary"].startswith("http"):
        st.write(short_text(article["summary"], 230))
    st.caption("💡 " + article["reason"])
    render_actions(article, user_id, prefix, interactive, liked)


def render_lead(article: dict, user_id: int, interactive: bool, liked: set) -> None:
    image_col, text_col = st.columns([2, 3], gap="large")
    with image_col:
        if article.get("image_url"):
            try:
                st.image(article["image_url"])
            except Exception:
                pass
    with text_col:
        st.markdown(
            f"<div class='lead-title'>{html.escape(article['title'])}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"{article['source']} · {article['topic']}")
        summary = article.get("summary") or ""
        if summary and not summary.startswith("http"):
            st.markdown(
                f"<p class='lead-summary dropcap'>{html.escape(summary)}</p>",
                unsafe_allow_html=True,
            )
        st.caption("💡 " + article["reason"])
        render_actions(article, user_id, "lead", interactive, liked)


def render_grid(articles: list, user_id: int, prefix: str, interactive: bool,
                liked: set, per_row: int = 3) -> None:
    for start in range(0, len(articles), per_row):
        columns = st.columns(per_row, gap="medium")
        for column, article in zip(columns, articles[start:start + per_row]):
            with column:
                render_article(article, user_id, prefix, interactive, liked)
        st.divider()


def estimate_minutes(articles: list) -> int:
    words = 0
    for article in articles:
        words += len(article["title"].split())
        summary = article.get("summary") or ""
        if not summary.startswith("http"):
            words += len(summary.split())
    return max(1, round(words / 200))


def render_learned_chart(weights: dict) -> None:
    rows = ""
    for topic, value in sorted(weights.items(), key=lambda item: -item[1]):
        percent = max(0.0, min(value / 3.0, 1.0)) * 100
        rows += (
            f"<div class='bar-row'><div class='bar-label'>{html.escape(str(topic))}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{percent:.0f}%'></div></div>"
            f"<div class='bar-value'>{value:.1f}</div></div>"
        )
    st.sidebar.markdown(rows, unsafe_allow_html=True)


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
    render_learned_chart(weights)

if st.sidebar.button("Switch reader"):
    for key in ("user_id", "user_name"):
        st.session_state.pop(key, None)
    st.rerun()

# Load this edition
label = datetime.strptime(choice, "%Y-%m-%d").strftime("%A, %d %B %Y")
articles = get_edition(user_id, choice) or []
interactive = choice == today
if interactive:
    skipped = get_feedback_ids(user_id, "skip")
    articles = [article for article in articles if article["id"] not in skipped]
liked = get_feedback_ids(user_id, "like")

# Masthead
middle = (
    f"{len(articles)} stories · about {estimate_minutes(articles)} min read"
    if articles else ""
)
st.markdown(
    f"<div class='mast-title'>The {html.escape(user_name)} Morning Paper</div>"
    f"<div class='dateline'><span>{html.escape(label)}</span><span>{middle}</span>"
    f"<span>Personalised for you</span></div>",
    unsafe_allow_html=True,
)

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
    items_html = "".join(
        f"<p><b>{number}.</b> {html.escape(str(text))}</p>"
        for number, text in enumerate(insights["takeaways"], 1)
    )
    note_html = ""
    if insights.get("note"):
        note_html = f"<p class='note'>Editor's note: {html.escape(str(insights['note']))}</p>"
    st.markdown(
        f"<div class='takeaways'><h4>TODAY'S 3 TAKEAWAYS</h4>{items_html}{note_html}</div>",
        unsafe_allow_html=True,
    )

lead, rest = articles[0], articles[1:]
wild = [a for a in rest if a.get("wildcard")]
regular = [a for a in rest if not a.get("wildcard")]

section_head("Lead story")
render_lead(lead, user_id, interactive, liked)

if regular[:4]:
    section_head("Top stories")
    render_grid(regular[:4], user_id, "top", interactive, liked, per_row=2)

by_topic = {}
for article in regular[4:]:
    by_topic.setdefault(article["topic"], []).append(article)
for topic, items in by_topic.items():
    section_head(f"{TOPIC_EMOJI.get(topic, '📰')} {topic}")
    render_grid(items, user_id, f"sec_{topic}", interactive, liked, per_row=3)

if wild:
    section_head("🎲 Wildcards: outside your usual topics")
    render_grid(wild, user_id, "wild", interactive, liked, per_row=3)