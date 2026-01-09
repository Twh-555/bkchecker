import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

st.set_page_config(page_title="Backlink Analyzer", layout="wide")
st.title("Backlink Analyzer")

def parse_backlinks(html):
    soup = BeautifulSoup(html, "html.parser")

    stats = {}
    for block in soup.select(".statistic"):
        value = block.find("h3").get_text(strip=True).replace(",", "")
        label = block.find("span").get_text(strip=True)
        stats[label] = int(value)

    rows = []
    for tr in soup.select("#backlinks tbody tr"):
        tds = tr.find_all("td")
        rows.append({
            "Page Title": tds[1].select_one("strong[data-key='title']").get_text(strip=True),
            "Source URL": tds[1].select_one("a[data-key='url']")["href"],
            "Anchor Text": tds[2].select_one("strong[data-key='title']").get_text(strip=True),
            "Target URL": tds[2].select_one("a[data-key='url']")["href"],
            "PA": int(tds[3].select_one(".value").text),
            "DA": int(tds[4].select_one(".value").text),
            "Found Date": tds[5].get_text(strip=True)
        })

    return stats, rows

domain = st.text_input("Enter Domain", "thewebhospitality.com")

if st.button("Analyze"):
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
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/143.0.0.0",
        "accept": "text/html"
    }

    with st.spinner("Fetching data..."):
        r = requests.get(url, params=params, headers=headers, timeout=30)

    if r.status_code == 200:
        stats, backlinks = parse_backlinks(r.text)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Backlinks", stats.get("backlinks", 0))
        c2.metric("Unique Backlinks", stats.get("unique backlinks", 0))
        c3.metric("Links to Homepage", stats.get("links to homepage", 0))
        c4.metric("Nofollow Backlinks", stats.get("nofollow backlinks", 0))

        df = pd.DataFrame(backlinks)

        st.subheader("Top Backlinks")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "backlinks.csv",
            "text/csv"
        )
    else:
        st.error("Request failed")

