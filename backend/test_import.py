import traceback
try:
    from app.main import app
    print("Success importing main!")
except Exception as e:
    traceback.print_exc()
