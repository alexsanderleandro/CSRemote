# Adicionar estas linhas após os imports existentes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models import Base
target_metadata = Base.metadata