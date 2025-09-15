import os
import json
from qdrant_client import QdrantClient
from qdrant_client.http import models
from tqdm.auto import tqdm

DATA_DIR = "data/vinegret_articles/json"
QDRANT_COLLECTION = "prague_events"

def load_paragraphs_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    paragraphs = data.get("paragraphs", [])
    # Filter out short or irrelevant paragraphs if needed
    paragraphs = [p for p in paragraphs if len(p.strip()) > 20]
    return paragraphs

def main():
    client = QdrantClient(url="http://qdrant:6333") # If you are running the script inside a Docker container: docker exec -it prague_events_chat_app python scripts/ingest_vinegret_to_qdrant.py
    #client = QdrantClient(url="http://localhost:6333") # If you are running the script on your local machine

    # Delete collection if exists
    try:
        client.delete_collection(collection_name=QDRANT_COLLECTION)
    except Exception:
        pass

    # Create collection with 1536 dimension for OpenAI embeddings
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    )

    points = []
    point_id = 0
    model_handle = "text-embedding-ada-002" #"jinaai/jina-embeddings-v2-small-en"

    for filename in tqdm(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(DATA_DIR, filename)
        paragraphs = load_paragraphs_from_file(filepath)
        for paragraph in paragraphs:
            point = models.PointStruct(
                id=point_id,
                vector=models.Document(text=paragraph, model=model_handle),  
                payload={"text": paragraph, "source_file": filename},
            )
            points.append(point)
            point_id += 1


    #'''
    # Upsert points without vectors (embedding must be done externally or via Qdrant's embedding integration)
    # Here we assume external embedding, so we will embed paragraphs before upsert
    # For now, just upsert with empty vectors to show structure (will update later)
    # To embed externally, we need to call OpenAI embeddings API for each paragraph

    # For demonstration, we embed paragraphs using OpenAI embeddings here
    from openai import OpenAI
    client_openai = OpenAI()

    batch_size = 50
    vectors = []
    payloads = []
    ids = []

    for i in tqdm(range(0, len(points), batch_size)):
        batch_points = points[i : i + batch_size]
        texts = [p.payload["text"] for p in batch_points]
        response = client_openai.embeddings.create(
            input=texts,
            model=model_handle
        )
        for j, embedding in enumerate(response.data):
            vectors.append(embedding.embedding)
            payloads.append(batch_points[j].payload)
            ids.append(batch_points[j].id)

    # Upsert with vectors in batches to avoid timeout
    batch_size_upsert = 20
    for i in range(0, len(ids), batch_size_upsert):
        batch_points = [
            models.PointStruct(id=ids[j], vector=vectors[j], payload=payloads[j])
            for j in range(i, min(i + batch_size_upsert, len(ids)))
        ]
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=batch_points,
        )
    #'''

    print(f"Ingested {len(ids)} paragraphs into Qdrant collection '{QDRANT_COLLECTION}'.")

if __name__ == "__main__":
    main()
