from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
import httpx
import re
import time

app = FastAPI(title="Backlink Analyzer API", version="1.1")

# =======================
# CORS (WordPress Safe)
# =======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WP plugin use karega to issue nahi hoga
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# Models
# =======================
class DomainRequest(BaseModel):
    domain: str

# =======================
# Simple Rate Limiter
# =======================
RATE_LIMIT = {}
LIMIT = 5          # 5 requests
WINDOW = 60        # per 60 seconds

def is_allowed(ip: str) -> bool:
    now = time.time()
    hits = RATE_LIMIT.get(ip, [])
    hits = [t for t in hits if now - t < WINDOW]

    if len(hits) >= LIMIT:
        return False

    hits.append(now)
    RATE_LIMIT[ip] = hits
    return True

# =======================
# Domain Validation
# =======================
DOMAIN_REGEX = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.[A-Za-z]{2,}$"

def validate_domain(domain: str):
    if not re.match(DOMAIN_REGEX, domain):
        raise HTTPException(status_code=400, detail="Invalid domain format")

# =======================
# HTML Parser
# =======================
def parse_backlinks(html: str):
    soup = BeautifulSoup(html, "html.parser")

    stats = {}
    for block in soup.select(".statistic"):
        try:
            value = block.find("h3").get_text(strip=True).replace(",", "")
            label = block.find("span").get_text(strip=True)
            stats[label] = int(value)
        except Exception:
            continue

    backlinks = []
    for tr in soup.select("#backlinks tbody tr"):
        try:
            tds = tr.find_all("td")
            backlinks.append({
                "page_title": tds[1].select_one("strong[data-key='title']").get_text(strip=True),
                "source_url": tds[1].select_one("a[data-key='url']")["href"],
                "anchor_text": tds[2].select_one("strong[data-key='title']").get_text(strip=True),
                "target_url": tds[2].select_one("a[data-key='url']")["href"],
                "pa": int(tds[3].select_one(".value").text),
                "da": int(tds[4].select_one(".value").text),
                "found_date": tds[5].get_text(strip=True)
            })
        except Exception:
            continue

    return stats, backlinks

# =======================
# Routes
# =======================
@app.get("/")
def home():
    return {
        "message": "Backlink Analyzer API",
        "status": "running"
    }

@app.post("/analyze")
async def analyze(request: Request, payload: DomainRequest):
    client_ip = request.client.host

    if not is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    domain = payload.domain.strip().lower()
    validate_domain(domain)

    url = "https://rankifyer.com/free-seo-tools/embed"

    params = {
        "id": "high-quality-backlinks",
        "ref": "https://rankifyer.com/backlink-checker/",
        "ref_hash": "ffd9bb20bb21736b47a1de5a39d1cdd3d382adcb50991497866ca45107878088",
        "h": "0",
        "r": "423b01",
        "site": domain,
        "exp": "1767834165"
    }

    headers = {
        "user-agent": "Mozilla/5.0",
        "accept": "text/html"
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Source service error")

        stats, backlinks = parse_backlinks(response.text)

        return {
            "success": True,
            "domain": domain,
            "stats": stats,
            "total_backlinks": len(backlinks),
            "backlinks": backlinks
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
