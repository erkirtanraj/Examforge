"""Restore ExamForge data: MONGO_URL=... DB_NAME=... python import_db.py
BSON alternative: mongorestore --uri="$MONGO_URL" --gzip --archive=examforge_db.archive.gz --nsFrom="test_database.*" --nsTo="$DB_NAME.*" --drop"""
import os, glob
from pymongo import MongoClient
from bson import json_util

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
here = os.path.dirname(os.path.abspath(__file__))
for path in sorted(glob.glob(os.path.join(here, "*.json"))):
    name = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        docs = json_util.loads(f.read())
    db[name].delete_many({})
    if docs:
        db[name].insert_many(docs)
    print(f"{name}: {len(docs)}")
