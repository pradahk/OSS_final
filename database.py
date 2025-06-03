import sqlite3
import datetime
import json # extracted_keywords 저장을 위해 json 모듈 사용

DATABASE_NAME = 'memory_app.db' # SQLite 데이터베이스 파일 이름

def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # 컬럼 이름으로 데이터 접근 가능하도록 설정
    return conn

def create_tables():
    """데이터베이스 테이블들을 생성합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birth_date TEXT NOT NULL, -- YYYY-MM-DD
            diagnosis_date TEXT NOT NULL, -- YYYY-MM-DD
            service_status TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'terminated'
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # QUESTIONS 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS QUESTIONS (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL, -- 'initial_memory', 'revisit_memory', 'new_general'
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # USER_ANSWERS 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USER_ANSWERS (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            answer_date TEXT NOT NULL, -- YYYY-MM-DD
            is_initial_answer BOOLEAN NOT NULL, -- 0 for FALSE, 1 for TRUE
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id),
            FOREIGN KEY (question_id) REFERENCES QUESTIONS(question_id)
        );
    """)

    # MEMORY_CHECKS 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MEMORY_CHECKS (
            check_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            original_answer_id INTEGER, -- FK to USER_ANSWERS, only if is_initial_answer is TRUE
            memory_status TEXT NOT NULL, -- 'remembered', 'forgotten'
            current_memory_text TEXT,
            similarity_score REAL,
            extracted_keywords_status TEXT, -- 'satisfied', 'insufficient'
            result TEXT NOT NULL, -- 'passed', 'failed', 'image_generated'
            check_type TEXT NOT NULL, -- 'manual_check', 'ai_check'
            extracted_keywords TEXT, -- JSON array string
            check_date TEXT NOT NULL, -- YYYY-MM-DD
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id),
            FOREIGN KEY (question_id) REFERENCES QUESTIONS(question_id),
            FOREIGN KEY (original_answer_id) REFERENCES USER_ANSWERS(answer_id)
        );
    """)

    # GENERATED_IMAGES 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GENERATED_IMAGES (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_check_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (memory_check_id) REFERENCES MEMORY_CHECKS(check_id)
        );
    """)

    # USER_PROGRESS 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USER_PROGRESS (
            progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE, -- 사용자별로 하나의 진행 상황만
            questions_answered_today INTEGER DEFAULT 0,
            total_initial_memory_questions_answered INTEGER DEFAULT 0,
            total_revisit_questions_answered INTEGER DEFAULT 0,
            total_new_general_questions_answered INTEGER DEFAULT 0,
            current_service_day INTEGER DEFAULT 0,
            last_activity_date TEXT, -- YYYY-MM-DD
            last_question_provided_date TEXT, -- YYYY-MM-DD
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id)
        );
    """)

    conn.commit()
    conn.close()
    print("데이터베이스 테이블이 성공적으로 생성되거나 이미 존재합니다.")


# --- 데이터 삽입/조회 예시 (CRUD 함수) ---

# 사용자 추가
def add_user(name, birth_date, diagnosis_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO USERS (name, birth_date, diagnosis_date)
        VALUES (?, ?, ?);
    """, (name, birth_date, diagnosis_date))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"사용자 '{name}' (ID: {user_id}) 추가됨.")
    return user_id

# 질문 추가
def add_question(question_text, question_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO QUESTIONS (question_text, question_type)
        VALUES (?, ?);
    """, (question_text, question_type))
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"질문 (ID: {question_id}, 유형: {question_type}) 추가됨.")
    return question_id

# 사용자 답변 추가
def add_user_answer(user_id, question_id, answer_text, answer_date, is_initial_answer):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO USER_ANSWERS (user_id, question_id, answer_text, answer_date, is_initial_answer)
        VALUES (?, ?, ?, ?, ?);
    """, (user_id, question_id, answer_text, answer_date, is_initial_answer))
    answer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"사용자 {user_id}의 답변 (ID: {answer_id}) 추가됨.")
    return answer_id

