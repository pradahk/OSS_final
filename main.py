# main.py
import streamlit as st

st.set_page_config(page_title="치매 증상 지연 서비스", layout="wide")

st.title("🧠 치매 초기 환자를 위한 증상 지연 서비스")

st.markdown("""
### 📌 사용 방법
1. 왼쪽 사이드바에서 원하는 페이지를 선택하세요.
2. 진단서를 먼저 업로드하여 사용자 정보를 등록합니다.
3. 이후 채팅 페이지에서 질문에 답변하며 회상 훈련을 시작합니다.

---
""")

st.info("왼쪽의 사이드바에서 페이지를 선택해 주세요.")
