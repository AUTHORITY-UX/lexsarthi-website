# ===================================================================
# LEXSARTHI ALPHA v5.0 – FINAL (No Mock, Robust Login)
# ===================================================================
# ... (all imports and setup same as before – keep your existing code)
# ... Only the login endpoint is changed below.
# ===================================================================

@auth_router.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    logger.info(f"Login attempt with: {user_login.username}")
    user = None
    if '@' in user_login.username:
        user = await get_user_by_email(user_login.username)
    else:
        user = await get_user_by_username(user_login.username)

    # 🔥 CRITICAL – MUST BE HERE
    if user is None:
        logger.warning(f"User not found: {user_login.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user_login.password, user["password_hash"]):
        logger.warning(f"Password mismatch for: {user['username']}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["id"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "tier": user.get("tier", "free"),
            "is_premium": user.get("is_premium", False),
        }
    }