# 기억 확인 결과 추가
def add_memory_check(user_id, question_id, original_answer_id, memory_status,
                     current_memory_text, similarity_score, extracted_keywords_status,
                     result, check_type, extracted_keywords, check_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    # extracted_keywords는 리스트가 들어올 수 있으므로 JSON 문자열로 변환
    if isinstance(extracted_keywords, list):
        extracted_keywords = json.dumps(extracted_keywords)
    cursor.execute("""
        INSERT INTO MEMORY_CHECKS (
            user_id, question_id, original_answer_id, memory_status,
            current_memory_text, similarity_score, extracted_keywords_status,
            result, check_type, extracted_keywords, check_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (user_id, question_id, original_answer_id, memory_status,
          current_memory_text, similarity_score, extracted_keywords_status,
          result, check_type, extracted_keywords, check_date))
    check_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"사용자 {user_id}의 기억 확인 (ID: {check_id}) 추가됨.")
    return check_id

# 생성된 이미지 정보 추가
def add_generated_image(memory_check_id, image_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO GENERATED_IMAGES (memory_check_id, image_url)
        VALUES (?, ?);
    """, (memory_check_id, image_url))
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"이미지 (ID: {image_id}) 추가됨.")
    return image_id

# 사용자 진행 상황 초기화 또는 업데이트
def create_or_update_user_progress(user_id, **kwargs):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 기존 진행 상황이 있는지 확인
    cursor.execute("SELECT * FROM USER_PROGRESS WHERE user_id = ?", (user_id,))
    progress = cursor.fetchone()

    if progress:
        # 기존 진행 상황이 있다면 업데이트
        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            update_fields.append(f"{key} = ?")
            update_values.append(value)
        update_values.append(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) # updated_at
        update_values.append(user_id)
        
        cursor.execute(f"""
            UPDATE USER_PROGRESS
            SET {', '.join(update_fields)}, updated_at = ?
            WHERE user_id = ?;
        """, tuple(update_values))
        print(f"사용자 {user_id}의 진행 상황 업데이트됨.")
    else:
        # 없다면 새로 생성
        # 기본값 설정 및 전달받은 kwargs 병합
        defaults = {
            'questions_answered_today': 0,
            'total_initial_memory_questions_answered': 0,
            'total_revisit_questions_answered': 0,
            'total_new_general_questions_answered': 0,
            'current_service_day': 0,
            'last_activity_date': None,
            'last_question_provided_date': None,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        defaults.update(kwargs) # kwargs가 defaults를 덮어씀

        fields = ['user_id'] + list(defaults.keys())
        values = [user_id] + list(defaults.values())

        placeholders = ', '.join(['?' for _ in fields])
        field_names = ', '.join(fields)

        cursor.execute(f"""
            INSERT INTO USER_PROGRESS ({field_names})
            VALUES ({placeholders});
        """, tuple(values))
        print(f"사용자 {user_id}의 진행 상황 초기화됨.")

    progress_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return progress_id

# 특정 사용자 정보 가져오기
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# 특정 질문 가져오기
def get_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM QUESTIONS WHERE question_id = ?", (question_id,))
    question = cursor.fetchone()
    conn.close()
    return question

# 특정 사용자의 모든 답변 가져오기
def get_user_answers(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USER_ANSWERS WHERE user_id = ?", (user_id,))
    answers = cursor.fetchall()
    conn.close()
    return answers

# 특정 사용자의 진행 상황 가져오기
def get_user_progress(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USER_PROGRESS WHERE user_id = ?", (user_id,))
    progress = cursor.fetchone()
    conn.close()
    return progress

# 기타 필요한 조회 함수들을 추가할 수 있습니다.
# 예: 특정 유형의 질문 목록 가져오기, 특정 사용자의 기억 확인 기록 가져오기 등

if __name__ == "__main__":
    # 이 파일을 직접 실행하면 데이터베이스를 생성하고 샘플 데이터를 넣어봅니다.
    create_tables()