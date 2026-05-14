#!/usr/bin/env python3
"""
Kjør inne i API-containeren:
  docker exec -it forente_planeter_api python create_admin.py
"""
import asyncio
import os
import sys
from getpass import getpass

import bcrypt
import asyncpg

RAW_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


async def create_user(username, email, password, role):
    conn = await asyncpg.connect(RAW_URL)
    try:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email=$1 OR username=$2", email, username
        )
        if existing:
            print(f"Bruker '{username}' / '{email}' finnes allerede.")
            return
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await conn.execute(
            """INSERT INTO users
               (username, email, password_hash, role, email_verified, is_active)
               VALUES ($1,$2,$3,$4,TRUE,TRUE)""",
            username, email, hashed, role,
        )
        print(f"Bruker opprettet: {username} ({role})")
    finally:
        await conn.close()


def main():
    print("=" * 50)
    print("  Forente Planeter - Opprett bruker")
    print("=" * 50)
    print()
    username = input("Brukernavn: ").strip()
    email    = input("E-post: ").strip()
    role     = input("Rolle [admin]: ").strip() or "admin"
    if role not in ("player", "admin", "superadmin", "elder_race"):
        print(f"Ugyldig rolle: {role}")
        sys.exit(1)
    password = getpass("Passord (maks 72 tegn): ")
    if len(password) < 8:
        print("Passord maa vaere minst 8 tegn")
        sys.exit(1)
    if len(password) > 72:
        print("Passord kan ikke vaere lengre enn 72 tegn")
        sys.exit(1)
    if getpass("Bekreft passord: ") != password:
        print("Passordene stemmer ikke")
        sys.exit(1)
    asyncio.run(create_user(username, email, password, role))


if __name__ == "__main__":
    main()
