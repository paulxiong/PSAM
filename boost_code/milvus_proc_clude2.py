# this is generated from clude2 by reading inline doc from 1_build_image_search_engine.copy()
import csv
from glob import glob
from pathlib import Path

import cv2
from towhee import pipe, ops, DataCollection
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
import os
import argparse

# Config
MODEL = 'resnet50' 
DEVICE = None
HOST = '127.0.0.1'
PORT = '19530'
TOPK = 10
DIM = 2048
COLLECTION_NAME = 'reverse_image_search'
INDEX_TYPE = 'IVF_FLAT'
METRIC_TYPE = 'L2'

# Load paths
def load_paths(src):
  if src.endswith('csv'):
    with open(src) as f:
      reader = csv.reader(f)
      next(reader)
      for row in reader:
        yield row[1]
  else:
    for pth in glob(src):
      yield pth

# Embedding pipeline  
p_embed = (
  pipe
    .input('src')
    .flat_map('src', 'path', load_paths)
    .map('path', 'img', ops.image_decode())
    .map('img', 'vec', ops.image_embedding.timm(model_name=MODEL, device=DEVICE))  
)

# Insert pipeline
p_insert = (
    p_embed
      .map(('path', 'vec'), 'ids', ops.ann_insert.milvus_client(
        host=HOST, port=PORT, collection_name=COLLECTION_NAME))
      .output('ids')  
)

# Search pipeline
p_search = (
    p_embed
      .map('vec', ('ids'), ops.ann_search.milvus_client(
        host=HOST, port=PORT, limit=TOPK,
        collection_name=COLLECTION_NAME))
      .map('ids', 'paths', lambda x: [y[0] for y in x])
      .output('path', 'paths')
)

# Create collection
def create_collection(name, dim):
  connections.connect(host=HOST, port=PORT)
  fields = [
    FieldSchema(name='path', dtype=DataType.VARCHAR, max_length=500, is_primary=True), 
    FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, dim=dim)
  ]
  schema = CollectionSchema(fields, 'image search collection')
  collection = Collection(name=name, schema=schema)

  index_params = {
    'metric_type': METRIC_TYPE,
    'index_type': INDEX_TYPE, 
    'params': {"nlist": 2048}
  }

  collection.create_index(field_name='embedding', index_params=index_params)
  return collection

# Main function
def main(insert_src, query_src, output_dir):
  
  # Step 1 - Create collection
  collection = create_collection(COLLECTION_NAME, DIM)  

  # Step 2 - Insert images
  p_insert(insert_src)

  # Step 3 - Search
  dc = p_search(query_src)

  # Get image paths
  result_paths = dc.to_list()[0].paths

  # Save images
  os.makedirs(output_dir, exist_ok=True)
  for i, img_path in enumerate(result_paths):
    img = cv2.imread(img_path)
    cv2.imwrite(os.path.join(output_dir, f"result_{i}.jpg"), img)

if __name__ == "__main__":
  
  parser = argparse.ArgumentParser(description='Image search')
  parser.add_argument('--insert_src', type=str, default='data/*.jpg')
  parser.add_argument('--query_src', type=str, default='query.jpg')
  parser.add_argument('--output_dir', type=str, default='results')
  args = parser.parse_args()

  main(args.insert_src, args.query_src, args.output_dir)