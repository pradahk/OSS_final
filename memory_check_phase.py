import streamlit as st
from datetime import date
import random
from utils.memory_check import MemoryChecker
from utils.image_generation import ImageGenerator
from utils.constants import MAX_DAILY_MEMORY_CHECKS, SIMILARITY_THRESHOLD
import database

class MemoryCheckPhase:
    """기억 점검 단계를 처리하는 클래스"""
    
    def __init__(self, user_id: int, db_ops):
        self.user_id = user_id
        self.db_ops = db_ops
        self.memory_checker = MemoryChecker()
        self.image_generator = ImageGenerator()
    
    def render(self):
        """기억 점검 단계 메인 렌더링"""
        st.info(f"🧠 **기억 유무 점검 단계**: 하루에 새로운 질문 1개와 기억 점검 {MAX_DAILY_MEMORY_CHECKS}개를 진행합니다.")
        
        # 결과 메시지가 있으면 먼저 표시
        if st.session_state.get('show_result', False):
            self._show_result_message()
            return
        
        # 진행 중인 기억 점검이 있는지 확인
        has_pending = self.db_ops.has_pending_memory_check(self.user_id)
        
        # 오늘 활동 현황 확인 (완료된 것만)
        new_answers_today, memory_checks_today = self.db_ops.get_today_activity_count(self.user_id)
        
        # 진행 중인 기억 점검이 있으면 그것을 먼저 처리
        if has_pending:
            self._handle_pending_memory_check()
            return
        
        # 오늘의 할당량 확인
        if new_answers_today >= 1 and memory_checks_today >= MAX_DAILY_MEMORY_CHECKS:
            st.success("✅ 오늘의 모든 활동을 완료하셨습니다! 내일 다시 만나요.")
            return
        
        # 먼저 새로운 질문을 처리
        if new_answers_today < 1:
            self._handle_new_question()
        elif memory_checks_today < MAX_DAILY_MEMORY_CHECKS:
            self._handle_memory_check()
    
    def _handle_pending_memory_check(self):
        """진행 중인 기억 점검 처리"""
        st.subheader("🧠 진행 중인 기억 점검")
        st.info("현재 진행 중인 기억 점검을 완료해주세요.")
        
        # 진행 중인 기억 점검 정보 가져오기
        pending_check = self._get_pending_memory_check()
        if not pending_check:
            st.error("진행 중인 기억 점검 정보를 찾을 수 없습니다.")
            return
        
        check_id, question_id, original_answer_id = pending_check
        
        # 원본 답변과 질문 정보 가져오기
        original_info = self._get_original_answer_info(question_id, original_answer_id)
        if not original_info:
            st.error("원본 답변 정보를 찾을 수 없습니다.")
            return
        
        question_text, answer_text = original_info
        
        # 세션 상태 설정
        st.session_state.current_memory_question = (question_id, answer_text, question_text)
        st.session_state.current_check_id = check_id
        st.session_state.awaiting_image_response = True
        
        # 이미지 응답 처리
        self._handle_image_response()
    
    def _get_pending_memory_check(self):
        """진행 중인 기억 점검 정보 가져오기"""
        today_str = date.today().strftime('%Y-%m-%d')
        
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT check_id, question_id, original_answer_id
            FROM MEMORY_CHECKS 
            WHERE user_id = ? AND check_date = ? 
            AND result IN ('requires_image', 'pending')
            ORDER BY created_at DESC LIMIT 1
        """, (self.user_id, today_str))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def _get_original_answer_info(self, question_id, original_answer_id):
        """원본 답변 정보 가져오기"""
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT q.question_text, ua.answer_text
            FROM QUESTIONS q
            JOIN USER_ANSWERS ua ON q.question_id = ua.question_id
            WHERE q.question_id = ? AND ua.answer_id = ?
        """, (question_id, original_answer_id))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def _handle_new_question(self):
        """새로운 질문 처리"""
        # context를 추가하여 key 중복 방지
        from components.initial_phase import render_initial_phase
        render_initial_phase(self.user_id, self.db_ops, context="memory_check")
    
    def _handle_memory_check(self):
        """기억 점검 처리"""
        st.subheader("🧠 오늘의 기억 점검")
        
        # 기억 점검 로직 실행
        if st.session_state.get('awaiting_image_response', False):
            self._handle_image_response()
        elif st.session_state.get('awaiting_memory_response', False):
            self._handle_memory_response()
        else:
            self._start_memory_check()
    
    def _start_memory_check(self):
        """기억 점검 시작"""
        # 사용 가능한 질문들 가져오기
        available_questions = self._get_available_questions()
        
        if not available_questions:
            st.success("🎉 모든 기억 점검을 완료하셨습니다!")
            return
        
        # 질문 선택
        current_answer = self._select_question(available_questions)
        if not current_answer:
            return
        
        question_id, answer_text, answer_date, question_text = current_answer
        st.session_state.current_memory_question = (question_id, answer_text, question_text)
        
        st.write(f"**{question_text}**")
        st.write("이 질문을 기억하시나요?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 기억해요", type="primary"):
                st.session_state.awaiting_memory_response = True
                st.rerun()
        
        with col2:
            if st.button("❌ 기억 안 나요"):
                # check_id를 미리 생성
                check_id = self._create_initial_memory_check(question_id)
                if check_id:
                    st.session_state.current_check_id = check_id
                    st.session_state.image_generated = True
                    st.session_state.awaiting_image_response = True
                    st.rerun()
                else:
                    st.error("기억 확인 정보를 생성할 수 없습니다.")
    
    def _get_available_questions(self):
        """사용 가능한 질문들 가져오기"""
        # DB에서 사용자 답변 가져오기
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ua.question_id, ua.answer_text, ua.answer_date, q.question_text
            FROM USER_ANSWERS ua
            JOIN QUESTIONS q ON ua.question_id = q.question_id
            WHERE ua.user_id = ? AND ua.is_initial_answer = 1
            ORDER BY ua.answer_date
        """, (self.user_id,))
        user_answers = cursor.fetchall()
        conn.close()
        
        completed_questions = self.db_ops.get_completed_questions(self.user_id)
        reusable_questions = self.db_ops.get_reusable_questions(self.user_id)
        
        # 점검 가능한 질문들 필터링
        available = []
        for answer in user_answers:
            question_id = answer[0]
            if question_id not in completed_questions or question_id in reusable_questions:
                available.append(answer)
        
        return available
    
    def _select_question(self, available_questions):
        """질문 선택 (재사용 가능한 질문 우선)"""
        completed_questions = self.db_ops.get_completed_questions(self.user_id)
        reusable_questions = self.db_ops.get_reusable_questions(self.user_id)
        
        reusable_available = [ans for ans in available_questions if ans[0] in reusable_questions]
        new_questions = [ans for ans in available_questions 
                        if ans[0] not in completed_questions and ans[0] not in reusable_questions]
        
        if reusable_available:
            return random.choice(reusable_available)
        elif new_questions:
            return new_questions[0]
        else:
            return None
    
    def _handle_memory_response(self):
        """기억 응답 처리"""
        question_id, original_answer, question_text = st.session_state.current_memory_question
        
        st.subheader("📝 기억 내용 확인")
        st.write(f"**{question_text}**")
        st.write("기억하고 계신 내용을 말씀해주세요:")
        
        # 고유한 key 사용
        current_memory = st.text_area(
            "현재 기억하고 계신 내용:", 
            key=f"memory_check_{question_id}_{st.session_state.get('memory_check_counter', 0)}"
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("답변 제출", type="primary", key=f"memory_submit_{question_id}"):
                if current_memory.strip():
                    self._process_memory_response(question_id, original_answer, current_memory.strip())
                else:
                    st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("취소", key=f"memory_cancel_{question_id}"):
                self._reset_state()
                st.rerun()
    
    def _process_memory_response(self, question_id, original_answer, current_memory):
        """기억 응답 처리"""
        # 유사도 계산
        is_passed, similarity, keyword_info = self.memory_checker.verify_memory(original_answer, current_memory)
        
        # 원본 답변 ID 찾기
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT answer_id FROM USER_ANSWERS 
            WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
        """, (self.user_id, question_id))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            st.error("원본 답변을 찾을 수 없습니다.")
            return
        
        original_answer_id = result[0]
        
        if is_passed:
            # 기억이 잘 보존된 경우
            self._handle_memory_success(question_id, original_answer_id, original_answer, 
                                      current_memory, similarity, keyword_info)
        else:
            # 기억이 틀린 경우 - 이미지 생성 단계로
            check_id = self._create_memory_check_record(question_id, original_answer_id, 
                                                       current_memory, similarity, keyword_info)
            st.session_state.current_check_id = check_id
            st.session_state.image_generated = True
            st.session_state.awaiting_image_response = True
            st.session_state.awaiting_memory_response = False
            st.warning("⚠️ 기억에 차이가 있습니다. 이미지를 생성하여 도움을 드리겠습니다.")
            st.rerun()
    
    def _handle_memory_success(self, question_id, original_answer_id, original_answer, 
                              current_memory, similarity, keyword_info=None):
        """기억 성공 처리"""
        # 키워드 정보 준비
        extracted_keywords = []
        if keyword_info:
            extracted_keywords = keyword_info.get('current_keywords', [])

        # DB에 저장
        database.add_memory_check(
            user_id=self.user_id,
            question_id=question_id,
            original_answer_id=original_answer_id,
            memory_status='remembered',
            current_memory_text=current_memory,
            similarity_score=similarity,
            extracted_keywords_status='satisfied',
            result='passed',
            check_type='manual_check',
            extracted_keywords = extracted_keywords,
            check_date=date.today().strftime('%Y-%m-%d')
        )
        
        # 결과 메시지 설정
        result_msg = f"**현재 답변**: {current_memory}\n\n"
        result_msg += f"**원본 답변**: {original_answer}\n\n"
        result_msg += "✅ 기억이 잘 보존되어 있습니다!\n"
        result_msg += "💡 이 질문은 나중에 다시 사용될 수 있습니다."
        
        st.session_state.result_message = result_msg
        st.session_state.result_type = 'success'
        st.session_state.show_result = True
        self._reset_state()
        st.rerun()
    
    def _create_memory_check_record(self, question_id, original_answer_id, current_memory, similarity):
        """기억 확인 레코드 생성"""
        return database.add_memory_check(
            user_id=self.user_id,
            question_id=question_id,
            original_answer_id=original_answer_id,
            memory_status='forgotten',
            current_memory_text=current_memory,
            similarity_score=similarity,
            extracted_keywords_status='manual',
            result='requires_image',
            check_type='manual_check',
            extracted_keywords='[]',
            check_date=date.today().strftime('%Y-%m-%d')
        )
    
    def _handle_image_response(self):
        """이미지 응답 처리"""
        # current_memory_question 확인
        if not st.session_state.get('current_memory_question'):
            st.error("❌ 질문 정보를 찾을 수 없습니다.")
            self._reset_state()
            st.rerun()
            return
        
        question_id, original_answer, question_text = st.session_state.current_memory_question
        
        st.subheader("🖼️ 기억 도움 이미지")
        st.write(f"**{question_text}**")
        
        # check_id 확인 및 복구 시도
        check_id = st.session_state.get('current_check_id')
        
        if not check_id:
            # check_id가 없으면 DB에서 찾거나 새로 생성
            check_id = self._find_or_create_check_id(question_id)
            
            if check_id:
                st.session_state.current_check_id = check_id
            else:
                st.error("❌ 기억 확인 정보를 찾을 수 없습니다.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("다시 시작", type="primary"):
                        self._reset_state()
                        st.rerun()
                return
        
        # 이미지 표시
        self._display_image(check_id, original_answer)
        
        st.write("---")
        st.write("🤔 **이미지를 보시고 기억이 나시나요?**")
        
        # 이미지 기억 입력 처리
        if st.session_state.get('awaiting_image_memory_input', False):
            self._handle_image_memory_input(question_id, original_answer, check_id)
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 이미지를 보니 기억해요", type="primary", key=f"remember_yes_{check_id}"):
                    st.session_state.awaiting_image_memory_input = True
                    st.rerun()
            
            with col2:
                if st.button("❌ 이미지를 봐도 기억 안 나요", key=f"remember_no_{check_id}"):
                    self._handle_complete_failure(question_id, original_answer, check_id)
    
    def _display_image(self, check_id, original_answer):
        """이미지 표시"""
        # 이미 생성된 이미지가 있는지 확인
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT image_url FROM GENERATED_IMAGES 
            WHERE memory_check_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (check_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            st.image(result[0], caption="생성된 기억 도움 이미지")
        else:
            # 새로운 이미지 생성
            with st.spinner("🎨 기억을 도울 이미지를 생성하고 있습니다..."):
                keywords = self.image_generator.extract_keywords(original_answer)
                
                if keywords:
                    database.update_memory_check_keywords(check_id, keywords, 'auto_extracted')
                    
                    image_url = self.image_generator.generate_image(keywords)
                    
                    if image_url:
                        database.add_generated_image(check_id, image_url)
                        st.image(image_url, caption="생성된 기억 도움 이미지")
                        st.success("✅ 이미지가 성공적으로 생성되었습니다!")
                    else:
                        st.error("❌ 이미지 생성에 실패했습니다.")
                else:
                    st.warning("⚠️ 키워드를 추출할 수 없어서 기본 이미지를 생성합니다.")
    
    def _handle_image_memory_input(self, question_id, original_answer, check_id):
        """이미지를 보고 기억한다고 한 경우의 입력 처리"""
        st.write("---")
        st.write("😊 **좋습니다! 기억하고 계신 내용을 말씀해주세요:**")
        st.write("💡 정확한 답변을 해주시면 이 질문을 나중에 다시 사용할 수 있습니다.")
        
        # 고유한 key 사용
        current_memory = st.text_area(
            "현재 기억하고 계신 내용:", 
            key=f"image_memory_{question_id}_{check_id}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("답변 제출", type="primary", key=f"image_submit_{check_id}"):
                if current_memory.strip():
                    self._verify_image_memory(question_id, original_answer, 
                                            current_memory.strip(), check_id)
                else:
                    st.warning("⚠️ 기억하고 계신 내용을 입력해주세요.")
        
        with col2:
            if st.button("취소", key=f"image_cancel_{check_id}"):
                # 취소 시 이전 상태로 돌아가기
                st.session_state.awaiting_image_memory_input = False
                st.rerun()
    
    def _verify_image_memory(self, question_id, original_answer, current_memory, check_id):
        """이미지 도움을 받은 기억 검증"""
        is_passed, similarity, keyword_info = self.memory_checker.verify_memory(original_answer, current_memory)
        
        if is_passed:
            # 답변이 일치하는 경우 - 재사용 질문으로 등록
            result_msg = "✅ **기억 검증 성공**\n\n"
            result_msg += f"**현재 답변**: {current_memory}\n\n"
            result_msg += f"**원본 답변**: {original_answer}\n\n"
            #result_msg += f"**유사도**: {similarity:.1%}\n\n"
            result_msg += "🔄 **이 질문은 재사용 가능한 질문으로 등록되었습니다.**\n"
            result_msg += "나중에 다시 기억을 점검할 때 사용될 수 있습니다."
            
            memory_status = 'remembered'
            result = 'passed'  # 재사용 가능한 질문으로 표시
            result_type = 'success'
            
        else:
            # 답변이 일치하지 않는 경우 - 정답 표시 후 질문 폐기
            result_msg = "❌ **기억 검증 실패**\n\n"
            result_msg += f"**입력하신 답변**: {current_memory}\n\n"
            result_msg += f"**정답**: {original_answer}\n\n"
            result_msg += "🗑️ **이 질문은 더 이상 사용되지 않습니다.**\n"
            result_msg += "다른 기억들에 집중하며 계속 노력해보세요!"
            
            memory_status = 'forgotten'
            result = 'failed_verification'  # 질문 폐기 표시
            result_type = 'warning'
        
        # DB 업데이트
        self._update_memory_check(check_id, memory_status, current_memory, similarity, result)
        
        # 상태 설정 후 결과 표시
        self._reset_state()  # 먼저 상태 리셋
        st.session_state.result_message = result_msg
        st.session_state.result_type = result_type
        st.session_state.show_result = True
        st.rerun()
        
    def _handle_complete_failure(self, question_id, original_answer, check_id):
        """완전히 기억하지 못한 경우 처리"""
        result_msg = "💭 **최종 기억 확인 실패**\n\n"
        result_msg += f"**정답**: {original_answer}\n\n"
        result_msg += "🗑️ **이 질문은 더 이상 사용되지 않습니다.**\n\n"
        result_msg += "🌟 다른 기억들을 소중히 간직하며 계속 노력해보세요!"
        
        # DB 업데이트
        self._update_memory_check(check_id, 'forgotten', '', 0.0, 'complete_failure')
        
        # 상태 설정 후 결과 표시
        self._reset_state()  # 먼저 상태 리셋
        st.session_state.result_message = result_msg
        st.session_state.result_type = 'info'
        st.session_state.show_result = True
        st.rerun()
    
    def _update_memory_check(self, check_id, memory_status, current_memory_text, 
                            similarity_score, result):
        """기억 확인 결과 업데이트"""
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE MEMORY_CHECKS 
            SET memory_status = ?, current_memory_text = ?, 
                similarity_score = ?, result = ?
            WHERE check_id = ?
        """, (memory_status, current_memory_text, similarity_score, result, check_id))
        conn.commit()
        conn.close()
    
    def _show_result_message(self):
        """결과 메시지 표시"""
        result_type = st.session_state.get('result_type', 'info')
        result_message = st.session_state.get('result_message', '')
        
        if result_type == 'success':
            st.success(result_message)
        elif result_type == 'warning':
            st.warning(result_message)
        else:
            st.info(result_message)
        
        if st.button("완료", type="primary", key="result_complete"):
            # 결과 상태 완전히 클리어
            st.session_state.show_result = False
            st.session_state.result_message = ""
            st.session_state.result_type = ""
            st.rerun()
    
    def _reset_state(self):
        """세션 상태 리셋"""
        st.session_state.awaiting_image_response = False
        st.session_state.awaiting_image_memory_input = False
        st.session_state.awaiting_memory_response = False
        st.session_state.current_memory_question = None
        st.session_state.image_generated = False
        st.session_state.current_check_id = None

    def _create_initial_memory_check(self, question_id):
        """초기 기억 확인 레코드 생성"""
        # 원본 답변 ID 찾기
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT answer_id FROM USER_ANSWERS 
            WHERE user_id = ? AND question_id = ? AND is_initial_answer = 1
        """, (self.user_id, question_id))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            original_answer_id = result[0]
            # 임시 레코드 생성
            check_id = database.add_memory_check(
                user_id=self.user_id,
                question_id=question_id,
                original_answer_id=original_answer_id,
                memory_status='forgotten',
                current_memory_text='',
                similarity_score=0.0,
                extracted_keywords_status='pending',
                result='requires_image',
                check_type='manual_check',
                extracted_keywords='[]',
                check_date=date.today().strftime('%Y-%m-%d')
            )
            return check_id
        return None
    
    def _find_or_create_check_id(self, question_id):
        """기존 check_id 찾기 또는 새로 생성"""
        # 오늘 날짜의 해당 질문에 대한 기록 찾기
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT check_id FROM MEMORY_CHECKS 
            WHERE user_id = ? AND question_id = ? 
            AND check_date = ? AND result = 'requires_image'
            ORDER BY created_at DESC LIMIT 1
        """, (self.user_id, question_id, date.today().strftime('%Y-%m-%d')))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            # 없으면 새로 생성
            return self._create_initial_memory_check(question_id)