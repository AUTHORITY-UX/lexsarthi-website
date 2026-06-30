@app.post("/ask")
@limiter.limit("30/minute")
async def ask(
    request: Request,
    query: str = Form(...),
    files: Optional[UploadFile] = File(None),
    search_web: str = Form("off"),
    lang: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    if not await check_query_limit(user_id):
        raise HTTPException(status_code=429, detail="Free limit reached. Upgrade to Premium.")
    
    # If a file is uploaded, extract its text and prepend/append to the query
    if files:
        try:
            file_text = await process_uploaded_file(files)
            # Combine query and extracted text
            combined_query = query + "\n\n--- Document Content ---\n" + file_text
        except Exception as e:
            logger.warning(f"File processing failed: {e}")
            combined_query = query
    else:
        combined_query = query

    await increment_query_count(user_id)
    agent_name = route_agent(combined_query)
    response_text = await execute_agent(agent_name, combined_query)
    verified_text, verifier_name = await verify_response(response_text, {})
    metadata = {
        "agent": agent_name,
        "verifier": verifier_name,
        "has_file": bool(files),
        "search_web": search_web,
        "lang": lang,
        "model": model,
    }
    expires_at = datetime.now() + timedelta(hours=24)
    stmt = queries.insert().values(
        user_id=user_id,
        query=combined_query,
        response=verified_text,
        metadata=metadata,
        expires_at=expires_at
    )
    await database.execute(stmt)
    return {
        "response": verified_text,
        "agent_used": agent_name,
        "verifier_used": verifier_name,
    }