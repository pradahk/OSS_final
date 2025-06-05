import streamlit as st
from datetime import date, timedelta, datetime
import json
from difflib import SequenceMatcher
import database  # database.py import
import pandas as pd
import os

st.header("💬 기억 회상 및 점검 챗")

# CSV에서 질문 불러오기
def load_questions_from_csv(csv_path="questions.csv"):
    """CSV 파일에서 질문들을 읽어와서 리스트로 반환"""
    try:
        if not os.path.exists(csv_path):
            # CSV 파일이 없으면 빈 리스트 반환
            return []
        
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # 질문 컬럼 찾기
        question_column = None
        possible_columns = ['question', 'question_text', '질문', 'questions']
        
        for col in possible_columns:
            if col in df.columns:
                question_column = col
                break
        
        if question_column is None:
            return []
        
        # 질문 리스트 생성
        questions = []
        for question_text in df[question_column].dropna():
            question_text = str(question_text).strip()
            if question_text:
                questions.append(question_text)
        
        return questions
        
    except Exception:
        return []

QUESTIONS = load_questions_from_csv("questions.csv")

# DB 초기화 및 질문 데이터 삽입
def initialize_db():
    """DB 테이블 생성 및 CSV에서 질문 데이터 로드"""
    database.create_tables()
    
    # 이미 질문이 있는지 확인
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM QUESTIONS")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # 질문이 없으면 CSV에서 로드한 질문들 삽입
        for question_text in QUESTIONS:
            database.add_question(question_text, 'csv_import')
        st.success(f"{len(QUESTIONS)}개의 질문이 CSV에서 DB에 추가되었습니다.")

    conn.close()

# 사용자 생성 또는 가져오기
def get_or_create_user():
    """세션의 사용자 정보를 기반으로 DB에서 사용자 가져오거나 생성"""
    if 'user_id' in st.session_state:
        return st.session_state.user_id
    
    if 'user_info' in st.session_state:
        user_info = st.session_state.user_info
        name = user_info.get('이름', '미상')
        birth_date = user_info.get('생년월일', date.today()).strftime('%Y-%m-%d')
        diagnosis_date = user_info.get('진단일', date.today()).strftime('%Y-%m-%d')
        
        # 동일한 이름과 생년월일을 가진 사용자가 있는지 확인
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id FROM USERS 
            WHERE name = ? AND birth_date = ?
        """, (name, birth_date))
        existing_user = cursor.fetchone()
        conn.close()
        
        if existing_user:
            user_id = existing_user[0]
        else:
            # 새 사용자 생성
            user_id = database.add_user(name, birth_date, diagnosis_date)
            # 진행 상황 초기화
            database.create_or_update_user_progress(
                user_id,
                last_activity_date=date.today().strftime('%Y-%m-%d'),
                current_service_day=1
            )
        
        st.session_state.user_id = user_id
        return user_id
    
    return None

# DB에서 질문 가져오기
def get_questions_from_db():
    """DB에서 질문 목록 가져오기"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id, question_text FROM QUESTIONS ORDER BY question_id")
    questions = cursor.fetchall()
    conn.close()
    return questions

# 메인 애플리케이션에서 사용할 질문 가져오기 함수
def get_current_questions():
    """현재 사용할 질문들을 DB에서 가져오기"""
    questions_data = get_questions_from_db()
    # (question_id, question_text) 튜플에서 question_text만 추출
    questions = [q[1] for q in questions_data]
    return questions

# DB에서 사용자 답변 가져오기
def get_user_answers_from_db(user_id):
    """DB에서 사용자 답변 가져오기"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ua.question_id, ua.answer_text, ua.answer_date, q.question_text
        FROM USER_ANSWERS ua
        JOIN QUESTIONS q ON ua.question_id = q.question_id
        WHERE ua.user_id = ? AND ua.is_initial_answer = 1
        ORDER BY ua.answer_date
    """, (user_id,))
    answers = cursor.fetchall()
    conn.close()
    return answers

# 답변 저장
def save_answer_to_db(user_id, question_id, answer_text, answer_date, is_initial=True):
    """답변을 DB에 저장"""
    return database.add_user_answer(
        user_id, question_id, answer_text, 
        answer_date.strftime('%Y-%m-%d'), is_initial
    )

