import streamlit as st
from datetime import date, datetime
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 모듈 임포트
import database
from utils.memory_check import MemoryChecker
from utils.constants import (
    INITIAL_PHASE_DAYS, 
    MAX_DAILY_NEW_QUESTIONS_MAINTENANCE, 
    MAX_DAILY_MEMORY_CHECKS
)
from components.user_info import render_user_info_form, show_user_stats
from components.initial_phase import render_initial_phase
from components.memory_check_phase import render_memory_check_phase

st.set_page_config(page_title="기억 회상 서비스", layout="wide")
st.header("💬 기억 회상 및 점검")

def init_session_state():
    """세션 상태 초기화"""
    default_states = {
        'user_info': None,
        'user_id': None,
        'current_memory_check': None,
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def initialize_database():
    """데이터베이스 초기화"""
    try:
        database.create_tables()
        return True
    except Exception as e:
        st.sidebar.error(f"❌ DB 초기화 실패: {e}")
        return False

def get_or_create_user(user_info: dict) -> int:
    """사용자 정보를 기반으로 user_id를 가져오거나 새로 생성합니다."""
    if not user_info or '이름' not in user_info:
        return None
    
    conn = database.get_db_connection()
    user = conn.execute("SELECT user_id FROM USERS WHERE name = ? AND birth_date = ?", 
                        (user_info['이름'], user_info['생년월일'].strftime('%Y-%m-%d'))).fetchone()
    conn.close()
    
    if user:
        return user['user_id']
    else:
        user_id = database.add_user(
            user_info['이름'], 
            user_info['생년월일'].strftime('%Y-%m-%d'), 
            user_info['진단일'].strftime('%Y-%m-%d')
        )
        # 초기 진행 상황 생성
        database.create_or_update_user_progress(
            user_id,
            last_activity_date=date.today().strftime('%Y-%m-%d'),
            current_service_day=1
        )
        return user_id

def main():
    """메인 실행 함수"""
    init_session_state()
    
    if not initialize_database():
        st.error("데이터베이스 초기화에 실패하여 앱을 실행할 수 없습니다.")
        return
    
    # 사용자 정보가 없으면 사이드바에서 입력 받기
    if st.session_state.user_info is None:
        with st.sidebar:
            st.info("서비스를 이용하려면 사용자 정보를 입력해주세요.")
            render_user_info_form()
        return
    
    # 사용자 ID 설정
    if st.session_state.user_id is None:
        user_id = get_or_create_user(st.session_state.user_info)
        st.session_state.user_id = user_id
    
    user_id = st.session_state.user_id
    
    # 사이드바에 사용자 통계 표시
    with st.sidebar:
        from utils.db_operations import DBOperations
        db_ops = DBOperations()
        show_user_stats(user_id, db_ops)
    
    # --- 메인 화면 로직 ---
    user_name = st.session_state.user_info.get('이름', '사용자')
    
    diagnosis_date = st.session_state.user_info.get('진단일')
    if isinstance(diagnosis_date, str):
        diagnosis_date = datetime.strptime(diagnosis_date, '%Y-%m-%d').date()

    days_since_diagnosis = MemoryChecker.get_days_since_diagnosis(diagnosis_date)
    
    st.write(f"안녕하세요, **{user_name}**님! (진단 후 {days_since_diagnosis}일째)")
    
    # 서비스 단계 결정
    is_initial_phase = days_since_diagnosis < INITIAL_PHASE_DAYS
    
    if is_initial_phase:
        # 30일 이내는 초기 회상만
        st.subheader("🧠 기억 떠올리기")
        st.info(f"**초기 회상 단계** - {INITIAL_PHASE_DAYS}일 동안은 새로운 기억을 차곡차곡 쌓는 시간이에요.")
        render_initial_phase(user_id, context="main")
    else:
        # 30일 이후에는 새로운 질문 + 기억 점검
        st.info(f"**기억 유지 단계** - 매일 새로운 질문 1개와 기억 점검 1개를 진행합니다.")
        
        # 오늘의 활동 현황 확인
        new_answers_today, memory_checks_today = database.get_today_activity_count(user_id)
        
        # 탭 구성 (새로운 질문을 첫 번째 탭으로)
        tab1, tab2 = st.tabs(["📝 새로운 질문", "🧠 기억 점검"])
        
        with tab1:
            # 오늘 답변 개수와 현재 단계 할당량 비교
            current_limit = MAX_DAILY_NEW_QUESTIONS_MAINTENANCE
            
            # 유지 단계에서는 오늘 답변이 1개 미만일 때만 새 질문 제공
            if new_answers_today < current_limit:
                st.subheader(f"📝 오늘의 새로운 질문 ({new_answers_today}/{current_limit})")
                render_initial_phase(user_id, context="maintenance")
            else:
                st.success("✅ 오늘의 새로운 질문을 모두 완료했습니다!")
                st.info("🧠 기억 점검 탭으로 이동해주세요.")
        
        with tab2:
            if memory_checks_today < MAX_DAILY_MEMORY_CHECKS:
                st.subheader(f"🧠 오늘의 기억 점검 ({memory_checks_today}/{MAX_DAILY_MEMORY_CHECKS})")
                render_memory_check_phase(user_id)
            else:
                st.success("✅ 오늘의 기억 점검을 모두 완료했습니다!")
                st.balloons()
    
    # 하단 정보
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 새로고침"):
            st.rerun()
    
    with col2:
        if st.button("🔧 정보 초기화"):
            st.session_state.clear()
            st.success("모든 정보가 초기화되었습니다.")
            st.rerun()

if __name__ == "__main__":
    main()