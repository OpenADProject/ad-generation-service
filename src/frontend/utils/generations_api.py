import requests
import streamlit as st

API_BASE = st.secrets["API_BASE"]
TIMEOUT = 20

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

    r = requests.post(f"{API_BASE}/generations/", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_generations(skip: int = 0, limit: int = 100) -> list[dict]:
    """GET /generations/"""
    r = requests.get(f"{API_BASE}/generations/", params={"skip": skip, "limit": limit}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def delete_generation(gen_id: int) -> dict:
    """DELETE /generations/{id}"""
    r = requests.delete(f"{API_BASE}/generations/{gen_id}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
