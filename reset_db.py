import os

if os.path.exists("documents.db"):
    os.remove("documents.db")
    print("Database reset successfully.")
else:
    print("Database does not exist.")
