import json
from vertexai.vision_models import MultiModalEmbeddingModel, Image
import vertexai

vertexai.init(
    project="unifind-2c6c6",
    location="us-central1"
)

model = MultiModalEmbeddingModel.from_pretrained(
    "multimodalembedding@001"
)

img = Image.load_from_file("images.jpeg")

embedding = model.get_embeddings(
    image=img
).image_embedding

record = {
    "id": "item_001",
    "embedding": embedding
}

with open("items.jsonl", "w", encoding="utf-8") as f:
    f.write(json.dumps(record) + "\n")

print("items.jsonl created")