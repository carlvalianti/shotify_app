@echo off
start "" cmd /c "py -m streamlit run app.py --server.port 8502"
timeout /t 3 > nul