import streamlit as st
from datetime import date, timedelta

def render_user_info_form():
    """사용자 정보 입력 폼 렌더링"""
    st.subheader("👤 사용자 정보 입력")
    
    with st.form("user_info_form"):
        name = st.text_input("이름을 입력해주세요:")
        birth_date = st.date_input(
            "생년월일을 선택해주세요:", 
            value=date(1950, 1, 1),
            min_value=date(1920, 1, 1),
            max_value=date.today()
        )
        diagnosis_date = st.date_input(
            "치매 진단일을 선택해주세요:",
            value=date.today() - timedelta(days=30),
            min_value=date(2020, 1, 1),
            max_value=date.today()
        )
        
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

def show_user_stats(user_id: int, db_ops):
    """사용자 통계 및 진행 상황 표시"""
    import database
    user_progress = database.get_user_progress(user_id)
    
    if user_progress:
        st.sidebar.header("📊 진행 상황")
        
        # 전체 통계
        st.sidebar.metric("초기 회상 완료", user_progress['total_initial_memory_questions_answered'])
        st.sidebar.metric("기억 점검 완료", user_progress['total_revisit_questions_answered'])
        st.sidebar.metric("서비스 이용일", user_progress['current_service_day'])
        
        # 오늘의 활동
        new_answers_today, memory_checks_today = db_ops.get_today_activity_count(user_id)
        
        st.sidebar.subheader("📅 오늘의 활동")
        st.sidebar.write(f"새로운 질문: {new_answers_today}")
        st.sidebar.write(f"기억 점검: {memory_checks_today}")