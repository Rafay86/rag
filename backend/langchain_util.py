from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from pinecone_util import vectorstore
from langchain.chains import LLMChain
from typing import List
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

#vector=vectorstore.as_retriever(search_kwargs={"k": 10})


def get_filtered_retriever(matched_source: str):
    return vectorstore.as_retriever(
        search_kwargs={
            "k": 10,
            "filter": {"source": {"$in": [matched_source]}},
        }
    )



def get_rag_chain(source: str,):
    """
    Create a Retrieval-Augmented Generation (RAG) chain for the given query.
    """
    print("source", source, "UNDER MAIN ")
    filtered_retriever = get_filtered_retriever(source)

    cohere_compressor = CohereRerank(model="rerank-multilingual-v3.0")
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=cohere_compressor, base_retriever=filtered_retriever
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are ANB regulatory Advisor, an AI assistant specialized in regulatory topics in Saudi Arabia, including Banks, Finance, Payments, AML/CTF, Money Exchange, and Credit Information.\n\n"
         "Your task is to reformulate the user's input into a **clear, precise, self-contained query** that captures the intent accurately without relying on previous chat turns.\n\n"
         "**Guidelines for Reformulation:**\n"
         "1. **Expand abbreviations** (e.g., 'AML' → 'Anti-Money Laundering', 'CC' → 'Credit Card').\n"
         "2. If the input is vague or incomplete, rephrase to make it legally and regulatorily precise while keeping financial terminology intact.\n"
         "3. Retain key regulatory context or department-relevant details.\n"
         "4. Do **not** introduce new assumptions or speculate.\n\n"
         "Return only the reformulated query."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    qa_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are ANB regulatory Advisor, a domain-specific assistant trained to handle questions related to the regulatory scope in Saudi Arabia.\n\n"
     "You provide factual, concise, and well-referenced answers strictly based on retrieved official SAMA documents or approved policies.\n\n"
     "When multiple relevant documents or sections are provided in the context, synthesize the information while maintaining accuracy.\n\n"
     "For each piece of information you use, cite the specific document source.\n\n"
     "**Scope of Topics:**\n"
     "- Banks\n"
     "- Finance\n"
     "- Payments\n"
     "- AML CTF (Anti-Money Laundering / Counter-Terrorism Financing)\n"
     "- Money Exchange\n"
     "- Credit Information\n\n"
     "- Data Classification Policy NDMO\n"
     "- OuteSourcing Rules\n"
     "- Governance Framework\n"
     "- Cyber Security Framwork\n"
     "- Personal Data Protection Law of SDAIA\n"
     "- AI Ethics Principles of SDAIA\n\n"
     "**Guidelines:**\n"
     "1. Use **only** the given context when forming your answer.\n"
     "2. Do not speculate** or rely on external knowledge.\n"
     "3. Retain key regulatory context or department-relevant details.\n"
     "4. Expand abbreviations when they appear.\n"
     "5. Be direct, objective, and structured in your responses."),
    ("system", "Context: {context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])


    llm = ChatOpenAI(model="gpt-4o-mini") # type: ignore
    history_aware_retriever = create_history_aware_retriever(
        llm, compression_retriever, contextualize_q_prompt
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)


simple_system_prompt = """
        You are ANB regulatory Advisor, a classifier for banking and financial regulation queries in Saudi Arabia.

        Rules:
        1. If the query is general/off-topic (greetings, jokes, chatbot questions), reply briefly and normally.
        2. If the query refers to laws, articles, penalties, compliance, or SAMA/ Saudi Arabia regulation, outsourcing, NDMO Data Classification/Policy, CyberSecurity, IT Framework — even if mixed with small talk — respond:
        False
        <one of:
            "Banking Control Law.pdf",
            "REGULATION OF WORK PROCEDURES AND LITIGATION EN.pdf",
            "Implementing Regulations of Credit Information Law.pdf",
            "Regulations of License Fees for Money Changing Business.pdf",
            "Implementing Regulations of the Law of Combating Terrorist Crimes and its Financing.pdf",
            "Combating Terrorism and Financing of Terrorism Law.pdf",
            "Law_of_Payments_and_Payment_Services-EN.pdf",
            "Implementing_Regulations_for_Law_of_Payments_and_Payment_Services-EN.pdf",
            "Finance_Lease_Law_EN.pdf",
            "Real_Estate_Finance_Law_ِEN.pdf",
            "Implementing Regulation to the AML Law October 2017.pdf",
            "Regulations_of_the_Finance_Lease-EN.pdf",
            "Implementing_Regulation_of_the_Real_Estate_Finance_Law_En.pdf",
            "Finance_Companies_Control_Law-EN1.pdf",
            "Currency Law.pdf",
            "Credit Information Law.pdf",
            "Anti-Money Laundering Law.pdf",
            "Anti -Forgery Law.pdf"
            "Cyber Security Framework.pdf",
            "Data Classification Policy.pdf",
            "Outsourcing Rules - Revised v2 Final Draft-Dec-2019.pdf",
            "SAMA-IT_Governance_Framework.pdf",
            "ai-principles.pdf",
            "Personal Data Protection Law.pdf"
        >
        3. Use chat history for context.

        No summaries. No explanations. No document text. Only return format or normal reply.
        """


simple_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "Context: " + simple_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}")
])


from document_util import get_all_documents

def get_simple_chain():
    documents = get_all_documents()
    filenames = [doc['filename'] for doc in documents]
    
    # Fallback if no documents
    if not filenames:
        filenames_str = "No documents available."
    else:
        filenames_str = "\n".join([f'"{f}",' for f in filenames])

    dynamic_system_prompt = f"""
        You are ANB regulatory Advisor, a classifier for banking and financial regulation queries in Saudi Arabia.

        Rules:
        1. If the query is general/off-topic (greetings, jokes, chatbot questions), reply briefly and normally.
        2. If the query refers to laws, articles, penalties, compliance, or SAMA/ Saudi Arabia regulation, outsourcing, NDMO Data Classification/Policy, CyberSecurity, IT Framework — even if mixed with small talk — OR if the query asks about any of the available documents, respond:
        False
        <one of:
{filenames_str}
        >
        3. Use chat history for context.

        No summaries. No explanations. No document text. Only return format or normal reply.
        """

    dynamic_prompt_template = ChatPromptTemplate.from_messages([
        ("system", "Context: " + dynamic_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    llm = ChatOpenAI(model="gpt-4o-mini")
    simple_chain = LLMChain(llm=llm, prompt=dynamic_prompt_template)
    return simple_chain
