import streamlit as st
from datetime import date, timedelta
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
        st.session_state.completed_questions = set()  # 폐기된 질문들

    if 'reusable_questions' not in st.session_state:
        st.session_state.reusable_questions = set()  # 재사용 가능한 질문들
    
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

# 텍스트 유사도 계산 함수
def calculate_similarity(text1, text2):
    """두 텍스트의 유사도를 0-1 사이의 값으로 반환"""
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()

# 날짜가 바뀌었는지 확인
def check_new_day():
    today = date.today()
    if st.session_state.last_activity_date != today:
        st.session_state.daily_question_count = 0
        st.session_state.last_activity_date = today
        return True
    return False

# 초기 회상 단계
def initial_phase():
    st.info("🔄 **초기 회상 단계**: 하루에 2개의 질문을 드립니다.")
    
    # 새로운 날인지 확인
    check_new_day()
    
    # 오늘 2개 질문을 모두 완료했는지 확인
    if st.session_state.daily_question_count >= 2:
        st.success("✅ 오늘의 모든 질문을 완료하셨습니다! 내일 다시 만나요.")
        return
    
    # 모든 질문을 완료했는지 확인
    if st.session_state.current_question_index >= len(QUESTIONS):
        st.success("🎉 모든 초기 회상 질문을 완료하셨습니다!")
        if st.button("기억 유무 점검 단계로 이동"):
            st.session_state.mode = 'memory_check_phase'
            st.session_state.current_question_index = 0
            st.session_state.daily_question_count = 0
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
                
                st.success("✅ 답변이 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 답변을 입력해주세요.")

# 기억 유무 점검 단계
def memory_check_phase():
    st.info("🧠 **기억 유무 점검 단계**: 이전 답변을 기억하시는지 확인합니다.")
    
    # 저장된 답변이 없는 경우
    if not st.session_state.stored_answers:
        st.warning("⚠️ 저장된 답변이 없습니다. 먼저 초기 회상 단계를 완료해주세요.")
        if st.button("초기 회상 단계로 돌아가기"):
            st.session_state.mode = 'initial_phase'
            st.rerun()
        return
    
    # 완료되지 않은 질문들 찾기
    available_questions = [idx for idx in st.session_state.stored_answers.keys() 
                          if idx not in st.session_state.completed_questions]
    
    if not available_questions:
        st.success("🎉 모든 기억 점검을 완료하셨습니다!")
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
                st.write("기억하고 계신 내용을 말씀해주세요:")
                
                current_memory = st.text_area("현재 기억하고 계신 내용:", key=f"image_memory_{current_q_idx}")
                
                if st.button("답변 제출", key="image_memory_submit"):
                    if current_memory.strip():
                        # 유사도 계산
                        similarity = calculate_similarity(original_answer, current_memory.strip())
                        
                        st.write(f"**현재 답변**: {current_memory.strip()}")
                        
                        # 유사도가 70% 이상이면 질문 재사용 가능으로 설정
                        if similarity >= 0.7:
                            st.success("✅ 기억이 잘 보존되어 있습니다! 원본 답변을 확인해보세요.")
                            st.write(f"**원본 답변**: {original_answer}")
                            st.session_state.reusable_questions.add(current_q_idx)
                            st.info("💡 이 질문은 나중에 다시 사용될 수 있습니다.")
                        else:
                            st.warning("⚠️ 기억에 차이가 있습니다. 원본 답변을 확인해보세요.")
                            st.write(f"**원본 답변**: {original_answer}")
                        
                        st.session_state.completed_questions.add(current_q_idx)
                        
                        # 상태 리셋
                        st.session_state.awaiting_image_response = False
                        st.session_state.current_memory_question = None
                        st.session_state.image_generated = False
                        
                        if st.button("다음 질문으로", key="next_after_image_remember"):
                            st.rerun()
                    else:
                        st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("❌ 기억 안 나요", key="image_no_remember"):
                st.write("💭 기억이 나지 않으시는군요. 원본 답변을 확인해보세요.")
                st.write(f"**원본 답변**: {original_answer}")
                
                # 질문 완료 처리 (삭제)
                st.session_state.completed_questions.add(current_q_idx)
                st.info("이 질문은 완료되었습니다.")
                
                # 상태 리셋
                st.session_state.awaiting_image_response = False
                st.session_state.current_memory_question = None
                st.session_state.image_generated = False
                
                if st.button("다음 질문으로", key="next_after_image_no_remember"):
                    st.rerun()
        
        return
    
    # 기억 응답을 기다리는 상태가 아닌 경우, 새로운 질문 제시
    if not st.session_state.awaiting_memory_response:
        # 첫 번째 사용 가능한 질문 선택
        current_q_idx = available_questions[0]
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
                # 이미지 생성 단계 (현재는 플레이스홀더)
                st.write("💡 **이미지 생성 중...**")
                # original_answer = st.session_state.stored_answers[current_q_idx]["answer"]
                # st.write(f"**과거 답변**: {original_answer}")
                st.image("https://via.placeholder.com/400x300.png?text=Memory+Image", 
                        caption="생성된 기억 이미지 (GPT-4o API 연동 예정)")
                
                # # 질문 완료 처리
                # st.session_state.completed_questions.add(current_q_idx)
                # st.success("🖼️ 이미지가 생성되었습니다. 이 질문은 완료되었습니다.")
                
                # if st.button("다음 질문으로"):
                #     st.rerun()

                st.session_state.awaiting_image_response = True
                st.session_state.image_generated = True
                st.rerun()
    
    # 기억한다고 답변한 경우, 상세 답변 요청
    else:
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
                    
                    # st.write(f"**원본 답변**: {original_answer}")
                    st.write(f"**현재 답변**: {current_memory.strip()}")
                    # st.write(f"**유사도**: {similarity:.2%}")
                    
                    # 유사도가 70% 이상이면 질문 폐기
                    if similarity >= 0.7:
                        st.success("✅ 기억이 잘 보존되어 있습니다! 이 질문은 완료됩니다.")
                        st.write(f"**원본 답변**: {original_answer}")
                        st.session_state.completed_questions.add(current_q_idx)
                        st.info("💡 이 질문은 나중에 다시 사용될 수 있습니다.")
                    else:
                        st.warning("⚠️ 기억에 차이가 있습니다. 이미지를 생성합니다.")
                        st.image("https://via.placeholder.com/400x300.png?text=Memory+Enhancement+Image", 
                                caption="기억 보강을 위한 생성 이미지")
                        st.write(f"**원본 답변**: {original_answer}")
                    
                    st.session_state.completed_questions.add(current_q_idx)
                    
                    # 상태 리셋
                    st.session_state.awaiting_memory_response = False
                    st.session_state.current_memory_question = None
                    
                    if st.button("다음 질문으로"):
                        st.rerun()
                else:
                    st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("취소"):
                st.session_state.awaiting_memory_response = False
                st.session_state.current_memory_question = None
                st.rerun()

# 메인 실행 함수
def main():
    init_session_state()
    
    # 사이드바에 현재 상태 표시
    with st.sidebar:
        st.header("📊 현재 상태")
        st.write(f"**단계**: {st.session_state.mode}")
        st.write(f"**저장된 답변 수**: {len(st.session_state.stored_answers)}")
        st.write(f"**완료된 질문 수**: {len(st.session_state.completed_questions)}")
        st.write(f"**재사용 가능 질문 수**: {len(st.session_state.reusable_questions)}")
        st.write(f"**오늘 답변한 질문**: {st.session_state.daily_question_count}")
        
        st.divider()
        
        # 단계 전환 버튼
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