import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMINS_FILE = os.path.join(BASE_DIR, "admins.json")
MASTER_ADMIN_ID = 7190342953

def get_admins() -> list[int]:
    if not os.path.exists(ADMINS_FILE):
        admins = [MASTER_ADMIN_ID]
        save_admins(admins)
        return admins
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            admins = json.load(f)
            if MASTER_ADMIN_ID not in admins:
                admins.append(MASTER_ADMIN_ID)
                save_admins(admins)
            return [int(a) for a in admins]
    except Exception:
        return [MASTER_ADMIN_ID]

def save_admins(admins: list[int]):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(set([int(a) for a in admins])), f, indent=2)

def is_admin(user_id: int) -> bool:
    try:
        return int(user_id) in get_admins()
    except Exception:
        return False

def add_admin(user_id: int) -> bool:
    try:
        uid = int(user_id)
        admins = get_admins()
        if uid not in admins:
            admins.append(uid)
            save_admins(admins)
            return True
        return False
    except Exception:
        return False

def remove_admin(user_id: int) -> bool:
    try:
        uid = int(user_id)
        if uid == MASTER_ADMIN_ID:
            return False # Cannot remove master admin
        admins = get_admins()
        if uid in admins:
            admins.remove(uid)
            save_admins(admins)
            return True
        return False
    except Exception:
        return False
