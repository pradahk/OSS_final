import sqlite3
import datetime
import json

DATABASE_NAME = 'memory_app.db'  # SQLite 데이터베이스 파일 이름

def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # 컬럼 이름으로 데이터 접근 가능하도록 설정
    return conn

def create_tables():
    """데이터베이스 테이블들을 생성합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- 기존 테이블 수정 및 유지 ---

    # USERS 테이블 (변경 없음)
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

    # QUESTIONS 테이블 (상태(status) 컬럼 추가)
    # 'active': 재질문 대상, 'archived': 재질문에서 제외(폐기)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS QUESTIONS (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL, -- 'initial_memory', 'revisit_memory', 'new_general'
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # USER_ANSWERS 테이블 (extracted_keywords 컬럼 추가)
    # 사용자의 모든 답변(최초, 재시도)을 저장합니다. 키워드는 최초 답변에만 저장됩니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USER_ANSWERS (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_text TEXT NOT NULL,
            answer_date TEXT NOT NULL, -- YYYY-MM-DD
            is_initial_answer BOOLEAN NOT NULL, -- 1이면 최초 답변, 0이면 재질문 답변
            extracted_keywords TEXT, -- JSON array string, 최초 답변에만 저장
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id),
            FOREIGN KEY (question_id) REFERENCES QUESTIONS(question_id)
        );
    """)

    # USER_PROGRESS 테이블 (변경 없음)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS USER_PROGRESS (
            progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
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

    # --- 재설계된 테이블 ---

    # MEMORY_CHECKS 테이블 (구조 재설계)
    # 각 재질문 '시도'를 기록하여 복잡한 시나리오를 추적합니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS MEMORY_CHECKS (
            check_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            original_answer_id INTEGER NOT NULL, -- 최초 답변의 ID
            recall_answer_id INTEGER, -- 사용자가 회상하여 답변한 내용의 ID (USER_ANSWERS 테이블 참조)
            check_step TEXT NOT NULL, -- 'initial_recall' (첫 시도), 'post_hint_recall' (힌트 후 시도)
            user_choice TEXT, -- 사용자의 첫 선택: 'remembers' 또는 'forgets'
            keyword_match_count INTEGER, -- 회상 답변과 키워드의 일치 개수
            check_result TEXT NOT NULL, -- 'pass', 'fail'
            hint_provided BOOLEAN NOT NULL DEFAULT 0, -- 이미지 힌트 제공 여부
            check_date TEXT NOT NULL, -- YYYY-MM-DD
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id),
            FOREIGN KEY (question_id) REFERENCES QUESTIONS(question_id),
            FOREIGN KEY (original_answer_id) REFERENCES USER_ANSWERS(answer_id),
            FOREIGN KEY (recall_answer_id) REFERENCES USER_ANSWERS(answer_id)
        );
    """)
    
    # GENERATED_IMAGES 테이블 (변경 없음, memory_check_id와의 관계 유지)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GENERATED_IMAGES (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_check_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (memory_check_id) REFERENCES MEMORY_CHECKS(check_id)
        );
    """)

    conn.commit()
    conn.close()
    print("데이터베이스 테이블이 성공적으로 생성되거나 이미 존재합니다.")


# --- 데이터 삽입/조회/수정 함수 (스키마 변경에 따라 수정됨) ---

def add_user(name, birth_date, diagnosis_date):
    """사용자 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO USERS (name, birth_date, diagnosis_date) VALUES (?, ?, ?)",
                   (name, birth_date, diagnosis_date))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def add_question(question_text, question_type):
    """질문 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO QUESTIONS (question_text, question_type) VALUES (?, ?)",
                   (question_text, question_type))
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id
    
def add_user_answer(user_id, question_id, answer_text, answer_date, is_initial_answer, extracted_keywords=None):
    """사용자 답변 추가. 최초 답변일 경우 키워드도 함께 저장합니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    keywords_json = None
    if is_initial_answer and extracted_keywords:
        # 한글 깨짐 방지를 위해 ensure_ascii=False 사용
        keywords_json = json.dumps(extracted_keywords, ensure_ascii=False)

    cursor.execute("""
        INSERT INTO USER_ANSWERS (user_id, question_id, answer_text, answer_date, is_initial_answer, extracted_keywords)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (user_id, question_id, answer_text, answer_date, is_initial_answer, keywords_json))
    answer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return answer_id

