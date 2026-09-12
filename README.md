# Speech & Prosody Perception Pilot Study Web App

A clean, deployable Streamlit application designed for cross-lingual speech perception and prosody pilot studies (English source audio & emphasized words vs. 5 candidate Malayalam target sentences).

---

## 🌟 Key Features

1. **Participant Intake & Demographics (Page 1)**:
   - Full Name, Email, Age, Gender
   - Language Proficiency (Malayalam & English)

2. **$N$-Sentence Perceptual Evaluation (Pages 2 to $N+1$)**:
   - Clean step progress tracker (`Sentence i of N`).
   - Integrated **audio player** for source English recordings.
   - High-contrast visual highlighting of **emphasized words** within the source sentence.
   - **5 Candidate Malayalam Sentences** with **mandatory selection requirement** before advancing to the next sentence.
   - Backward and forward navigation.

3. **Automated Data Persistence & Export**:
   - Each completed session generates a unique `Participant ID`.
   - Aggregates all selections and participant demographics into `data/responses/all_responses.csv`.
   - Saves individual JSON snapshots per participant in `data/responses/<participant_id>.json`.
   - In-app researcher download button for direct CSV export.

---

## 🚀 How to Run Locally

1. **Activate the Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```

2. **Run the Streamlit App**:
   ```bash
   streamlit run app.py
   ```
   *Or without activating:*
   ```powershell
   .\venv\Scripts\streamlit run app.py
   ```

3. Open your browser at `http://localhost:8501`.

---

## ⚙️ How to Customize Sentences & Audio

You do not need to change any python code to add your own sentences!

1. Open `data/study_data.json`.
2. Add or modify sentence items in the `sentences` list:
   ```json
   {
     "id": 1,
     "audio_file": "my_sentence_1.wav",
     "source_english": "I never said she stole my money.",
     "emphasized_words": ["never"],
     "target_options": [
       {"id": "A", "text": "മലയാളം വാചകം 1..."},
       {"id": "B", "text": "മലയാളം വാചകം 2..."},
       {"id": "C", "text": "മലയാളം വാചകം 3..."},
       {"id": "D", "text": "മലയാളം വാചകം 4..."},
       {"id": "E", "text": "മലയാളം വാചകം 5..."}
     ]
   }
   ```
3. Put your real audio files (`.wav` or `.mp3`) in the `data/audio/` folder matching the filenames in the JSON.
   *(If an audio file is not found, the app automatically creates a harmonic tone so you can test immediately without errors).*

## 📊 Permanent Cloud Storage (Google Sheets)

By default, responses are saved locally to `data/responses/all_responses.csv`. 

When deployed online (e.g. on Streamlit Cloud), connect a Google Sheet so results are saved permanently in real-time to your Google Drive:

1. **Create a Google Sheet**:
   - Create a blank Google Sheet in your Google Drive (e.g., named *Pilot Study Responses*).
   - Copy its URL from the browser address bar.

2. **Create a Google Cloud Service Account (Free)**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the **Google Sheets API** and **Google Drive API**.
   - Under **Credentials**, click **Create Credentials > Service Account**.
   - Click on the service account, go to the **Keys** tab, click **Add Key > Create New Key > JSON**, and download the JSON key.

3. **Share Your Google Sheet**:
   - Open your Google Sheet, click **Share**, and paste the service account's email address (e.g., `xxx@xxx.iam.gserviceaccount.com`) as **Editor**.

4. **Connect to Streamlit**:
   - **Locally**: Copy `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml` and fill in the values from your downloaded JSON.
   - **On Streamlit Cloud**: In your app settings on [share.streamlit.io](https://share.streamlit.io), go to **Secrets** and paste the same contents from `.streamlit/secrets.toml`.
