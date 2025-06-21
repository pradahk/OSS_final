#!/usr/bin/env python3
"""
치매 증상 지연 서비스 상수 정의
"""

# === 서비스 단계 설정 ===
INITIAL_PHASE_DAYS = 30  # 초기 회상 단계 기간 (일)
MAX_DAILY_NEW_QUESTIONS_INITIAL = 2  # 초기 30일 동안 매일 새로운 질문 개수
MAX_DAILY_NEW_QUESTIONS_MAINTENANCE = 1  # 30일 이후 매일 새로운 질문 개수
MAX_DAILY_MEMORY_CHECKS = 1  # 30일 이후 매일 기억 점검 개수

# === 키워드 추출 및 유사도 검사 ===
MAX_KEYWORDS_PER_ANSWER = 6  # 답변당 최대 키워드 개수
KEYWORD_MATCH_THRESHOLD = 3  # 통과를 위한 최소 키워드 매칭 개수
SIMILARITY_THRESHOLD = 0.5  # 유사도 임계값 (0~1)

# === 이미지 생성 설정 ===
OPENAI_MODEL = "dall-e-3"  # OpenAI 이미지 생성 모델
IMAGE_SIZE = "1024x1024"  # 생성될 이미지 크기
IMAGE_QUALITY = "standard"  # 이미지 품질 (standard, hd)

# === 데이터베이스 설정 ===
DATABASE_NAME = 'memory_app.db'

# === 서비스 상태 ===
SERVICE_STATUS_ACTIVE = 'active'
SERVICE_STATUS_COMPLETED = 'completed'
SERVICE_STATUS_TERMINATED = 'terminated'

# === 질문 타입 ===
QUESTION_TYPE_INITIAL = 'initial_memory'
QUESTION_TYPE_REVISIT = 'revisit_memory'
QUESTION_TYPE_NEW_GENERAL = 'new_general'

# === 질문 상태 ===
QUESTION_STATUS_ACTIVE = 'active'
QUESTION_STATUS_ARCHIVED = 'archived'

# === 기억 확인 단계 ===
CHECK_STEP_INITIAL_RECALL = 'initial_recall'
CHECK_STEP_POST_HINT_RECALL = 'post_hint_recall'

# === 기억 확인 결과 ===
CHECK_RESULT_PASS = 'pass'
CHECK_RESULT_FAIL = 'fail'

# === 사용자 선택 ===
USER_CHOICE_REMEMBERS = 'remembers'
USER_CHOICE_FORGETS = 'forgets'