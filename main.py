from fastapi import FastAPI

app = FastAPI(title="Secure API")


@app.get("/health")
def health_check():
	return {"status": "ok"}
