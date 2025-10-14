import time
from typing import Optional, Tuple
import streamlit as st
import json
from pathlib import Path
from utils.generations_api import save_generation, list_generations, delete_generation
from utils.model_api import generate_text
from st_copy import copy_button

BANNER_IMG_PATH   = "assets/community_text.png"

def ensure_session() -> None:
    """
    세션 상태 초기화
    - insta_text_result 키가 없을 경우 기본값 생성
    """
    if "insta_text_result" not in st.session_state:
        st.session_state.insta_text_result = None

# JSON 로드 & 캐시
@st.cache_data
def load_locations_json(path: str = "assets/regions_filtered.json") -> dict:
    """
    지역 선택용 JSON 파일 로드 및 트리 형태로 변환
    - 원본(list 스키마) → {시/도: {시/군/구: [읍/면/동]}} 구조
    - dict 형태면 그대로 반환
    - 캐시 적용으로 반복 호출 최적화
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"지역 JSON 파일을 찾을 수 없습니다: {p.resolve()}")

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 이미 dict 형태면 그대로 반환 (호환성)
    if isinstance(data, dict):
        return data

    if not isinstance(data, list):
        raise ValueError("지원하지 않는 JSON 형식입니다. dict 또는 list 여야 합니다.")

    tree: dict[str, dict[str, set[str]]] = {}
    for row in data:
        # 컬럼명 고정 (주신 스키마)
        sido = (row.get("시/도") or "").strip()
        sg   = (row.get("시/군/구") or "").strip()
        emds = row.get("읍/면/동/리") or []
        if not (sido and sg and isinstance(emds, list)):
            continue
        bucket = tree.setdefault(sido, {}).setdefault(sg, set())
        for e in emds:
            name = (e or "").strip()
            if name:
                bucket.add(name)

    # set → 정렬 리스트
    normalized = {
        s: {g: sorted(list(emd_set)) for g, emd_set in sub.items()}
        for s, sub in tree.items()
    }
    return normalized

def reset_cascade_state(level_key: str, *child_keys: str) -> None:
    """
    캐스케이딩 지역 선택 박스 상태 초기화
    - 상위 선택이 변경되면 하위 선택값 리셋
    """
    # 현재 렌더링에서 선택된 값
    current = st.session_state.get(level_key)
    # 이전 렌더링에서 기억해둔 부모 선택
    memo_key = f"__memo_{level_key}"
    prev = st.session_state.get(memo_key)
    if prev != current:
        # 부모가 바뀌면 자식들 초기화
        for ck in child_keys:
            if ck in st.session_state:
                del st.session_state[ck]
        st.session_state[memo_key] = current

def render_intro() -> None:
    """
    상단 배너 및 인스타 텍스트 생성 가이드 표시
    """
    st.image(BANNER_IMG_PATH)
    st.markdown(
        """
        <style>
        .centered-text {
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <p style='font-size:18px; text-align:center;'>
        상품명/상호명, 말투 톤, 마케팅 타겟층, 영어 번역 옵션을 순서대로 입력해 주세요.
        <br><b>모두 입력이 끝나면</b> 맨 아래의 <span style="background-color:#c79dd7; color:white; padding:2px 6px; border-radius:30px;">광고 문구 생성하기</span> 버튼을 눌러주세요.
        </p>
        """,
        unsafe_allow_html=True
    )
    st.write(" ")
    st.write(" ")

def render_guide(
    label: str = "**광고 문구 생성 가이드**",
    page: str = "./pages/text_main_page.py",
):
    """
    가이드 버튼 렌더링
    - 클릭 시 안내 페이지로 이동
    """
    if st.button(label, type="primary"):
        st.switch_page(page)
    st.caption("💡 처음이라면 가이드를 확인하고 진행해 보세요!")
    
# 입력 폼
def build_form() -> Tuple[bool, str, str, str, bool, str]:
    """
    인스타그램 텍스트 생성 폼 렌더링
    - 상호명/상품명, 톤, 타겟, 영어 번역 옵션, 지역 수집
    - 캐스케이딩 지역 선택 지원

    Returns:
        submitted (bool): 제출 여부
        title (str): 상품/상호명
        tone (str): 말투 톤
        target (str): 마케팅 타겟층
        english_translation (bool): 영어 번역 포함 여부
        location (str): 지역명
    """
    with st.container(border=True):
        st.subheader("요청 사항 입력하기")

        # ① 상호/상품명
        st.markdown("① 상품명이나 상호명을 입력해주세요.")
        title = st.text_input(label="(간단한 설명을 함께 적어주시면 더 자연스럽고 풍성한 글이 생성돼요 😊)", key="insta_text_title")
        st.write(" ")

        # ② 톤
        st.markdown("② 원하시는 말투 톤을 선택해주세요.")
        tone = st.selectbox(
            label="", label_visibility="collapsed",
            options=["친근한", "고급스러운", "전문적인", "감성적인"], index=None, key="insta_text_tone",
        )
        st.write(" ")

        # ③ 타겟
        st.markdown("③ 마케팅 대상을 입력해주세요.")
        target = st.text_input(label="", label_visibility="collapsed", key="insta_text_target")
        st.write(" ")

        # ④ 영어 번역
        st.markdown("④ 영어 번역을 함께 넣을까요?")
        english_translation_label = st.selectbox(
            label="", label_visibility="collapsed",
            options=["포함", "포함 안 함"], index=None, key="insta_text_translate",
        )
        english_translation = (
            None if english_translation_label is None else english_translation_label == "포함"
        )
        st.write(" ")

        # ⑤ 지역 (동적 캐스케이딩 - 폼이 아니므로 즉시 갱신)
        st.markdown("⑤ 지역을 선택해주세요.")
        loc_data = load_locations_json("assets/regions_filtered.json")
        sido_options = sorted(loc_data.keys())
        col1, col2, col3 = st.columns(3)

        with col1:
            sido = st.selectbox("시/도", options=sido_options, index=None,
                                key="loc_sido", placeholder="선택")
        reset_cascade_state("loc_sido", "loc_sigungu", "loc_eupmyeondong")

        children = loc_data.get(sido, {}) if sido else {}
        sigungu_options = sorted(children.keys()) if isinstance(children, dict) else []

        with col2:
            sigungu = st.selectbox("시/군/구", options=sigungu_options, index=None,
                                key="loc_sigungu", placeholder="선택",
                                disabled=not bool(sido))
        reset_cascade_state("loc_sigungu", "loc_eupmyeondong")

        leaf = children.get(sigungu, []) if (sido and sigungu and isinstance(children, dict)) else []
        eupmyeondong_options = leaf if isinstance(leaf, list) else []

        with col3:
            eupmyeondong = st.selectbox("읍/면/동", options=eupmyeondong_options, index=None,
                                        key="loc_eupmyeondong", placeholder="선택",
                                        disabled=not bool(sido and sigungu))

        if sido and sigungu and eupmyeondong:
            location = f"{sido} {sigungu} {eupmyeondong}"
        elif sido and sigungu:
            location = f"{sido} {sigungu}"
        elif sido:
            location = f"{sido}"
        else:
            location = None

        st.write("")
        # 폼이 아니므로 일반 버튼 사용 (누르는 즉시 rerun)
        submitted = st.button("광고 문구 생성하기", type="primary", width="stretch")

        return submitted, title, tone, target, english_translation, location

# 텍스트 생성 결과
def render_result(text: str) -> None:
    """
    텍스트 생성 결과 표시
    - 결과 텍스트 출력 및 복사 버튼
    - 다운로드 버튼 제공
    """
    st.success("텍스트가 생성되었습니다! 🎉")
    with st.container(border=True):
        copy_button(
            text,
            icon="st",  # 폰트 영향 회피
            tooltip="클립보드에 복사",
            copied_label="복사 완료!",
            key=text,
        )
        st.markdown(text)

    st.download_button(
        "텍스트 다운로드",
        data=text.encode("utf-8"),
        file_name="insta_caption.txt",
        mime="text/plain",
        type="primary", 
        width="stretch"
    )

def main() -> None:
    """
    인스타그램 텍스트 생성 페이지 엔트리 포인트
    - 세션 초기화 및 인트로 렌더링
    - 입력 폼 렌더링
    - 제출 시 텍스트 생성 및 결과 표시
    - 생성 이력 저장
    """
    ensure_session()
    render_intro()
    render_guide()

    submitted, title, tone, target, english_translation, location = build_form()

    st.divider()

    if not submitted:
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    if not tone:
        st.warning("원하시는 말투 톤을 선택해주세요.")
        return

    if english_translation is None:
        st.warning("영어 번역 포함 여부를 선택해주세요.")
        return

    if not location:
        st.warning("지역을 선택해주세요.")
        return
    
               
     # 진행 표시: spinner
    placeholder = st.empty()
    with placeholder, st.spinner("센스있는 광고 문구를 생성 중이에요 ⌛"):
        generated_text = generate_text(
            product=title,
            tone=tone,
            target_audience=target,
            translate_en=english_translation,
            location = location
        )

    # 진행바 지우고 결과 렌더
    placeholder.empty()
    with placeholder.container():
        render_result(generated_text)
        st.session_state.insta_text_result = generated_text

        input_text = (
            f"[채널: instagram]\n"
            f"상품/상호명: {title}\n"
            f"톤: {tone}\n"
            f"타겟층: {target}\n"
            f"지역: {location}\n"
            f"영어 번역 포함: {'예' if english_translation else '아니오'}\n"
        )
    
        try:
            saved = save_generation(
                input_text=input_text,
                input_image_path=None,
                output_text=generated_text,
            )
            st.info(f"생성 이력이 저장되었어요 · ID: {saved.get('id','?')}")
        except Exception as e:
            st.warning(f"이력 저장은 건너뛰었습니다: {e}")

if __name__ == "__main__":
    main()
