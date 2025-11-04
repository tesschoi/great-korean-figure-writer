# app.py
# 중학교 1학년 영어 작문 보조 웹앱 (Gemini API 기반, 최종 버전)

import streamlit as st
import os
from google import genai
from google.genai import types
import urllib.parse 
import json # <--- JSON 처리를 위해 라이브러리 추가
# import base64 # 사진 첨부 기능 제거로 인해 삭제
# import io # 사진 첨부 기능 제거로 인해 삭제
import re # 최종 검증을 위한 정규식 라이브러리 추가

# --- 1. 앱 설정 및 CSS 스타일링 (폰트, 제목 등) ---
def setup_page():
    # Noto Sans KR (깔끔한 폰트) 및 Nanum Myeongjo (명조체) 폰트 적용을 위한 CSS
    st.markdown(
        """
        <style>
        @import url('https://fonts.com/css2?family=Nanum+Myeongjo:wght@400;700&family=Noto+Sans+KR:wght@400;700&display=swap');
        
        /* 1. 전체 UI (제목, 버튼, 안내 등)는 가독성 좋은 Noto Sans KR (고딕체) 적용 */
        .stApp, .stMarkdown, h1, h2, h3, h4, .stButton, .stTextInput, .stFileUploader {
            font-family: 'Noto Sans KR', sans-serif !important;
        }

        /* 2. 학생의 작성/번역 결과/피드백 내용 (컨텐츠 영역)만 Nanum Myeongjo (명조체) 적용 */
        /* 텍스트 입력 영역 (작성란) - 명조체 */
        .stTextArea textarea {
            font-family: 'Nanum Myeongjo', serif !important;
            font-size: 1.1em;
            line-height: 1.6;
        }
        
        /* 제목 스타일 (Noto Sans KR 유지) */
        h1 {
            color: #1E88E5; /* 산뜻한 파란색 */
            text-align: center;
        }

        /* 피드백 박스 스타일 (명조체 적용) */
        .feedback-box {
            font-family: 'Nanum Myeongjo', serif !important; /* 명조체 강제 적용 */
            background-color: #E3F2FD; 
            border-left: 5px solid #1E88E5;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 1.05em;
            white-space: pre-wrap; /* 피드백 내용 줄바꿈 유지 */
        }
        
        /* 번역 결과 박스 스타일 추가 (명조체 적용) */
        .translation-box {
            font-family: 'Nanum Myeongjo', serif !important; /* 명조체 강제 적용 */
            background-color: #f0fdf4; /* 연한 초록색 배경 */
            border: 2px solid #16a34a; /* 진한 초록색 테두리 */
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 1.1em;
            color: #16a34a;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title("🇰🇷 Great Korean Figure Writer 🖊️")
    st.subheader("나만의 한국 위인 소개글 작성 및 AI 피드백 (중학교 1학년)")

# --- 2. Gemini API를 이용한 피드백 요청 함수 ---
def get_ai_feedback(student_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ 오류: Gemini API 키가 환경 변수(GEMINI_API_KEY)에 설정되지 않았습니다.")
        return None
    
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Gemini Client 초기화 오류: {e}")
        return None
    
    # 현재 문장 수를 계산하여 조건 충족 여부 확인에 사용
    sentence_count = len([s for s in student_text.split('.') if s.strip()])
    
    # 중학교 1학년 수준에 맞춘 AI 제약 조건 추가 (관계대명사, 어려운 어휘 금지)
    restriction_notes = (
        "학생은 중학교 1학년이므로, 제안하는 수정 문장이나 개선 조언 시 절대 **관계대명사(who, which, that)**를 사용하지 마세요. "
        "또한, 어휘 수준을 **중학교 1학년**에게 맞춰 주세요. 'legendary', 'remarkable'과 같은 어려운 단어 대신 'great', 'famous', 'important'와 같은 기본 어휘를 사용하도록 조언하고 수정하세요."
    )
    
    system_prompt = f"""
    당신은 중학교 1학년 학생의 영어 작문 보조 AI 튜터입니다.
    {restriction_notes}
    
    학생이 작성한 '한국의 위인 소개글'에 대해 아래 3가지 단계로 피드백을 제공하세요.
    학생의 글: "{student_text}"
    
    ---
    **1. 조건 충족 확인 (⭐):**
    제시된 4가지 필수 정보 및 3가지 Key Expression 사용 여부를 *각각* 확인하고 O/X로 판단하세요.
    - 직업/신분/역할 포함 여부: (O/X)
    - 업적 1개 이상 포함 여부: (O/X)
    - 훌륭한 이유 포함 여부: (O/X)
    - 위인 모습 묘사 포함 여부: (O/X)
    - to부정사(목적/의도) 사용 여부: (O/X)
    - because 사용 여부: (O/X)
    - look 사용(외양 묘사) 여부: (O/X)
    - 7문장 이상 여부 (현재 {sentence_count} 문장): (O/X) 
    
    **2. 유창성 및 오류 수정 (✅):**
    문법(어법), 어휘, 철자, 대소문자, 문장 부호 오류를 찾아 수정된 완벽한 문장만 제시하세요. 
    (수정된 문장만 제시하며, 여러 오류가 있으면 모두 수정된 최종 문장만 나열하세요. 오류가 없으면 "✅ 오류 없음. 글의 문법, 어휘, 철자가 완벽합니다."라고 명시)
    
    **3. 종합 피드백 및 개선 조언 (💡):**
    - 글의 흐름이 자연스러운지 평가하고 개선할 점을 간결하게 설명하세요.
    - 특히 1단계에서 충족하지 못한 조건(X 항목)을 언급하며 학생이 다음 작성 시 *어떻게* 보완해야 할지 구체적인 영어 표현 예시와 함께 친절하게 조언하세요. (한국어로 작성)
    ---
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[system_prompt],
            config=types.GenerateContentConfig(
                temperature=0.3 
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API 호출 중 오류가 발생했습니다: {e}")
        return "Gemini API 호출에 실패했습니다. 잠시 후 다시 시도해주세요."

# --- 2-1. 한글->영어 번역 함수 (최종, 마침표 후처리 로직 제거) ---
def get_translation(korean_text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "API 키 설정 오류"
    
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Gemini Client 초기화 오류: {e}"

    # ****** JSON 출력을 강제하는 System Prompt 및 Schema 정의 ******
    # 🚨 비상 대책: 모델의 한국어 출력 자체를 원천 봉쇄 (기존 로직 유지)
    system_prompt = (
        "You are an English-Only Translation Machine. "
        "Your task is ONLY to translate the Korean text you receive into fluent English. "
        "You MUST return the translation in a single-line JSON format with the key 'translation'. "
        "Provide ONLY the JSON object and nothing else. "
        "DO NOT use any Korean language in your output, including in the JSON value." # <-- 모든 한국어 출력 금지 지침 유지
    )
    
    # JSON 스키마 정의: { "translation": "..." }
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "translation": types.Schema(
                type=types.Type.STRING,
                description="The complete English translation of the user's Korean input. Ensure the response is in English."
            )
        },
        required=["translation"]
    )
    # ********************************************************************************
    
    try:
        # User contents: 모델에게 번역할 텍스트만 깔끔하게 전달
        user_message = f"Translate this Korean text: {korean_text}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[user_message],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1, # 창의성을 최대한 낮춰서 지침 준수를 높임
                # JSON 출력 타입 강제
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        
        raw_json_text = response.text.strip()
        
        try:
            # JSON 파싱 및 'translation' 키에서 값 추출
            parsed_json = json.loads(raw_json_text)
            clean_translation = parsed_json.get("translation", "번역 결과가 없습니다. (JSON key 오류)").strip()
            
            # 최종 검증 1: 결과가 비어있거나 오류 텍스트라면 재시도 유도
            if not clean_translation or "번역 결과가 없습니다" in clean_translation:
                 return "🚨 번역 결과가 없습니다. 다시 시도해 주세요."

            # 최종 검증 2: 혹시 모를 한국어 포함 여부 확인 
            if re.search(r'[\uac00-\ud7a3]', clean_translation):
                # 여전히 한국어가 포함되어 있다면 입력 텍스트를 따라했을 가능성이 높습니다.
                return f"🚨 번역 실패: 모델이 한국어 입력값을 반환했습니다. 원본 입력값: {korean_text}"
                
            # === 마침표 후처리 로직 제거: 번역 결과에 마침표를 추가하지 않습니다. ===
            # if clean_translation and not clean_translation.endswith(('.', '!', '?')):
            #      clean_translation += '.'
            # ===================================================================

            return clean_translation
            
        except json.JSONDecodeError:
            # 파싱 실패 시: 모델이 JSON 대신 예상치 못한 텍스트를 반환한 경우
            st.error(f"❌ 오류: 모델이 요구된 JSON 형식이 아닌 텍스트를 반환했습니다. 원본 응답: {raw_json_text}")
            # 입력값에 마침표를 붙여서 반환하는 경우도 JSON 파싱 실패로 이어질 가능성이 높습니다.
            return f"❌ 오류 발생: {raw_json_text} (모델이 잘못된 형식을 반환했거나 입력값을 따라했습니다.)"
            
    except Exception as e:
        return f"번역 API 호출 중 오류 발생: {e}"

# --- 이메일 링크 생성 함수 (첨부 파일 처리 로직 제거) ---
def create_mailto_link(essay, feedback, email): 
    # ... (기존 로직 유지) ...
    body_content = (
        "안녕하세요 선생님,\n\n"
        "[학생 이름]: [반/번호] \n"
        "AI 튜터링을 완료한 저의 위인 소개글 최종 결과입니다.\n\n"
        "----------------------------------------------------\n"
        "**1. 학생이 작성한 최종 글:**\n"
        f"{essay}\n\n"
        "----------------------------------------------------\n"
        "**2. AI가 제공한 최종 피드백:**\n"
        f"{feedback}\n"
    )
    
    subject = "AI 튜터 작문 최종 결과: 한국 위인 소개글 (학생 이름과 반/번호를 꼭 수정하세요)"
    
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body_content)
    
    return f"mailto:{email}?subject={encoded_subject}&body={encoded_body}"


