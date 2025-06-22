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
from utils.constants import INITIAL_PHASE_DAYS
from components.user_info import render_user_info_form, show_user_stats
from components.initial_phase import render_initial_phase
# 클래스가 아닌, 새로 만든 함수를 임포트합니다.
from components.memory_check_phase import render_memory_check_phase

st.set_page_config(page_title="기억 회상 서비스", layout="wide")
st.header("💬 기억 회상 및 점검")

def init_session_state():
    """세션 상태 초기화"""
    # memory_check_phase에서 사용하는 상태들을 여기에 포함하여 한 번에 관리합니다.
    default_states = {
        'user_info': None,
        'user_id': None,
        'memory_check_step': 'initial', # 재질문 단계의 상태
        'current_question': None,
        'original_answer_info': None,
        'hint_image_url': None,
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
    
    # user_info가 None이거나 비어있는 경우 처리
    if not user_info:
        st.error("user_info가 비어있습니다.")
        return None
    
    # 필요한 키가 있는지 확인
    required_keys = ['이름', '생년월일', '진단일']
    missing_keys = [key for key in required_keys if key not in user_info]
    if missing_keys:
        st.error(f"필수 정보가 없습니다: {missing_keys}")
        return None
    
    conn = database.get_db_connection()
    user = conn.execute("SELECT user_id FROM USERS WHERE name = ? AND birth_date = ?", 
                        (user_info['이름'], user_info['생년월일'].strftime('%Y-%m-%d'))).fetchone()
    conn.close()
    
    if user:
        return user['user_id']
    else:
        return database.add_user(user_info['이름'], user_info['생년월일'].strftime('%Y-%m-%d'), user_info['진단일'].strftime('%Y-%m-%d'))

def main():
    """메인 실행 함수"""
    init_session_state()
    
    if not initialize_database():
        st.error("데이터베이스 초기화에 실패하여 앱을 실행할 수 없습니다.")
        return
    
    # DB 작업 객체 생성을 먼저 해야 합니다
    from utils.db_operations import DBOperations  # 추가
    db_ops = DBOperations()  # 추가
    
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
        show_user_stats(user_id, db_ops)
    
    # --- 메인 화면 로직 ---
    user_name = st.session_state.user_info.get('이름', '사용자')
    
    # str -> date 객체로 변환
    #diagnosis_date_str = st.session_state.user_info.get('진단일')
    #diagnosis_date = datetime.strptime(diagnosis_date_str, '%Y-%m-%d').date() if isinstance(diagnosis_date_str, str) else diagnosis_date_str
    
    diagnosis_date = st.session_state.user_info.get('진단일')
    if isinstance(diagnosis_date, str):
        from datetime import datetime
        diagnosis_date = datetime.strptime(diagnosis_date, '%Y-%m-%d').date()

    # MemoryChecker의 staticmethod를 올바르게 호출
    days_since_diagnosis = MemoryChecker.get_days_since_diagnosis(diagnosis_date)
    
    st.write(f"안녕하세요, **{user_name}**님! (진단 후 {days_since_diagnosis}일째)")
    
    # 서비스 단계 결정 (직접 계산)
    is_initial_phase = days_since_diagnosis < INITIAL_PHASE_DAYS
    
    if is_initial_phase:
        # 30일 이내는 초기 회상만
        st.subheader("기억 떠올리기")
        st.info(f"{INITIAL_PHASE_DAYS}일 동안은 새로운 기억을 차곡차곡 쌓는 시간이에요.")
        # 더 이상 db_ops를 전달하지 않습니다.
        render_initial_phase(user_id, context="main")
    else:
        # 30일 이후에는 탭으로 분리
        tab1, tab2 = st.tabs(["🧠 기억 확인하기", "📝 새로운 기억 추가하기"])
        
        with tab1:
            # MemoryCheckPhase 클래스 대신 render_memory_check_phase 함수를 직접 호출
            render_memory_check_phase(user_id)
        
        with tab2:
            render_initial_phase(user_id, context="additional")
    
    # 개발자 도구 (필요 시 사용)
    render_developer_tools()

def render_developer_tools():
    """개발자 도구 렌더링"""
    with st.sidebar.expander("🔧 관리자 기능"):
        if st.button("세션 상태 초기화 (사용자 정보 유지)"):
            keys_to_keep = ['user_info', 'user_id']
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.success("세션 상태가 초기화되었습니다.")
            st.rerun()
        
        if st.button("모든 정보 초기화 (로그아웃)"):
            st.session_state.clear()
            st.success("모든 정보가 초기화되었습니다.")
            st.rerun()

if __name__ == "__main__":
    main()