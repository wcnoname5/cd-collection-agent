from . import cd_agent
import os

import google.auth
from dotenv import load_dotenv

load_dotenv()

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ["GOOGLE_CLOUD_LOCATION"]="global"
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

from . import agent
