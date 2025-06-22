import streamlit as st
from datetime import date, datetime, timedelta
import database
from components.initial_phase import render_initial_phase, is_in_initial_phase, get_current_phase_info
from components.memory_check_phase import render_memory_check_phase
from utils.constants import (
    INITIAL_PHASE_DAYS,
    MAX_DAILY_NEW_QUESTIONS_INITIAL,
    MAX_DAILY_NEW_QUESTIONS_MAINTENANCE,
    MAX_DAILY_MEMORY_CHECKS
)
import json

# 페이지 설정
st.set_page_config(
    page_title="치매 증상 지연 서비스", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_database():
    """데이터베이스 초기화"""
    try:
        database.create_tables()
        # 기본 질문들 추가 (실제 서비스에서는 더 많은 질문들이 필요)
        # init_default_questions()
        auto_load_questions_from_csv()
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {e}")

def auto_load_questions_from_csv():
    """앱 실행시 자동으로 CSV에서 질문 로딩"""
    from utils.question_loader import load_questions_from_csv
    import os
    
    # 현재 DB의 질문 개수 확인
    conn = database.get_db_connection()
    existing_count = conn.execute("SELECT COUNT(*) FROM QUESTIONS").fetchone()[0]
    conn.close()
    
    # CSV 파일에서 질문 로딩 시도
    csv_questions = load_questions_from_csv("questions.csv")
    
    if csv_questions and len(csv_questions) > existing_count:
        # 🔧 수정: CSV에 더 많은 질문이 있으면 기존 질문 삭제하고 CSV 질문으로 교체
        
        # 기존 질문 모두 삭제
        conn = database.get_db_connection()
        conn.execute("DELETE FROM QUESTIONS")
        conn.commit()
        conn.close()
        
        # CSV 질문들 추가
        for question_text in csv_questions:
            database.add_question(question_text.strip(), "csv_import")
        
        # 저장 확인
        conn = database.get_db_connection()
        new_count = conn.execute("SELECT COUNT(*) FROM QUESTIONS").fetchone()[0]
        conn.close()
        
        #st.success(f"✅ CSV에서 {len(csv_questions)}개 질문을 DB에 저장! (기존 {existing_count}개 교체)")
        # st.write(f"🔍 **확인**: 현재 DB 질문 개수: {new_count}")
        
    elif not csv_questions and existing_count == 0:
        # CSV 로딩 실패시 기본 질문 사용 (기존 로직)
        default_questions = [
            "가장 기억에 남는 여행은 어디였나요?",
            "어린 시절 가장 좋아했던 음식은 무엇인가요?",
        ]
        for question_text in default_questions:
            database.add_question(question_text, "default")
        st.warning(f"⚠️ CSV를 찾을 수 없어 기본 질문 {len(default_questions)}개 사용")
    else:
        st.info(f"⚠️ 기존 질문 {existing_count}개 사용 중 (CSV: {len(csv_questions) if csv_questions else 0}개)")

def render_sidebar(user_id=None):
    """사이드바 렌더링"""    
    if user_id:
        user = database.get_user(user_id)
        if user:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 사용자 정보")
            st.sidebar.write(f"**이름:** {user['name']}")
            st.sidebar.write(f"**생년월일:** {user['birth_date']}")
            st.sidebar.write(f"**진단일:** {user['diagnosis_date']}")
            
            # 현재 단계 정보
            phase_info = get_current_phase_info(user_id)
            if phase_info:
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 📊 현재 단계")
                st.sidebar.write(f"**단계:** {phase_info['phase_name']}")
                st.sidebar.write(f"**진단일로부터:** {phase_info['days_since_diagnosis']+1}일차")
                
                if phase_info['is_initial']:
                    remaining_days = INITIAL_PHASE_DAYS - phase_info['days_since_diagnosis']
                    st.sidebar.write(f"**남은 기간:** {remaining_days}일")
            
            # 오늘의 활동 현황
            new_answers_today, memory_checks_today = database.get_today_activity_count(user_id)
            
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📅 오늘의 활동")
            
            if phase_info and phase_info['is_initial']:
                st.sidebar.write(f"**새로운 질문:** {new_answers_today}/{phase_info['max_daily_questions']}")
                progress = new_answers_today / phase_info['max_daily_questions']
                st.sidebar.progress(progress)
            else:
                st.sidebar.write(f"**새로운 질문:** {new_answers_today}/{MAX_DAILY_NEW_QUESTIONS_MAINTENANCE}")
                st.sidebar.write(f"**기억 점검:** {memory_checks_today}/{MAX_DAILY_MEMORY_CHECKS}")
                
                new_progress = new_answers_today / MAX_DAILY_NEW_QUESTIONS_MAINTENANCE
                memory_progress = memory_checks_today / MAX_DAILY_MEMORY_CHECKS
                
                st.sidebar.progress(new_progress)
                st.sidebar.progress(memory_progress)
            
            # 전체 진행 상황
            user_progress = database.get_user_progress(user_id)
            if user_progress:
                st.sidebar.markdown("---")
                st.sidebar.markdown("### 📈 전체 진행 상황")
                st.sidebar.metric("총 답변한 질문", user_progress['total_initial_memory_questions_answered'])
                st.sidebar.metric("총 기억 점검", user_progress['total_revisit_questions_answered'])

def render_user_registration():
    """사용자 등록 폼"""
    st.title("🧠 치매 증상 지연 서비스에 오신 것을 환영합니다")
    
    st.markdown("""
    ### 📋 서비스 소개
    
    이 서비스는 치매 초기 환자분들의 증상 진행을 지연시키기 위한 기억 훈련 프로그램입니다.
    
    **서비스 진행 방식:**
    - **초기 30일**: 진단일로부터 30일 동안 매일 2개의 새로운 기억 질문
    - **30일 이후**: 매일 1개의 새로운 질문 + 1개의 기억 점검
    
    **기억 점검 방식:**
    - 이전에 답변하신 질문을 다시 물어봅니다
    - 키워드 기반으로 기억 정확도를 확인합니다
    - 필요시 이미지 힌트를 제공합니다
    """)
    
def render_main_service(user_id):
    """메인 서비스 렌더링"""
    # 사용자 정보 확인
    user = database.get_user(user_id)
    if not user:
        st.error("❌ 사용자 정보를 찾을 수 없습니다.")
        if st.button("처음부터 다시 시작"):
            if 'user_id' in st.session_state:
                del st.session_state.user_id
            st.rerun()
        return
    
    # 현재 단계 확인
    phase_info = get_current_phase_info(user_id)
    if not phase_info:
        st.error("❌ 단계 정보를 확인할 수 없습니다.")
        return
    
    # 페이지 제목
    st.title(f"🧠 {user['name']}님의 기억 훈련")
    
    # 단계별 안내
    if phase_info['is_initial']:
        remaining_days = INITIAL_PHASE_DAYS - phase_info['days_since_diagnosis']
        st.info(f"📅 **{phase_info['phase_name']}** - {remaining_days}일 남음 "
                f"(진단일로부터 {phase_info['days_since_diagnosis']+1}일차)")
    else:
        st.info(f"📅 **{phase_info['phase_name']}** "
                f"(진단일로부터 {phase_info['days_since_diagnosis']+1}일차)")
    
    # 오늘의 활동 현황
    new_answers_today, memory_checks_today = database.get_today_activity_count(user_id)
    
    # 활동 상태에 따른 탭 구성
    if phase_info['is_initial']:
        # 초기 30일 - 새로운 질문만
        st.markdown("---")
        render_initial_phase(user_id, "main")
    else:
        # 30일 이후 - 새로운 질문 + 기억 점검
        tab1, tab2 = st.tabs(["📝 새로운 질문", "🧠 기억 점검"])
        
        with tab1:
            if new_answers_today < MAX_DAILY_NEW_QUESTIONS_MAINTENANCE:
                render_initial_phase(user_id, "maintenance")
            else:
                st.success("✅ 오늘의 새로운 질문을 모두 완료했습니다!")
                st.info("🧠 기억 점검 탭으로 이동해주세요.")
        
        with tab2:
            if memory_checks_today < MAX_DAILY_MEMORY_CHECKS:
                render_memory_check_phase(user_id)
            else:
                st.success("✅ 오늘의 기억 점검을 모두 완료했습니다!")
                st.balloons()
    
    # 하단 정보
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 새로고침"):
            st.rerun()
    
    with col2:
        if st.button("📊 전체 통계 보기"):
            show_detailed_stats(user_id)
    
    with col3:
        if st.button("⚙️ 설정"):
            show_settings(user_id)

def show_detailed_stats(user_id):
    """상세 통계 표시"""
    st.subheader("📊 상세 통계")
    
    user_progress = database.get_user_progress(user_id)
    if user_progress:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 답변한 질문", user_progress['total_initial_memory_questions_answered'])
        
        with col2:
            st.metric("총 기억 점검", user_progress['total_revisit_questions_answered'])
        
        with col3:
            st.metric("서비스 이용일", user_progress['current_service_day'])
    
    # 최근 활동 내역
    st.subheader("📅 최근 활동")
    conn = database.get_db_connection()
    
    recent_answers = conn.execute("""
        SELECT Q.question_text, UA.answer_text, UA.answer_date 
        FROM USER_ANSWERS UA
        JOIN QUESTIONS Q ON UA.question_id = Q.question_id
        WHERE UA.user_id = ? AND UA.is_initial_answer = 1
        ORDER BY UA.created_at DESC LIMIT 5
    """, (user_id,)).fetchall()
    
    if recent_answers:
        for answer in recent_answers:
            with st.expander(f"{answer['answer_date']} - {answer['question_text'][:50]}..."):
                st.write(f"**질문:** {answer['question_text']}")
                st.write(f"**답변:** {answer['answer_text']}")
    else:
        st.info("아직 답변한 질문이 없습니다.")
    
    conn.close()

def show_settings(user_id):
    """설정 페이지"""
    st.subheader("⚙️ 설정")
    
    user = database.get_user(user_id)
    
    st.write("**사용자 정보**")
    st.write(f"이름: {user['name']}")
    st.write(f"생년월일: {user['birth_date']}")
    st.write(f"진단일: {user['diagnosis_date']}")
    
    st.markdown("---")
    
    if st.button("🔄 사용자 정보 재설정"):
        if 'user_id' in st.session_state:
            del st.session_state.user_id
        st.success("사용자 정보가 재설정됩니다.")
        st.rerun()

def main():
    """메인 애플리케이션"""
    # 데이터베이스 초기화
    initialize_database()
    
    # 사용자 ID 확인
    user_id = st.session_state.get('user_id')
    
    # 사이드바 렌더링
    render_sidebar(user_id)
    
    # 메인 컨텐츠
    if user_id:
        render_main_service(user_id)
    else:
        render_user_registration()

if __name__ == "__main__":
    main()