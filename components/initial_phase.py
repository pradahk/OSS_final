import streamlit as st
from datetime import date
import database
from utils.constants import MAX_DAILY_NEW_QUESTIONS

def render_initial_phase(user_id: int, db_ops, context: str = "main"):
    """
    초기 회상 단계 렌더링
    
    Args:
        user_id: 사용자 ID
        db_ops: DB 작업 객체
        context: 렌더링 컨텍스트 (key 중복 방지용)
    """
    st.info(f"🔄 **초기 회상 단계**: 하루에 {MAX_DAILY_NEW_QUESTIONS}개의 질문을 드립니다.")
    
    # 오늘 활동 현황 확인
    new_answers_today, _ = db_ops.get_today_activity_count(user_id)
    
    if new_answers_today >= MAX_DAILY_NEW_QUESTIONS:
        st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # DB에서 질문 가져오기
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question_id, question_text FROM QUESTIONS ORDER BY question_id")
    questions = cursor.fetchall()
    
    cursor.execute("""
        SELECT DISTINCT question_id FROM USER_ANSWERS 
        WHERE user_id = ? AND is_initial_answer = 1
    """, (user_id,))
    answered_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    
    # 답변하지 않은 질문 찾기
    unanswered_questions = [q for q in questions if q[0] not in answered_ids]
    
    if not unanswered_questions:
        st.success("🎉 모든 초기 회상 질문을 완료하셨습니다!")
        if st.button("기억 유무 점검 단계로 이동", key=f"{context}_move_to_memory_check"):
            st.session_state.mode = 'memory_check_phase'
            st.rerun()
        return
    
    # 첫 번째 미답변 질문 표시
    question_id, question_text = unanswered_questions[0]
    
    st.subheader(f"질문 {question_id}")
    st.write(f"**{question_text}**")
    
    # 답변 입력 - context를 key에 포함
    answer = st.text_area(
        "답변을 입력해주세요:", 
        key=f"{context}_initial_answer_{question_id}"
    )
    
    if st.button("답변 제출", type="primary", key=f"{context}_submit_{question_id}"):
        if answer.strip():
            # 답변을 DB에 저장
            database.add_user_answer(
                user_id, question_id, answer.strip(), 
                date.today().strftime('%Y-%m-%d'), True
            )
            
            # 사용자 진행 상황 업데이트
            database.create_or_update_user_progress(
                user_id,
                total_initial_memory_questions_answered=len(answered_ids) + 1,
                last_activity_date=date.today().strftime('%Y-%m-%d')
            )
            
            st.success("✅ 답변이 저장되었습니다!")
            st.rerun()
        else:
            st.warning("⚠️ 답변을 입력해주세요.")
