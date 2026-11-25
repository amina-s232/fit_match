from app.services.extractor import BACKEND, MODEL, ping

print(f"Backend: {BACKEND}, model: {MODEL}")
print("Reply:", ping())
