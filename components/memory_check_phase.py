import streamlit as st
from datetime import date
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import database
from utils.constants import (
    MAX_DAILY_MEMORY_CHECKS,
    KEYWORD_MATCH_THRESHOLD,
    CHECK_STEP_INITIAL_RECALL,
    CHECK_STEP_POST_HINT_RECALL,
    CHECK_RESULT_PASS,
    CHECK_RESULT_FAIL,
    USER_CHOICE_REMEMBERS,
    USER_CHOICE_FORGETS,
    QUESTION_STATUS_ARCHIVED
)
from utils.memory_check import MemoryChecker
from utils.image_generation import ImageGenerator
import json

class MemoryCheckPhase:
    """기억 점검 단계를 처리하는 클래스"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.memory_checker = MemoryChecker()
        self.image_generator = ImageGenerator()
        self.today_str = date.today().strftime('%Y-%m-%d')
    
    def render(self):
        """기억 점검 단계 메인 렌더링"""
        st.info(f"🧠 **기억 점검 단계**: 하루에 {MAX_DAILY_MEMORY_CHECKS}개의 기억 점검을 진행합니다.")
        
        # 오늘 완료된 기억 점검 수 확인
        _, memory_checks_today = database.get_today_activity_count(self.user_id)
        
        if memory_checks_today >= MAX_DAILY_MEMORY_CHECKS:
            st.success("✅ 오늘의 모든 기억 점검을 완료하셨습니다! 내일 다시 만나요.")
            st.balloons()
            return
        
        # 진행 중인 기억 점검이 있는지 세션 상태로만 확인
        if self._has_pending_memory_check():
            self._handle_pending_check()
            return
        
        # 새로운 기억 점검 시작
        self._start_new_memory_check(memory_checks_today)
    
    def _has_pending_memory_check(self):
        """세션 상태에서 진행 중인 기억 점검이 있는지 확인"""
        return st.session_state.get('current_memory_check') is not None
    
    def _start_new_memory_check(self, memory_checks_today):
        """새로운 기억 점검 시작"""
        # 재질문할 질문 가져오기 (가장 오래된 것)
        questions_to_revisit = database.get_questions_to_revisit(self.user_id)
        
        if not questions_to_revisit:
            st.info("📝 현재 점검할 수 있는 기억이 없습니다. 더 많은 질문에 답변해주세요.")
            return
        
        # 첫 번째 질문 선택
        question = questions_to_revisit[0]
        question_id = question['question_id']
        question_text = question['question_text']
        
        # 원본 답변 정보 가져오기
        original_answer_info = database.get_initial_answer_with_keywords(self.user_id, question_id)
        if not original_answer_info:
            st.error("원본 답변 정보를 찾을 수 없습니다.")
            return
        
        original_answer_id = original_answer_info['answer_id']
        original_answer_text = original_answer_info['answer_text']
        original_keywords = original_answer_info['keywords']
        
        st.subheader(f"🤔 기억 점검 (남은 점검: {MAX_DAILY_MEMORY_CHECKS - memory_checks_today}개)")
        st.markdown("---")
        
        # 재질문 표시
        st.markdown(f"### 📝 이전에 질문했던 내용을 기억하시나요?")
        st.markdown(f"**Q. {question_text}**")
        
        st.markdown("---")
        st.write("🤔 **이 질문을 기억하시나요?**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 기억해요", type="primary", key=f"remember_{question_id}"):
                self._handle_remembers_choice(question_id, question_text, original_answer_id, 
                                             original_answer_text, original_keywords)
        
        with col2:
            if st.button("❌ 기억이 안 나요", key=f"forget_{question_id}"):
                self._handle_forgets_choice(question_id, question_text, original_answer_id, 
                                           original_answer_text, original_keywords)
    
    def _handle_remembers_choice(self, question_id, question_text, original_answer_id, 
                                original_answer_text, original_keywords):
        """사용자가 '기억한다'고 선택한 경우"""
        # 세션 상태에만 저장 (DB는 최종 완료시에만 저장)
        st.session_state.current_memory_check = {
            'question_id': question_id,
            'question_text': question_text,
            'original_answer_id': original_answer_id,
            'original_answer_text': original_answer_text,
            'original_keywords': original_keywords,
            'step': 'first_recall',
            'user_choice': USER_CHOICE_REMEMBERS
        }
        
        st.rerun()
    
    def _handle_forgets_choice(self, question_id, question_text, original_answer_id, 
                              original_answer_text, original_keywords):
        """사용자가 '기억 못한다'고 선택한 경우"""
        # 세션 상태에만 저장
        st.session_state.current_memory_check = {
            'question_id': question_id,
            'question_text': question_text,
            'original_answer_id': original_answer_id,
            'original_answer_text': original_answer_text,
            'original_keywords': original_keywords,
            'step': 'show_hint',
            'user_choice': USER_CHOICE_FORGETS
        }
        
        st.rerun()
    
    def _handle_pending_check(self):
        """진행 중인 기억 점검 처리"""
        check_info = st.session_state.current_memory_check
        step = check_info.get('step', 'first_recall')
        
        if step == 'first_recall':
            self._handle_first_recall_input(check_info)
        elif step == 'show_hint':
            self._handle_hint_display(check_info)
        elif step == 'second_recall':
            self._handle_second_recall_input(check_info)
        elif step == 'show_original':
            self._handle_show_original(check_info)
    
    def _handle_first_recall_input(self, check_info):
        """첫 번째 회상 답변 입력 처리"""
        st.subheader("💭 기억하고 계신 내용을 말씀해주세요")
        st.markdown(f"**Q. {check_info['question_text']}**")
        st.write("💡 정확한 답변을 해주시면 이 질문을 나중에 다시 사용할 수 있습니다.")
        
        recall_text = st.text_area(
            "기억하고 계신 내용을 자유롭게 적어주세요:",
            key=f"first_recall_{check_info['question_id']}",
            height=120
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("답변 제출", type="primary", key=f"submit_first_{check_info['question_id']}"):
                if recall_text.strip():
                    self._verify_first_recall(check_info, recall_text.strip())
                else:
                    st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("취소", key=f"cancel_first_{check_info['question_id']}"):
                self._cancel_memory_check()

    def _verify_first_recall(self, check_info, recall_text):
        """첫 번째 회상 답변 검증 (수정본)"""
        # MemoryChecker의 키워드 검증 함수를 올바르게 호출합니다.
        is_pass, match_count = self.memory_checker.verify_memory_by_keywords(
            check_info['original_keywords'], 
            recall_text
        )
        
        if is_pass:
            # 통과 - 질문 재사용 가능, DB에 최종 결과 저장
            # _save_memory_check_result에 '유사도' 대신 '키워드 일치 개수'를 전달합니다.
            self._save_memory_check_result(
                check_info, 
                recall_text, 
                CHECK_RESULT_PASS, 
                match_count
            )
            
            st.success("✅ 기억 검증 성공!")
            #st.info(f"매칭된 키워드: {match_count}개 (통과 기준: {self.memory_checker.keyword_threshold}개)")
            st.success("🔄 이 질문은 나중에 다시 사용될 수 있습니다.")
            
            # 기억 점검 절차를 완전히 종료합니다.
            self._complete_memory_check()
        else:
            # 실패 - 힌트 제공
            #st.warning(f"⚠️ 키워드 매칭 부족: {match_count}개 (통과 기준: {self.memory_checker.keyword_threshold}개)")
            st.info("💡 기억을 도울 이미지를 보여드릴게요.")
            
            # 다음 단계(힌트)로 넘어가기 위해 세션 상태를 업데이트합니다.
            check_info['step'] = 'show_hint'
            check_info['first_recall_text'] = recall_text
            check_info['first_match_count'] = match_count # 유사도 대신 키워드 개수를 저장
            st.session_state.current_memory_check = check_info
            st.rerun()


    def _handle_hint_display(self, check_info):
        """힌트 이미지 표시"""
        st.subheader("🖼️ 기억 도움 이미지")
        st.markdown(f"**Q. {check_info['question_text']}**")
        
        # 이미지 생성 및 표시
        if not self._display_hint_image(check_info):
            # 이미지 생성 실패 시 바로 원본 답변 표시로 이동
            check_info['step'] = 'show_original'
            st.session_state.current_memory_check = check_info
            st.rerun()
            return
        
        st.write("---")
        st.write("🤔 **이미지를 보시고 기억이 나시나요?**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 이미지를 보니 기억해요", type="primary", key=f"hint_remember_{check_info['question_id']}"):
                # 두 번째 회상으로 이동
                check_info['step'] = 'second_recall'
                st.session_state.current_memory_check = check_info
                st.rerun()
        
        with col2:
            if st.button("❌ 이미지를 봐도 기억 안 나요", key=f"hint_forget_{check_info['question_id']}"):
                # 원본 답변 표시로 이동
                check_info['step'] = 'show_original'
                st.session_state.current_memory_check = check_info
                st.rerun()
    
    def _handle_second_recall_input(self, check_info):
        """두 번째 회상 답변 입력 처리"""
        st.subheader("💭 이미지를 보고 기억하신 내용을 말씀해주세요")
        st.markdown(f"**Q. {check_info['question_text']}**")
        st.write("💡 정확한 답변을 해주시면 이 질문을 나중에 다시 사용할 수 있습니다.")
        
        recall_text = st.text_area(
            "이미지를 보고 기억하신 내용을 적어주세요:",
            key=f"second_recall_{check_info['question_id']}",
            height=120
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("답변 제출", type="primary", key=f"submit_second_{check_info['question_id']}"):
                if recall_text.strip():
                    self._verify_second_recall(check_info, recall_text.strip())
                else:
                    st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("기억이 안 나요", key=f"give_up_{check_info['question_id']}"):
                # 원본 답변 표시로 이동
                check_info['step'] = 'show_original'
                st.session_state.current_memory_check = check_info
                st.rerun()
    
    def _verify_second_recall(self, check_info, recall_text):
        """두 번째 회상 답변 검증 (수정본)"""
        # MemoryChecker의 키워드 검증 함수를 올바르게 호출하고,
        # 'original_keywords'를 인자로 전달합니다.
        is_pass, match_count = self.memory_checker.verify_memory_by_keywords(
            check_info['original_keywords'], 
            recall_text
        )
        
        if is_pass:
            # 통과 - 질문 재사용 가능
            # _save_memory_check_result에 '유사도' 대신 정확한 '키워드 일치 개수'를 전달합니다.
            self._save_memory_check_result(
                check_info, 
                recall_text, 
                CHECK_RESULT_PASS, 
                match_count,
                hint_provided=True
            )
            
            st.success("✅ 기억 검증 성공!")
            #st.info(f"매칭된 키워드: {match_count}개 (통과 기준: {self.memory_checker.keyword_threshold}개)")
            st.success("  이 질문은 나중에 다시 사용될 수 있습니다.")
            
            self._complete_memory_check()
        else:
            # 실패 - 원본 답변 표시하고 질문 폐기
            #st.warning(f"⚠️ 기억 검증 실패: 키워드 매칭 부족 ({match_count}개)")
            
            # 원본 답변 표시 단계로 이동
            check_info['step'] = 'show_original'
            check_info['second_recall_text'] = recall_text
            check_info['second_match_count'] = match_count # 유사도 대신 키워드 개수를 저장
            st.session_state.current_memory_check = check_info
            st.rerun()

    def _handle_show_original(self, check_info):
        """원본 답변 표시 및 질문 폐기"""
        st.subheader("📋 원본 답변 확인")
        st.markdown(f"**Q. {check_info['question_text']}**")
        st.write("---")
        
        st.write("💡 **이전에 답변하셨던 내용입니다:**")
        st.info(check_info['original_answer_text'])
        
        st.write("---")
        st.warning("🗑️ 이 질문은 더 이상 사용되지 않습니다.")
        st.write("다른 기억들에 집중하며 계속 노력해보세요!")
        
        # 질문 폐기 및 최종 결과 저장
        database.update_question_status(check_info['question_id'], QUESTION_STATUS_ARCHIVED)
        
        # 마지막 시도한 답변이 있으면 사용, 없으면 빈 문자열
        final_recall_text = check_info.get('second_recall_text', check_info.get('first_recall_text', ''))
        final_similarity = check_info.get('second_similarity', check_info.get('first_similarity', 0.0))
        
        self._save_memory_check_result(
            check_info, 
            final_recall_text, 
            CHECK_RESULT_FAIL, 
            final_similarity,
            hint_provided=True
        )
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("확인", type="primary", key=f"confirm_original_{check_info['question_id']}"):
                self._complete_memory_check()
    
    def _display_hint_image(self, check_info):
        """힌트 이미지 표시"""
        try:
            # 새 이미지 생성
            with st.spinner("🎨 기억을 도울 이미지를 생성하고 있습니다..."):
                keywords = check_info['original_keywords']
                
                if keywords:
                    image_url = self.image_generator.generate_image(keywords)
                    
                    if image_url:
                        st.image(image_url, caption="기억 도움 이미지")
                        st.success("✅ 이미지가 성공적으로 생성되었습니다!")
                        return True
                    else:
                        st.error("❌ 이미지 생성에 실패했습니다.")
                        return False
                else:
                    st.warning("⚠️ 키워드가 없어서 이미지를 생성할 수 없습니다.")
                    return False
        except Exception as e:
            st.error(f"이미지 처리 중 오류 발생: {e}")
            return False
    
    def _save_memory_check_result(self, check_info, recall_text, result, match_count, hint_provided=False):
        """기억 점검 결과를 DB에 저장"""
        # 회상 답변 저장
        recall_answer_id = database.add_user_answer(
            user_id=self.user_id,
            question_id=check_info['question_id'],
            answer_text=recall_text,
            answer_date=self.today_str,
            is_initial_answer=False
        )
        
        # 기억 점검 결과 저장
        database.add_memory_check(
            user_id=self.user_id,
            question_id=check_info['question_id'],
            original_answer_id=check_info['original_answer_id'],
            check_date=self.today_str,
            check_step=CHECK_STEP_POST_HINT_RECALL if hint_provided else CHECK_STEP_INITIAL_RECALL,
            check_result=result,
            recall_answer_id=recall_answer_id,
            user_choice=check_info['user_choice'],
            keyword_match_count=match_count,
            hint_provided=hint_provided
        )
    
    def _complete_memory_check(self):
        """기억 점검 완료 처리"""
        if 'current_memory_check' in st.session_state:
            del st.session_state.current_memory_check
        
        st.success("🎉 기억 점검이 완료되었습니다!")
        
        # 잠시 후 새로고침
        import time
        time.sleep(2)
        st.rerun()
    
    def _cancel_memory_check(self):
        """기억 점검 취소"""
        if 'current_memory_check' in st.session_state:
            del st.session_state.current_memory_check
        
        st.info("기억 점검이 취소되었습니다.")
        st.rerun()


def render_memory_check_phase(user_id: int):
    """기억 점검 단계 렌더링 함수"""
    memory_checker = MemoryCheckPhase(user_id)
    memory_checker.render()
