import streamlit as st
from pymongo import MongoClient
from typing import List, Dict
import os

# ------------------ CONFIG ------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "friendsmatch"
COLLECTION = "users"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users = db[COLLECTION]

# ------------------ SIMILARITY FUNCTIONS ------------------
def jaccard(a: List[str], b: List[str]) -> float:
    setA = set([x.strip().lower() for x in a if x.strip()])
    setB = set([x.strip().lower() for x in b if x.strip()])
    if not setA and not setB:
        return 1.0
    intersection = setA.intersection(setB)
    union = setA.union(setB)
    return len(intersection) / len(union) if union else 0

def profile_similarity(a: Dict, b: Dict) -> Dict:
    scores = []
    categoriesA = {c["name"].lower(): c["items"] for c in a.get("categories", [])}
    categoriesB = {c["name"].lower(): c["items"] for c in b.get("categories", [])}

    all_cats = set(categoriesA.keys()).union(categoriesB.keys())
    for cat in all_cats:
        sim = jaccard(categoriesA.get(cat, []), categoriesB.get(cat, []))
        scores.append({"category": cat.title(), "sim": sim})

    overall = sum([s["sim"] for s in scores]) / len(scores) if scores else 0
    return {"overall": overall, "details": scores}

# ------------------ STREAMLIT UI ------------------
st.set_page_config(page_title="Friends & Match", layout="wide")
st.title("🤝 Friends & Match")

# Sidebar navigation
mode = st.sidebar.radio("Choose an action", ["Create/Update Profile", "View Friend Profile", "Compare Profiles"])

if mode == "Create/Update Profile":
    st.header("👤 Create or Update Your Profile")
    username = st.text_input("Username (unique)")
    display_name = st.text_input("Display Name")
    avatar = st.text_input("Avatar URL (optional)")

    categories = []
    default_cats = ["Music", "Movies", "Books", "Food", "Sports"]
    for cat in default_cats:
        items = st.text_area(f"Your {cat} (comma-separated)", key=cat).split(",")
        categories.append({"name": cat, "items": [i.strip() for i in items if i.strip()]})

    if st.button("💾 Save Profile"):
        if not username:
            st.error("Username is required")
        else:
            users.update_one(
                {"username": username},
                {"$set": {"username": username, "displayName": display_name, "avatar": avatar, "categories": categories}},
                upsert=True
            )
            st.success("Profile saved successfully!")

elif mode == "View Friend Profile":
    st.header("🔎 View Friend Profile")
    friend_username = st.text_input("Friend's Username")
    if st.button("Load Friend"):
        friend = users.find_one({"username": friend_username})
        if not friend:
            st.error("Friend not found")
        else:
            st.subheader(friend.get("displayName") or friend["username"])
            if friend.get("avatar"):
                st.image(friend["avatar"], width=120)
            for c in friend.get("categories", []):
                st.write(f"**{c['name']}**: {', '.join(c['items'])}")

elif mode == "Compare Profiles":
    st.header("⚖️ Compare Profiles")
    userA = st.text_input("Your Username")
    userB = st.text_input("Friend's Username")

    if st.button("Compare"):
        a = users.find_one({"username": userA})
        b = users.find_one({"username": userB})
        if not a or not b:
            st.error("One or both profiles not found")
        else:
            sim = profile_similarity(a, b)
            st.subheader(f"Overall Match: {sim['overall']*100:.0f}%")
            for d in sim["details"]:
                st.write(f"**{d['category']}** → {d['sim']*100:.0f}% match")
