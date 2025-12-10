from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.db.models.subscription import Subscription
