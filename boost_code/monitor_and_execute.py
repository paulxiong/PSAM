import sys
import time
import subprocess
import os
import sqlite3
import csv

# Boost-AI-began: new func: after detected file_to_monitor, it should be a database, named images_database.db, changed,
def create_img_path_table(db_connection):
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS img_path (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL);''')
    path="abcdefg"
    cursor.execute("INSERT INTO img_path (path) VALUES (?)", (path,))                        
    cursor.execute('''CREATE TABLE IF NOT EXISTS last_insert_csv_path (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        path TEXT NOT NULL);''')
    db_connection.commit()

def retrieve_csv_path(db_connection,tablex):
    cursor = db_connection.cursor()
    query = f"SELECT path FROM {tablex} LIMIT 1;"
    cursor.execute(query)
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def update_last_insert_csv_path(db_connection, new_path):
    cursor = db_connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='last_insert_csv_path';")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Check if there are any rows in the table
        cursor.execute("SELECT COUNT(*) FROM last_insert_csv_path;")
        row_count = cursor.fetchone()[0]
        if row_count > 0:
            # If there are rows, update the existing record
            cursor.execute("UPDATE last_insert_csv_path SET path = ? WHERE id = ?", (new_path, 1))
        else:
            cursor.execute("INSERT INTO last_insert_csv_path (path) VALUES (?)", (new_path,))
            
    else:
        # If the table doesn't exist, create it and insert a record
        cursor.execute('''CREATE TABLE last_insert_csv_path (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            path TEXT NOT NULL);''')
        cursor.execute("INSERT INTO last_insert_csv_path (path) VALUES (?)", (new_path,))
    db_connection.commit()

def mark_csv_path_as_processed(db_connection, processed_path):
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM insert_csv_path WHERE path = ?", (processed_path,))
    db_connection.commit()

def process_external_csv(db_connection, external_csv_path):
    new_path_list=[]
    cursor = db_connection.cursor()
    with open(external_csv_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # Skip header
        for row in csv_reader:
            if len(row) == 3:
                _, path, _ = row
                cursor.execute("SELECT * FROM img_path WHERE path=?", (path,))
                existing_path = cursor.fetchone()
                if not existing_path:
                    # cursor.execute("INSERT INTO img_path (path) VALUES (?)", (path,))
                    # db_connection.commit()
                    new_path_list.append(path)
                else:
                    with open(external_csv_path, 'r+') as csv_file:
                        csv_content = csv_file.read()
                        csv_file.seek(0)
                        csv_file.write(csv_content.replace(','.join(row), '', 1))
                        csv_file.truncate()
            else:
                print(f"Ignoring row with unexpected number of values: {row}")
        db_connection.commit()
    return new_path_list


def main(file_to_monitor, python_script, *python_args):
    print("Monitoring started...")

    # Wait for the file to appear
    while not os.path.exists(file_to_monitor):
        print(f"Waiting for {file_to_monitor} to appear...")
        time.sleep(1)

    last_modified = os.path.getmtime(file_to_monitor)
    db_connection = sqlite3.connect(file_to_monitor)
    try:
        create_img_path_table(db_connection)
        
        while True:
            time.sleep(1)
            current_modified = os.path.getmtime(file_to_monitor)
            if current_modified != last_modified:
                last_modified = current_modified
                print("File modified. Updating image paths and executing Python script...")

                insert_csv_path = retrieve_csv_path(db_connection,"insert_csv_path")
                if insert_csv_path:
                    mark_csv_path_as_processed(db_connection, insert_csv_path)  # Mark path as processed
                    update_last_insert_csv_path(db_connection, insert_csv_path)  # Update or create table
                    if os.path.exists(insert_csv_path) and process_external_csv(db_connection, insert_csv_path):
                        insert_csv_path = f'{insert_csv_path}'
                        print(f'*******************   insert ****************')
                        print(["python3", python_script, "--bypass-query", "--insert-src", insert_csv_path,"--query-src",file_to_monitor])
                        print("\n")
                        subprocess.run(["python3", python_script, "--bypass-query", "--insert-src", insert_csv_path,"--query-src",file_to_monitor])
               # boost-ai-began: add a table "last-insert-src-path-dir" to database;
                last_insert_csv_path =retrieve_csv_path(db_connection,"last_insert_csv_path")
                if last_insert_csv_path:

                    cursor = db_connection.cursor()
                    cursor.execute("SELECT path FROM query_image_path WHERE op='ping'")  # Assuming 'images' is the table name
                    image_paths = [row[0] for row in cursor.fetchall()]
                    if len(image_paths) > 0:
                        python_args = ["--bypass-insert", "--insert-src", last_insert_csv_path, "--query-src", file_to_monitor]
                        print(f'*******************   Search ****************')
                        print(["python3", python_script] + python_args)
                        print("\n")
                        # db_connection.close()
                        subprocess.run(["python3", python_script] + python_args)
                    else:
                        # db_connection.close()
                        print("No query image found in the database by SELECT path FROM query_image_path WHERE op='ping'")
                else:
                    print( "No last_insert_csv_path " )
    except KeyboardInterrupt:
        print("Monitoring stopped.")
    finally:
        db_connection.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 monitor_and_execute.py <file_to_monitor> <python_script> [python_args ...]")
    else:
        file_to_monitor = sys.argv[1]
        python_script = sys.argv[2]
        python_args = sys.argv[3:]
        main(file_to_monitor, python_script, *python_args)
# following line is the cmd should run as the back end of TikTok Clone.
# python monitor_and_execute.py /Users/boxiong/Library/Containers/com.example.tiktokClone/Data/Documents/image_database.db search.py 