# 기억 확인 결과 저장
def save_memory_check_to_db(user_id, question_id, original_answer_id, memory_status, 
                           current_memory_text, similarity_score, result):
    """기억 확인 결과를 DB에 저장"""
    return database.add_memory_check(
        user_id=user_id,
        question_id=question_id,
        original_answer_id=original_answer_id,
        memory_status=memory_status,
        current_memory_text=current_memory_text,
        similarity_score=similarity_score,
        extracted_keywords_status='manual',
        result=result,
        check_type='manual_check',
        extracted_keywords=json.dumps([]),
        check_date=date.today().strftime('%Y-%m-%d')
    )

# 사용자 진행 상황 업데이트
def update_user_progress(user_id, **kwargs):
    """사용자 진행 상황 업데이트"""
    database.create_or_update_user_progress(user_id, **kwargs)

# 완료된 질문 확인
def get_completed_questions(user_id):
    """기억 확인이 완료된 질문들 가져오기"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT question_id FROM MEMORY_CHECKS 
        WHERE user_id = ? AND result IN ('passed', 'failed')
    """, (user_id,))
    completed = cursor.fetchall()
    conn.close()
    return set(row[0] for row in completed)

# 재사용 가능한 질문 확인
def get_reusable_questions(user_id):
    """재사용 가능한 질문들 가져오기 (기억을 잘 유지하고 있는 질문들)"""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT question_id FROM MEMORY_CHECKS 
        WHERE user_id = ? AND result = 'passed' AND similarity_score >= 0.7
    """, (user_id,))
    reusable = cursor.fetchall()
    conn.close()
    return set(row[0] for row in reusable)

# 세션 상태 초기화
def init_session_state():
    if 'mode' not in st.session_state:
        st.session_state.mode = 'initial_phase'
    
    if 'awaiting_memory_response' not in st.session_state:
        st.session_state.awaiting_memory_response = False
    
    if 'current_memory_question' not in st.session_state:
        st.session_state.current_memory_question = None

    if 'image_generated' not in st.session_state:
        st.session_state.image_generated = False
    
    if 'awaiting_image_response' not in st.session_state:
        st.session_state.awaiting_image_response = False
    
    if 'show_result' not in st.session_state:
        st.session_state.show_result = False
    
    if 'result_message' not in st.session_state:
        st.session_state.result_message = ""
    
    if 'result_type' not in st.session_state:
        st.session_state.result_type = ""

# 텍스트 유사도 계산 함수
def calculate_similarity(text1, text2):
    """두 텍스트의 유사도를 0-1 사이의 값으로 반환"""
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()

# 진단일로부터 경과한 일수 계산
def get_days_since_diagnosis():
    """진단일로부터 경과한 일수 계산"""
    if 'user_info' in st.session_state and '진단일' in st.session_state.user_info:
        diagnosis_date = st.session_state.user_info['진단일']
        return (date.today() - diagnosis_date).days
    return 0

# 진단일 기준으로 현재 모드 결정
def determine_mode_by_diagnosis():
    """진단일 기준으로 현재 모드 결정"""
    days_passed = get_days_since_diagnosis()
    if days_passed < 30:
        return 'initial_phase'
    else:
        return 'memory_check_phase'

# 오늘의 활동 현황 확인
def get_today_activity_count(user_id):
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

# 초기 회상 단계
def initial_phase():
    st.info("🔄 **초기 회상 단계**: 하루에 2개의 질문을 드립니다.")
    
    user_id = get_or_create_user()
    if not user_id:
        st.error("사용자 정보를 불러올 수 없습니다.")
        return
    
    # 오늘 활동 현황 확인
    new_answers_today, memory_checks_today = get_today_activity_count(user_id)
    
    # 오늘 2개 질문을 모두 완료했는지 확인
    if new_answers_today >= 2:
        st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # DB에서 질문 가져오기
    questions = get_questions_from_db()
    user_answers = get_user_answers_from_db(user_id)
    answered_question_ids = set(answer[0] for answer in user_answers)
    
    # 답변하지 않은 질문 찾기
    unanswered_questions = [q for q in questions if q[0] not in answered_question_ids]
    
    if not unanswered_questions:
        st.success("🎉 모든 초기 회상 질문을 완료하셨습니다!")
        if st.button("기억 유무 점검 단계로 이동"):
            st.session_state.mode = 'memory_check_phase'
            st.rerun()
        return
    
    # 첫 번째 미답변 질문 표시
    current_question = unanswered_questions[0]
    question_id, question_text = current_question
    
    st.subheader(f"질문 {question_id}")
    st.write(f"**{question_text}**")
    
    # 답변 입력
    answer = st.text_area("답변을 입력해주세요:", key=f"initial_answer_{question_id}")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("답변 제출", type="primary"):
            if answer.strip():
                # 답변을 DB에 저장
                save_answer_to_db(user_id, question_id, answer.strip(), date.today())
                
                # 사용자 진행 상황 업데이트
                update_user_progress(
                    user_id,
                    total_initial_memory_questions_answered=len(answered_question_ids) + 1,
                    last_activity_date=date.today().strftime('%Y-%m-%d')
                )
                
                st.success("✅ 답변이 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 답변을 입력해주세요.")

# 기억 유무 점검 단계
def memory_check_phase():
    st.info("🧠 **기억 유무 점검 단계**: 하루에 새로운 질문 1개와 기억 점검 1개를 진행합니다.")
    
    user_id = get_or_create_user()
    if not user_id:
        st.error("사용자 정보를 불러올 수 없습니다.")
        return
    
    # 오늘 활동 현황 확인
    new_answers_today, memory_checks_today = get_today_activity_count(user_id)
    
    # 오늘의 할당량 확인
    if new_answers_today >= 1 and memory_checks_today >= 1:
        st.success("✅ 오늘의 모든 활동을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # DB에서 데이터 가져오기
    questions = get_questions_from_db()
    user_answers = get_user_answers_from_db(user_id)
    completed_questions = get_completed_questions(user_id)
    reusable_questions = get_reusable_questions(user_id)
    
    answered_question_ids = set(answer[0] for answer in user_answers)
    
    # 먼저 새로운 질문을 처리
    if new_answers_today < 1:
        unanswered_questions = [q for q in questions if q[0] not in answered_question_ids]
        
        if unanswered_questions:
            st.subheader("📝 오늘의 새로운 질문")
            current_question = unanswered_questions[0]
            question_id, question_text = current_question
            
            st.write(f"**{question_text}**")
            
            answer = st.text_area("답변을 입력해주세요:", key=f"new_answer_{question_id}")
            
            if st.button("답변 제출", type="primary", key="new_submit"):
                if answer.strip():
                    # 답변을 DB에 저장
                    save_answer_to_db(user_id, question_id, answer.strip(), date.today())
                    
                    st.success("✅ 답변이 저장되었습니다!")
                    st.rerun()
                else:
                    st.warning("⚠️ 답변을 입력해주세요.")
            return
    
    # 새로운 질문을 완료했거나 이미 완료한 경우, 기억 점검 진행
    elif memory_checks_today < 1:
        st.subheader("🧠 오늘의 기억 점검")
        
        # 결과 메시지 표시 (있는 경우)
        if st.session_state.show_result:
            if st.session_state.result_type == 'success':
                st.success(st.session_state.result_message)
            elif st.session_state.result_type == 'warning':
                st.warning(st.session_state.result_message)
            elif st.session_state.result_type == 'info':
                st.info(st.session_state.result_message)
            
            # 결과 표시 후 상태 리셋
            st.session_state.show_result = False
            
            # 다음 질문으로 버튼
            if st.button("완료", type="primary"):
                st.session_state.result_message = ""
                st.session_state.result_type = ""
                st.rerun()
            return
        
        # 기억 점검 로직 실행
        handle_memory_check(user_id, user_answers, completed_questions, reusable_questions)

def handle_memory_check(user_id, user_answers, completed_questions, reusable_questions):
    """기억 점검 처리"""
    
    # 이미지 응답을 기다리는 상태인 경우
    if st.session_state.awaiting_image_response:
        handle_image_response(user_id, user_answers)
        return
    
    # 기억 응답을 기다리는 상태인 경우
    if st.session_state.awaiting_memory_response and st.session_state.current_memory_question is not None:
        handle_memory_response(user_id, user_answers)
        return
    
    # 점검 가능한 질문들 찾기
    available_questions = []
    for answer in user_answers:
        question_id = answer[0]
        if question_id not in completed_questions or question_id in reusable_questions:
            available_questions.append(answer)
    
    if not available_questions:
        st.success("🎉 모든 기억 점검을 완료하셨습니다!")
        return
    
    # 재사용 가능한 질문 우선 선택
    reusable_available = [ans for ans in available_questions if ans[0] in reusable_questions]
    new_questions = [ans for ans in available_questions if ans[0] not in completed_questions and ans[0] not in reusable_questions]
    
    # 재사용 가능한 질문이 있으면 그 중에서 랜덤 선택
    if reusable_available:
        import random
        current_answer = random.choice(reusable_available)
    elif new_questions:
        current_answer = new_questions[0]
    else:
        st.success("🎉 모든 기억 점검을 완료하셨습니다!")
        return
    
    question_id, answer_text, answer_date, question_text = current_answer
    st.session_state.current_memory_question = (question_id, answer_text, question_text)
    
    st.subheader("🧠 기억 확인")
    st.write(f"**{question_text}**")
    st.write("이 질문을 기억하시나요?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 기억해요", type="primary"):
            st.session_state.awaiting_memory_response = True
            st.rerun()
    
    with col2:
        if st.button("❌ 기억 안 나요"):
            st.session_state.image_generated = True
            st.session_state.awaiting_image_response = True
            st.rerun()

def handle_memory_response(user_id, user_answers):
    """기억 응답 처리"""
    question_id, original_answer, question_text = st.session_state.current_memory_question
    
    st.subheader("📝 기억 내용 확인")
    st.write(f"**{question_text}**")
    st.write("기억하고 계신 내용을 말씀해주세요:")
    
    current_memory = st.text_area("현재 기억하고 계신 내용:", key=f"memory_check_{question_id}")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("답변 제출", type="primary"):
            if current_memory.strip():
                # 유사도 계산
                similarity = calculate_similarity(original_answer, current_memory.strip())
                
                # 기억 확인 결과를 DB에 저장
                if similarity >= 0.7:
                    memory_status = 'remembered'
                    result = 'passed'
                    result_msg = f"**현재 답변**: {current_memory.strip()}\n\n"
                    result_msg += f"**원본 답변**: {original_answer}\n\n"
                    result_msg += "✅ 기억이 잘 보존되어 있습니다!\n"
                    result_msg += "💡 이 질문은 나중에 다시 사용될 수 있습니다."
                    st.session_state.result_type = 'success'
                else:
                    # 기억이 틀린 경우 - 이미지 생성 단계로 이동
                    st.warning("⚠️ 기억에 차이가 있습니다. 이미지를 생성하여 도움을 드리겠습니다.")
                    st.session_state.image_generated = True
                    st.session_state.awaiting_image_response = True
                    st.session_state.awaiting_memory_response = False
                    st.rerun()
                    return
                
                # 원본 답변 ID 찾기
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT answer_id FROM USER_ANSWERS 
                    WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
                """, (user_id, question_id))
                original_answer_row = cursor.fetchone()
                conn.close()
                
                if original_answer_row:
                    original_answer_id = original_answer_row[0]
                    
                    # 기억 확인 결과 저장
                    save_memory_check_to_db(
                        user_id, question_id, original_answer_id, 
                        memory_status, current_memory.strip(), similarity, result
                    )
                
                st.session_state.result_message = result_msg
                st.session_state.show_result = True
                
                # 상태 리셋
                st.session_state.awaiting_memory_response = False
                st.session_state.current_memory_question = None
                
                st.rerun()
            else:
                st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
    
    with col2:
        if st.button("취소"):
            st.session_state.awaiting_memory_response = False
            st.session_state.current_memory_question = None
            st.rerun()

