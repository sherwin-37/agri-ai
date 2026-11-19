# AGRI-AI

AGRI-AI is a Streamlit farming dashboard with a simulator, multilingual chat,
voice controls, and optional Arduino sensor support.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run agribot.py
```

For AI answers, set `DEEPSEEK_API_KEY` as an environment variable or in
`.streamlit/secrets.toml`:

```toml
DEEPSEEK_API_KEY = "your-key"
```

Without a key, the dashboard still runs with its local/basic replies.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app**.
3. Select this repository, the `main` branch, and `agribot.py` as the app file.
4. Add `DEEPSEEK_API_KEY` under the app's **Settings → Secrets** if AI answers
   are needed. Do not commit secrets to GitHub.

The Community Cloud host cannot access an Arduino connected to your computer;
use the simulator there. The bundled `agri_data_base.pdf` is included in this
repository and is used automatically. Additional textbook pages can be uploaded
in the app's sidebar.
