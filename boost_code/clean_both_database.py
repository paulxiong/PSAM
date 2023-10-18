import os
import pymilvus # Changed to pymilvus
from pymilvus import CollectionSchema # Changed to pymilvus
import subprocess

# Delete file 
files =[ '/Users/boxiong/Library/Containers/com.example.tiktokClone/Data/Documents/image_database.db',
            '/Users/boxiong/Documents/image_database.db'
]
for file in files:
    if os.path.exists(file):
        print(f'removed:{file}')
        os.remove(file)
    else:
        print(f'removing (not found) {file}  ')

# Launch Docker if not running   
# result = subprocess.run(['docker', 'ps'], stdout=subprocess.PIPE).stdout.decode('utf-8')
# if 'boost_code' not in result:
#     print('Docker not running, starting it now...')
#     subprocess.run(['docker', 'start', 'boost_code'], check=True)
    
# Connect to Milvus
milvus = pymilvus.Milvus('localhost', '19530') # Changed to pymilvus 

# Drop collection
milvus.drop_collection(collection_name='reverse_image_search') 
print(f'removed:reverse_image_search in Milvus')

# Additional task
# subprocess.run(['python', 'monitor_and_execute.py', 
#                 '/Users/boxiong/Library/Containers/com.example.tiktokClone/Data/Documents/image_database.db', 
#                 'search.py'])