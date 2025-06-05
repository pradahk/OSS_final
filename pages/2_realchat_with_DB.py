import streamlit as st
from datetime import date
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 모듈 임포트
import database  # database 모듈 직접 import
from utils.db_operations import DBOperations
from utils.memory_check import MemoryChecker
from utils.constants import INITIAL_PHASE_DAYS
from components.user_info import render_user_info_form, show_user_stats
from components.initial_phase import render_initial_phase
from components.memory_check_phase import MemoryCheckPhase

st.header("💬 기억 회상 및 점검 챗")

def init_session_state():
    """세션 상태 초기화"""
    default_states = {
        'mode': 'initial_phase',
        'awaiting_memory_response': False,
        'current_memory_question': None,
        'image_generated': False,
        'awaiting_image_response': False,
        'show_result': False,
        'result_message': "",
        'result_type': "",
        'awaiting_image_memory_input': False,
        'current_check_id': None
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def initialize_database():
    """데이터베이스 초기화 (CSV 없이)"""
    try:
        # 테이블 생성 및 기본 질문 초기화
        database.create_tables()
        
        # 질문 개수 확인
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM QUESTIONS")
        question_count = cursor.fetchone()[0]
        conn.close()
        
        if question_count > 0:
            st.sidebar.success(f"✅ DB 초기화 완료 ({question_count}개 질문)")
        else:
            st.sidebar.warning("⚠️ 질문이 없습니다. 관리자에게 문의하세요.")
            
    except Exception as e:
        st.sidebar.error(f"❌ DB 초기화 실패: {e}")
        return False
    
    return True

def main():
    """메인 실행 함수"""
    # 세션 상태 초기화
    init_session_state()
    
    # 메모리 체크 카운터 초기화 (key 중복 방지용)
    if 'memory_check_counter' not in st.session_state:
        st.session_state.memory_check_counter = 0
    
    # DB 초기화 (CSV 의존성 없음)
    if not initialize_database():
        st.error("데이터베이스 초기화에 실패했습니다.")
        return
    
    # DB 작업 객체 생성
    db_ops = DBOperations()
    
    # 사용자 정보가 없으면 입력 받기
    if 'user_info' not in st.session_state:
        render_user_info_form()
        return
    
    # 사용자 ID 가져오기 또는 생성
    if 'user_id' not in st.session_state:
        user_id = db_ops.get_or_create_user(st.session_state.user_info)
        if user_id:
            st.session_state.user_id = user_id
        else:
            st.error("사용자 정보를 생성할 수 없습니다.")
            return
    
    user_id = st.session_state.user_id
    
    # 사용자 통계 표시
    show_user_stats(user_id, db_ops)
    
    # 사용자 정보 표시
    user_name = st.session_state.user_info.get('이름', '사용자')
    diagnosis_date = st.session_state.user_info.get('진단일', date.today())
    days_since_diagnosis = MemoryChecker.get_days_since_diagnosis(diagnosis_date)
    
    st.write(f"안녕하세요, **{user_name}**님! (진단 후 {days_since_diagnosis}일째)")
    
    # 진단일 기준으로 모드 결정
    current_mode = MemoryChecker.determine_mode_by_diagnosis(diagnosis_date, INITIAL_PHASE_DAYS)
    
    # 모드별 렌더링
    if current_mode == 'initial_phase' or days_since_diagnosis < INITIAL_PHASE_DAYS:
        # 30일 이내는 초기 회상만
        render_initial_phase(user_id, db_ops, context="main")
    else:
        # 30일 이후에는 탭으로 선택 가능
        tab1, tab2 = st.tabs(["🧠 기억 점검", "📝 초기 회상 추가"])
        
        with tab1:
            # 메모리 체크 카운터 증가
            st.session_state.memory_check_counter += 1
            memory_check_phase = MemoryCheckPhase(user_id, db_ops)
            memory_check_phase.render()
        
        with tab2:
            render_initial_phase(user_id, db_ops, context="additional")
    
    # 개발자 도구
    render_developer_tools(user_id, db_ops)

def render_developer_tools(user_id, db_ops):
    """개발자 도구 렌더링"""
    with st.expander("🔧 관리자 기능 (개발용)"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("세션 상태 초기화"):
                keys_to_keep = ['user_info', 'user_id']
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep:
                        del st.session_state[key]
                st.success("세션 상태가 초기화되었습니다.")
                st.rerun()
        
        with col2:
            if st.button("완전 초기화"):
                st.session_state.clear()
                st.success("모든 세션 상태가 초기화되었습니다.")
                st.rerun()
        
        with col3:
            if st.button("질문 재초기화"):
                try:
                    database.initialize_default_questions()
                    st.success("기본 질문이 재초기화되었습니다.")
                except Exception as e:
                    st.error(f"초기화 실패: {e}")
        
        # DB 상태 표시
        if user_id:
            st.write(f"**현재 사용자 ID**: {user_id}")
            
            # 통계 정보
            conn = database.get_db_connection()
            cursor = conn.cursor()
            
            # 총 질문 수
            cursor.execute("SELECT COUNT(*) FROM QUESTIONS")
            total_questions = cursor.fetchone()[0]
            st.write(f"**총 질문 수**: {total_questions}개")
            
            # 답변 수
            cursor.execute("""
                SELECT COUNT(*) FROM USER_ANSWERS 
                WHERE user_id = ? AND is_initial_answer = 1
            """, (user_id,))
            answer_count = cursor.fetchone()[0]
            st.write(f"**총 답변 수**: {answer_count}개")
            
            # 기억 점검 수
            cursor.execute("SELECT COUNT(*) FROM MEMORY_CHECKS WHERE user_id = ?", (user_id,))
            check_count = cursor.fetchone()[0]
            st.write(f"**기억 점검 수**: {check_count}개")
            
            # 결과별 통계
            cursor.execute("""
                SELECT result, COUNT(*) FROM MEMORY_CHECKS 
                WHERE user_id = ? GROUP BY result
            """, (user_id,))
            results = cursor.fetchall()
            
            if results:
                st.write("**기억 점검 결과 분포:**")
                for result, count in results:
                    st.write(f"- {result}: {count}개")
            
            # 질문 타입별 통계
            cursor.execute("SELECT question_type, COUNT(*) FROM QUESTIONS GROUP BY question_type")
            question_types = cursor.fetchall()
            
            if question_types:
                st.write("**질문 타입별 통계:**")
                for qtype, count in question_types:
                    st.write(f"- {qtype}: {count}개")
            
            conn.close()

def render_admin_question_management():
    """관리자용 질문 관리 기능 (선택사항)"""
    with st.expander("📝 질문 관리 (관리자용)"):
        st.subheader("새 질문 추가")
        
        new_question = st.text_area("새 질문을 입력하세요:", key="new_question_input")
        question_type = st.selectbox("질문 타입:", ['default', 'custom', 'seasonal'], key="question_type_select")
        
        if st.button("질문 추가", key="add_question_btn"):
            if new_question.strip():
                try:
                    database.add_question(new_question.strip(), question_type)
                    st.success("✅ 새 질문이 추가되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 질문 추가 실패: {e}")
            else:
                st.warning("⚠️ 질문을 입력해주세요.")
        
        st.subheader("기존 질문 목록")
        
        # 최근 추가된 질문들 표시
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT question_id, question_text, question_type, created_at 
            FROM QUESTIONS 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_questions = cursor.fetchall()
        conn.close()
        
        if recent_questions:
            for qid, qtext, qtype, created in recent_questions:
                st.write(f"**{qid}** [{qtype}] {qtext[:60]}..." if len(qtext) > 60 else f"**{qid}** [{qtype}] {qtext}")

if __name__ == "__main__":
    main()
    
    # 선택사항: 관리자 질문 관리 기능
    # render_admin_question_management()
