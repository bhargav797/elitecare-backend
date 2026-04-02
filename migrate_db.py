import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import app.main  # Imports all models so Base.metadata is populated
from app.database import Base

load_dotenv()

# 1. Connect to Local PostgreSQL Database
local_url = "postgresql+psycopg2://postgres:user@localhost:5432/hospital_db"
try:
    local_engine = create_engine(local_url)
    # Test connection
    with local_engine.connect() as conn:
        print("✅ Successfully connected to Local PostgreSQL Database")
except Exception as e:
    print(f"❌ Failed to connect to local database. Ensure your local PostgreSQL is running! Error: {e}")
    exit(1)

# 2. Connect to Remote Neon Database
neon_url = os.getenv("NEON_DATABASE_URL")
if not neon_url:
    print("❌ NEON_DATABASE_URL is missing in .env")
    print("Please add your Neon connection string to the .env file as NEON_DATABASE_URL='...'")
    exit(1)

# Fix driver 
if neon_url.startswith("postgres://"):
    neon_url = neon_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif neon_url.startswith("postgresql://") and not neon_url.startswith("postgresql+psycopg2://"):
    neon_url = neon_url.replace("postgresql://", "postgresql+psycopg2://", 1)

try:
    cloud_engine = create_engine(neon_url)
    with cloud_engine.connect() as conn:
        print("✅ Successfully connected to Cloud Neon Database")
except Exception as e:
    print(f"❌ Failed to connect to Neon. Check your connection string! Error: {e}")
    exit(1)


print("\nStarting migration from Local PostgreSQL to Cloud Neon PostgreSQL...")

# 3. Create tables in the new Neon Cloud DB
Base.metadata.create_all(bind=cloud_engine)

# 4. Copy Data
for table in Base.metadata.sorted_tables:
    print(f"Migrating table: {table.name}...")
    
    try:
        with local_engine.connect() as local_conn:
            result = local_conn.execute(table.select())
            rows = result.fetchall()
            
            if not rows:
                print(f"  -> Skipping {table.name} (0 rows locally)")
                continue
    except Exception as e:
        print(f"  -> Error reading {table.name} locally: {e}")
        continue
        
    print(f"  -> Copied {len(rows)} rows from {table.name}")
    data = [dict(row._mapping) for row in rows]
    
    # Insert safely into cloud postgres
    with cloud_engine.begin() as cloud_conn:
        try:
            cloud_conn.execute(table.delete())
            cloud_conn.execute(table.insert(), data)
        except Exception as e:
            print(f"  -> Error inserting into {table.name}: {e}")

print("\n🚀 Migration complete! All your local data is now in your Neon Database.")
