from app.db.database import Base, engine
import app.models.actual_costs

Base.metadata.create_all(bind=engine)
print("Tables created.")