def add_memory_check(user_id, question_id, original_answer_id, check_date, check_step, check_result, 
                     recall_answer_id=None, user_choice=None, keyword_match_count=None, hint_provided=False):
    """기억 확인 결과 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO MEMORY_CHECKS (
            user_id, question_id, original_answer_id, check_date, check_step, check_result,
            recall_answer_id, user_choice, keyword_match_count, hint_provided
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (user_id, question_id, original_answer_id, check_date, check_step, check_result,
          recall_answer_id, user_choice, keyword_match_count, hint_provided))
    check_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return check_id

def add_generated_image(memory_check_id, image_url):
    """생성된 이미지 정보 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO GENERATED_IMAGES (memory_check_id, image_url) VALUES (?, ?)",
                   (memory_check_id, image_url))
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return image_id

def update_question_status(question_id, status):
    """질문의 상태를 변경합니다 ('active' 또는 'archived')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE QUESTIONS SET status = ? WHERE question_id = ?", (status, question_id))
    conn.commit()
    conn.close()
    print(f"질문 ID {question_id}의 상태가 '{status}'로 변경되었습니다.")

# --- 데이터 조회 함수 ---

def get_user(user_id):
    """특정 사용자 정보 가져오기"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM USERS WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def get_initial_answer_with_keywords(user_id, question_id):
    """특정 질문에 대한 사용자의 최초 답변과 키워드를 가져옵니다."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT answer_id, answer_text, extracted_keywords 
        FROM USER_ANSWERS 
        WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
    """, (user_id, question_id))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        keywords = json.loads(result['extracted_keywords']) if result['extracted_keywords'] else []
        return {
            'answer_id': result['answer_id'],
            'answer_text': result['answer_text'],
            'keywords': keywords
        }
    return None

def get_questions_to_revisit(user_id):
    """사용자에게 재방문할 질문 목록을 오래된 순으로 가져옵니다."""
    conn = get_db_connection()
    # 사용자가 답변했고, 상태가 'active'인 질문만 가져옵니다.
    # USER_ANSWERS와 조인하여 답변한 질문만 대상으로 하고, 생성일 순으로 정렬합니다.
    questions = conn.execute("""
        SELECT Q.question_id, Q.question_text
        FROM QUESTIONS Q
        JOIN USER_ANSWERS UA ON Q.question_id = UA.question_id
        WHERE UA.user_id = ? AND UA.is_initial_answer = 1 AND Q.status = 'active'
        ORDER BY Q.created_at ASC
    """, (user_id,)).fetchall()
    conn.close()
    return questions

# create_or_update_user_progress 함수는 기존 구조를 유지해도 문제 없어 보입니다.
# get_user_progress, get_user_answers 등의 기본 조회 함수도 그대로 사용 가능합니다.
# (이하 기존 함수들은 생략)


if __name__ == "__main__":
    # 이 파일을 직접 실행하면 데이터베이스 테이블을 생성합니다.
    create_tables()

    # --- 아래는 수정된 스키마에 따른 예시 데이터 삽입 (테스트용) ---
    print("\n--- 테스트 데이터 삽입 예시 ---")
    try:
        # 1. 사용자 추가
        user_id = add_user("김철수", "1950-05-10", "2024-01-15")
        print(f"사용자 추가 완료 (ID: {user_id})")

        # 2. 질문 추가
        q_id = add_question("가장 기억에 남는 여행은 어디였나요?", "initial_memory")
        print(f"질문 추가 완료 (ID: {q_id})")
        
        # 3. 최초 답변 및 키워드 저장
        today = datetime.date.today().strftime('%Y-%m-%d')
        keywords = ["제주도", "가족", "해변", "유채꽃", "흑돼지", "행복"]
        initial_answer_id = add_user_answer(user_id, q_id, "가족들과 갔던 제주도 여행이 가장 기억에 남아요. 해변에서 놀고 유채꽃도 보고 흑돼지도 먹어서 행복했어요.", today, is_initial_answer=True, extracted_keywords=keywords)
        print(f"최초 답변 추가 완료 (ID: {initial_answer_id})")

        # 4. 재질문 시나리오 예시 ('기억한다'고 답변 후 통과)
        recall_answer_text = "제주도에 가족들이랑 갔던거요. 흑돼지 맛있었음."
        # 재질문 답변 저장
        recall_answer_id = add_user_answer(user_id, q_id, recall_answer_text, today, is_initial_answer=False)
        # 기억 확인 결과 저장
        add_memory_check(
            user_id=user_id,
            question_id=q_id,
            original_answer_id=initial_answer_id,
            check_date=today,
            check_step='initial_recall',
            user_choice='remembers',
            keyword_match_count=3, # "제주도", "가족", "흑돼지"
            check_result='pass',
            recall_answer_id=recall_answer_id
        )
        print("재질문 시나리오(pass) 테스트 완료")
        
        # 5. 질문 폐기 시나리오 예시
        update_question_status(q_id, 'archived')
        print("질문 폐기 테스트 완료")

    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")