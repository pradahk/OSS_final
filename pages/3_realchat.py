import streamlit as st
from datetime import date, timedelta, datetime
import json
from difflib import SequenceMatcher

st.header("💬 기억 회상 및 점검 챗봇")

# 하드코딩된 질문 리스트
QUESTIONS = [
    "젊었을 때 자주 가셨던 장소가 기억나시나요?",
    "자주 입던 옷이나 색깔이 떠오르시나요?",
    "주말이나 명절에 하던 가족 활동이 기억나시나요?",
    "늘 다니시던 산책길이 떠오르시나요?",
    "가족과의 추억 중 가장 소중한 순간은 언제였나요?",
    "자주 사용하시던 물건이 기억나시나요?",
    "명절에 입던 옷이나 하시던 음식이 떠오르시나요?",
    "젊은 시절 친구들과의 만남 장소가 떠오르시나요?"
]

# 세션 상태 초기화
def init_session_state():
    if 'mode' not in st.session_state:
        st.session_state.mode = 'initial_phase'  # 'initial_phase' 또는 'memory_check_phase'
    
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    
    if 'daily_question_count' not in st.session_state:
        st.session_state.daily_question_count = 0
    
    if 'stored_answers' not in st.session_state:
        st.session_state.stored_answers = {}  # {question_index: {"answer": str, "date": date}}
    
    if 'completed_questions' not in st.session_state:
        st.session_state.completed_questions = set()

    if 'reusable_questions' not in st.session_state:
        st.session_state.reusable_questions = set()

    if 'completed_questions' not in st.session_state:
        st.session_state.completed_questions = set()  # 폐기된 질문들
    
    if 'last_activity_date' not in st.session_state:
        st.session_state.last_activity_date = date.today()
    
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
        st.session_state.result_type = ""  # 'success', 'warning', 'info'
    
    if 'daily_new_questions' not in st.session_state:
        st.session_state.daily_new_questions = 0  # 오늘 답변한 새로운 질문 수
    
    if 'daily_memory_checks' not in st.session_state:
        st.session_state.daily_memory_checks = 0  # 오늘 수행한 기억 점검 수

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

# 날짜가 바뀌었는지 확인
def check_new_day():
    today = date.today()
    if st.session_state.last_activity_date != today:
        st.session_state.daily_question_count = 0
        st.session_state.daily_new_questions = 0
        st.session_state.daily_memory_checks = 0
        st.session_state.last_activity_date = today
        
        # 진단일 기준으로 모드 자동 설정
        if 'user_info' in st.session_state and '진단일' in st.session_state.user_info:
            st.session_state.mode = determine_mode_by_diagnosis()
        
        return True
    return False

# 초기 회상 단계
def initial_phase():
    st.info("🔄 **초기 회상 단계**: 하루에 2개의 질문을 드립니다.")
    
    # 새로운 날인지 확인
    check_new_day()
    
    # 오늘 2개 질문을 모두 완료했는지 확인
    if st.session_state.daily_new_questions >= 2:
        st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # 모든 질문을 완료했는지 확인
    if st.session_state.current_question_index >= len(QUESTIONS):
        st.success("🎉 모든 초기 회상 질문을 완료하셨습니다!")
        if st.button("기억 유무 점검 단계로 이동"):
            st.session_state.mode = 'memory_check_phase'
            st.session_state.current_question_index = 0
            st.session_state.daily_question_count = 0
            st.session_state.daily_new_questions = 0
            st.rerun()
        return
    
    # 현재 질문 표시
    question_idx = st.session_state.current_question_index
    question = QUESTIONS[question_idx]
    
    st.subheader(f"질문 {question_idx + 1}")
    st.write(f"**{question}**")
    
    # 답변 입력
    answer = st.text_area("답변을 입력해주세요:", key=f"initial_answer_{question_idx}")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("답변 제출", type="primary"):
            if answer.strip():
                # 답변 저장
                st.session_state.stored_answers[question_idx] = {
                    "answer": answer.strip(),
                    "date": date.today(),
                    "question": question
                }
                
                # 카운터 증가
                st.session_state.current_question_index += 1
                st.session_state.daily_question_count += 1
                st.session_state.daily_new_questions += 1
                
                st.success("✅ 답변이 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 답변을 입력해주세요.")

