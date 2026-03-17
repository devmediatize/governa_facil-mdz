from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Sistema de Incidências")

templates = Jinja2Templates(directory="templates")
