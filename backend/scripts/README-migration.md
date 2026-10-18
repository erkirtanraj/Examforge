Staged MongoDB to MySQL migration

This is an intermediate preservation importer only; it does not switch the live API to MySQL.

Safety steps:
1. Take and verify a MongoDB backup.
2. Configure MONGO_URL, MONGO_DB_NAME, and DATABASE_URL in a trusted shell; never commit secrets.
3. Install motor, SQLAlchemy, and asyncmy in that environment.
4. Run: python backend/scripts/mongo_to_mysql_staging.py --dry-run
5. Review collection counts and disk capacity.
6. To stage data, set ALLOW_STAGING_IMPORT=YES and rerun without --dry-run.
7. Compare counts and sample payloads before relational normalization.

The importer upserts by (collection_name, id), is rerunnable, and never mutates MongoDB. ef_documents is not the final relational schema. The live API uses Mongo-specific filters, update operators, projections, cursors, upserts and aggregation; those must be converted and tested before production can switch.