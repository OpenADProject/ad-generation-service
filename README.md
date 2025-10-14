### 협업일지
- 윤승호: [https://www.notion.so/yoonsnowdev/1d6219b29fc380a0b152d5457e2f4839?pvs=4](https://www.notion.so/1d6219b29fc380a0b152d5457e2f4839?pvs=21)
- 김민경: [https://endurable-ice-f3c.notion.site/Daily-268218930d5e80b59688f91293fb744c](https://www.notion.so/Daily-268218930d5e80b59688f91293fb744c?pvs=21)
- 김하늘: [https://www.notion.so/26906aa61633805c8115c3b58a0a42c4?source=copy_link](https://www.notion.so/26906aa61633805c8115c3b58a0a42c4?pvs=21)
- 방지형: [https://www.notion.so/237f89eac2f180dcbce8de3bb40cdd64?source=copy_link](https://www.notion.so/237f89eac2f180dcbce8de3bb40cdd64?pvs=21)
- 손주희: [https://www.notion.so/23846e2fcad880189b0ad50df0aea229?source=copy_link](https://www.notion.so/26846e2fcad880f799a3e4702d382700?pvs=21)

<br>
<br>
<br>


# 📌 프로젝트 개요
디지털 마케팅의 높은 장벽을 허무는 것을 목표로 합니다. IT 기기나 복잡한 설명서가 낯선 부모님 세대나 소상공인도, 단 몇 번의 클릭만으로 자신의 상황에 꼭 맞는 전문가 수준의 광고 콘텐츠를 즉시 생성할 수 있는 가장 직관적인 AI 서비스를 만듭니다.

### 해결하려는 문제
소상공인이나 시니어 세대는 마케팅의 필요성을 느끼지만, 시간 부족, 높은 비용, 복잡한 디지털 툴 사용의 어려움 때문에 효과적인 광고를 집행하지 못하고 있습니다.

### 타겟 유저
* 디지털 마케팅에 익숙하지 않은 50대 이상의 시니어 사장님
* 마케팅 전담 인력 없이 혼자서 모든 것을 해결해야 하는 1인 사업가

### 핵심 기능
* 선택지 기반 단순 입력 구조로 사용 편의성 극대화
* 인스타그램, 네이버 플레이스, 지역 커뮤니티별 문체와 포맷 자동 반영
* 사람, 동물 등 다양한 모델을 사용해 특별한 광고 콘텐츠 제작 

### 기대 효과
사용자는 더 이상 광고 문구를 고민하는 데 시간을 낭비하지 않고, 클릭 몇 번만으로 광고를 만들 수 있습니다. 이를 통해 마케팅 비용과 노력을 줄여 핵심 비즈니스에 더 집중할 수 있고 누구나 기술의 도움을 받아 자신의 가게를 효과적으로 알릴 수 있습니다.

### 기술 스택

- **언어:**
  ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
- **프레임워크:**
  ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
- **라이브러리:**
  ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
  ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
  ![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=white)
- **도구:**
  ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)
  ![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)
  ![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)

<br>
<br>

# ⚙️ 설치 및 실행 방법
이 프로젝트는 Backend, Frontend, Model Server 총 3개의 서버를 실행해야 정상적으로 동작합니다.

### 1. 사전 준비
1. **리포지토리 복제(Clone)**
    ```bash
    git clone [https://github.com/your-username/ad-generation-service.git](https://github.com/your-username/ad-generation-service.git)
    cd ad-generation-service
    ```

2. **가상환경 생성 및 활성화**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **필수 라이브러리 설치**
    ```bash
    pip install -r requirements.txt
    ```

4. **환경 변수 (.env)**
    환경 변수는 각 서버 루트에 존재합니다.
    ```bash
    OPENAI_API_KEY=YourOpenAIKey
    HF_TOKEN=YourHuggingfaceKey
    ```

### 2. 서버 실행
각 서버는 **별도의 터미널 창**을 열어서 실행해야 합니다.

1.  **Backend 서버 실행 (FastAPI)**
    * **실행 위치:** `src/backend/`
    * **명령어:**
        ```bash
        cd src/backend
        uvicorn main:app --reload
        ```

2.  **Frontend 서버 실행 (Streamlit)**
    * **실행 위치:** `src/frontend/`
    * **명령어:**
        ```bash
        cd src/frontend
        streamlit run app.py
        ```
        
3.  **Model 서버 실행 (API Server)**
    * **실행 위치:** `src/model/imagemodel/`
    * **명령어:**
        ```bash
        cd src/model/imagemodel
        python api_server.py
        ```

4.  **Text Model 서버 실행 (FastAPI)**
    * **실행 위치:** `src/model/textmodel/`
    * **명령어:**
        ```bash
        cd src/model/textmodel
        uvicorn text_generation:app --reload
        ```

<br>
<br>

# 📂 프로젝트 구조
Frontend, Backend, AI Model의 역할을 명확히 분리해 구성되어 있습니다. 각 디렉토리의 주요 역할은 다음과 같습니다.

```bash
ad-generation-service/
├── README.md                # 프로젝트 설명 문서
├── database.db              # SQLite 데이터베이스 파일
├── image/                   # README에 사용될 이미지/GIF 저장 폴더
├── requirements.txt         # 프로젝트 의존성 라이브러리 목록
├── scripts/                 # DB 초기화 등 보조 스크립트 폴더
└── src/                     # 핵심 소스 코드 폴더
    ├── backend/             # FastAPI 백엔드 서버
    ├── frontend/            # Streamlit 프론트엔드 서버
    ├── model/               # AI 모델 및 모델 API 서버
    └── serving/             # 모델 서빙 관련 코드
```

<br>
<br>

# 💡 데모 사이트
아래 링크와 테스트 계정으로 접속해 프로젝트의 주요 기능을 직접 체험해 볼 수 있습니다.

🔗 **Link:** **[http://34.123.118.58:8501/](http://34.123.118.58:8501/)**

---

### **로그인 정보**
| 구분 | 내용 |
|:---:|:---|
| 아이디 | `admin` |
| 비밀번호 | `1234` |

---

![서비스 메인 화면](image/OpenADProject_text.gif)

<br>
<br>

# 🤖 사용한 모델 및 라이선스
라이선스 규정을 준수하기 위해 각 모델의 사용 정책을 확인했습니다.

### 텍스트 생성 모델
* OpenAI GPT-4.1-mini: OpenAI API 전용 (상업적 사용 가능, API 기반)

### 이미지 생성 모델
* stabilityai/stable-diffusion-xl-base-1.0: OpenRAIL++ (상업적 사용 가능, 모델 사용 시 제한된 사용 정책 준수 필요)
* stabilityai/stable-diffusion-xl-refiner-1.0: OpenRAIL++ (상업적 사용 가능, 모델 사용 시 제한된 사용 정책 준수 필요)
* madebyollin/sdxl-vae-fp16-fix: OpenRAIL++ (상업적 사용 가능, 모델 사용 시 제한된 사용 정책 준수 필요)

### 보조 및 제어 모델 (Supporting & Control Models)
* diffusers/controlnet-depth-sdxl-1.0: OpenRAIL++ (상업적 사용 가능, 모델 사용 시 제한된 사용 정책 준수 필요)
* diffusers/controlnet-canny-sdxl-1.0: OpenRAIL++ (상업적 사용 가능, 모델 사용 시 제한된 사용 정책 준수 필요)
* destitech/controlnet-inpaint-dreamer-sdxl: Apache-2.0 (상업적 사용 가능, 라이선스 및 저작권 고지 필요)
* h94/IP-Adapter: Apache-2.0 (상업적 사용 가능, 라이선스 및 저작권 고지 필요)
* laion/CLIP-ViT-H-14-laion2B-s32B-b79K: OpenRAIL (IP-Adapter의 이미지 인코더로 사용)
* IDEA-Research/grounding-dino-tiny: Apache-2.0 (객체 탐지를 위한 모델)
* facebook/sam-vit-huge: Apache-2.0 (이미지 분할을 위한 Segment Anything Model)