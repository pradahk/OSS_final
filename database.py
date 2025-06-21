import sqlite3
import datetime
import json
from typing import List, Dict, Optional, Tuple

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
            status TEXT NOT NULL DEFAULT 'active', -- 'active', 'archived'
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
            is_initial_answer BOOLEAN NOT NULL, -- 1이면 최초 답변, 0이면 재질문 답변
            extracted_keywords TEXT, -- JSON array string, 최초 답변에만 저장
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES USERS(user_id),
            FOREIGN KEY (question_id) REFERENCES QUESTIONS(question_id)
        );
    """)

    # USER_PROGRESS 테이블
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

    # MEMORY_CHECKS 테이블
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

    conn.commit()
    conn.close()
    print("데이터베이스 테이블이 성공적으로 생성되거나 이미 존재합니다.")


# --- 데이터 삽입/수정 함수 ---

def add_user(name: str, birth_date: str, diagnosis_date: str) -> int:
    """사용자 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO USERS (name, birth_date, diagnosis_date) VALUES (?, ?, ?)",
                   (name, birth_date, diagnosis_date))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def add_question(question_text: str, question_type: str) -> int:
    """질문 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO QUESTIONS (question_text, question_type) VALUES (?, ?)",
                   (question_text, question_type))
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id
    
def add_user_answer(user_id: int, question_id: int, answer_text: str, answer_date: str, 
                    is_initial_answer: bool, extracted_keywords: Optional[List[str]] = None) -> int:
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

def add_memory_check(user_id: int, question_id: int, original_answer_id: int, check_date: str, 
                     check_step: str, check_result: str, recall_answer_id: Optional[int] = None, 
                     user_choice: Optional[str] = None, keyword_match_count: Optional[int] = None, 
                     hint_provided: bool = False) -> int:
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

def add_generated_image(memory_check_id: int, image_url: str) -> int:
    """생성된 이미지 정보 추가"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO GENERATED_IMAGES (memory_check_id, image_url) VALUES (?, ?)",
                   (memory_check_id, image_url))
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return image_id

def update_question_status(question_id: int, status: str):
    """질문의 상태를 변경합니다 ('active' 또는 'archived')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE QUESTIONS SET status = ? WHERE question_id = ?", (status, question_id))
    conn.commit()
    conn.close()
    print(f"질문 ID {question_id}의 상태가 '{status}'로 변경되었습니다.")

def create_or_update_user_progress(user_id: int, **kwargs):
    """사용자 진행 상황 생성 또는 업데이트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 기존 진행 상황 확인
    cursor.execute("SELECT * FROM USER_PROGRESS WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        # 업데이트
        set_clauses = [f"{key} = ?" for key in kwargs]
        values = list(kwargs.values())
        if set_clauses:
            values.append(user_id)
            query = f"UPDATE USER_PROGRESS SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
            cursor.execute(query, values)
    else:
        # 새로 생성
        columns = ['user_id'] + list(kwargs.keys())
        placeholders = ['?'] * len(columns)
        values = [user_id] + list(kwargs.values())
        query = f"INSERT INTO USER_PROGRESS ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(query, values)
    
    conn.commit()
    conn.close()

# --- 데이터 조회 함수 ---

def get_user(user_id: int) -> Optional[sqlite3.Row]:
    """특정 사용자 정보 가져오기"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM USERS WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def get_user_progress(user_id: int) -> Optional[sqlite3.Row]:
    """사용자 진행 상황 가져오기"""
    conn = get_db_connection()
    progress = conn.execute("SELECT * FROM USER_PROGRESS WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return progress

def get_initial_answer_with_keywords(user_id: int, question_id: int) -> Optional[Dict]:
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

def get_questions_to_revisit(user_id: int) -> List[sqlite3.Row]:
    """사용자에게 재방문할 질문 목록을 오래된 순으로 가져옵니다."""
    conn = get_db_connection()
    query = """
        SELECT Q.question_id, Q.question_text
        FROM QUESTIONS Q
        JOIN USER_ANSWERS UA ON Q.question_id = UA.question_id
        WHERE UA.user_id = ? AND UA.is_initial_answer = 1 AND Q.status = 'active'
        ORDER BY Q.created_at ASC
    """
    questions = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return questions

def get_all_users() -> List[sqlite3.Row]:
    """모든 사용자 목록 가져오기"""
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM USERS ORDER BY created_at DESC").fetchall()
    conn.close()
    return users

def get_today_activity_count(user_id):
    """오늘의 활동 현황을 가져옵니다 (새로운 답변 수, 기억 점검 수)"""
    conn = get_db_connection()
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    # 오늘 새로운 답변 수
    new_answers_count = conn.execute("""
        SELECT COUNT(*) FROM USER_ANSWERS
        WHERE user_id = ? AND is_initial_answer = 1 AND answer_date = ?
    """, (user_id, today_str)).fetchone()[0]
    
    # 오늘 완료된 기억 점검 수 (pass 또는 fail 결과가 있는 것)
    memory_checks_count = conn.execute("""
        SELECT COUNT(DISTINCT question_id) FROM MEMORY_CHECKS
        WHERE user_id = ? AND check_date = ? AND check_result IN ('pass', 'fail')
    """, (user_id, today_str)).fetchone()[0]
    
    conn.close()
    return new_answers_count, memory_checks_count

if __name__ == "__main__":
    # 이 파일을 직접 실행하면 데이터베이스 테이블을 생성/확인합니다.
    create_tables()