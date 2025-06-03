import streamlit as st
from datetime import date, timedelta
import json
from difflib import SequenceMatcher

st.header("💬 기억 회상 및 점검 챗봇")

if 'user_info' not in st.session_state or not st.session_state.user_info:
    st.warning("먼저 진단서를 업로드하여 사용자 정보를 등록해주세요.")
    st.stop()


# 진단일 기준
diagnosis_date = st.session_state.user_info.get("진단일", None)
today = date.today()

# 1개월 이내 여부 판단
if diagnosis_date and (today - diagnosis_date).days <= 30:
    num_questions_today = 2
    st.info("🔄 초기 회상 단계입니다. 하루에 2개 질문을 드립니다.")
else:
    num_questions_today = 1
    st.info("🧠 기억 유무 점검 단계입니다. 하루에 1개의 새로운 질문을 드립니다.\n"
            "또한, 예전에 답변하셨던 추억을 체크합니다.")
    st.session_state.phase = 'memory_check'