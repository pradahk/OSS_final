# 상수 정의
SIMILARITY_THRESHOLD = 0.7
MAX_DAILY_NEW_QUESTIONS = 2
MAX_DAILY_MEMORY_CHECKS = 1
INITIAL_PHASE_DAYS = 30
MAX_KEYWORDS_PER_ANSWER = 3

# OpenAI 설정
OPENAI_MODEL = "dall-e-3"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"

# 질문 타입
QUESTION_TYPES = {
    'INITIAL': 'initial_memory',
    'REVISIT': 'revisit_memory',
    'GENERAL': 'new_general',
    'CSV_IMPORT': 'csv_import'
}

# 기억 확인 결과 타입
MEMORY_CHECK_RESULTS = {
    'PASSED': 'passed',
    'FAILED': 'failed',
    'IMAGE_GENERATED': 'image_generated',
    'FAILED_VERIFICATION': 'failed_verification',
    'COMPLETE_FAILURE': 'complete_failure',
    'REQUIRES_IMAGE': 'requires_image',
    'IMAGE_ASSISTED': 'image_assisted'
}