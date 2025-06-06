### streamlitUI branch에 대한 설명

+ 본 branch는 <치매 증상 지연 서비스> 구축 중, UI의 필요성을 느끼고 5월 18일에 구축되었습니다.

+ 본 branch는 아래와 같은 기능을 가집니다.

    + 진단서 자동 분석: PDF 진단서 업로드 및 자동 정보 추출, 환자 기본 정보 (이름, 생년월일, 진단일) 자동 파싱, 치매 진단 여부 확인

    + 단계별 시스템:
         
         + 초기 회상 단계 (진단 후 30일 이내): 하루 최대 2개의 새로운 질문 제공, 개인적 기억과 경험에 대한 질문, 답변 내용을 데이터베이스에 안전하게 저장
     
         + 기억 점검 단계 (진단 후 30일 이후): 하루 1개의 새로운 질문 + 1개의 기억 점검, 과거 답변과 현재 기억 비교 분석, koBERT 모델 기반 유사도 측정

    + AI 이미지 생성: 기억하지 못하는 경우 OpenAI DALL-E를 활용한 기억 보조 이미지 생성, 답변 내용에서 모델을 활용해 키워드 자동 추출, 시각적 단서를 통한 기억 회복 지원
      
    + 진행 상황 추적: 일별/누적 활동 현황 모니터링, 기억 점검 성공률 통계, 재사용 가능한 질문 관리 시스템

+ 본 branch의 시스템 아키텍쳐는 아래와 같습니다.

├── main.py                    # 메인 애플리케이션 진입점

├── database.py               # SQLite 데이터베이스 관리

├── pages/

│   ├── 1_documentUpload.py   # 진단서 업로드 페이지

│   └── 2_realchat_with_DB.py # 메인 채팅 인터페이스

├── components/               # UI 컴포넌트

│   ├── initial_phase.py      # 초기 회상 단계 UI

│   ├── memory_check_phase.py # 기억 점검 단계 UI

│   └── user_info.py          # 사용자 정보 관리

├── utils/                    # 유틸리티 모듈

│   ├── db_operations.py      # 데이터베이스 작업

│   ├── memory_check.py       # 기억 검증 로직

│   ├── image_generation.py   # AI 이미지 생성

│   ├── question_loader.py    # 질문 로딩 시스템

│   └── constants.py          # 시스템 상수

└── migrate_questions.py      # CSV 질문 마이그레이션 도구

### streamlitUI 설치 및 실행 방법

##### 설치

1. 환경 설정
   
// 저장소 클론

`git clone [repository-url]`

`cd dementia-delay-service`

// 의존성 설치

`pip install -r requirements.txt`

2. OpenAI API 설정

`utils/image_generation.py` 파일에서 API 키 설정:

`OPENAI_API_KEY = "your-openai-api-key-here"`

3. 데이터 베이스 초기화 (선택 사항)

`python migrate_questions.py`

4. 애플리케이션 실행

`streamlit run main.py`

##### 사용 방법

###### 1단계: 진단서 업로드

  + 페이지 사이드바에서 "1_documentUpload" 선택

  + PDF 진단서 파일 업로드

  + 자동 추출된 정보 확인

###### 2단계: 기억 훈련 시작

  + "2_realchat_with_DB" 페이지로 이동

  + 진단일 기준으로 자동 단계 결정

  + 일일 할당량에 따른 질문 수행
