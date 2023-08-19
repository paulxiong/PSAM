import csv
from glob import glob
from pathlib import Path
import cv2
from towhee.types.image import Image
import time
import argparse
from PIL import Image as PILImage
import sqlite3  # Add this line to import the sqlite3 module

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

def load_image_from_database(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT path FROM query_image_path")  # Assuming 'images' is the table name
    image_paths = [row[0] for row in cursor.fetchall()]
    connection.close()
    if len(image_paths) > 0:
        return image_paths[-1]  # Return the last image path from the database
    else:
        raise RuntimeError("No image paths found in the database")

def decode_image(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise RuntimeError(f"Error reading image: {image_path}")
        return image
    except Exception as e:
        raise RuntimeError(f"Error reading image: {image_path}, Error: {e}")

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
            try:
                img = cv2.imread(item)
                if img is not None:
                    yield item
                else:
                    print(f"Error reading image: {item}, Skipping.")
            except Exception as e:
                print(f"Error reading image: {item}, Skipping. Error: {e}")


# Create Milvus collection
def create_milvus_collection(collection_name, dim, metric_type):
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
        print("drop {collection_name}")
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
    # Print the collection's items and their paths
    print("Collection created:", collection_name)
    entities = collection.num_entities
    for i in range(entities):
        entity = collection.get_entity_by_id(i)
        print(f"Item Path for entity {i}: {entity.path}")
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

def main(insert_src, query_src, output_dir, bypass_insert, bypass_query):
    # Convert input paths to full paths
    if not bypass_insert and insert_src:
        insert_src = Path(insert_src).resolve().as_posix()
    if not bypass_query and query_src:
        query_src = Path(query_src).resolve().as_posix()
        if query_src.endswith('.db'):
            query_src = load_image_from_database(query_src)
        # else:
        #     query_src = list(load_image(query_src))
        query_src = Path(query_src).resolve().as_posix()

    # Connect to Milvus service
    connections.connect(host=HOST, port=PORT)
    # Embedding pipeline
    p_embed = (
        pipe.input('src')
            .flat_map('src', 'img_path', load_image)
            .map('img_path', 'img', decode_image)
            .map('img', 'vec', ops.image_embedding.timm(model_name=MODEL, device=DEVICE))
    )

    # Create or load collection
    collection = None
    if not bypass_insert and insert_src:
        collection = create_milvus_collection(COLLECTION_NAME, DIM, METRIC_TYPE)
        print(f'A new collection created: {COLLECTION_NAME}')
        p_insert = (
            p_embed.map(('img_path', 'vec'), 'mr', ops.ann_insert.milvus_client(
                        host=HOST,
                        port=PORT,
                        collection_name=COLLECTION_NAME
                        ))
                .output('mr')
        )
        # Execute the p_insert pipeline
        insert_results = p_insert(insert_src)

        # Check for errors in the insert results
        # for result in insert_results.iter():
        #     if result.error:
        #         img_path = result.input['img_path'] if 'img_path' in result.input else None
        #         print(f"Error inserting image: {img_path}, Skipping.")
        #     else:
        #         print("Image inserted successfully:", result.input['img_path'])


    # Search for query image(s) if not bypassed
    if not bypass_query and query_src:
        # Search pipeline
        p_search_pre = (
            p_embed.map('vec', ('search_res'), ops.ann_search.milvus_client(
                        host=HOST, port=PORT, limit=TOPK,
                        collection_name=COLLECTION_NAME))
                .map('search_res', 'pred', lambda x: [str(Path(y[0]).resolve()) for y in x])
        )
        p_search = p_search_pre.output('img_path', 'pred')

        # Search for query image(s)
        dc = p_search(query_src)
        # Save search results
        p_search_img = (
            p_search_pre.map('pred', 'pred_images', read_images)
                .output('img', 'pred_images')
        )
        search_results = p_search_img(query_src)
    
        # Save search results to the output directory
        search_results_dir = Path(output_dir) / "search_results"
        search_results_dir.mkdir(parents=True, exist_ok=True)

        # Convert DataQueue to a list of tuples
        search_results_list = search_results.to_list()
        
        for idx, result in enumerate(search_results_list):
            img_path = result[0]  # Assuming the first element is the query images 
            img_list = result[1]  # Assuming the second element is the list of images

            # Save each image to the output directory
            for i, img in enumerate(img_list):
                try:
                    img_filename = f"result_{idx}_{i}.jpg"
                    img_save_path = search_results_dir / img_filename

                    # Convert the Image object to a PIL Image object
                    pil_img = PILImage.fromarray(img)

                    # Save the PIL Image to the output directory
                    pil_img.save(img_save_path)
                except Exception as e:
                    print(f"Error saving image: {img_filename}, Skipping. Error: {e}")
                    
        #boost_ai: in addition to original return, the search_results_list 
        # should also return a image's path, which is identical to where it read, 
        # the one in imgs.csv. So please modify needed code for this.
        # Get image paths for returned IDs
        # p_paths = (
        #     p_search
        #         .map('pred', 'ids', lambda x: [{'id': id} for id in x]) 
        #         .map('ids', 'paths', ops.retrieve.milvus(HOST, PORT, COLLECTION_NAME))
        # )

        # Convert DataQueue to a list of tuples
        search_results_list = dc.to_list()
        # Write the similar image paths to a CSV file
        # Get the directory path of the --insert-src file
        sim_img_csv="。sim-imgs.csv"
        try:
            insert_src_dir = Path(insert_src).resolve().parent
            # Combine the directory path with the sim-img.csv filename
            csv_file_path = insert_src_dir / sim_img_csv 
        except:
            csv_file_path = Path(output_dir) / sim_img_csv
        with open(csv_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["id", "path", "label"])  # Write the header
            for idx, result in enumerate(search_results_list):
                img_path = result[0]  # Get the query image's path
                similar_paths = result[1]  # Get the paths of similar images
                # Write query image info
                query_image_id = idx
                csv_writer.writerow([query_image_id, img_path, "null"])
        
                # Loop through similar images and write their info
                for similar_path in similar_paths:
                    query_image_id += 1  # Increase the id for each similar image
                    csv_writer.writerow([query_image_id, similar_path, "null"])
        print(f"Similar image paths written to {csv_file_path}")
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
    parser.add_argument("--insert-src", type=str, help="Path to the CSV containing image data for insertion")
    parser.add_argument("--query-src", type=str, help="Path to the query image")
    parser.add_argument("--output-dir", type=str,default=".", help="Directory to save search results")
    parser.add_argument("--bypass-insert", action="store_true", help="Bypass the --insert-src process")
    parser.add_argument("--bypass-query", action="store_true", help="Bypass the --query-src process")
    args = parser.parse_args()

    main(args.insert_src, args.query_src, args.output_dir, args.bypass_insert, args.bypass_query)
