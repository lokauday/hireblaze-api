from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Note: Models are imported in init_db() function to avoid circular imports
# All models must import Base from this module
