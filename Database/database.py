from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#URL_DATABASE = "postgresql://postgres:WQ4G4hiP&9DVgAq@db.fhnsslvedulvfzwjbbph.supabase.co:5432/postgres"
URL_DATABASE ="postgresql://postgres:0000@localhost:5432/Fyp"
engine = create_engine(URL_DATABASE)

sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
