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
   python app.py --insert-src /path/to/insert/src.csv
   ```

2. Search for similar images:

   ```bash
   python app.py --query-src /path/to/query/image.jpg --output-dir /path/to/output/directory
   ```

3. Bypass specific processes:

   ```bash
   python app.py --query-src /path/to/query/image.jpg --bypass-insert
   ```

   ```bash
   python app.py --insert-src /path/to/insert/src.csv --bypass-query
   ```

## Examples

### Insert Images

To insert images into the collection, provide a CSV file with image paths:

```bash
python app.py --insert-src insert_src.csv
```

### Search for Similar Images

To search for similar images based on a query image, provide the query image and specify the output directory:

```bash
python app.py --query-src query_image.jpg --output-dir search_results
```

### Bypass Specific Processes

To bypass either the insertion or query process, use the `--bypass-insert` or `--bypass-query` flags:

```bash
python app.py --query-src query_image.jpg --bypass-insert
```

```bash
python app.py --insert-src insert_src.csv --bypass-query
```

## Output

The app saves search results in the specified output directory. Additionally, a `sim-img.csv` file is created containing the paths of the query image and its similar images.

## Dependencies

- pymilvus
- towhee
- opencv-python-headless
- pillow

