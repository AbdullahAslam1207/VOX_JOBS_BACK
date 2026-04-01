from fastapi import FastAPI,Path, HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel,EmailStr
from typing import List, Annotated
from Database import Tables as search_models
from Auth_service import models as auth_models

from sqlalchemy.orm import Session

from Auth_service import auth as auth_service
from CRUD import CRUD as CRUD
from Scrapping import scrape as Scrapping
from conversations import router as conversation_router
from Apply_Now import router as apply_router



app = FastAPI()
app.include_router(auth_service.router)
app.include_router(CRUD.router)
app.include_router(Scrapping.router)
app.include_router(conversation_router)
app.include_router(apply_router.router)


origin = "http://localhost:5173"  # Adjust this to your frontend URL

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)