def handle_image_response(user_id, user_answers):
    """이미지 응답 처리"""
    question_id, original_answer, question_text = st.session_state.current_memory_question
    
    st.subheader("🖼️ 생성된 이미지")
    st.write(f"**{question_text}**")
    st.image("https://via.placeholder.com/400x300.png?text=Memory+Image", 
            caption="생성된 기억 이미지 (GPT-4o API 연동 예정)")
    
    st.write("이미지를 보시고 기억이 나시나요?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 기억해요", type="primary", key="image_remember"):
            # 이미지 기억 입력 상태로 전환
            st.session_state.awaiting_image_memory_input = True
            st.rerun()
        
        # 이미지를 보고 기억한다고 한 경우의 입력 처리
        if st.session_state.get('awaiting_image_memory_input', False):
            st.write("기억하고 계신 내용을 말씀해주세요:")
            
            current_memory = st.text_area("현재 기억하고 계신 내용:", key=f"image_memory_{question_id}")
            
            col1_input, col2_input = st.columns(2)
            with col1_input:
                if st.button("답변 제출", key="image_memory_submit"):
                    if current_memory.strip():
                        # 유사도 계산
                        similarity = calculate_similarity(original_answer, current_memory.strip())
                        
                        # 결과 메시지 설정
                        result_msg = f"**현재 답변**: {current_memory.strip()}\n\n"
                        result_msg += f"**원본 답변**: {original_answer}\n\n"
                        
                        # 원본 답변 ID 찾기
                        conn = database.get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT answer_id FROM USER_ANSWERS 
                            WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
                        """, (user_id, question_id))
                        original_answer_row = cursor.fetchone()
                        conn.close()
                        
                        if original_answer_row:
                            original_answer_id = original_answer_row[0]
                            
                            if similarity >= 0.7:
                                result_msg += "✅ 이미지를 보고 기억을 잘 떠올리셨습니다!\n"
                                result_msg += "💡 이 질문은 나중에 다시 사용될 수 있습니다."
                                st.session_state.result_type = 'success'
                                memory_status = 'remembered'
                                result = 'passed'
                            else:
                                result_msg += "⚠️ 기억에 차이가 있습니다.\n"
                                result_msg += "이 질문은 완료 처리됩니다."
                                st.session_state.result_type = 'warning'
                                memory_status = 'forgotten'
                                result = 'failed'
                            
                            # 기억 확인 결과 저장
                            save_memory_check_to_db(
                                user_id, question_id, original_answer_id, 
                                memory_status, current_memory.strip(), similarity, result
                            )
                        
                        st.session_state.result_message = result_msg
                        st.session_state.show_result = True
                        
                        # 상태 완전 리셋
                        st.session_state.awaiting_image_response = False
                        st.session_state.awaiting_image_memory_input = False
                        st.session_state.current_memory_question = None
                        st.session_state.image_generated = False
                        
                        st.rerun()
                    else:
                        st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
            
            with col2_input:
                if st.button("취소", key="image_memory_cancel"):
                    st.session_state.awaiting_image_memory_input = False
                    st.rerun()
    
    with col2:
        if st.button("❌ 기억 안 나요", key="image_no_remember"):
            # 결과 메시지 설정
            result_msg = "💭 기억이 나지 않으시는군요.\n\n"
            result_msg += f"**원본 답변**: {original_answer}\n\n"
            result_msg += "이 질문은 완료되었습니다."
            
            # 원본 답변 ID 찾기
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT answer_id FROM USER_ANSWERS 
                WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
            """, (user_id, question_id))
            original_answer_row = cursor.fetchone()
            conn.close()
            
            if original_answer_row:
                original_answer_id = original_answer_row[0]
                
                # 기억 확인 결과 저장
                save_memory_check_to_db(
                    user_id, question_id, original_answer_id, 
                    'forgotten', '', 0.0, 'failed'
                )
            
            st.session_state.result_message = result_msg
            st.session_state.result_type = 'info'
            st.session_state.show_result = True
            
            # 상태 완전 리셋
            st.session_state.awaiting_image_response = False
            st.session_state.current_memory_question = None
            st.session_state.image_generated = False
            
            st.rerun()

