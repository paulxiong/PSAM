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
    db_connection.commit()

def retrieve_csv_path(db_connection):
    cursor = db_connection.cursor()
    cursor.execute("SELECT path FROM insert_csv_path LIMIT 1;")
    result = cursor.fetchone()
    if result:
        return result[0]
    return None
def mark_csv_path_as_processed(db_connection, processed_path):
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM insert_csv_path WHERE path = ?", (processed_path,))
    db_connection.commit()

def process_external_csv(db_connection, external_csv_path):
    cursor = db_connection.cursor()
    with open(external_csv_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # Skip header
        for row in csv_reader:
            _, path, _ = row
            cursor.execute("SELECT * FROM img_path WHERE path=?", (path,))
            existing_path = cursor.fetchone()
            if not existing_path:
                cursor.execute("INSERT INTO img_path (path) VALUES (?)", (path,))
                db_connection.commit()
            else:
                with open(external_csv_path, 'r+') as csv_file:
                    csv_content = csv_file.read()
                    csv_file.seek(0)
                    csv_file.write(csv_content.replace(','.join(row), '', 1))
                    csv_file.truncate()
        db_connection.commit()

def main(file_to_monitor, python_script, *python_args):
    print("Monitoring started...")
    last_modified = os.path.getmtime(file_to_monitor)

    # db_connection = sqlite3.connect("images_database.db")
    db_connection = sqlite3.connect(file_to_monitor)
    try:
        create_img_path_table(db_connection)
        
        while True:
            time.sleep(1)
            current_modified = os.path.getmtime(file_to_monitor)
            if current_modified != last_modified:
                last_modified = current_modified
                print("File modified. Updating image paths and executing Python script...")

                insert_csv_path = retrieve_csv_path(db_connection)
                if insert_csv_path:
                    process_external_csv(db_connection, insert_csv_path)
                    mark_csv_path_as_processed(db_connection, insert_csv_path)  # Mark path as processed
                    if os.path.exists(insert_csv_path):
                        subprocess.run(["python3", python_script, "--bypass-query", "--insert-src", insert_csv_path])
                subprocess.run(["python3", python_script] + list(python_args))                        
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
