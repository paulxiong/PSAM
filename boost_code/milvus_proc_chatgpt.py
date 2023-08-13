import csv
from glob import glob
from pathlib import Path
import cv2
from towhee.types.image import Image
import time
import argparse
from PIL import Image as PILImage

from towhee import pipe, ops, DataCollection
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

# Global parameters
MODEL = 'resnet50'
DEVICE = None
HOST = '127.0.0.1'
PORT = '19530'
TOPK = 10
DIM = 2048
COLLECTION_NAME = 'reverse_image_search'
INDEX_TYPE = 'IVF_FLAT'
METRIC_TYPE = 'L2'

# Load image path
def load_image(x):
    if x.endswith('csv'):
        with open(x) as f:
            reader = csv.reader(f)
            next(reader)
            for item in reader:
                yield item[1]
    else:
        for item in glob(x):
            yield item

# Create Milvus collection
def create_milvus_collection(collection_name, dim, metric_type):
    fields = [
        FieldSchema(name='path', dtype=DataType.VARCHAR, description='path to image', max_length=500, 
                    is_primary=True, auto_id=False),
        FieldSchema(name='embedding', dtype=DataType.FLOAT_VECTOR, description='image embedding vectors', dim=dim)
    ]
    schema = CollectionSchema(fields=fields, description='reverse image search')
    collection = Collection(name=collection_name, schema=schema)

    index_params = {
        'metric_type': metric_type,
        'index_type': INDEX_TYPE,
        'params': {"nlist": 2048}
    }
    collection.create_index(field_name='embedding', index_params=index_params)
    return collection

# Load and read images
def read_images(img_paths):
    imgs = []
    for p in img_paths:
        imgs.append(Image(cv2.imread(p), 'BGR'))
    return imgs

# Calculate Average Precision by comparing predictions and ground truths
def get_ap(pred: list, gt: list):
    ct = 0
    score = 0.
    for i, n in enumerate(pred):
        if n in gt:
            ct += 1
            score += (ct / (i + 1))
    if ct == 0:
        ap = 0
    else:
        ap = score / ct
    return ap

def main(insert_src, query_src, output_dir):
    # Convert input paths to full paths
    insert_src = Path(insert_src).resolve().as_posix()
    query_src = Path(query_src).resolve().as_posix()

    # Connect to Milvus service
    connections.connect(host=HOST, port=PORT)

    # Embedding pipeline
    p_embed = (
        pipe.input('src')
            .flat_map('src', 'img_path', load_image)
            .map('img_path', 'img', ops.image_decode())
            .map('img', 'vec', ops.image_embedding.timm(model_name=MODEL, device=DEVICE))
    )

    # Create collection
    collection = create_milvus_collection(COLLECTION_NAME, DIM, METRIC_TYPE)
    print(f'A new collection created: {COLLECTION_NAME}')

    # Insert pipeline
    p_insert = (
        p_embed.map(('img_path', 'vec'), 'mr', ops.ann_insert.milvus_client(
                    host=HOST,
                    port=PORT,
                    collection_name=COLLECTION_NAME
                    ))
            .output('mr')
    )

    # Insert data
    p_insert(insert_src)

    # Search pipeline
    p_search_pre = (
        p_embed.map('vec', ('search_res'), ops.ann_search.milvus_client(
                    host=HOST, port=PORT, limit=TOPK,
                    collection_name=COLLECTION_NAME))
            .map('search_res', 'pred', lambda x: [str(Path(y[0]).resolve()) for y in x])
    )
    p_search = p_search_pre.output('img_path', 'pred')

    # Load collection
    collection.load()

    # Search for query image(s)
    dc = p_search(query_src)

    # Save search results
    p_search_img = (
        p_search_pre.map('pred', 'pred_images', read_images)
            .output('img', 'pred_images')
    )
    search_results = p_search_img(query_src)
    # DataCollection(search_results).to_directory(output_dir, add_source=True)
    # Save search results to the output directory
    search_results_dir = Path(output_dir) / "search_results"
    search_results_dir.mkdir(parents=True, exist_ok=True)

    # Convert DataQueue to a list of tuples
    search_results_list = search_results.to_list()

    for idx, result in enumerate(search_results_list):
        img_path = result[0]  # Assuming the first element is the image path
        img_list = result[1]  # Assuming the second element is the list of images

        # Save each image to the output directory
        for i, img in enumerate(img_list):
            img_filename = f"result_{idx}_{i}.jpg"
            img_save_path = search_results_dir / img_filename

            # Convert the Image object to a PIL Image object
            pil_img = PILImage.fromarray(img)

            # Save the PIL Image to the output directory
            pil_img.save(img_save_path)            
            
            
        
    # # Evaluation pipeline
    # p_eval = (
    #     p_search_pre.map('img_path', 'gt', ground_truth)
    #         .map(('pred', 'gt'), 'ap', get_ap)
    #         .output('ap')
    # )

    # # Run evaluation pipeline over all test data
    # start = time.time()
    # bm = p_eval(query_src)
    # end = time.time()

    # # Group AP in a list
    # res = DataCollection(bm).to_list()

    # # Calculate mAP
    # mAP = mean([x.ap for x in res])

    # print(f'mAP@{TOPK}: {mAP}')
    # print(f'qps: {len(res) / (end - start)}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reverse Image Search powered by Towhee & Milvus")
    parser.add_argument("--insert-src", type=str, required=True, help="Path to the CSV containing image data for insertion")
    parser.add_argument("--query-src", type=str, required=True, help="Path to the query image")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save search results")
    args = parser.parse_args()

    main(args.insert_src, args.query_src, args.output_dir)