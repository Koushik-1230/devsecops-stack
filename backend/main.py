from fastapi import FastAPI, HTTPException, Header, Depends
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

USERS= {
    "admin@test.com": {
        "password": "admin123",
        "role": "admin",
        "org_id": "org123"
    }
}
CLUSTERS = {
    "cluster123": {
        "id" : "c1",
        "name": "Cluster 1",
        "org_id": "org123",
    }
}

METRICS_DB= []

def create_token(data:dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_agent(auth_header: str):
    if not auth_header:
        raise HTTPException(401, "Missing token")
    token = auth_header.split(" ")[1]
    cluster = CLUSTERS.get(token)
    if not cluster:
        raise HTTPException(401, "Invalid token")
    return cluster

@app.post("/auth/login")
def login(email: str, password: str):
    user = USERS.get(email)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"email": email, "role": user["role"], "org_id": user["org_id"]})
    return {"access_token": token}

@app.post("/ingest")
def ingest(data:dict, authorization:str= Header(None)):
    cluster = verify_agent(authorization)

    record = {
        "cluster_id": cluster["id"],
        "cluster_name": cluster["name"],
        "org_id": cluster["org_id"],
        "k8s_nodes": data.get("k8s_nodes"),
        "prometheus": data.get("prometheus"),
        "timestamp": data.get("timestamp")
    }
    METRICS_DB.append(record)
    print(f"Received metrics from {cluster['name']}: {record}")

    return {"status": "stored", "cluster": cluster["name"]}

@app.get("/metrics")
def get_metrics(user=Depends(get_current_user)):
    org_id = user["org_id"]
    return [record for record in METRICS_DB if record["org_id"] == org_id]

@app.get("/metrics/{cluster_name}")
def get_cluster_metrics(cluster_name: str, user=Depends(get_current_user)):
    org_id = user["org_id"]
    return [record for record in METRICS_DB if record["org_id"] == org_id and record["cluster_name"] == cluster_name]

@app.get("/")
def root():
    return {"message": "Welcome to the DevSecOps Metrics API"}