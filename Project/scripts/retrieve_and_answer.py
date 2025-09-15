import openai
from qdrant_client import QdrantClient
from qdrant_client.http import models

QDRANT_COLLECTION = "prague_events"
TOP_K = 5

#client_openai = OpenAI()
client_qdrant = QdrantClient(url="http://qdrant:6333")

def query_qdrant(query, top_k=TOP_K):
    # Embed the query using OpenAI embeddings
    embedding_response = openai.Embedding.create(
        input=[query],
        model="text-embedding-ada-002"  # Use the correct embedding model
    )
    query_embedding = embedding_response['data'][0]['embedding']

    # Query Qdrant for nearest neighbors
    search_result = client_qdrant.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_embedding,
        limit=top_k,
        with_payload=True
    )
    return search_result

def build_prompt(query, search_results):
    prompt_template = """
You are a helpful assistant answering questions about events in Prague based on the provided context.

Use only the facts from the CONTEXT when answering the QUESTION.

CONTEXT:
{context}

QUESTION:
{question}

Answer in English.
""".strip()

    context = "\n\n".join([hit.payload["text"] for hit in search_results])
    prompt = prompt_template.format(context=context, question=query)
    return prompt

def answer_question(query):
    search_results = query_qdrant(query)
    prompt = build_prompt(query, search_results)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content
    return answer

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/retrieve_and_answer.py \"Your question here\"")
        sys.exit(1)
    question = sys.argv[1]
    answer = answer_question(question)
    print("Answer:")
    print(answer)
