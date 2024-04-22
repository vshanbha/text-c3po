import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_community.chat_models import ChatOllama

st.title("Text Translator App")
if "API_KEY" in st.secrets:
    openai_api_key = st.secrets["API_KEY"]
else:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
eng_form = st.form("eng_form")
# Instantiate LLM model
# llm = ChatOllama(model="mistral",temperature=0.2)
llm = None

def translate(text, language):
    # Prompt
    prompt_string = """You are any language to {language} translator.
                        Autodetect the language of {{ .Prompt }} and respond strictly with translation in {language}.
                        Provide multiple translations where possible with relevant commentary.
                        Where possible provide both formal and informal versions.
                        Limit the translation count to a maximum of 3"""
    system_prompt = SystemMessagePromptTemplate.from_template(prompt_string)
    sample_h_prompt0 = HumanMessagePromptTemplate.from_template('Translate to German language')
    sample_h_prompt1 = HumanMessagePromptTemplate.from_template('How is it going ?')
    sample_a_prompt1 = AIMessagePromptTemplate.from_template('German Informal : Wie gehts ?\n\nGerman formal : Wie geht es Ihnen ?')
    sample_h_prompt2 = HumanMessagePromptTemplate.from_template('My name is John Doe')
    sample_a_prompt2 = AIMessagePromptTemplate.from_template('German Informal : Ich bin John Doe\n\nGerman alternative : Ich Heiße John Doe')
    sample_h_prompt3 = HumanMessagePromptTemplate.from_template('Translate to English language')
    sample_h_prompt4 = HumanMessagePromptTemplate.from_template('woher kommen Sie?')
    sample_a_prompt4 = AIMessagePromptTemplate.from_template('English : Where are you from ?\n\nEnglish alternative : Where do you come from ?')
    sample_h_prompt5 = HumanMessagePromptTemplate.from_template('wie heißen Sie')
    sample_a_prompt5 = AIMessagePromptTemplate.from_template('English : What is your name')
    human_prompt0 = HumanMessagePromptTemplate.from_template('Translate to {language} language' )
    human_prompt1 = HumanMessagePromptTemplate.from_template('{text}' )
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, sample_h_prompt0,
                                                    sample_h_prompt1, sample_a_prompt1, sample_h_prompt2, sample_a_prompt2, 
                                                    sample_h_prompt3, sample_h_prompt4, sample_a_prompt4, sample_h_prompt5, 
                                                    sample_a_prompt5, human_prompt0, human_prompt1])
    request = chat_prompt.format_prompt(text = text, language = language).to_messages()
    # Run LLM model
    response = llm.invoke(request)
    # Print results
    print(response)
    return response.content

with eng_form:
    selected_lang = eng_form.selectbox(
        "Select Target Language",
        ("German","English","Spanish","French", "Dutch",
         "Afrikaans","Portuguese", "Danish", "Swedish", "Greek",
         "Hindi","Marathi","Telgu", "Tamil", "Kannada","Gujrati",)
    )
    in_col, out_col = eng_form.columns(2)
    topic_text = in_col.text_area("Enter Text",placeholder="Enter Text:", height=300)
    submitted = eng_form.form_submit_button("Translate")
    output = ''
        
    if not openai_api_key:
        st.info("Please add your API key to continue.")
    else :
        llm = ChatOpenAI( openai_api_key=openai_api_key, temperature=0.2, max_tokens=300)
        if submitted:
            output = translate(topic_text, selected_lang)
            out_col.text_area("Output language {} ".format(selected_lang), value=output, height=300)
