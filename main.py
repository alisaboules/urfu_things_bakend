import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from vertexai.vision_models import MultiModalEmbeddingModel, Image
from google.cloud import aiplatform
import vertexai


PROJECT_ID = "unifind-2c6c6"
REGION = "us-central1"
INDEX_ID = "4715275406926675968"
ENDPOINT_ID = "1138665236841103360"
DEPLOYED_INDEX_ID = "lost_found_stream_v1"

vertexai.init(project=PROJECT_ID, location=REGION)
aiplatform.init(project=PROJECT_ID, location=REGION)

model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
index = aiplatform.MatchingEngineIndex(INDEX_ID)
endpoint = aiplatform.MatchingEngineIndexEndpoint(ENDPOINT_ID)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://urfu-things-1.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_embedding_from_image_bytes(image_bytes: bytes):
    # Создаём объект Image напрямую из байтов
    img = Image(image_bytes=image_bytes)
    return model.get_embeddings(image=img).image_embedding

@app.post("/search")
async def search_similar(file: UploadFile = File(...), top_k: int = 5):
    image_bytes = await file.read()
    emb = get_embedding_from_image_bytes(image_bytes)
    response = endpoint.find_neighbors(
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[emb],
        num_neighbors=top_k
    )
    results = [{"id": neighbor.id, "distance": neighbor.distance} for neighbor in response[0]]
    return {"results": results}
@app.post("/upsert")
async def upsert_item(datapoint_id: str = Form(), file: UploadFile = File(...)):
    image_bytes = await file.read()
    emb = get_embedding_from_image_bytes(image_bytes)
    index.upsert_datapoints([{"datapoint_id": datapoint_id, "feature_vector": emb}])
    return {"status": "ok"}

# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run(app, host="0.0.0.0", port=port)