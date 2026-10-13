"""Restore the exported ExamForge data: MONGO_URL=... DB_NAME=... python import_db.py"""
import json, os, glob
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
here = os.path.dirname(os.path.abspath(__file__))
for path in sorted(glob.glob(os.path.join(here, "*.json"))):
    name = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        docs = json.load(f)
    db[name].delete_many({})
    if docs:
        db[name].insert_many(docs)
    print(f"{name}: {len(docs)}")
