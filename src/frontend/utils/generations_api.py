import requests
import streamlit as st
from typing import Any, Dict, List, Optional, Tuple

API_BASE = st.secrets["API_BASE"]
TIMEOUT = 20

def _auth_headers() -> dict:
    """
    인증 헤더 생성
    - 세션에 저장된 access_token을 가져와 Bearer 헤더 구성
    - 토큰이 없으면 빈 dict 반환
    """
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

# 기본 데이터 관리
def save_generation(input_text: str,
                    input_image_path: str | None = None,
                    output_text: str | None = None,
                    output_image_path: str | None = None) -> dict:
    """
    POST /generations/
    - 광고 생성 결과(텍스트/이미지)를 서버에 저장
    - 응답: 생성된 generation 객체(JSON)
    """
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
    """
    GET /generations/
    - 광고 생성 이력 목록 조회
    - 최신순 정렬은 클라이언트에서 처리
    """
    r = requests.get(f"{API_BASE}/generations/", params={"skip": skip, "limit": limit}, headers=_auth_headers(), timeout=TIMEOUT)
    ### 디버깅용
    # st.write("DEBUG generations resp:", r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def delete_generation(gen_id: int) -> dict:
    """
    DELETE /generations/{id}
    - 특정 생성 이력을 삭제
    - 응답: 삭제 결과 메시지(JSON)
    """
    r = requests.delete(f"{API_BASE}/generations/{gen_id}", headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# 모델 이미지 관리
def upload_user_model(alias: str, file_name: str, file_bytes: bytes) -> dict:
    """
    POST /user-models/
    - 사용자 모델 이미지 업로드
    - multipart/form-data로 전송 (alias, file)
    - 응답: 업로드된 모델 정보(JSON)
    """
    url = f"{API_BASE}/user-models/"
    files = {"file": (file_name, file_bytes, "application/octet-stream")}
    data = {"alias": alias}
    r = requests.post(url, files=files, data=data, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_user_models() -> list[dict]:
    """
    GET /user-models/
    - 사용자 모델 이미지 목록 조회
    """
    url = f"{API_BASE}/user-models/"
    r = requests.get(url, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def rename_user_model(model_id: int, new_alias: str) -> dict:
    """
    PATCH /user-models/{id}
    - 모델 이름(alias) 변경
    - payload: {"alias": "새 이름"}
    """
    url = f"{API_BASE}/user-models/{model_id}"
    payload = {"alias": new_alias}
    r = requests.patch(url, json=payload, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_user_model(model_id: int) -> dict:
    """
    DELETE /user-models/{id}
    - 사용자 모델 삭제
    """
    url = f"{API_BASE}/user-models/{model_id}"
    r = requests.delete(url, headers=_auth_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# 로그인 관리
def login_user(username, password):
    """
    POST /auth/login
    - 로그인 요청
    - 성공 시 access_token 반환
    - 실패 시 None 반환
    - 연결 오류 발생 시 스트림릿 에러 표시
    """
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

# 회원가입
def signup_user(username: str, password: str, timeout: int = TIMEOUT) -> Tuple[bool, Dict[str, Any] | str]:
    """
    POST /auth/users/
    - 회원가입 요청
    - 성공: (True, 응답 JSON)
    - 실패: (False, 에러 정보 또는 메시지)
    - 422: 유효성 검증 실패, 409: 중복 사용자 처리
    """
    # 입력 간단 정리
    u = (username or "").strip()
    p = (password or "").strip()

    if not u or not p:
        return False, {"code": 400, "message": "아이디와 비밀번호를 모두 입력해주세요."}

    url = f"{API_BASE}/auth/users/"
    payload = {"username": u, "password": p}

    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code in (200, 201):
            return True, r.json()
        if r.status_code == 422:
            # FastAPI validation 에러 형태 반영
            return False, {
                "code": 422,
                "message": "입력값 검증에 실패했습니다.",
                "errors": r.json().get("detail", []),
            }
        if r.status_code in (400, 409):
            # 중복 사용자 등
            data = {}
            try:
                data = r.json()
            except Exception:
                pass
            return False, {
                "code": r.status_code,
                "message": data.get("detail") if isinstance(data, dict) else "요청이 거절되었습니다.",
            }

        # 그 외
        return False, {"code": r.status_code, "message": "회원가입에 실패했습니다."}
    except requests.RequestException as e:
        return False, f"네트워크 오류: {e}"