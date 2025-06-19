import streamlit as st
from datetime import date
import database
from utils.constants import MAX_DAILY_NEW_QUESTIONS
from keyword_extractor import get_keyword_extractor # 키워드 추출기 임포트

def render_initial_phase(user_id: int, context: str = "main"):
    """
    초기 회상 단계 렌더링 (키워드 추출 기능 통합)
    
    Args:
        user_id: 사용자 ID
        context: 렌더링 컨텍스트 (key 중복 방지용)
    """
    st.info(f"🔄 **초기 회상 단계**: 하루에 {MAX_DAILY_NEW_QUESTIONS}개의 새로운 기억에 대한 질문을 드립니다. 가볍게 답변해주세요.")

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

    if new_answers_today >= MAX_DAILY_NEW_QUESTIONS:
        st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        st.balloons()
        return

    # --- 답변하지 않은 질문 가져오기 ---
    conn = database.get_db_connection()
    cursor = conn.cursor()
    # 전체 질문 목록
    cursor.execute("SELECT question_id, question_text FROM QUESTIONS ORDER BY question_id")
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
        st.success("🎉 내일부터는 초기 회상 질문과 기억을 다시 확인하는 시간을 가질 거예요.")
        # 자동으로 다음 단계로 넘어가거나, 사용자의 확인을 받을 수 있습니다.
        # 여기서는 완료 메시지만 표시합니다.
        return

    # --- 다음 질문 표시 및 답변 입력 ---
    question_id, question_text = unanswered_questions[0]
    
    st.subheader(f"기억 떠올리기 (남은 질문: {MAX_DAILY_NEW_QUESTIONS - new_answers_today}개)")
    st.markdown(f"#### Q. {question_text}")
    
    answer = st.text_area(
        "이 질문에 대한 당신의 기억을 자유롭게 적어주세요.",
        key=f"{context}_initial_answer_{question_id}",
        height=150
    )
    
    if st.button("답변 제출하고 기억 저장하기", type="primary", key=f"{context}_submit_{question_id}"):
        if answer.strip():
            with st.spinner("답변을 분석하여 당신의 기억을 저장하고 있습니다... 잠시만 기다려주세요."):
                # 1. 키워드 추출 모델 로드 및 키워드 추출 (사용자에게 노출되지 않음)
                try:
                    extractor = get_keyword_extractor()
                    extracted_keywords = extractor.extract_keywords(answer.strip())
                except Exception as e:
                    st.error(f"키워드 추출 중 오류가 발생했습니다: {e}")
                    extracted_keywords = [] # 오류 발생 시 빈 리스트로 처리

                # 2. 답변과 추출된 키워드를 DB에 저장 (수정된 DB 함수 사용)
                database.add_user_answer(
                    user_id=user_id,
                    question_id=question_id,
                    answer_text=answer.strip(),
                    answer_date=today_str,
                    is_initial_answer=True,
                    extracted_keywords=extracted_keywords
                )
                
                # 3. 사용자 진행 상황 업데이트
                # create_or_update_user_progress는 내부적으로 존재 여부를 확인하므로 그대로 사용 가능
                conn = database.get_db_connection()
                progress = conn.execute("SELECT total_initial_memory_questions_answered FROM USER_PROGRESS WHERE user_id = ?", (user_id,)).fetchone()
                total_answered = progress['total_initial_memory_questions_answered'] + 1 if progress else 1
                conn.close()

                database.create_or_update_user_progress(
                    user_id,
                    total_initial_memory_questions_answered=total_answered,
                    last_activity_date=today_str
                )

            st.success("✅ 당신의 소중한 기억이 안전하게 저장되었습니다!")
            # 잠시 후 자동으로 새로고침하여 다음 질문 표시
            st.rerun()
        else:
            st.warning("⚠️ 답변을 입력해주세요. 어떤 기억이든 소중합니다.")