import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate

# from langchain_community.chat_models import ChatOllama
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

st.set_page_config(
    page_title='Text C-3PO - Translator App',
    page_icon=':robot_face:'
)
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
    prompt_string = """You are translator who translates from many languages to {language} .
                        Autodetect the origin languages in {{ .Prompt }}. 
                        If multiple languages are detected store all detected languages as an array of strings in origin_language.
                        Respond strictly with translation of complete {{ .Prompt }} in {language}.
                        Provide multiple translations where possible with relevant commentary in the {language}.
                        Where possible provide both formal and informal versions.
                        Translated output should be provided as a JSON schema per below instrucctions
                        {format_instructions}
                        """
    system_prompt = SystemMessagePromptTemplate.from_template(prompt_string)
    human_prompt = HumanMessagePromptTemplate.from_template('{text}' )
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    request = chat_prompt.format_prompt(text = text, language = language,
                                        format_instructions = parser.get_format_instructions()).to_messages()
    # Run LLM model
    response = llm.invoke(request)
    return parser.parse(response.content)

with eng_form:
    selected_lang = eng_form.selectbox(
        "Select Target Language",
        ("English","German","Spanish","French", "Dutch",
         "Afrikaans","Portuguese", "Danish", "Swedish", "Greek",
         "Chinese","Persian",
         "Hindi","Marathi","Telgu", "Tamil", "Kannada","Gujrati",
         "Bangla"
         )
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
            # convert all keys to lower case
            output = {k.lower(): v for k, v in output.items()}
            # Print results
            if 'error' in output and output['error']:
                st.warning(output['error'])            
            formal = output['formal'] if 'formal' in output else ''
            informal = output['informal'] if 'informal' in output else ''
            comment =  output['commentary'] if 'commentary' in output else ''
            out = "Formal : {} \n\nInformal : {}\n\nNote: {}".format(formal, informal, comment)
            out_meta.text_area("Detected language {}".format(output['origin_language'])
                                   , value=out, height=300)
            output
            
