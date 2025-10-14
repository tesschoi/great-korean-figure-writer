# app.py

import streamlit as st
from google import genai
from google.genai import types
import os

# --- 1. 앱 설정 및 CSS 스타일링 (폰트, 제목 등) ---
def setup_page():
    # 명조체 계열 폰트 적용을 위한 CSS
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Nanum+Myeongjo&display=swap');
        
        .main-font {
            font-family: 'Nanum Myeongjo', serif;
            font-size: 1.1em;
        }
        
        /* 텍스트 입력 영역에도 폰트 적용 (Streamlit의 텍스트 영역 클래스) */
        textarea {
            font-family: 'Nanum Myeongjo', serif !important;
        }

        /* 큰 제목 스타일 */
        h1 {
            color: #1E90FF; /* 파란색 계열 */
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title("🇰🇷 Great Korean Figure Writer 🖊️")
    st.subheader("나만의 한국 위인 소개글 작성 및 AI 피드백 앱 (중학교 1학년)")

# --- 2. Gemini API를 이용한 피드백 요청 함수 ---
# 피드백 기준을 상세히 포함하여 LLM의 응답 품질을 높임
def get_ai_feedback(student_text):
    # API 키 설정 (보안을 위해 환경 변수에서 불러옴)
    try:
        # st.secrets 대신 os.environ을 사용하여 Render 배포 환경 변수와 일치시킴
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    except KeyError:
        st.error("❌ 오류: Gemini API 키가 설정되지 않았습니다. 환경 변수를 확인해주세요.")
        return "API 오류로 피드백을 제공할 수 없습니다."
    
    # AI에게 전달할 상세한 시스템 프롬프트 (가이드라인)
    system_prompt = f"""
    당신은 중학교 1학년 학생의 영어 작문 보조 AI 튜터입니다.
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
    - 7문장 이상 여부 (현재 {len(student_text.split('.'))} 문장): (O/X) (마침표 기준)
    
    **2. 유창성 및 오류 수정 (✅):**
    문법(어법), 어휘, 철자, 대소문자, 문장 부호 오류를 찾아 수정된 완벽한 문장을 제시하세요. 
    (수정된 문장만 제시하고, 오류가 없으면 "✅ 오류 없음"이라고 명시)
    
    **3. 종합 피드백 및 개선 조언 (💡):**
    - 글의 흐름이 자연스러운지 평가하고 개선할 점을 간결하게 설명하세요.
    - 특히 충족하지 못한 조건(1단계의 X 항목)을 언급하며 학생이 다음 작성 시 *어떻게* 보완해야 할지 구체적인 영어 표현 예시와 함께 친절하게 조언하세요. (한국어로 작성)
    ---
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # 응답 속도가 빠르고 텍스트 생성에 적합한 모델 선택
            contents=[system_prompt],
            config=types.GenerateContentConfig(
                temperature=0.3 # 창의성보다 정확한 피드백을 위해 낮은 온도 설정
            )
        )
        return response.text
    except Exception as e:
        return f"Gemini API 호출 중 오류가 발생했습니다: {e}"

# --- 3. Streamlit 메인 함수 ---
def main():
    setup_page()
    
    # 앱 안내 및 작성 조건 제시
    st.markdown(
        """
        <div class="main-font">
        환영합니다! 아래 조건에 따라 **여러분이 소개하고 싶은 한국의 위인**을 영어로 소개하는 글을 작성하고 피드백을 받아보세요.
        
        ### 📝 필수 작성 조건 (Content Check)
        1. 위인의 **직업/신분/역할** 쓰기
        2. 위인의 **업적**을 1개 이상 쓰기
        3. 위인이 **훌륭하다고 생각하는 이유** 쓰기
        4. 위인의 **모습**이 담긴 사진을 제시하며 **외양을 묘사**하는 내용 쓰기
        
        ### 🔑 Key Expressions (Grammar Check)
        - **to부정사**를 사용하여 행동의 목적/의도 표현하기 (e.g., *He worked hard **to** save the country.*)
        - **because**를 사용하여 이유를 표현하기
        - **look**을 사용하여 외양을 묘사하기 (e.g., *She **looks** kind.*)
        
        ### ✅ 최종 완성 조건
        1. 완성된 글은 **7문장 이상**이어야 합니다.
        2. 글은 주제에 맞게 **흐름이 자연**스러워야 합니다.
        3. 어휘, 철자, 어법, 대소문자, 문장 부호에 **오류가 없어야** 합니다.
        </div>
        <br>
        """, 
        unsafe_allow_html=True
    )
    
    # 텍스트 입력 영역
    st.markdown("### ✍️ 내 소개글 작성하기")
    # Streamlit 텍스트 영역 (height 설정으로 충분한 공간 확보)
    user_text = st.text_area(
        "여기에 위인 소개글을 영어로 작성하세요.", 
        height=300,
        key="essay_input",
        placeholder="e.g., I want to introduce King Sejong. He was a great king of Joseon Dynasty..."
    )

    # 위인 사진 업로드 (선택 사항이지만 외양 묘사 조건에 필요)
    st.markdown("### 📸 위인 사진 업로드 (선택)")
    uploaded_file = st.file_uploader("위인의 사진을 업로드해주세요.", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="업로드된 위인 사진", width=200)

    # 피드백 요청 버튼
    if st.button("✨ AI 튜터에게 피드백 요청하기"):
        if not user_text.strip():
            st.warning("먼저 소개글을 작성해주세요!")
        else:
            with st.spinner("AI 튜터가 열심히 분석 중입니다..."):
                feedback = get_ai_feedback(user_text)
            
            st.markdown("---")
            st.markdown("### 🤖 AI 튜터 피드백 결과")
            # 피드백 내용에 폰트 적용
            st.markdown(f'<div class="main-font">{feedback}</div>', unsafe_allow_html=True)

            st.balloons() # 피드백 완료 시 시각 효과
            
            # 수정 유도 메시지
            st.markdown(
                """
                <br>
                <div class="main-font" style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border-left: 5px solid #1E90FF;">
                👆 **수정하기:** 피드백을 참고하여 위의 '내 소개글 작성하기' 칸에서 글을 직접 수정해 보세요! 모든 조건에 O를 받을 때까지 반복할 수 있습니다.
                </div>
                """, 
                unsafe_allow_html=True
            )

# 앱 실행
if __name__ == "__main__":
    main()