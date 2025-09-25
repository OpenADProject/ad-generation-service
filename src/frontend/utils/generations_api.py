import requests
import streamlit as st
from typing import Any, Dict, List, Optional, Tuple

API_BASE = st.secrets["API_BASE"]
TIMEOUT = 20

def _auth_headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

# 기본 데이터 관리
def save_generation(input_text: str,
                    input_image_path: str | None = None,
                    output_text: str | None = None,
                    output_image_path: str | None = None) -> dict:
    """POST /generations/"""
    payload = {"input_text": input_text}
    if input_image_path:
        payload["input_image_path"] = input_image_path
    if output_text:
        payload["output_text"] = output_text
    if output_image_path:
        payload["output_image_path"] = output_image_path

    r = requests.post(f"{API_BASE}/generations/", json=payload, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_generations(skip: int = 0, limit: int = 100) -> list[dict]:
    """GET /generations/"""
    r = requests.get(f"{API_BASE}/generations/", params={"skip": skip, "limit": limit}, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_generation(gen_id: int) -> dict:
    """DELETE /generations/{id}"""
    r = requests.delete(f"{API_BASE}/generations/{gen_id}", headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# 모델 이미지 관리
def upload_user_model(alias: str, file_name: str, file_bytes: bytes) -> dict:
    """
    POST /user-models/
    - 백엔드 라우터는 `alias`(Form), `file`(File) 로 받으므로
      여기서는 multipart(form-data)로 전송
    """
    url = f"{API_BASE}/user-models/"
    files = {"file": (file_name, file_bytes, "application/octet-stream")}
    data = {"alias": alias}
    r = requests.post(url, files=files, data=data, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_user_models() -> list[dict]:
    """GET /user-models/"""
    url = f"{API_BASE}/user-models/"
    r = requests.get(url, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def rename_user_model(model_id: int, new_alias: str) -> dict:
    """PATCH /user-models/{id}  (payload: {'alias': '새 이름'})"""
    url = f"{API_BASE}/user-models/{model_id}"
    payload = {"alias": new_alias}
    r = requests.patch(url, json=payload, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_user_model(model_id: int) -> dict:
    """DELETE /user-models/{id}"""
    url = f"{API_BASE}/user-models/{model_id}"
    r = requests.delete(url, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# 로그인 관리
def login_user(username, password):
    try:
        r = requests.post(
            f"{API_BASE}/auth/login",
            data={"username": username, "password": password},
            timeout=TIMEOUT
        )
        # st.write("DEBUG login response:", r.status_code, r.text)
        if r.status_code != 200:
            return None
        data = r.json()
        # 표준: access_token. 혹시 token 키가 오면 호환
        return data.get("access_token") or data.get("token")
    except requests.ConnectionError:
        st.error("백엔드 서버에 연결할 수 없습니다.")
        return None