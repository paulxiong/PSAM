""" standalone.py based on pymilvus """
import random
import multiprocessing
from milvus import default_server
import socket


from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection,
    utility
)

# This example shows how to:
#   1. connect to Milvus server
#   2. create a collection
#   3. insert entities
#   4. create index
#   5. search
# Optional, if you want store all related data to specific location
# default it wil using ~/.milvus-io/milvus-server/<__version_of_milvus__>

def start_milvus_server():
    default_server.set_base_dir('uhella')
    default_server.start()

_HOST = '127.0.0.1'
# The port may be changed, by default it's 19530
_PORT = default_server.listen_port

# Const names
_COLLECTION_NAME = 'demo'
# _COLLECTION_NAME = 'reverse_image_search'
_ID_FIELD_NAME = 'id_field'
_VECTOR_FIELD_NAME = 'float_vector_field'

# Vector parameters
_DIM = 128
_INDEX_FILE_SIZE = 32  # max file size of stored index

# Index parameters
_METRIC_TYPE = 'L2'
_INDEX_TYPE = 'IVF_FLAT'
_NLIST = 1024
_NPROBE = 16
_TOPK = 3


# Create a Milvus connection
import time

def create_connection():
    print(f"\nCreate connection...")
    start_time = time.time()
    timeout = 150  # Timeout in seconds
    while time.time() - start_time < timeout:
        try:
            connections.connect(host=_HOST, port=_PORT)
            print(f"\nList connections:")
            print(connections.list_connections())
            return True # Connection successful, exit the function
        except Exception as e:
            print(f"Connection error: {e}")
            time.sleep(1)  # Wait for 1 second before retrying
    print("Connection timeout. Exiting...")
    return False  # Exit the program if connection fails after timeout

# Create a collection named 'demo'
def create_collection(name, id_field, vector_field):
    field1 = FieldSchema(name=id_field, dtype=DataType.INT64, description="int64", is_primary=True)
    field2 = FieldSchema(name=vector_field, dtype=DataType.FLOAT_VECTOR, description="float vector", dim=_DIM,
                         is_primary=False)
    schema = CollectionSchema(fields=[field1, field2], description="collection description")
    collection = Collection(name=name, data=None, schema=schema, properties={"collection.ttl.seconds": 15})
    print("\ncollection created:", name)
    return collection


def has_collection(name):
    return utility.has_collection(name)


# Drop a collection in Milvus
def drop_collection(name):
    collection = Collection(name)
    collection.drop()
    print("\nDrop collection: {}".format(name))


# List all collections in Milvus
def list_collections():
    print("\nlist collections:")
    print(utility.list_collections())


def insert(collection, num, dim):
    data = [
        [i for i in range(num)],
        [[random.random() for _ in range(dim)] for _ in range(num)],
    ]
    collection.insert(data)
    return data[1]


def get_entity_num(collection):
    print("\nThe number of entity:")
    print(collection.num_entities)


def create_index(collection, filed_name):
    index_param = {
        "index_type": _INDEX_TYPE,
        "params": {"nlist": _NLIST},
        "metric_type": _METRIC_TYPE}
    collection.create_index(filed_name, index_param)
    print("\nCreated index:\n{}".format(collection.index().params))


def drop_index(collection):
    collection.drop_index()
    print("\nDrop index sucessfully")


def load_collection(collection):
    collection.load()


def release_collection(collection):
    collection.release()


def search(collection, vector_field, id_field, search_vectors):
    search_param = {
        "data": search_vectors,
        "anns_field": vector_field,
        "param": {"metric_type": _METRIC_TYPE, "params": {"nprobe": _NPROBE}},
        "limit": _TOPK,
        "expr": "id_field >= 0"}
    results = collection.search(**search_param)
    for i, result in enumerate(results):
        print("\nSearch result for {}th vector: ".format(i))
        for j, res in enumerate(result):
            print("Top {}: {}".format(j, res))


def set_properties(collection):
    collection.set_properties(properties={"collection.ttl.seconds": 1800})

MILVUS_SERVER_ADDRESS = ('127.0.0.1', 19530)

def is_milvus_server_running():
    # Try to connect to the Milvus server
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(MILVUS_SERVER_ADDRESS)
        return True  # Milvus server is running
    except (ConnectionRefusedError, OSError):
        return False  # Milvus server is not running

def main():
    if not is_milvus_server_running():
        # start the Milvus server in a separate process
        milvus_process = multiprocessing.Process(target=start_milvus_server)
        milvus_process.daemon = True
        milvus_process.start()
    else:
        print("Milvus server is already running")    
    # create a connection
    create_connection()

    # drop collection if the collection exists
    if has_collection(_COLLECTION_NAME):
        # list_collections()
        # List all collections
        collections = utility.list_collections()

        # Find the collection by name
        target_collection = None
        for collection in collections:
            print(f'collection name: {Collection(collection).name}')
            print(f'entity_count: {Collection(collection).num_entities}')
            # if collection.name == collection_name:
            #     target_collection = collection
            #     break

        if target_collection is not None:
            # Get the number of entities in the collection
            entity_count = target_collection.num_entities
            return entity_count
        
    #     drop_collection(_COLLECTION_NAME)

    # create collection
    collection = create_collection(_COLLECTION_NAME, _ID_FIELD_NAME, _VECTOR_FIELD_NAME)

    # alter ttl properties of collection level
    set_properties(collection)

    # show collections
    list_collections()

    # insert 10000 vectors with 128 dimension
    vectors = insert(collection, 10000, _DIM)

    collection.flush()
    # get the number of entities
    get_entity_num(collection)

    # create index
    create_index(collection, _VECTOR_FIELD_NAME)

    # load data to memory
    load_collection(collection)

    # search
    # search(collection, _VECTOR_FIELD_NAME, _ID_FIELD_NAME, vectors[:3])

    # release memory
    # release_collection(collection)

    # drop collection index
    # drop_index(collection)

    # drop collection
    # drop_collection(_COLLECTION_NAME)


if __name__ == '__main__':
    main()
