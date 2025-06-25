from fastapi import FastAPI
from pydantic import BaseModel

class AudioPacket(BaseModel):
    #Fileparameter
    upload_url: str 

class FilePacket(BaseModel):
    file_url: str
    upload_url: str

app = FastAPI()

'''
A single route which accepts a signed url to download a music file and processes and send back to a signed url.
'''

