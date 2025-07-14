@echo off
start "" cmd /c "py -m streamlit run app.py --server.port 8501"
timeout /t 3 > nul