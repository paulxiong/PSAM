from pymilvus import Collection, connections,utility

_HOST = '127.0.0.1'
_PORT = 19530

def connect_to_milvus(host, port):
    # Connect to the Milvus server
    connections.connect(host=host, port=port)

def get_collections():
    # List all collections
    return utility.list_collections()
    # collection_names = Collection.list_names()

    # collections = []
    # for collection_name in collection_names:
    #     collection = Collection(collection_name)
    #     collections.append(collection)

    # return collections

def print_collection_entity_counts():
    connect_to_milvus(_HOST, _PORT)
    collections = get_collections()

    if collections:
        print("Collection Entity Counts:")
        for collection in collections:
            entity_count = Collection(name=collection).num_entities
            collection_name = collection
            print(f"Collection: {collection_name}, Entity Count: {entity_count}")
    else:
        print("No collections found.")

if __name__ == '__main__':
    print_collection_entity_counts()
