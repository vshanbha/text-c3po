import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser


st.title("Text Translator App")
if "API_KEY" in st.secrets:
    openai_api_key = st.secrets["API_KEY"]
else:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
eng_form = st.form("eng_form")
# Instantiate LLM model
# llm = ChatOllama(model="mistral",temperature=0.2)
llm = None

class Translation(BaseModel):
    language: str = Field(description="Translation to this language")
    origin_language: str = Field(description="Autodected langauge of the {{.Prompt}}")
    formal: str = Field(description="Formal version of translated output of the {{.Prompt}}")
    informal: str = Field(description="Informal version of translated output of the {{.Prompt}}")
    commentary: str = Field(description="Special commentary about the translation")
    error: str = Field(description="Error message if there was an error in translation")

def translate(text, language):
    # Parser
    parser = JsonOutputParser(pydantic_object=Translation)
    # Prompt
    prompt_string = """You are any language to {language} translator.
                        Autodetect the language of {{ .Prompt }} as origin_language and respond strictly with translation in {language}.
                        Provide multiple translations where possible with relevant commentary in the origin_language.
                        Where possible provide both formal and informal versions.
                        """
    system_prompt = SystemMessagePromptTemplate.from_template(prompt_string)
    human_prompt0 = HumanMessagePromptTemplate.from_template('Translate to {language} language' )
    human_prompt1 = HumanMessagePromptTemplate.from_template('{text}\n{format_instructions}' )
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt0, human_prompt1])
    request = chat_prompt.format_prompt(text = text, language = language,
                                        format_instructions = parser.get_format_instructions()).to_messages()
    # Run LLM model
    response = llm.invoke(request)
    # Print results
    return parser.parse(response.content)

with eng_form:
    selected_lang = eng_form.selectbox(
        "Select Target Language",
        ("German","English","Spanish","French", "Dutch",
         "Afrikaans","Portuguese", "Danish", "Swedish", "Greek",
         "Hindi","Marathi","Telgu", "Tamil", "Kannada","Gujrati",)
    )
    in_col, out_meta = eng_form.columns(2)
    topic_text = in_col.text_area("Enter Text",placeholder="Enter Text:", height=300)
    submitted = eng_form.form_submit_button("Translate")
    output = ''
        
    if not openai_api_key:
        st.info("Please add your API key to continue.")
    else :
        llm = ChatOpenAI( openai_api_key=openai_api_key, temperature=0.2, max_tokens=300)
        if submitted:
            output = translate(topic_text, selected_lang)
            out = "Formal : {} \n\nInformal : {}\n\nNote: {}".format(output['formal'], output['informal'], output['commentary'])

            out_meta.text_area("Detected language {}".format(output['origin_language'])
                                   , value=out, height=300)