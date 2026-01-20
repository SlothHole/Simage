import csv
import os
from typing import List, Dict, Any

def amend_records_csv(csv_path: str, updates: List[Dict[str, Any]], key_field: str = "file_name") -> None:
    """
    Amend records.csv in place: update rows matching key_field with new data from updates.
    Backup the original file before writing.
    """
    backup_path = csv_path + ".bak"
    if not os.path.exists(backup_path):
        os.replace(csv_path, backup_path)
    else:
        os.remove(csv_path)
        os.replace(backup_path, csv_path)
        os.replace(csv_path, backup_path)
    with open(backup_path, "r", encoding="utf-8", newline="") as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys() if reader else []
    # Build update map
    update_map = {u[key_field]: u for u in updates}
    new_rows = []
    for row in reader:
        k = row[key_field]
        if k in update_map:
            row.update(update_map[k])
        new_rows.append(row)
    # Add new rows for any updates not present
    for k, u in update_map.items():
        if not any(row[key_field] == k for row in new_rows):
            new_rows.append(u)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in new_rows:
            writer.writerow(row)
