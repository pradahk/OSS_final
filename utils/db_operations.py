import database
from datetime import date
from typing import List, Tuple, Optional, Set
import json

class DBOperations:
    """데이터베이스 작업을 처리하는 클래스"""
    
    @staticmethod
    def initialize_questions(questions: List[str]) -> None:
        """CSV에서 로드한 질문들을 DB에 초기화"""
        database.create_tables()
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM QUESTIONS")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            for question_text in questions:
                database.add_question(question_text, 'csv_import')
    
    @staticmethod
    def get_or_create_user(user_info: dict) -> Optional[int]:
        """사용자 정보를 기반으로 DB에서 사용자 가져오거나 생성"""
        name = user_info.get('이름', '미상')
        birth_date = user_info.get('생년월일', date.today()).strftime('%Y-%m-%d')
        diagnosis_date = user_info.get('진단일', date.today()).strftime('%Y-%m-%d')
        
        # 동일한 사용자 확인
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM USERS 
            WHERE name = ? AND birth_date = ?
        """, (name, birth_date))
        existing_user = cursor.fetchone()
        conn.close()
        
        if existing_user:
            return existing_user[0]
        else:
            # 새 사용자 생성
            user_id = database.add_user(name, birth_date, diagnosis_date)
            database.create_or_update_user_progress(
                user_id,
                last_activity_date=date.today().strftime('%Y-%m-%d'),
                current_service_day=1
            )
            return user_id
    
    @staticmethod
    def get_today_activity_count(user_id: int) -> Tuple[int, int]:
        """오늘의 활동 현황 확인"""
        today_str = date.today().strftime('%Y-%m-%d')
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # 오늘 답변한 새로운 질문 수
        cursor.execute("""
            SELECT COUNT(*) FROM USER_ANSWERS 
            WHERE user_id = ? AND answer_date = ? AND is_initial_answer = 1
        """, (user_id, today_str))
        new_answers_today = cursor.fetchone()[0]
        
        # 오늘 수행한 기억 점검 수
        cursor.execute("""
            SELECT COUNT(*) FROM MEMORY_CHECKS 
            WHERE user_id = ? AND check_date = ?
        """, (user_id, today_str))
        memory_checks_today = cursor.fetchone()[0]
        
        conn.close()
        return new_answers_today, memory_checks_today
    
    @staticmethod
    def get_completed_questions(user_id: int) -> Set[int]:
        """기억 확인이 완료된 질문들 가져오기"""
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT question_id FROM MEMORY_CHECKS 
            WHERE user_id = ? AND result IN ('failed_verification', 'complete_failure')
        """, (user_id,))
        completed = cursor.fetchall()
        conn.close()
        return set(row[0] for row in completed)
    
    @staticmethod
    def get_reusable_questions(user_id: int, similarity_threshold: float = 0.7) -> Set[int]:
        """재사용 가능한 질문들 가져오기"""
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT question_id FROM MEMORY_CHECKS 
            WHERE user_id = ? AND result = 'passed' AND similarity_score >= ?
        """, (user_id, similarity_threshold))
        reusable = cursor.fetchall()
        conn.close()
        return set(row[0] for row in reusable)