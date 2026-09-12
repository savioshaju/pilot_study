import streamlit as st
import os
import re
import uuid
import math
from datetime import datetime
from utils.data_manager import (
    load_study_data,
    ensure_sample_audio_files,
    get_audio_path,
    save_participant_response,
)

# Set page config to wide mode for the table layout
st.set_page_config(
    page_title="Speech & Prosody Pilot Study",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling for Table-Based Layout
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Malayalam:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans Malayalam', sans-serif;
    }

    /* Constrain max width for great readability while keeping table spacious */
    .block-container {
        max-width: 1240px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
    }

    .main-header {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        padding: 1.2rem 1.6rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .main-header p {
        color: #DBEAFE;
        margin-top: 0.25rem;
        font-size: 0.9rem;
        margin-bottom: 0;
    }

    /* Instructions Box */
    .instructions-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        padding: 0.85rem 1.2rem;
        margin-bottom: 1.2rem;
        font-size: 0.92rem;
        color: #334155;
        line-height: 1.55;
    }
    .instructions-card b {
        color: #0F172A;
    }

    .step-badge {
        display: inline-block;
        background: #EFF6FF;
        color: #1D4ED8;
        font-weight: 600;
        padding: 0.25rem 0.7rem;
        border-radius: 6px;
        font-size: 0.85rem;
    }

    /* Table Column Headers */
    .table-col-header {
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        padding: 0.4rem 0;
    }

    /* Question number tag */
    .q-tag {
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 700;
        color: #1E40AF;
        background: #DBEAFE;
        padding: 0.12rem 0.4rem;
        border-radius: 4px;
        margin-bottom: 0.3rem;
    }

    /* Compact Native Audio Player */
    div[data-testid="stAudio"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stAudio"] audio {
        height: 32px !important;
        width: 100% !important;
        min-width: 110px !important;
        max-width: 175px !important;
        border-radius: 16px !important;
    }

    /* English Sentence styling */
    .english-cell {
        font-size: 0.95rem;
        color: #0F172A;
        line-height: 1.5;
        font-weight: 500;
        padding-top: 0.15rem;
    }

    .emphasis-inline {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 700;
        padding: 0.08rem 0.35rem;
        border-radius: 4px;
        border: 1px solid #FDE68A;
    }

    /* Stressed Word Tag */
    .stressed-tag {
        display: inline-block;
        background: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
        font-size: 0.88rem;
        font-weight: 600;
        padding: 0.2rem 0.55rem;
        border-radius: 5px;
        margin-top: 0.15rem;
    }

    /* Compact Radio Group inside table cell */
    div[data-testid="stRadio"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.2rem !important;
        display: flex !important;
        flex-direction: column !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        background: transparent !important;
        border: none !important;
        padding: 2px 6px !important;
        margin: 0 !important;
        border-radius: 4px !important;
        cursor: pointer !important;
        transition: background 0.1s ease !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background-color: #F1F5F9 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: #EFF6FF !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-family: 'Noto Sans Malayalam', 'Inter', sans-serif !important;
        font-size: 0.94rem !important;
        line-height: 1.48 !important;
        color: #1E293B !important;
        margin: 0 !important;
    }

    .card-container {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        div[data-testid="stAudio"] audio {
            max-width: 100% !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load study configurations and ensure demo audio exists
study_data = load_study_data()
metadata = study_data.get("study_metadata", {})
sentences = study_data.get("sentences", [])
ensure_sample_audio_files(sentences)

# Initialize Session State
if "page" not in st.session_state:
    st.session_state.page = "demographics"  # "demographics" | "trial" | "thank_you"
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "participant_info" not in st.session_state:
    st.session_state.participant_info = {}
if "responses" not in st.session_state:
    st.session_state.responses = {}  # sentence_id -> dict
if "submitting" not in st.session_state:
    st.session_state.submitting = False


def highlight_sentence(text, emphasized_words):
    """Wraps emphasized words in a styled HTML span for high visual clarity."""
    highlighted = text
    for word in emphasized_words:
        pattern = re.compile(rf"\b({re.escape(word)})\b", re.IGNORECASE)
        highlighted = pattern.sub(r'<span class="emphasis-inline">\1</span>', highlighted)
    return highlighted


# ==========================================
# PAGE 1: DEMOGRAPHICS & USER ONBOARDING
# ==========================================
if st.session_state.page == "demographics":
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{metadata.get('title', 'Speech Perception & Prosody Pilot Study')}</h1>
            <p>{metadata.get('description', 'Welcome! Please fill in your basic background details before starting the perceptual evaluation.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card-container">
            <h3 style="margin-top:0;">Participant Background</h3>
            <p style="color: #64748B; font-size: 0.95rem;">
                This information helps us understand language background and acoustic conditions for our evaluation.
                All responses are strictly confidential and anonymized for academic research.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("demographics_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="e.g., Alex Thomas")
        with col2:
            email = st.text_input("Email Address *", placeholder="e.g., alex@example.com")

        col3, col4 = st.columns(2)
        with col3:
            age = st.number_input("Age *", min_value=12, max_value=100, value=22, step=1)
        with col4:
            gender = st.selectbox(
                "Gender *",
                ["Prefer not to say", "Female", "Male", "Non-binary", "Other"],
            )

        st.markdown("---")
        st.subheader("Language Proficiency")

        col5, col6 = st.columns(2)
        with col5:
            malayalam_prof = st.selectbox(
                "Proficiency in Malayalam *",
                [
                    "Native / Mother Tongue",
                    "Advanced (Fluent in reading, writing & speaking)",
                    "Intermediate (Comfortable speaking & understanding)",
                    "Elementary (Basic comprehension)",
                ],
                index=0,
            )
        with col6:
            english_prof = st.selectbox(
                "Proficiency in English *",
                [
                    "Native / Bilingual",
                    "Advanced (Fluent in reading, writing & speaking)",
                    "Intermediate (Comfortable speaking & understanding)",
                    "Elementary (Basic comprehension)",
                ],
                index=1,
            )

        submitted = st.form_submit_button("Begin Pilot Study", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Please enter your full name.")
            elif not email.strip() or "@" not in email:
                st.error("Please provide a valid email address.")
            else:
                participant_id = f"P_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
                st.session_state.participant_info = {
                    "participant_id": participant_id,
                    "name": name.strip(),
                    "email": email.strip(),
                    "age": int(age),
                    "gender": gender,
                    "malayalam_proficiency": malayalam_prof,
                    "english_proficiency": english_prof,
                }
                st.session_state.current_page = 0
                st.session_state.page = "trial"
                st.rerun()


# ==========================================
# PAGE 2: COMPACT TABLE-BASED TRIALS (10 PER PAGE)
# ==========================================
elif st.session_state.page == "trial":
    total_sentences = len(sentences)
    PAGE_SIZE = 10
    total_pages = max(1, math.ceil(total_sentences / PAGE_SIZE))

    curr_page = st.session_state.current_page
    start_idx = curr_page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_sentences)
    current_batch = sentences[start_idx:end_idx]

    # Header with Progress
    progress_val = end_idx / float(total_sentences)
    st.progress(progress_val)

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
            <span class="step-badge">Page {curr_page + 1} of {total_pages} &bull; Questions {start_idx + 1}–{end_idx} of {total_sentences}</span>
            <span style="font-size: 0.9rem; color: #64748B;">Participant: <b>{st.session_state.participant_info.get('name', 'Guest')}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Clear Instructions at top of page
    st.markdown(
        """
        <div class="instructions-card">
            <b>Instructions:</b>
            <ol style="margin: 0.35rem 0 0 1.2rem; padding: 0;">
                <li>Listen to the audio control in each row.</li>
                <li>Observe the complete English sentence and its highlighted <b>Stressed Word</b>.</li>
                <li>Select the candidate Malayalam translation that best captures the intended emphasis, prosody, and meaning.</li>
                <li>All 10 questions on this page must be answered to proceed.</li>
            </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Table Header Row
    col_h1, col_h2 = st.columns([4.8, 6.2])
    with col_h1:
        st.markdown('<div class="table-col-header">Audio, English Sentence & Stressed Word</div>', unsafe_allow_html=True)
    with col_h2:
        st.markdown('<div class="table-col-header">Candidate Malayalam Translations</div>', unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.2rem 0 0.6rem 0; border: none; border-top: 2px solid #CBD5E1;' />", unsafe_allow_html=True)

    # Table Rows for Current Page (up to 10 questions)
    for item in current_batch:
        s_id = item.get("id")
        src_eng = item.get("source_english", "")
        emph_words = item.get("emphasized_words", [])
        stressed_display = ", ".join(emph_words) if emph_words else "-"
        target_options = item.get("target_options", [])
        audio_file = item.get("audio_file", f"audio_{s_id}.wav")
        audio_path = get_audio_path(audio_file)

        option_labels = [f"({opt['id']}) {opt['text']}" for opt in target_options]
        saved_index = st.session_state.responses.get(s_id, {}).get("selected_index", None)

        col1, col2 = st.columns([4.8, 6.2])

        # Column 1: Audio, English Sentence, and Stressed Word (Stacked Vertically)
        with col1:
            st.markdown(f"<span class='q-tag'>#{s_id}</span>", unsafe_allow_html=True)
            if audio_path and os.path.exists(audio_path):
                st.audio(audio_path, format="audio/wav")
            else:
                st.caption("Audio unavailable")

            highlighted = highlight_sentence(src_eng, emph_words)
            st.markdown(f"<div class='english-cell' style='margin: 0.35rem 0 0.3rem 0;'>{highlighted}</div>", unsafe_allow_html=True)

            st.markdown(
                f"<div style='display: flex; align-items: center; gap: 6px;'>"
                f"<span style='font-size: 0.8rem; color: #64748B; font-weight: 600;'>Stressed:</span>"
                f"<span class='stressed-tag'>{stressed_display}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Column 2: Malayalam Candidate Options Grouped in cell
        with col2:
            selected_option = st.radio(
                label=f"Q{s_id}_options",
                options=option_labels,
                index=saved_index if saved_index is not None else None,
                key=f"radio_q_{s_id}",
                label_visibility="collapsed",
            )
            # Store answer into session state immediately upon selection
            if selected_option is not None:
                chosen_idx = option_labels.index(selected_option)
                chosen_obj = target_options[chosen_idx]
                st.session_state.responses[s_id] = {
                    "sentence_id": s_id,
                    "source_english": src_eng,
                    "emphasized_words": emph_words,
                    "selected_option_id": chosen_obj["id"],
                    "selected_target_text": chosen_obj["text"],
                    "selected_index": chosen_idx,
                }

        st.markdown("<hr style='margin: 0.35rem 0; border: none; border-top: 1px solid #E2E8F0;' />", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    # Bottom Pagination Controls
    col_nav1, col_nav2, col_nav3 = st.columns([1.5, 2.5, 2.0])

    with col_nav1:
        if curr_page > 0:
            if st.button("Previous Page", use_container_width=True, disabled=st.session_state.submitting):
                st.session_state.current_page -= 1
                st.rerun()

    with col_nav2:
        st.markdown(
            f"<div style='text-align: center; color: #64748B; font-size: 0.9rem; padding-top: 0.5rem;'>"
            f"Page <b>{curr_page + 1}</b> of <b>{total_pages}</b> &bull; {len(current_batch)} questions"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_nav3:
        is_last_page = (curr_page == total_pages - 1)
        btn_label = "Submit All Responses" if is_last_page else "Next Page"

        if st.button(btn_label, type="primary", use_container_width=True, disabled=st.session_state.submitting):
            # Check if all 10 questions on the current page have been selected
            missing_on_page = [
                item.get("id")
                for item in current_batch
                if item.get("id") not in st.session_state.responses
            ]

            if missing_on_page:
                st.error(f"Please answer all 10 questions on this page before continuing. (Missing: #{', #'.join(map(str, missing_on_page))})")
            else:
                if not is_last_page:
                    st.session_state.current_page += 1
                    st.rerun()
                else:
                    # Final Submission: Check that all questions across all pages are completed
                    all_missing = [
                        s.get("id", i + 1)
                        for i, s in enumerate(sentences)
                        if s.get("id", i + 1) not in st.session_state.responses
                    ]
                    if all_missing:
                        st.error(f"Some questions on earlier pages were not answered: #{', #'.join(map(str, all_missing))}")
                    else:
                        st.session_state.submitting = True
                        with st.spinner("Submitting Please wait..."):
                            response_list = [st.session_state.responses[s.get("id", i + 1)] for i, s in enumerate(sentences)]
                            pid, csv_path, gsheet_synced = save_participant_response(
                                st.session_state.participant_info, response_list
                            )
                            st.session_state.final_pid = pid
                            st.session_state.gsheet_synced = gsheet_synced
                            st.session_state.submitting = False
                            st.session_state.page = "thank_you"
                            st.rerun()


# ==========================================
# PAGE 3: THANK YOU & DATA PERSISTENCE
# ==========================================
elif st.session_state.page == "thank_you":
    st.progress(1.0)
    st.markdown(
        """
        <div class="main-header" style="text-align: center; background: linear-gradient(135deg, #059669 0%, #10B981 100%);">
            <h1 style="font-size: 2.2rem;">Thank You</h1>
            <p style="font-size: 1.1rem; color: #ECFDF5;">Your responses have been successfully recorded for this pilot study.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pid = st.session_state.get("final_pid", "N/A")
    participant_name = st.session_state.participant_info.get("name", "Participant")
    gsheet_synced = st.session_state.get("gsheet_synced", False)

    storage_message = (
        "Your answers have been permanently recorded."
        if gsheet_synced
        else "Your answers have been safely stored. You may now close this browser tab."
    )

    st.markdown(
        f"""
        <div class="card-container" style="text-align: center;">
            <h3>Submission Summary</h3>
            <p style="color: #475569;">Participant ID: <b style="color: #4F46E5; font-size: 1.1rem;">{pid}</b></p>
            <p style="color: #475569;">Participant: <b>{participant_name}</b></p>
            <p style="color: #475569;">Total Sentences Evaluated: <b>{len(sentences)}</b></p>
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; padding: 0.8rem; border-radius: 8px; margin-top: 1rem;">
                {storage_message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