# 기억 유무 점검 단계
def memory_check_phase():
    st.info("🧠 **기억 유무 점검 단계**: 하루에 새로운 질문 1개와 기억 점검 1개를 진행합니다.")
    
    # 새로운 날인지 확인
    check_new_day()
    
    # 오늘의 할당량 확인
    if st.session_state.daily_new_questions >= 1 and st.session_state.daily_memory_checks >= 1:
        st.success("✅ 오늘의 모든 활동을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # 저장된 답변이 없는 경우
    if not st.session_state.stored_answers:
        st.warning("⚠️ 저장된 답변이 없습니다. 먼저 초기 회상 단계를 완료해주세요.")
        if st.button("초기 회상 단계로 돌아가기"):
            st.session_state.mode = 'initial_phase'
            st.rerun()
        return
    
    # 먼저 새로운 질문을 처리
    if st.session_state.daily_new_questions < 1 and st.session_state.current_question_index < len(QUESTIONS):
        st.subheader("📝 오늘의 새로운 질문")
        question_idx = st.session_state.current_question_index
        question = QUESTIONS[question_idx]
        
        st.write(f"**{question}**")
        
        answer = st.text_area("답변을 입력해주세요:", key=f"new_answer_{question_idx}")
        
        if st.button("답변 제출", type="primary", key="new_submit"):
            if answer.strip():
                # 답변 저장
                st.session_state.stored_answers[question_idx] = {
                    "answer": answer.strip(),
                    "date": date.today(),
                    "question": question
                }
                
                # 카운터 증가
                st.session_state.current_question_index += 1
                st.session_state.daily_new_questions += 1
                
                st.success("✅ 답변이 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 답변을 입력해주세요.")
    
    # 새로운 질문을 완료했거나 이미 완료한 경우, 기억 점검 진행
    elif st.session_state.daily_memory_checks < 1:
        st.subheader("🧠 오늘의 기억 점검")
        
        # 여기서부터는 기존의 기억 점검 로직
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
            if st.button("다음 질문으로 계속하기", type="primary"):
                st.session_state.result_message = ""
                st.session_state.result_type = ""
                st.session_state.daily_memory_checks += 1  # 기억 점검 완료
                st.rerun()
            return
        
        # 이미지 응답을 기다리는 상태인 경우
        if st.session_state.awaiting_image_response:
            current_q_idx = st.session_state.current_memory_question
            question = st.session_state.stored_answers[current_q_idx]["question"]
            original_answer = st.session_state.stored_answers[current_q_idx]["answer"]
            
            st.subheader("🖼️ 생성된 이미지")
            st.write(f"**{question}**")
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
                    
                    current_memory = st.text_area("현재 기억하고 계신 내용:", key=f"image_memory_{current_q_idx}")
                    
                    col1_input, col2_input = st.columns(2)
                    with col1_input:
                        if st.button("답변 제출", key="image_memory_submit"):
                            if current_memory.strip():
                                # 유사도 계산
                                similarity = calculate_similarity(original_answer, current_memory.strip())
                                
                                # 결과 메시지 설정
                                result_msg = f"**현재 답변**: {current_memory.strip()}\n\n"
                                result_msg += f"**원본 답변**: {original_answer}\n\n"
                                
                                # 유사도가 70% 이상이면 질문 재사용 가능으로 설정
                                if similarity >= 0.7:
                                    result_msg += "✅ 이미지를 보고 기억을 잘 떠올리셨습니다!\n"
                                    result_msg += f"**원본 답변**: {original_answer}\n\n"
                                    result_msg += "💡 이 질문은 나중에 다시 사용될 수 있습니다."
                                    st.session_state.result_type = 'success'
                                    st.session_state.reusable_questions.add(current_q_idx)
                                else:
                                    result_msg += "⚠️ 기억에 차이가 있습니다.\n"
                                    result_msg += f"**원본 답변**: {original_answer}\n\n"
                                    result_msg += "이 질문은 완료 처리됩니다."
                                    st.session_state.result_type = 'warning'
                                
                                st.session_state.completed_questions.add(current_q_idx)
                                
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
                    
                    st.session_state.result_message = result_msg
                    st.session_state.result_type = 'info'
                    st.session_state.show_result = True
                    
                    # 질문 완료 처리 (삭제)
                    st.session_state.completed_questions.add(current_q_idx)
                    
                    # 상태 완전 리셋
                    st.session_state.awaiting_image_response = False
                    st.session_state.awaiting_image_memory_input = False
                    st.session_state.current_memory_question = None
                    st.session_state.image_generated = False
                    
                    st.rerun()
            
            return
        
        # 기억 응답을 기다리는 상태이면서 현재 질문이 있는 경우
        if st.session_state.awaiting_memory_response and st.session_state.current_memory_question is not None:
            current_q_idx = st.session_state.current_memory_question
            question = st.session_state.stored_answers[current_q_idx]["question"]
            original_answer = st.session_state.stored_answers[current_q_idx]["answer"]
            
            st.subheader("📝 기억 내용 확인")
            st.write(f"**{question}**")
            st.write("기억하고 계신 내용을 말씀해주세요:")
            
            current_memory = st.text_area("현재 기억하고 계신 내용:", key=f"memory_check_{current_q_idx}")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("답변 제출", type="primary"):
                    if current_memory.strip():
                        # 유사도 계산
                        similarity = calculate_similarity(original_answer, current_memory.strip())
                        
                        # 결과 메시지 설정
                        result_msg = f"**현재 답변**: {current_memory.strip()}\n\n"
                        result_msg += f"**원본 답변**: {original_answer}\n\n"
                        
                        # 유사도가 70% 이상이면 재사용 가능
                        if similarity >= 0.7:
                            result_msg += "✅ 기억이 잘 보존되어 있습니다! 이 질문은 완료됩니다.\n"
                            result_msg += "💡 이 질문은 나중에 다시 사용될 수 있습니다."
                            st.session_state.result_type = 'success'
                            st.session_state.reusable_questions.add(current_q_idx)  # 재사용 가능으로 분류
                            st.session_state.completed_questions.add(current_q_idx)
                        else:
                            # 기억이 틀린 경우 - 이미지 생성 단계로 이동
                            st.warning("⚠️ 기억에 차이가 있습니다. 이미지를 생성하여 도움을 드리겠습니다.")
                            st.session_state.image_generated = True
                            st.session_state.awaiting_image_response = True
                            # 원본 답변은 표시하지 않음
                            st.rerun()
                            return
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
            
            return
        
        # 완료되지 않은 질문들 찾기 (재사용 가능한 질문도 포함)
        available_questions = [idx for idx in st.session_state.stored_answers.keys() 
                              if idx not in st.session_state.completed_questions or idx in st.session_state.reusable_questions]
        
        # 재사용 가능한 질문 중에서 랜덤 선택 우선
        reusable_available = [idx for idx in available_questions if idx in st.session_state.reusable_questions]
        new_questions = [idx for idx in available_questions if idx not in st.session_state.completed_questions and idx not in st.session_state.reusable_questions]
        
        # 재사용 가능한 질문이 있으면 그 중에서 랜덤 선택, 없으면 새 질문 선택
        if reusable_available:
            import random
            current_q_idx = random.choice(reusable_available)
        elif new_questions:
            current_q_idx = new_questions[0]
        else:
            st.success("🎉 모든 기억 점검을 완료하셨습니다!")
            return
        st.session_state.current_memory_question = current_q_idx
        
        question = st.session_state.stored_answers[current_q_idx]["question"]
        
        st.subheader("🧠 기억 확인")
        st.write(f"**{question}**")
        st.write("이 질문을 기억하시나요?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 기억해요", type="primary"):
                st.session_state.awaiting_memory_response = True
                st.rerun()
        
        with col2:
            if st.button("❌ 기억 안 나요"):
                # 이미지 생성 표시
                st.session_state.image_generated = True
                st.session_state.awaiting_image_response = True
                st.rerun()

# 메인 실행 함수
def main():
    init_session_state()
    
    # 진단서 업로드 여부 확인
    if 'user_info' not in st.session_state or '진단일' not in st.session_state.user_info:
        st.warning("⚠️ 먼저 1단계에서 진단서를 업로드해주세요.")
        st.info("진단서를 업로드하면 진단일에 따라 자동으로 적절한 단계가 설정됩니다.")
        return
    
    # 진단일 기준으로 초기 모드 설정 (최초 1회만)
    if 'mode_initialized' not in st.session_state:
        st.session_state.mode = determine_mode_by_diagnosis()
        st.session_state.mode_initialized = True
    
    # 사이드바에 현재 상태 표시
    with st.sidebar:
        st.header("📊 현재 상태")
        
        # 사용자 정보 표시
        if 'user_info' in st.session_state:
            st.write(f"**이름**: {st.session_state.user_info.get('이름', '미상')}")
            st.write(f"**나이**: {st.session_state.user_info.get('나이', '미상')}세")
            
            if '진단일' in st.session_state.user_info:
                diagnosis_date = st.session_state.user_info['진단일']
                days_passed = get_days_since_diagnosis()
                st.write(f"**진단일**: {diagnosis_date}")
                st.write(f"**경과일**: {days_passed}일")
                st.write(f"**자동 설정 모드**: {determine_mode_by_diagnosis()}")
        
        st.divider()
        
        st.write(f"**현재 단계**: {st.session_state.mode}")
        st.write(f"**저장된 답변 수**: {len(st.session_state.stored_answers)}")
        st.write(f"**완료된 질문 수**: {len(st.session_state.completed_questions)}")
        st.write(f"**재사용 가능 질문 수**: {len(st.session_state.reusable_questions)}")
        
        if st.session_state.mode == 'initial_phase':
            st.write(f"**오늘 답변한 질문**: {st.session_state.daily_new_questions}/2")
        else:
            st.write(f"**오늘 새 질문**: {st.session_state.daily_new_questions}/1")
            st.write(f"**오늘 기억 점검**: {st.session_state.daily_memory_checks}/1")
        
        st.divider()
        
        st.subheader("🔧 테스트 기능")
        # 단계 전환 버튼 (테스트용)
        if st.session_state.mode == 'initial_phase':
            if st.button("🧠 기억 점검 단계로 이동"):
                st.session_state.mode = 'memory_check_phase'
                st.rerun()
        else:
            if st.button("🔄 초기 회상 단계로 이동"):
                st.session_state.mode = 'initial_phase'
                st.rerun()
        
        # 데이터 초기화 버튼
        if st.button("🗑️ 모든 데이터 초기화"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # 메인 로직 실행
    if st.session_state.mode == 'initial_phase':
        initial_phase()
    else:
        memory_check_phase()

if __name__ == "__main__":
    main()