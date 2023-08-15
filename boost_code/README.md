# Reverse Image Search App

This app performs reverse image search using Towhee and Milvus. Given a query image, it finds similar images in a collection and saves the results along with their paths.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/your-repo.git
   ```

2. Install the required packages:

   ```bash
   pip install pymilvus towhee opencv-python-headless pillow
   ```

## Usage

1. Insert images into the collection:

   ```bash
   python search.py --bypass-insert --insert-src /path/to/insert/src.csv --query-src /path/to/query/image.jpg
   ```

2. Search for similar images:

   ```bash
   python search.py --query-src /path/to/query/image.jpg --output-dir /path/to/output/directory
   ```

3. Bypass specific processes:

   ```bash
   python search.py --query-src /path/to/query/image.jpg --bypass-insert
   ```

   ```bash
   python search.py --bypass-query --insert-src /path/to/insert/src.csv
   ```

## Examples

### Insert Images and Search for Similar Images

To insert images into the collection and search for similar images in one command:

```bash
python search.py --bypass-insert --insert-src insert_src.csv --query-src query_image.jpg
```

### Search for Similar Images

To search for similar images based on a query image, provide the query image and specify the output directory:

```bash
python search.py --query-src query_image.jpg --output-dir search_results
```

### Bypass Specific Processes

To bypass either the insertion or query process, use the `--bypass-insert` or `--bypass-query` flags:

```bash
python search.py --query-src query_image.jpg --bypass-insert
```

```bash
python search.py --bypass-query --insert-src insert_src.csv
```

## Output

The app saves search results in the specified output directory. Additionally, a `。sim-imgs.csv` file is created containing the paths of the query image and its similar images.

## Dependencies

- pymilvus
- towhee
- opencv-python-headless
- pillow

