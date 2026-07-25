# routes/sports.py - Sports Routes
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from datetime import datetime

router = APIRouter(prefix="/api/sports", tags=["Sports"])

@router.get("/cricket")
async def get_cricket_scores():
    """Get live cricket scores"""
    # Simulated cricket scores
    matches = [
        {
            "match": "India vs Australia",
            "status": "Live",
            "score": "India 245/3 (42.3 overs)",
            "batting": "Kohli 82* (98), Rahul 45 (56)",
            "bowling": "Starc 1-45, Cummins 1-38"
        },
        {
            "match": "England vs South Africa",
            "status": "Live",
            "score": "England 156/5 (30 overs)",
            "batting": "Root 42* (67), Stokes 28 (32)",
            "bowling": "Rabada 2-32, Ngidi 1-28"
        }
    ]
    return {"status": "ok", "matches": matches, "timestamp": datetime.now().isoformat()}

@router.get("/football")
async def get_football_scores():
    """Get live football scores"""
    matches = [
        {
            "match": "Manchester City vs Arsenal",
            "status": "Live",
            "score": "2-1",
            "scorers": "De Bruyne 23', Haaland 45+2' | Saka 12'",
            "possession": "Man City 58% - 42% Arsenal"
        },
        {
            "match": "Barcelona vs Real Madrid",
            "status": "FT",
            "score": "3-2",
            "scorers": "Lewandowski 12', 67', Gavi 45' | Vinicius 23', Bellingham 89'",
            "possession": "Barca 62% - 38% Real"
        }
    ]
    return {"status": "ok", "matches": matches, "timestamp": datetime.now().isoformat()}

@router.get("/tennis")
async def get_tennis_scores():
    """Get tennis scores"""
    matches = [
        {
            "match": "Djokovic vs Alcaraz",
            "status": "Live",
            "score": "6-4, 3-6, 4-3 (on serve)",
            "tournament": "Wimbledon Final"
        }
    ]
    return {"status": "ok", "matches": matches, "timestamp": datetime.now().isoformat()}

@router.get("/leagues")
async def get_leagues():
    """Get sports leagues"""
    leagues = {
        "cricket": ["IPL", "ICC World Cup", "T20 World Cup", "Ashes"],
        "football": ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"],
        "tennis": ["Wimbledon", "US Open", "French Open", "Australian Open"]
    }
    return {"status": "ok", "leagues": leagues, "timestamp": datetime.now().isoformat()}