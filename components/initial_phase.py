import streamlit as st
from datetime import date, datetime, timedelta
import database
from utils.constants import (
    MAX_DAILY_NEW_QUESTIONS_INITIAL, 
    MAX_DAILY_NEW_QUESTIONS_MAINTENANCE,
    INITIAL_PHASE_DAYS
)
from keyword_extractor import get_keyword_extractor

def is_in_initial_phase(user_id: int) -> bool:
    """
    사용자가 초기 회상 단계(진단일로부터 30일)에 있는지 확인
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        bool: 초기 단계이면 True, 유지 단계이면 False
    """
    # 사용자 정보 가져오기
    user = database.get_user(user_id)
    if not user:
        return False
    
    # 진단일 파싱
    diagnosis_date = datetime.strptime(user['diagnosis_date'], '%Y-%m-%d').date()
    
    # 현재 날짜와 진단일 차이 계산
    days_since_diagnosis = (date.today() - diagnosis_date).days
    
    # 30일 이내면 초기 단계
    return days_since_diagnosis < INITIAL_PHASE_DAYS

def get_current_phase_info(user_id: int) -> dict:
    """
    현재 단계 정보 반환
    
    Returns:
        dict: {
            'is_initial': bool,
            'days_since_diagnosis': int,
            'max_daily_questions': int,
            'phase_name': str
        }
    """
    user = database.get_user(user_id)
    if not user:
        return None
    
    diagnosis_date = datetime.strptime(user['diagnosis_date'], '%Y-%m-%d').date()
    days_since_diagnosis = (date.today() - diagnosis_date).days
    is_initial = days_since_diagnosis < INITIAL_PHASE_DAYS
    
    return {
        'is_initial': is_initial,
        'days_since_diagnosis': days_since_diagnosis,
        'max_daily_questions': MAX_DAILY_NEW_QUESTIONS_INITIAL if is_initial else MAX_DAILY_NEW_QUESTIONS_MAINTENANCE,
        'phase_name': '초기 회상 단계' if is_initial else '기억 유지 단계'
    }

