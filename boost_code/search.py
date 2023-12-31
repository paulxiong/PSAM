import csv
from glob import glob
from pathlib import Path
import cv2
from pillow_heif import register_heif_opener 
from towhee.types.image import Image
import time
import argparse
from PIL import Image as PILImage
import sqlite3  # Add this line to import the sqlite3 module

from towhee import pipe, ops, DataCollection
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
import numpy as np

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
# global DB_path  # Declare DB_path as a global variable and initialize it
register_heif_opener()

def load_image_from_database(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT path FROM query_image_path WHERE op='ping'")  # Assuming 'images' is the table name
    image_paths = [row[0] for row in cursor.fetchall()]
    if len(image_paths) > 0:
        last_image_path = image_paths[-1]
        cursor.execute("UPDATE query_image_path SET op = ? WHERE path = ?", ('pong', last_image_path))
        connection.commit()
        connection.close()
        return last_image_path
    else:
        connection.close()
        print("No query image found in the database by SELECT path FROM query_image_path WHERE op='ping'")
        return None

# def decode_image(image_path):
#     try:
#         image = cv2.imread(image_path)
#         if image is None:
#             raise RuntimeError(f"Error reading image: {image_path}")
#         return image
#     except Exception as e:
#         raise RuntimeError(f"Error reading image: {image_path}, Error: {e}")
def decode_image(image_path):
    try:
        if image_path.lower().endswith('.heic'):
            pil_image = PILImage.open(image_path)
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            # heif_file = pyheif.read(image_path)
            # image = cv2.cvtColor(heif_file.to_rgb().tobytes(), cv2.COLOR_RGB2BGR)
        else:
            image = cv2.imread(image_path)
        
        if image is None:
            raise RuntimeError(f"Error reading None image: {image_path}")
        
        return image
    except Exception as e:
        raise RuntimeError(f"Error reading image in decode_image: {image_path}, Error: {e}")

        
#update images to image_database.db
def update_imgs_in_db(loading_path):
    global DB_path  # Add this line to indicate that you're modifying the global variable

    if DB_path:
        connection = sqlite3.connect(DB_path)
        print("update_imgs_in_db established: {DB_path}")
    else:
        print("update_imgs_in_db Error: DB_path is NULL")
    cursor = connection.cursor()
    if loading_path is None:
        print("update_imgs_in_db is None")
    for path in loading_path:
        cursor.execute("INSERT INTO img_path (path) VALUES (?)", (path,))
        print(f'loading_path: {path}')
        connection.commit()
    connection.close()
        

# Load image path: read imgs.csv, appendto loadig_path. Note: non-csv supprt may have issues.
loading_path=[]
def load_image(x):
    print(f'insert loadin_image reading {x}')

    # x='/Users/boxiong/Downloads/test/1.csv'
    if x.endswith('csv'):
        with open(x) as f:
            reader = csv.reader(f)
            next(reader)
            for item in reader:
                print(item)
                if len(item) < 2:
                    print("inserting image: None")
                else:
                    print(f"inserting image: {item[1]}")
                    loading_path.append(item[1])
                    yield item[1]
    else:
        for item in glob(x):
            try:
                image_path = item
                if image_path.lower().endswith('.heic'):
                    pil_image = PILImage.open(image_path)
                    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    # img = pyheif.read(image_path)
                    # img = cv2.cvtColor(heif_file.to_rgb().tobytes(), cv2.COLOR_RGB2BGR)    
                else:
                    img = cv2.imread(item)
                if img is not None:
                    yield item
                else:
                    print(f"Error reading image: {item}, Skipping.")
            except Exception as e:
                print(f"Error reading image: {item}, Skipping. Error: {e}")

# Create Milvus collection
def create_milvus_collection(collection_name, dim, metric_type):
    if not utility.has_collection(collection_name):
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
    else:
            collection = Collection(name=collection_name)
            print("Collection already exists:", collection_name)
    return collection

# Load and read images
def read_images(img_paths):
    imgs = []
    for p in img_paths:
        # imgs.append(Image(cv2.imread(p), 'BGR'))
        if p.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif','webp')):
            # If the file has a common image extension, use cv2.imread
            imgs.append(cv2.imread(p))
        elif p.lower().endswith('.heic'):
            pil_image = PILImage.open(p)
            img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            imgs.append(img)
        else:
            raise ValueError(f"Unsupported image format for file: {p}")
            
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

    global DB_path
    DB_path = Path(query_src).resolve().as_posix() 
    print(f"DB_path : {DB_path}")
    if not bypass_insert and insert_src:
        insert_src = Path(insert_src).resolve().as_posix()
        print(f'main insert_src {insert_src}')
    if not bypass_query and query_src:
        query_src = Path(query_src).resolve().as_posix()
        if query_src.endswith('.db'):
            query_src = load_image_from_database(query_src)
        # else:
        #     query_src = list(load_image(query_src))
        if query_src:
            query_src = Path(query_src).resolve().as_posix()
        else:
            print("No query image, exit")
            return
    # Connect to Milvus service
    connections.connect(host=HOST, port=PORT)
    # Embedding pipeline
    p_embed = (
        pipe.input('src')
            .flat_map('src', 'img_path', load_image)
            .map('img_path', 'img', decode_image)
            .map('img_path', 'img_path', lambda img_path: (img_path, print(img_path))[0]) #this line is for debug only, can be removed
            .map('img', 'vec', ops.image_embedding.timm(model_name=MODEL, device=DEVICE))
            .map('vec', 'vec', lambda vec: (vec, print(vec))[0]) #this line is for debug only, can be removed
    )

    # Create or load collection
    collection = None
    if not bypass_insert and insert_src:
        collection = create_milvus_collection(COLLECTION_NAME, DIM, METRIC_TYPE)
        print(f'The collection found: {COLLECTION_NAME}')
        p_insert = (
            p_embed.map('img_path', 'img_path', lambda img_path: (img_path, print('<<< '+img_path))[0]) #this line is for debug only, can be removed
                .map(('img_path', 'vec'), 'mr', ops.ann_insert.milvus_client(
                        host=HOST,
                        port=PORT,
                        collection_name=COLLECTION_NAME
                        ))
                .map('img_path', 'img_path', lambda img_path: (img_path, print('>>> '+img_path))[0])
                .output('mr')
            # p_embed.map('img_path', 'img_path', lambda img_path: (img_path, print('<<< '+img_path))[0]) #this line is for debug only, can be removed
            #     .map(['img_path', 'vec'], 'mr',collection.insert)
            #     .map('img_path', 'img_path', lambda img_path: (img_path, print('>>> '+img_path))[0])
            #     .output('mr')
        )
        # Execute the p_insert pipeline
        try:
            print('<<< Number of data inserted:', collection.num_entities)
            insert_results = p_insert(insert_src)
            print('Insertion successful Number of data inserted:', collection.num_entities,'>>>')
        except Exception as e:
            print("Exception occurred:", e)
        
        # insert_results = p_insert(insert_src)

        # try:
        #     result = p_insert(insert_src).result()
        #     insert_results = result.get('mr')  # Assuming 'mr' is the output key
        #     if insert_results:
        #         print("Insertion successful")
        #     else:
        #         print("Insertion failed")
        # except Exception as e:
        #     print("Exception occurred:", e)        
        
        
        update_imgs_in_db(loading_path)
        # Convert DataQueue to a list and then iterate over the list
        # insert_results_list = insert_results.to_list()
        # for result in insert_results_list:
        #     if result.error:
        #         img_path = result.input['img_path'] if 'img_path' in result.input else None
        #         print(f"Error inserting image: {img_path}, Skipping.")
        #     else:
        #         print("Image inserted successfully:", result.input['img_path'])

    # Search for query image(s) if not bypassed
    if not bypass_query and query_src:
        print("search began <<<")
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
    
        print("search ended >>>")
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
                print(f"Similar image {similar_paths} written to {csv_file_path}")
        
                # Loop through similar images and write their info
                for similar_path in similar_paths:
                    query_image_id += 1  # Increase the id for each similar image
                    csv_writer.writerow([query_image_id, similar_path, "null"])
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
    print(f'__main__ {args.insert_src}')
    main(args.insert_src, args.query_src, args.output_dir, args.bypass_insert, args.bypass_query)
