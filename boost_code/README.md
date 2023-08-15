# Reverse Image Search App

This app performs reverse image search using Towhee and Milvus. Given a query image, it finds similar images in a collection and saves the results along with their paths.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/your-repo.git
   ```

2. Install the required packages:

   ```bash
   pip install pymilvus==2.2.1 towhee opencv-python-headless pillow
   ```
3. Launch Milvus docker:

   ```bash
   docker-compose up -d
   ```
   This command starts all the services defined in your docker-compose.yml file and runs them in the background (detached mode).
   
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
### Insert Images Only, Searching later

To insert images into dabase only:

```bash
python search.py --bypass-query --insert-src /path/to/insert/src.csv
```

### Search for Similar Images and output to `。sim-imgs.csv`

To search for similar images and output `/your_dir/。sim-imgs.csv` in one command:

```bash
python search.py --bypass-insert --insert-src /your_dir/insert_src.csv --query-src query_image.jpg
```
(`--insert-src /your_dir/insert_src.csv` will not really apply but given `。sim-imgs.csv` a directory. )

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