# 통계 및 진행 상황 표시
def show_user_stats():
    """사용자 통계 및 진행 상황 표시"""
    if 'user_id' not in st.session_state:
        return
    
    user_id = st.session_state.user_id
    user_progress = database.get_user_progress(user_id)
    
    if user_progress:
        st.sidebar.header("📊 진행 상황")
        
        # 전체 통계
        st.sidebar.metric("초기 회상 완료", user_progress['total_initial_memory_questions_answered'])
        st.sidebar.metric("기억 점검 완료", user_progress['total_revisit_questions_answered'])
        st.sidebar.metric("서비스 이용일", user_progress['current_service_day'])
        
        # 오늘의 활동
        new_answers_today, memory_checks_today = get_today_activity_count(user_id)
        
        st.sidebar.subheader("📅 오늘의 활동")
        
        current_mode = determine_mode_by_diagnosis()
        if current_mode == 'initial_phase':
            st.sidebar.write(f"새로운 질문: {new_answers_today}/2")
            progress_value = min(new_answers_today / 2.0, 1.0)
            st.sidebar.progress(progress_value)
        else:
            st.sidebar.write(f"새로운 질문: {new_answers_today}/1")
            st.sidebar.write(f"기억 점검: {memory_checks_today}/1")
            
            total_progress = (new_answers_today + memory_checks_today) / 2.0
            st.sidebar.progress(min(total_progress, 1.0))