# --- 3. Streamlit 메인 함수 ---
def main():
    # Streamlit 페이지 설정을 가장 먼저 실행하여 넓은 화면(Wide Layout)을 기본으로 사용하도록 지정
    st.set_page_config(layout="wide") 
    
    setup_page()
    
    # 작성 조건 안내
    st.markdown(
        """
        <div>
        환영합니다! 아래 조건에 따라 **여러분이 소개하고 싶은 한국의 위인**을 영어로 소개하는 글을 작성하고 피드백을 받아보세요.
        
        ### 📝 필수 작성 조건 (Content Check)
        1. 위인의 **직업/신분/역할** 쓰기
        2. 위인의 **업적**을 1개 이상 쓰기
        3. 위인이 **훌륭하다고 생각하는 이유** 쓰기
        4. 위인의 **모습**이 담긴 사진을 제시하며 **외양을 묘사**하는 내용 쓰기
        
        ### 🔑 Key Expressions (Grammar Check)
        - **to부정사**를 사용하여 행동의 목적/의도 표현하기 
        - **because**를 사용하여 이유를 표현하기
        - **look**을 사용하여 외양을 묘사하기 
        
        ### ✅ 최종 완성 조건
        1. 완성된 글은 **7문장 이상**이어야 합니다.
        2. 글은 주제에 맞게 **흐름이 자연**스러워야 합니다.
        3. 어휘, 철자, 어법, 대소문자, 문장 부호에 **오류가 없어야** 합니다.
        </div>
        <br>
        """, 
        unsafe_allow_html=True
    )
    
    # --- 4. 한글 번역기 영역 추가 (새로운 기능) ---
    st.markdown("---")
    st.markdown("### 🗣️ 한글 표현 번역기 (작문 보조 도구)")
    st.markdown("떠오르는 한글 표현을 여기에 입력하고 번역 버튼을 누르면 영어로 바꿔줍니다. (문장 단위 번역)")
    
    korean_input = st.text_input(
        "번역할 한글 문장이나 짧은 표현을 입력하세요.", 
        key="korean_translator_input",
        placeholder="예시: 그는 위대한 발명가입니다."
    )
    
    # 세션 상태에서 번역 결과를 관리
    if 'translated_text' not in st.session_state:
        st.session_state['translated_text'] = "번역 결과가 여기에 표시됩니다."

    if st.button("🔄 영어로 번역하기", key="translate_button", use_container_width=False):
        if korean_input.strip():
            with st.spinner("AI가 번역 중입니다..."):
                translation_result = get_translation(korean_input)
                st.session_state['translated_text'] = translation_result
        else:
            st.session_state['translated_text'] = "번역할 한글 표현을 입력해주세요."

    # 번역 결과를 깔끔하게 표시
    st.markdown("#### ✨ 번역 결과 (English)")
    # 브라우저 자동 번역 방지 속성은 유지합니다.
    st.markdown(
        f'<div class="translation-box" translate="no">{st.session_state["translated_text"]}</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    # --- 한글 번역기 영역 끝 ---


    # 텍스트 입력 영역
    st.markdown("### ✍️ 내 소개글 작성하기")
    user_text = st.text_area(
        "여기에 위인 소개글을 영어로 작성하세요.", 
        height=350,
        key="essay_input",
        placeholder="예시: I want to introduce Sejong the Great. He was a great king of Joseon Dynasty...",
    )
    # ... (나머지 로직은 변경 없음)
    
    # 위인 사진 업로드 
    st.markdown("### 📸 위인 사진 업로드 (선택, 외양 묘사를 위해 권장)")
    # 'uploaded_file' 객체를 세션 상태에 저장하여 이메일 전송 시 사용합니다.
    uploaded_file = st.file_uploader("위인의 사진을 업로드해주세요.", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="업로드된 위인 사진", width=250)

    # 피드백 요청 버튼
    feedback = None
    if st.button("✨ AI 튜터에게 피드백 요청하기", use_container_width=True):
        if not user_text.strip():
            st.warning("먼저 소개글을 작성해주세요! (7문장 이상)")
        else:
            with st.spinner("AI 튜터가 학생의 글을 꼼꼼하게 분석하고 있습니다..."):
                feedback = get_ai_feedback(user_text)
            
            if feedback:
                st.session_state['user_essay'] = user_text
                st.session_state['ai_feedback'] = feedback
                
                st.markdown("---")
                st.markdown("### 🤖 AI 튜터 피드백 결과")
                # 피드백 박스는 명조체 유지
                st.markdown(f'<div class="feedback-box">{feedback}</div>', unsafe_allow_html=True)

                st.balloons() 
                
                # 수정 유도 메시지
                st.markdown(
                    """
                    <br>
                    <div style="background-color: #fffde7; padding: 10px; border-radius: 5px; border-left: 5px solid #FFC107;">
                    👆 **수정하고 다시 받기:** 피드백을 참고하여 위의 '내 소개글 작성하기' 칸에서 글을 직접 수정해 보세요! 모든 조건에 O를 받을 때까지 반복할 수 있습니다.
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    
    # --- 5. 결과 공유 기능 (선생님께 이메일 전송) ---
    if 'ai_feedback' in st.session_state and st.session_state['ai_feedback']:
        st.markdown("---")
        st.markdown("### 💌 최종 결과 선생님께 보내기")

        # 이메일 주소 자동 입력 (선생님 주소)
        teacher_email = st.text_input(
            "선생님 이메일 주소 (자동 입력됨)", 
            value="fun_english_ssam@naver.com", 
            key="teacher_email_input",
            placeholder="선생님의 이메일 주소가 자동으로 입력됩니다."
        )
        
        # 이메일 보내기 버튼 (실제로는 링크를 HTML로 출력하여 이메일 클라이언트를 엽니다)
        if st.button("📧 최종 결과 이메일 클라이언트 열기 (클릭)", use_container_width=True):
            if not teacher_email.strip():
                st.error("❌ 오류: 선생님 이메일 주소를 입력해주세요.")
            else:
                mailto_href = create_mailto_link(
                    st.session_state['user_essay'], 
                    st.session_state['ai_feedback'], 
                    teacher_email
                )
                
                # HTML 마크다운을 이용하여 자동 이메일 발송 링크 실행
                st.markdown(
                    f"""
                    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 8px; border: 1px solid #4CAF50;">
                        <p>👆 위 링크를 클릭하면 학생의 이메일 앱(또는 웹 메일)이 열립니다.</p>
                        <a href="{mailto_href}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-align: center; border-radius: 5px; text-decoration: none; font-size: 1.1em; margin-top: 10px;">
                            ✉️ 이메일 작성 시작하기
                        </a>
                        <p style="margin-top: 15px; color: #D32F2F;">**[주의]** 이메일이 열리면, **제목에 학생 이름과 반/번호를 반드시 수정**하고 내용을 확인한 후 발송하도록 학생들에게 지도해 주세요.</p>
                    </div>
                    """, unsafe_allow_html=True
                )

# 앱 실행
if __name__ == "__main__":
    # 세션 상태 초기화
    if 'user_essay' not in st.session_state:
        st.session_state['user_essay'] = ""
    if 'ai_feedback' not in st.session_state:
        st.session_state['ai_feedback'] = ""
        
    main()