def render_initial_phase(user_id: int, context: str = "main"):
    """
    초기 회상 단계 렌더링 (진단일 기준 30일 체크 포함)
    
    Args:
        user_id: 사용자 ID
        context: 렌더링 컨텍스트 (key 중복 방지용)
    """
    # 현재 단계 정보 확인
    phase_info = get_current_phase_info(user_id)
    if not phase_info:
        st.error("❌ 사용자 정보를 찾을 수 없습니다.")
        return
    
    # 단계별 다른 메시지 표시
    if context != "maintenance":
        if phase_info['is_initial']:
            remaining_days = INITIAL_PHASE_DAYS - phase_info['days_since_diagnosis']
            st.info(f"🔄 **{phase_info['phase_name']}** (진단일로부터 {phase_info['days_since_diagnosis']+1}일차)\n\n"
                    f"매일 {phase_info['max_daily_questions']}개의 새로운 기억 질문을 드립니다. ({remaining_days}일 남음)")
        else:
            st.info(f"🧠 **{phase_info['phase_name']}** (진단일로부터 {phase_info['days_since_diagnosis']+1}일차)\n\n"
                    f"매일 {phase_info['max_daily_questions']}개의 새로운 질문과 기억 점검을 진행합니다.")

    # --- 오늘 답변한 질문 수 확인 ---
    conn = database.get_db_connection()
    cursor = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) FROM USER_ANSWERS
        WHERE user_id = ? AND is_initial_answer = 1 AND answer_date = ?
    """, (user_id, today_str))
    new_answers_today = cursor.fetchone()[0]
    conn.close()

    # 할당량 체크
    # if new_answers_today >= phase_info['max_daily_questions']:
    #     if phase_info['is_initial']:
    #         st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
    #     else:
    #         st.success("✅ 오늘의 새로운 질문을 완료하셨습니다!")
    #     st.balloons()
    #     return

    # 할당량 체크 (초기 단계에서만 적용)
    # if phase_info['is_initial'] and new_answers_today >= phase_info['max_daily_questions']:
    #     st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
    #     st.balloons()
    #     return
    # elif not phase_info['is_initial'] and context == "maintenance" and new_answers_today >= phase_info['max_daily_questions']:
    #     st.success("✅ 오늘의 새로운 질문을 완료하셨습니다!")
    #     st.balloons()
    #     return

    if context == "maintenance" and new_answers_today >= phase_info['max_daily_questions']:
        if phase_info['is_initial']:
            st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        else:
            st.success("✅ 오늘의 새로운 질문을 완료하셨습니다!")
        st.balloons()
        return

    # --- 답변하지 않은 질문 가져오기 ---
    conn = database.get_db_connection()
    cursor = conn.cursor()
    # 전체 질문 목록 (active 상태만)
    cursor.execute("""
        SELECT question_id, question_text FROM QUESTIONS 
        WHERE status = 'active' 
        ORDER BY question_id
    """)
    all_questions = cursor.fetchall()
    
    # 사용자가 이미 답변한 초기 질문 ID 목록
    cursor.execute("""
        SELECT DISTINCT question_id FROM USER_ANSWERS 
        WHERE user_id = ? AND is_initial_answer = 1
    """, (user_id,))
    answered_ids = {row['question_id'] for row in cursor.fetchall()}
    conn.close()
    
    # 답변하지 않은 질문 필터링
    unanswered_questions = [q for q in all_questions if q['question_id'] not in answered_ids]

    if not unanswered_questions:
        if phase_info['is_initial']:
            st.success("🎉 모든 초기 질문을 완료하셨습니다! 내일부터는 기억 점검도 함께 진행됩니다.")
        else:
            st.info("📝 모든 질문에 답변하셨습니다. 기억 점검 단계로 이동해주세요.")
        return

    # --- 다음 질문 표시 및 답변 입력 ---
    question_id, question_text = unanswered_questions[0]
    
    remaining_questions = phase_info['max_daily_questions'] - new_answers_today
    st.subheader(f"💭 기억 떠올리기 (남은 질문: {remaining_questions}개)")
    st.markdown(f"#### Q. {question_text}")
    
    answer = st.text_area(
        "이 질문에 대한 당신의 기억을 자유롭게 적어주세요.",
        key=f"{context}_initial_answer_{question_id}",
        height=150,
        placeholder="어떤 기억이든 소중합니다. 편안하게 적어주세요..."
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("답변 제출하고 기억 저장하기", type="primary", key=f"{context}_submit_{question_id}"):
            if answer.strip():
                _save_answer_with_keywords(user_id, question_id, answer.strip(), today_str, phase_info)
            else:
                st.warning("⚠️ 답변을 입력해주세요. 어떤 기억이든 소중합니다.")
    
    with col2:
        if st.button("건너뛰기", key=f"{context}_skip_{question_id}"):
            st.info("💡 건너뛴 질문은 나중에 다시 나타날 수 있습니다.")

def _save_answer_with_keywords(user_id: int, question_id: int, answer_text: str, today_str: str, phase_info: dict):
    """답변과 키워드를 저장하고 진행 상황 업데이트"""
    with st.spinner("답변을 분석하여 당신의 기억을 저장하고 있습니다... 잠시만 기다려주세요."):
        try:
            # 1. 키워드 추출
            extractor = get_keyword_extractor()
            if extractor:
                extracted_keywords = extractor.extract_keywords(answer_text)
                if extracted_keywords:
                    st.info(f"🔍 추출된 키워드: {', '.join(extracted_keywords)}")
            else:
                st.warning("⚠️ 키워드 추출기를 사용할 수 없어 답변만 저장됩니다.")
                extracted_keywords = []
        except Exception as e:
            st.error(f"키워드 추출 중 오류가 발생했습니다: {e}")
            extracted_keywords = []

        # 2. 답변과 키워드 DB 저장
        database.add_user_answer(
            user_id=user_id,
            question_id=question_id,
            answer_text=answer_text,
            answer_date=today_str,
            is_initial_answer=True,
            extracted_keywords=extracted_keywords
        )
        
        # 3. 사용자 진행 상황 업데이트
        conn = database.get_db_connection()
        progress = conn.execute(
            "SELECT total_initial_memory_questions_answered FROM USER_PROGRESS WHERE user_id = ?", 
            (user_id,)
        ).fetchone()
        total_answered = progress['total_initial_memory_questions_answered'] + 1 if progress else 1
        conn.close()

        database.create_or_update_user_progress(
            user_id,
            total_initial_memory_questions_answered=total_answered,
            last_activity_date=today_str
        )

    st.success("✅ 당신의 소중한 기억이 안전하게 저장되었습니다!")
    
    # 단계별 다른 완료 메시지
    if phase_info['is_initial']:
        st.success(f"🎯 초기 회상 단계 진행: {total_answered}개 완료")
    else:
        st.success(f"🎯 오늘의 새로운 질문: 완료!")
    
    # 잠시 후 자동으로 새로고침하여 다음 질문 표시
    st.rerun()