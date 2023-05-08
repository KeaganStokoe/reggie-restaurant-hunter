from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

from add_establishment import add_location

app = FastAPI()

class Establishment(BaseModel):
    name: str

@app.post("/add_establishment/")
async def add_establishment(establishment: Establishment):
    result = add_location(establishment.name)
    print(result)

    ## You may want to check that details were successfully retrieved before calling add to json:
    if result:
        return {"status": "success"}
    else:
        return {"status": "failed"}