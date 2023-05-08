from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

from add_establishment import add_location
from get_establishments import get_establishments

app = FastAPI()

class Establishment(BaseModel):
    name: str

class SearchTerm(BaseModel):
    term: str


@app.post("/add_establishment/")
async def add_establishment(establishment: Establishment):
    result = add_location(establishment.name)
    print(result)

    ## You may want to check that details were successfully retrieved before calling add to json:
    if result:
        return {"status": "success"}
    else:
        return {"status": "failed"}
    
@app.post("/search_establishments/")
async def search_establishments(search_term: SearchTerm):
    result = get_establishments(search_term.term)
    if result: 
        return {"result": result}
    else:
        return {"status": "No results found."}