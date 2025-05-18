import streamlit as st
from datetime import date, timedelta

st.header("💬 질문 응답")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.warning("먼저 진단서를 업로드하여 사용자 정보를 등록해주세요.")
    st.stop()

questions = [
    "젊었을 때 자주 가셨던 장소가 기억나시나요?",
    "자주 입던 옷이나 색깔이 떠오르시나요?",
    "주말이나 명절에 하던 가족 활동이 기억나시나요?",
    "늘 다니시던 산책길이 떠오르시나요?",
    "가족과의 추억 중 가장 소중한 순간은 언제였나요?",
    "자주 사용하시던 물건이 기억나시나요?",
    "명절에 입던 옷이나 하시던 음식이 떠오르시나요?",
    "젊은 시절 친구들과의 장소가 떠오르시나요?"
]

# 상태 변수 초기화
if 'q_index' not in st.session_state:
    st.session_state.q_index = 0
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'phase' not in st.session_state:
    st.session_state.phase = 'input'  # 'input' 또는 'memory_check'

# 진단일 기준
diagnosis_date = st.session_state.user_info.get("진단일", None)
today = date.today()

# 1개월 이내 여부 판단
if diagnosis_date and (today - diagnosis_date).days <= 30:
    num_questions_today = 2
    st.info("🔄 초기 회상 단계입니다. 하루에 2개 질문을 드립니다.")
else:
    num_questions_today = 1
    st.info("🧠 기억 유무 점검 단계입니다. 하루에 1개 질문을 드립니다.")
    st.session_state.phase = 'memory_check'

# 현재 질문
q_num = st.session_state.q_index
if q_num >= len(questions):
    st.success("모든 질문을 완료하셨습니다.")
    st.stop()

question = questions[q_num]
st.subheader(f"질문 {q_num + 1}")
st.write(question)

# 회상 단계 vs 기억 점검 단계
if st.session_state.phase == 'input':
    answer = st.text_area("당신의 답변을 입력해주세요:", key=f"answer_{q_num}")
    if st.button("답변 제출"):
        if answer.strip():
            st.session_state.answers[q_num] = {
                "answer": answer.strip(),
                "date": today
            }
            st.session_state.q_index += 1
            if st.session_state.q_index % num_questions_today == 0:
                st.success("오늘의 질문이 끝났습니다. 내일 다시 만나요!")
                st.stop()
            else:
                st.rerun()
        else:
            st.warning("답변을 입력해주세요.")
else:  # memory_check 단계
    if q_num not in st.session_state.answers:
        st.warning("이 질문에 대한 과거 답변이 없어 회상이 불가합니다.")
        st.stop()

    st.write("🧠 이 질문을 기억하시나요?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 기억나요"):
            st.session_state.q_index += 1
            st.rerun()
    with col2:
        if st.button("❌ 기억 안 나요"):
            st.write("💡 예전 답변을 기반으로 이미지를 생성합니다...")
            st.write(f"과거 답변: {st.session_state.answers[q_num]['answer']}")
            # 👉 GPT4o or DALL·E 호출해서 이미지 생성 코드 연결 위치
            st.image("https://via.placeholder.com/300x200.png?text=기억+이미지", caption="생성된 기억 이미지")
            # 재질문 여부 판단 로직은 여기 추가
