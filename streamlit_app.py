import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_community.chat_models import ChatOllama

st.title("Text Translator App")
openai_api_key = st.text_input("OpenAI API Key", type="password")
eng_form = st.form("eng_form")
# Instantiate LLM model
# llm = ChatOllama(model="mistral",temperature=0.2)
llm = None

def translate_DE(text):
    # Prompt
    prompt_string = """You are any language to German translator.
                        Autodetect the language of {{ .Prompt }} and respond strictly with translation in German.
                        Provide multiple translations where possible with relevant commentary.
                        For German translation provide both formal and informal versions where possible.
                        Limit the translation count to a maximum of 3"""
    system_prompt = SystemMessagePromptTemplate.from_template(prompt_string)

    sample_h_prompt1 = HumanMessagePromptTemplate.from_template('How is it going ?')
    sample_a_prompt1 = AIMessagePromptTemplate.from_template('German Informal : Wie gehts ?\n\nGerman formal : Wie geht es Ihnen ?')
    sample_h_prompt2 = HumanMessagePromptTemplate.from_template('My name is John Doe')
    sample_a_prompt3 = AIMessagePromptTemplate.from_template('German Informal : Ich bin John Doe\n\nGerman alternative : Ich Heiße John Doe')
    human_prompt = HumanMessagePromptTemplate.from_template('{text}')
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, 
                                                    sample_h_prompt1, sample_a_prompt1, 
                                                    sample_h_prompt2, sample_a_prompt3, 
                                                    human_prompt])
    request = chat_prompt.format_prompt(text = text).to_messages()
    # Run LLM model
    response = llm(request)
    # Print results
    print(response)
    return response.content

def translate_EN(text):
    # Prompt
    prompt_string = """You are any language to English translator.
                        Autodetect the language of {{ .Prompt }} and Respond strictly with translation in English.
                        Provide multiple translations where possible with relevant commentary.
                        Limit the translation count to a maximum of 3"""
    system_prompt = SystemMessagePromptTemplate.from_template(prompt_string)

    sample_h_prompt1 = HumanMessagePromptTemplate.from_template('woher kommen Sie?')
    sample_a_prompt1 = AIMessagePromptTemplate.from_template('English : Where are you from ?\n\nEnglish alternative : Where do you come from ?')
    sample_h_prompt2 = HumanMessagePromptTemplate.from_template('wie heißen Sie')
    sample_a_prompt3 = AIMessagePromptTemplate.from_template('English : What is your name')
    human_prompt = HumanMessagePromptTemplate.from_template('{text}')
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, 
                                                    sample_h_prompt1, sample_a_prompt1, 
                                                    sample_h_prompt2, sample_a_prompt3, 
                                                    human_prompt])
    request = chat_prompt.format_prompt(text = text).to_messages()
    # Run LLM model
    response = llm(request)
    # Print results
    print(response)
    return response.content

with eng_form:
    selected_lang = eng_form.selectbox(
        "Select Target Language",
        ("German","English")
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
            if selected_lang == "German":
                output = translate_DE(topic_text)
            elif selected_lang == "English":
                output = translate_EN(topic_text)
            out_col.text_area("Output language {} ".format(selected_lang), value=output, height=300)
