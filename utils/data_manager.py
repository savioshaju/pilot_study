import json
import os
import math
import struct
import wave
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
RESPONSES_DIR = os.path.join(DATA_DIR, "responses")
STUDY_FILE = os.path.join(DATA_DIR, "study_data.json")

# Ensure required directories exist
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(RESPONSES_DIR, exist_ok=True)


def load_study_data():
    """Loads study metadata and sentence evaluation items from JSON."""
    if not os.path.exists(STUDY_FILE):
        return {"study_metadata": {}, "sentences": []}
    with open(STUDY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def ensure_sample_audio_files(sentences):
    """
    Ensures that for every sentence item, if the audio file doesn't exist,
    a lightweight harmonic test tone is generated so the web app won't crash.
    """
    sample_rate = 22050
    duration_s = 2.0
    num_samples = int(sample_rate * duration_s)

    tones = [440.0, 523.25, 587.33, 659.25, 698.46]

    for idx, s in enumerate(sentences):
        filename = s.get("audio_file", f"audio_{idx+1}.wav")
        filepath = os.path.join(AUDIO_DIR, filename)
        if not os.path.exists(filepath):
            freq = tones[idx % len(tones)]
            with wave.open(filepath, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                raw_frames = bytearray()
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    # Gentle envelope
                    envelope = math.sin(math.pi * t / duration_s)
                    val = int(32767.0 * 0.4 * envelope * math.sin(2.0 * math.pi * freq * t))
                    raw_frames.extend(struct.pack("<h", max(-32768, min(32767, val))))
                wav_file.writeframes(raw_frames)


def get_audio_path(filename):
    """Returns absolute path to an audio file if it exists."""
    path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(path):
        return path
    return None


def sync_to_google_sheets(flat_rows):
    """
    Attempts to permanently sync participant responses to a configured Google Sheet.
    Checks:
    1. st.secrets["gcp_service_account"] and st.secrets["google_sheets"]["spreadsheet_url" | "spreadsheet_name"]
    2. Local file 'service_account.json' (for local testing)
    Returns (success: bool, message: str)
    """
    if not flat_rows:
        return False, "No data rows to sync."

    try:
        import gspread
        import streamlit as st
    except ImportError:
        return False, "gspread library not available."

    client = None
    sheet_target = None

    try:
        # Check Streamlit secrets
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            sa_info = dict(st.secrets["gcp_service_account"])
            client = gspread.service_account_from_dict(sa_info)
            if "google_sheets" in st.secrets:
                sheet_target = st.secrets["google_sheets"].get("spreadsheet_url") or st.secrets["google_sheets"].get("spreadsheet_name")

        # Fallback to local service_account.json
        local_sa = os.path.join(BASE_DIR, "service_account.json")
        if not client and os.path.exists(local_sa):
            client = gspread.service_account(filename=local_sa)
            study_data = load_study_data()
            sheet_target = study_data.get("study_metadata", {}).get("google_sheet_url_or_name")

        if not client or not sheet_target:
            return False, "Google Sheets credentials not configured. Responses stored to local CSV/JSON backup."

        # Attempt sync with up to 3 retries in case of transient network hiccups
        import time
        max_retries = 3
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                # Open sheet by URL or by Name
                if sheet_target.startswith("https://"):
                    spreadsheet = client.open_by_url(sheet_target)
                else:
                    spreadsheet = client.open(sheet_target)

                worksheet = spreadsheet.sheet1
                headers = list(flat_rows[0].keys())

                existing_values = worksheet.get_all_values()
                if not existing_values:
                    worksheet.append_row(headers)
                    rows_to_append = [[str(row.get(h, "")) for h in headers] for row in flat_rows]
                    worksheet.append_rows(rows_to_append)
                else:
                    existing_headers = existing_values[0]
                    # If old format is present (has 'sentence_id' or un-indexed headers), reset to new layout
                    is_old_format = ("sentence_id" in existing_headers) or any(
                        not h.startswith("Q") and ' - "' in h for h in existing_headers
                    )
                    if is_old_format:
                        worksheet.clear()
                        worksheet.append_row(headers)
                        existing_headers = headers

                    # Ensure any new question headers are added to row 1
                    missing_headers = [h for h in headers if h not in existing_headers]
                    if missing_headers:
                        existing_headers.extend(missing_headers)
                        worksheet.update(values=[existing_headers], range_name="1:1")

                    rows_to_append = [[str(row.get(h, "")) for h in existing_headers] for row in flat_rows]
                    worksheet.append_rows(rows_to_append)

                return True, "Successfully synced to Google Sheet."
            except Exception as ex:
                last_err = ex
                print(f"[Google Sheets Sync Attempt {attempt}/{max_retries} failed]: {ex}. Retrying in 2 seconds...")
                time.sleep(2)

        print(f"[Google Sheets Final Sync Notice]: {last_err}")
        return False, str(last_err)
    except Exception as e:
        print(f"[Google Sheets Sync Notice]: {e}")
        return False, str(e)


def save_participant_response(participant_info, responses):
    """
    Saves the participant's demographic data and ALL N trial selections in a SINGLE ROW.
    1. Saves individual JSON snapshot (local fail-safe)
    2. Appends to master CSV in wide format (1 participant = 1 row)
    3. Syncs to Google Sheet in wide format with headers: Q{id}: <English Sentence> - "<Emphasized Word>"
    """
    participant_id = participant_info.get("participant_id", f"P_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Save individual JSON record
    record = {
        "participant_id": participant_id,
        "submitted_at": timestamp,
        "demographics": participant_info,
        "trial_responses": responses
    }
    json_path = os.path.join(RESPONSES_DIR, f"{participant_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # 2. Build a SINGLE row per participant (wide format)
    single_participant_row = {
        "participant_id": participant_id,
        "submitted_at": timestamp,
        "name": participant_info.get("name", ""),
        "email": participant_info.get("email", ""),
        "age": participant_info.get("age", ""),
        "gender": participant_info.get("gender", ""),
        "malayalam_proficiency": participant_info.get("malayalam_proficiency", ""),
        "english_proficiency": participant_info.get("english_proficiency", ""),
    }

    # Add each trial as a unique column: Q{s_id}: [English sentence] - "[emphasized word]"
    # Using the question index ensures duplicate English sentences will NEVER overwrite each other
    for idx, item in enumerate(responses):
        s_id = item.get("sentence_id", idx + 1)
        src = item.get("source_english", "").strip()
        emph = ", ".join(item.get("emphasized_words", []))
        col_name = f'Q{s_id}: {src} - "{emph}"' if emph else f'Q{s_id}: {src}'

        opt_id = item.get("selected_option_id", "")
        opt_text = item.get("selected_target_text", "")
        selected_val = f"({opt_id}) {opt_text}" if opt_id and opt_text else opt_text

        single_participant_row[col_name] = selected_val

    flat_rows = [single_participant_row]

    # 3. Save to local CSV (wide format)
    df_new = pd.DataFrame(flat_rows)
    csv_path = os.path.join(RESPONSES_DIR, "all_responses.csv")
    if os.path.exists(csv_path):
        try:
            df_existing = pd.read_csv(csv_path)
            # If old format without 'Q1:' or with 'sentence_id', replace with clean wide format
            has_old_cols = ("sentence_id" in df_existing.columns) or any(
                not col.startswith("Q") and ' - "' in col for col in df_existing.columns
            )
            if has_old_cols:
                # Rebuild all historical responses from saved JSON files
                rebuild_and_sync_all_responses()
                return participant_id, csv_path, True
            else:
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
        except Exception:
            df_new.to_csv(csv_path, index=False, encoding="utf-8-sig")
    else:
        df_new.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 4. Sync single row to Google Sheets
    gsheet_synced, gsheet_message = sync_to_google_sheets(flat_rows)

    return participant_id, csv_path, gsheet_synced


def rebuild_and_sync_all_responses():
    """
    Rebuilds all_responses.csv and Google Sheets from all JSON records in data/responses/
    Ensuring every participant has exactly 1 single row containing all their answered questions.
    """
    all_rows = []
    if not os.path.exists(RESPONSES_DIR):
        return False, "No responses directory."

    json_files = sorted([f for f in os.listdir(RESPONSES_DIR) if f.endswith(".json")])
    for jf in json_files:
        filepath = os.path.join(RESPONSES_DIR, jf)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                rec = json.load(f)
            demographics = rec.get("demographics", {})
            row = {
                "participant_id": rec.get("participant_id", ""),
                "submitted_at": rec.get("submitted_at", ""),
                "name": demographics.get("name", ""),
                "email": demographics.get("email", ""),
                "age": demographics.get("age", ""),
                "gender": demographics.get("gender", ""),
                "malayalam_proficiency": demographics.get("malayalam_proficiency", ""),
                "english_proficiency": demographics.get("english_proficiency", ""),
            }
            for idx, item in enumerate(rec.get("trial_responses", [])):
                s_id = item.get("sentence_id", idx + 1)
                src = item.get("source_english", "").strip()
                emph = ", ".join(item.get("emphasized_words", []))
                col_name = f'Q{s_id}: {src} - "{emph}"' if emph else f'Q{s_id}: {src}'

                opt_id = item.get("selected_option_id", "")
                opt_text = item.get("selected_target_text", "")
                selected_val = f"({opt_id}) {opt_text}" if opt_id and opt_text else opt_text

                row[col_name] = selected_val
            all_rows.append(row)
        except Exception as e:
            print(f"Error reading {jf}: {e}")

    if not all_rows:
        return False, "No valid responses found."

    df = pd.DataFrame(all_rows)
    csv_path = os.path.join(RESPONSES_DIR, "all_responses.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Clear and rewrite Google Sheets with the clean master dataset
    try:
        import gspread
        import streamlit as st
        with open(os.path.join(BASE_DIR, ".streamlit", "secrets.toml"), "rb") as f:
            import tomllib
            secrets = tomllib.load(f)

        sa_info = secrets.get("gcp_service_account")
        sheet_target = secrets.get("google_sheets", {}).get("spreadsheet_url")
        if sa_info and sheet_target:
            client = gspread.service_account_from_dict(sa_info)
            sh = client.open_by_url(sheet_target)
            ws = sh.sheet1
            headers = list(df.columns)
            ws.clear()
            ws.append_row(headers)
            values = df.fillna("").astype(str).values.tolist()
            ws.append_rows(values)
            return True, "Rebuilt and synced successfully."
    except Exception as e:
        print(f"Failed to sync rebuilt data to Google Sheets: {e}")
        return False, str(e)

    return True, "Local CSV rebuilt."