# 사용자 정보 입력
def get_user_info():
    """사용자 기본 정보 입력"""
    st.subheader("👤 사용자 정보 입력")
    
    with st.form("user_info_form"):
        name = st.text_input("이름을 입력해주세요:")
        birth_date = st.date_input("생년월일을 선택해주세요:", 
                                  value=date(1950, 1, 1),
                                  min_value=date(1930, 1, 1),
                                  max_value=date.today())
        diagnosis_date = st.date_input("치매 진단일을 선택해주세요:",
                                     value=date.today() - timedelta(days=30),
                                     min_value=date(2020, 1, 1),
                                     max_value=date.today())
        
        submitted = st.form_submit_button("시작하기", type="primary")
        
        if submitted:
            if name.strip():
                st.session_state.user_info = {
                    '이름': name.strip(),
                    '생년월일': birth_date,
                    '진단일': diagnosis_date
                }
                st.success(f"안녕하세요, {name}님! 기억 회상 서비스를 시작합니다.")
                st.rerun()
            else:
                st.warning("⚠️ 이름을 입력해주세요.")

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    # DB 초기화
    initialize_db()
    
    # 세션 상태 초기화
    init_session_state()
    
    # 사용자 정보가 없으면 입력 받기
    if 'user_info' not in st.session_state:
        get_user_info()
        return
    
    # 사용자 통계 표시
    show_user_stats()
    
    # 진단일 기준으로 모드 결정
    diagnosis_mode = determine_mode_by_diagnosis()
    
    # 현재 모드 표시
    user_name = st.session_state.user_info.get('이름', '사용자')
    days_since_diagnosis = get_days_since_diagnosis()
    
    st.write(f"안녕하세요, **{user_name}**님! (진단 후 {days_since_diagnosis}일째)")
    
    # 모드 선택 탭
    if diagnosis_mode == 'initial_phase':
        if st.session_state.mode != 'initial_phase':
            st.session_state.mode = 'initial_phase'
        initial_phase()
    else:
        # 30일 이후에는 모드 선택 가능
        tab1, tab2 = st.tabs(["🧠 기억 점검", "📝 초기 회상 추가"])
        
        with tab1:
            if st.session_state.mode != 'memory_check_phase':
                st.session_state.mode = 'memory_check_phase'
            memory_check_phase()
        
        with tab2:
            if st.session_state.mode != 'initial_phase':
                st.session_state.mode = 'initial_phase'
            initial_phase()
    
    # 관리자 기능 (개발용)
    with st.expander("🔧 관리자 기능 (개발용)"):
        if st.button("세션 상태 초기화"):
            for key in list(st.session_state.keys()):
                if key not in ['user_info', 'user_id']:
                    del st.session_state[key]
            st.success("세션 상태가 초기화되었습니다.")
            st.rerun()
        
        if st.button("완전 초기화 (사용자 정보 포함)"):
            st.session_state.clear()
            st.success("모든 세션 상태가 초기화되었습니다.")
            st.rerun()
        
        # DB 상태 확인
        if 'user_id' in st.session_state:
            user_id = st.session_state.user_id
            st.write(f"**현재 사용자 ID**: {user_id}")
            
            # 사용자 답변 현황
            user_answers = get_user_answers_from_db(user_id)
            st.write(f"**총 답변 수**: {len(user_answers)}개")
            
            # 기억 점검 현황
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM MEMORY_CHECKS WHERE user_id = ?", (user_id,))
            memory_check_count = cursor.fetchone()[0]
            st.write(f"**기억 점검 수**: {memory_check_count}개")
            
            cursor.execute("""
                SELECT result, COUNT(*) FROM MEMORY_CHECKS 
                WHERE user_id = ? GROUP BY result
            """, (user_id,))
            results = cursor.fetchall()
            for result, count in results:
                st.write(f"- {result}: {count}개")
            
            conn.close()

if __name__ == "__main__":
    main()