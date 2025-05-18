# 
import streamlit as st

st.header("💬 2단계: 질문 응답 채팅")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.warning("먼저 진단서를 업로드하여 사용자 정보를 등록해주세요.")
    st.stop()

# 질문 리스트
questions = [
    "젊었을 때 자주 가셨던 장소가 기억나시나요?",
    "자주 입던 옷이나 색깔이 떠오르시나요?",
    "주말이나 명절에 하던 가족 활동이 기억나시나요?"
]

# 상태 초기화
if 'q_index' not in st.session_state:
    st.session_state.q_index = 0

if 'answers' not in st.session_state:
    st.session_state.answers = {}

# 질문 표시
if st.session_state.q_index < len(questions):
    q_num = st.session_state.q_index
    question = questions[q_num]

    st.subheader(f"질문 {q_num + 1}")
    st.write(question)

    # 이전에 입력한 답변이 있으면 기본값으로 보여줌
    default_answer = st.session_state.answers.get(q_num, "")
    answer = st.text_area("당신의 답변을 입력해주세요:", value=default_answer, key=f"answer_{q_num}")

    if st.button("답변 제출", key=f"submit_{q_num}"):
        if answer.strip():
            st.session_state.answers[q_num] = answer.strip()
            st.success("답변이 저장되었습니다.")
            st.session_state.q_index += 1
        else:
            st.warning("답변을 입력해주세요.")
else:
    st.success("모든 질문에 답변하셨습니다. 감사합니다!")
    st.write("👇 당신의 전체 답변 기록")
    for idx, ans in st.session_state.answers.items():
        st.markdown(f"**질문 {idx + 1}:** {questions[idx]}")
        st.markdown(f"- 답변: {ans}")
