# 모든 서버 실행 파일
import sys

# 예시
commands = {
    "backend": [
        sys.executable, "-m", "uvicorn", "src.backend.app.main:app",
        "--host", "0.0.0.0", "--port", "9000", "--reload"
    ],
    "serving": [
        sys.executable, "-m", "uvicorn", "src.serving.app.main:app",
        "--host", "0.0.0.0", "--port", "9001", "--reload"
    ],
    "frontend": [
        sys.executable, "-m", "streamlit", "run", "src/frontend/app.py",
        "--server.port", "8501"
    ]
}