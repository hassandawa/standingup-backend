"""
Tests for the startingUP backend API endpoints.

Uses pytest-asyncio for async tests and httpx's AsyncClient for HTTP calls.
Gemini API calls are mocked so no real API key is needed.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.main import app
from app.services.auth_service import _hash_password


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_PROFILE = {
    "skills": ["Full-Stack Development", "AI/ML", "UI/UX Design", "Cloud Computing"],
    "interests": ["Education", "SaaS", "Productivity"],
    "experience_level": "Intermediate",
    "budget": "100",
    "time_per_week": "10",
    "preferred_industry": "EdTech",
    "goal": "Hackathon MVP",
}

VALID_IDEA = {
    "startup_name": "SkillPath AI",
    "pitch": "An AI mentor that turns student skills into personalized career and startup roadmaps.",
    "problem": "Students have skills but do not know how to convert them into real projects.",
    "solution": "SkillPath AI analyzes skills, interests, and goals to generate startup ideas.",
    "target_users": ["Students", "Freelancers", "Hackathon participants"],
    "why_now": "AI tools now allow solo builders to launch MVPs faster than ever.",
    "opportunity_score": 8.7,
    "feasibility_score": 8.0,
    "demand_score": 9.0,
    "monetization_score": 7.5,
    "competition_gap_score": 8.0,
    "founder_fit_score": 9.0,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_mongo():
    """Mock the MongoDB client so tests never touch a real database."""
    with patch("app.main.client") as mock_client, \
         patch("app.database.client", mock_client), \
         patch("app.services.database_service.founder_profiles") as mock_fp, \
         patch("app.services.database_service.startup_plans") as mock_sp, \
         patch("app.services.auth_service.users") as mock_users, \
         patch("app.services.auth_service.password_resets") as mock_pr:
        # Make the ping command used in lifespan and health check succeed
        mock_client.admin.command = MagicMock(return_value=True)

        # Configure startup_plans mock
        mock_sp.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_sp.find.return_value = []
        mock_sp.delete_one.return_value = MagicMock(deleted_count=1)
        mock_users.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_users.find_one.return_value = None
        mock_users.update_one.return_value = MagicMock(modified_count=1)
        mock_pr.delete_many.return_value = MagicMock()
        mock_pr.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_pr.find_one.return_value = None

        yield {
            "client": mock_client,
            "founder_profiles": mock_fp,
            "startup_plans": mock_sp,
            "users": mock_users,
            "password_resets": mock_pr,
        }


@pytest_asyncio.fixture
async def client():
    """Yield an httpx AsyncClient wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "startingUP"


# ---------------------------------------------------------------------------
# 1b. Auth endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signup_creates_user_session(client: AsyncClient, _mock_mongo):
    response = await client.post(
        "/api/auth/signup",
        json={"name": "Student Builder", "email": "Student@Example.com", "password": "Password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["user"]["name"] == "Student Builder"
    assert data["user"]["email"] == "student@example.com"
    _mock_mongo["users"].insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409(client: AsyncClient, _mock_mongo):
    _mock_mongo["users"].insert_one.side_effect = DuplicateKeyError("duplicate email")

    response = await client.post(
        "/api/auth/signup",
        json={"name": "Student Builder", "email": "student@example.com", "password": "Password123"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signin_returns_user_session(client: AsyncClient, _mock_mongo):
    salt, password_hash = _hash_password("Password123")
    _mock_mongo["users"].find_one.return_value = {
        "_id": ObjectId(),
        "name": "Student Builder",
        "email": "student@example.com",
        "password_salt": salt,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }

    response = await client.post(
        "/api/auth/signin",
        json={"email": "student@example.com", "password": "Password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["user"]["email"] == "student@example.com"
    _mock_mongo["users"].update_one.assert_called_once()


@pytest.mark.asyncio
async def test_signin_invalid_password_returns_401(client: AsyncClient, _mock_mongo):
    salt, password_hash = _hash_password("Password123")
    _mock_mongo["users"].find_one.return_value = {
        "_id": ObjectId(),
        "name": "Student Builder",
        "email": "student@example.com",
        "password_salt": salt,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }

    response = await client.post(
        "/api/auth/signin",
        json={"email": "student@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_returns_generic_message(client: AsyncClient, _mock_mongo):
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_forgot_password_existing_email_returns_success(client: AsyncClient, _mock_mongo):
    _mock_mongo["users"].find_one.return_value = {
        "_id": ObjectId(),
        "email": "student@example.com",
    }

    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_me_and_logout_use_bearer_token(client: AsyncClient, _mock_mongo):
    user_id = ObjectId()
    _mock_mongo["users"].find_one.return_value = {
        "_id": user_id,
        "name": "Student Builder",
        "email": "student@example.com",
        "tokens": ["token-123"],
        "created_at": datetime.now(timezone.utc),
    }

    me_response = await client.get("/api/auth/me", headers={"Authorization": "Bearer token-123"})
    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(user_id)

    logout_response = await client.post("/api/auth/logout", headers={"Authorization": "Bearer token-123"})
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Signed out successfully"


# ---------------------------------------------------------------------------
# 2. Profile analysis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_profile_returns_founder_type(client: AsyncClient, _mock_mongo):
    mock_result = {
        "founder_type": "AI SaaS Builder",
        "strengths": ["Python", "AI/ML", "FastAPI"],
        "weaknesses": ["Limited budget", "No marketing experience"],
        "best_startup_categories": ["EdTech", "SaaS", "Productivity"],
    }
    with patch("app.services.ai_service._generate", return_value=mock_result):
        response = await client.post("/api/profile/analyze", json=VALID_PROFILE)

    assert response.status_code == 200
    data = response.json()
    assert data["founder_type"] == "AI SaaS Builder"
    assert "strengths" in data
    assert "weaknesses" in data
    assert "best_startup_categories" in data


# ---------------------------------------------------------------------------
# 3. Startup idea generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_ideas_returns_ideas_array(client: AsyncClient, _mock_mongo):
    mock_result = {
        "ideas": [
            {
                **VALID_IDEA,
                "startup_name": f"Startup {i}",
            }
            for i in range(3)
        ]
    }
    with patch("app.services.ai_service._generate", return_value=mock_result):
        response = await client.post("/api/startups/generate", json=VALID_PROFILE)

    assert response.status_code == 200
    data = response.json()
    assert "ideas" in data
    assert len(data["ideas"]) == 3
    for idea in data["ideas"]:
        assert "startup_name" in idea
        assert "opportunity_score" in idea


# ---------------------------------------------------------------------------
# 4. Full startup plan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_plan_returns_full_plan(client: AsyncClient, _mock_mongo):
    mock_result = {
        "startup_name": "SkillPath AI",
        "pitch": "An AI mentor for students.",
        "problem": "Students cannot convert skills into projects.",
        "solution": "AI-powered skill-to-startup platform.",
        "target_users": ["Students", "Freelancers"],
        "why_now": "AI tools enable solo builders.",
        "opportunity_score": 8.7,
        "competitors": [
            {"name": "CompetitorA", "strengths": ["Brand"], "weaknesses": ["Price"]},
        ],
        "competitor_limitations": ["No AI personalization"],
        "our_advantages": ["AI-driven", "Low cost"],
        "market_gaps": ["Personalized learning"],
        "mvp_features": ["Feature1", "Feature2"],
        "mvp_v1_scope": "Core features only",
        "mvp_v2_features": ["Future1"],
        "roadmap": [
            {"week": 1, "title": "Foundation", "tasks": ["Setup"]},
            {"week": 2, "title": "Build", "tasks": ["Code"]},
            {"week": 3, "title": "Test", "tasks": ["QA"]},
            {"week": 4, "title": "Launch", "tasks": ["Deploy"]},
        ],
        "revenue_model": {
            "pricing_model": "Freemium",
            "monetization_methods": ["Subscriptions"],
            "first_customer_strategy": "University partnerships",
            "recommendation": "B2C",
        },
        "launch_strategy": "Start with universities.",
        "swot": {
            "strengths": ["AI expertise"],
            "weaknesses": ["Small team"],
            "opportunities": ["Growing EdTech market"],
            "threats": ["Big competitors"],
        },
        "risks": ["Funding", "Adoption"],
        "hackathon_pitch": "A 60-second pitch.",
        "thirty_second_pitch": "A 30-second pitch.",
    }
    payload = {
        "profile": VALID_PROFILE,
        "idea": VALID_IDEA,
    }
    with patch("app.services.ai_service._generate", return_value=mock_result):
        response = await client.post("/api/startups/plan", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["startup_name"] == "SkillPath AI"
    assert "competitors" in data
    assert "roadmap" in data
    assert "swot" in data
    assert "revenue_model" in data
    assert "hackathon_pitch" in data


# ---------------------------------------------------------------------------
# 5. Save and list roundtrip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_and_list_plans_roundtrip(client: AsyncClient, _mock_mongo):
    plan_id = str(ObjectId())
    user_id = ObjectId()
    _mock_mongo["users"].find_one.return_value = {
        "_id": user_id,
        "name": "Student Builder",
        "email": "student@example.com",
        "tokens": ["token-123"],
        "created_at": datetime.now(timezone.utc),
    }
    mock_plan_doc = {
        "_id": str(ObjectId(plan_id)),
        "plan": {"startup_name": "TestStartup"},
        "profile": VALID_PROFILE,
        "user_id": str(user_id),
    }

    # --- save ---
    with patch("app.routes.startups.save_startup_plan", return_value=plan_id):
        save_payload = {
            "plan": {
                "startup_name": "TestStartup",
                "pitch": "Pitch",
                "problem": "Problem",
                "solution": "Solution",
                "target_users": ["Users"],
                "why_now": "Now",
                "opportunity_score": 7.0,
                "competitors": [],
                "competitor_limitations": [],
                "our_advantages": [],
                "market_gaps": [],
                "mvp_features": [],
                "roadmap": [],
                "revenue_model": {},
                "launch_strategy": "Strategy",
                "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
                "risks": [],
                "hackathon_pitch": "Pitch",
                "thirty_second_pitch": "Short pitch",
            },
            "profile": VALID_PROFILE,
        }
        save_response = await client.post(
            "/api/startups/save",
            json=save_payload,
            headers={"Authorization": "Bearer token-123"},
        )

    assert save_response.status_code == 200
    save_data = save_response.json()
    assert save_data["plan_id"] == plan_id

    # --- list ---
    with patch("app.routes.startups.get_saved_plans", return_value=[mock_plan_doc]):
        list_response = await client.get(
            "/api/startups/saved",
            headers={"Authorization": "Bearer token-123"},
        )

    assert list_response.status_code == 200
    list_data = list_response.json()
    assert "plans" in list_data
    assert len(list_data["plans"]) >= 1


# ---------------------------------------------------------------------------
# 6. Delete plan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_plan(client: AsyncClient, _mock_mongo):
    plan_id = str(ObjectId())
    _mock_mongo["users"].find_one.return_value = {
        "_id": ObjectId(),
        "name": "Student Builder",
        "email": "student@example.com",
        "tokens": ["token-123"],
        "created_at": datetime.now(timezone.utc),
    }
    with patch("app.routes.startups.delete_startup_plan", return_value=True):
        response = await client.delete(
            f"/api/startups/{plan_id}",
            headers={"Authorization": "Bearer token-123"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Plan deleted successfully"


@pytest.mark.asyncio
async def test_delete_plan_not_found(client: AsyncClient, _mock_mongo):
    plan_id = str(ObjectId())
    _mock_mongo["users"].find_one.return_value = {
        "_id": ObjectId(),
        "name": "Student Builder",
        "email": "student@example.com",
        "tokens": ["token-123"],
        "created_at": datetime.now(timezone.utc),
    }
    with patch("app.routes.startups.delete_startup_plan", return_value=False):
        response = await client.delete(
            f"/api/startups/{plan_id}",
            headers={"Authorization": "Bearer token-123"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_saved_plans_requires_auth(client: AsyncClient, _mock_mongo):
    response = await client.get("/api/startups/saved")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 7. Validation errors (422)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_profile_missing_skills_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE}
    bad_payload.pop("skills")
    response = await client.post("/api/profile/analyze", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_profile_missing_interests_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE}
    bad_payload.pop("interests")
    response = await client.post("/api/profile/analyze", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_profile_missing_goal_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE}
    bad_payload.pop("goal")
    response = await client.post("/api/profile/analyze", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_ideas_empty_skills_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE, "skills": []}
    response = await client.post("/api/startups/generate", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_ideas_empty_interests_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE, "interests": []}
    response = await client.post("/api/startups/generate", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_ideas_empty_goal_returns_422(client: AsyncClient, _mock_mongo):
    bad_payload = {**VALID_PROFILE, "goal": ""}
    response = await client.post("/api/startups/generate", json=bad_payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 8. Multi-agent startup evaluation
# ---------------------------------------------------------------------------

VALID_EVALUATION_RESULT = {
    "decision": "Fund",
    "overall_score": 82,
    "evaluations": [
        {
            "agent": "Tech Expert",
            "score": 85,
            "strengths": ["Strong tech stack", "Feasible MVP"],
            "risks": ["Scaling challenges"],
            "improvements": ["Add tests early"],
        },
        {
            "agent": "Finance Expert",
            "score": 78,
            "strengths": ["Good unit economics"],
            "risks": ["High burn rate"],
            "improvements": ["Focus on paid tiers"],
        },
        {
            "agent": "Marketing Expert",
            "score": 83,
            "strengths": ["Clear audience", "Strong positioning"],
            "risks": ["Competitive space"],
            "improvements": ["Content marketing strategy"],
        },
    ],
    "summary": "Strong potential with recommended improvements.",
}

VALID_COFOUNDER_RESULT = {
    "name": "Alex Codex",
    "personality": "A pragmatic builder who turns ideas into shippable products.",
    "strengths": ["Backend architecture", "DevOps", "Fundraising"],
    "complement": "Fills the user's lack of infrastructure experience.",
    "advice": ["Ship fast, learn faster", "Focus on one metric", "Talk to users daily"],
}

VALID_ROADMAP_RESULT = {
    "roadmap": [
        {
            "phase": "Phase 1: Foundation",
            "tasks": [
                {
                    "phase": "Phase 1: Foundation",
                    "task": "Set up project repository",
                    "priority": "High",
                    "estimated_time_hours": 4,
                    "tools_needed": ["Git", "GitHub"],
                    "status": "Pending",
                }
            ],
        }
    ],
}

VALID_README_RESULT = {
    "project_name": "SkillPath AI",
    "problem": "Students have skills but no direction.",
    "solution": "AI generates personalized startup ideas.",
    "features": ["Skill analysis", "Idea generation"],
    "tech_stack": ["Python", "FastAPI", "React"],
    "architecture": "Frontend React app communicating with FastAPI backend.",
    "setup_steps": ["Clone repo", "Install deps", "Run app"],
    "future_improvements": ["Mobile app", "Team features"],
    "markdown": "# SkillPath AI\n\n## Problem\n...",
}


@pytest.mark.asyncio
async def test_evaluate_startup_returns_funding_decision(client: AsyncClient, _mock_mongo):
    def mock_eval_fn(*args, **kwargs):
        return VALID_EVALUATION_RESULT

    with patch("app.services.ai_service._generate", return_value=VALID_EVALUATION_RESULT["evaluations"][0]):
        with patch("app.routes.enhanced.analyze_profile") as mock_analyze:
            mock_analyze.return_value = {
                "founder_type": "AI Builder",
                "strengths": ["Python"],
                "weaknesses": ["Marketing"],
                "best_startup_categories": ["SaaS"],
            }
            payload = {"profile": VALID_PROFILE, "idea": VALID_IDEA}
            response = await client.post("/api/startups/evaluate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] in ("Fund", "Revise", "Reject")
    assert 0 <= data["overall_score"] <= 100
    assert "evaluations" in data
    assert len(data["evaluations"]) >= 1
    assert "summary" in data


@pytest.mark.asyncio
async def test_evaluate_startup_invalid_returns_422(client: AsyncClient, _mock_mongo):
    response = await client.post("/api/startups/evaluate", json={})
    assert response.status_code == 422


@ pytest.mark.asyncio
async def test_generate_cofounder_returns_persona(client: AsyncClient, _mock_mongo):
    with patch("app.routes.enhanced.analyze_profile") as mock_analyze:
        mock_analyze.return_value = {
            "founder_type": "AI Builder",
            "strengths": ["Python"],
            "weaknesses": ["Marketing"],
            "best_startup_categories": ["SaaS"],
        }
        with patch("app.services.ai_service._generate", return_value=VALID_COFOUNDER_RESULT):
            payload = {"profile": VALID_PROFILE, "idea": VALID_IDEA}
            response = await client.post("/api/startups/cofounder", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "personality" in data
    assert "strengths" in data
    assert "complement" in data
    assert "advice" in data
    assert len(data["advice"]) == 3


@pytest.mark.asyncio
async def test_generate_cofounder_invalid_returns_422(client: AsyncClient, _mock_mongo):
    response = await client.post("/api/startups/cofounder", json={})
    assert response.status_code == 422


@ pytest.mark.asyncio
async def test_generate_roadmap_returns_tasks(client: AsyncClient, _mock_mongo):
    mock_plan = {
        "startup_name": "SkillPath AI",
        "pitch": "Pitch",
        "problem": "Problem",
        "solution": "Solution",
        "target_users": ["Users"],
        "why_now": "Now",
        "opportunity_score": 7.0,
        "competitors": [],
        "competitor_limitations": [],
        "our_advantages": [],
        "market_gaps": [],
        "mvp_features": ["Feature1"],
        "roadmap": [],
        "revenue_model": {},
        "launch_strategy": "Strategy",
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "risks": [],
        "hackathon_pitch": "Pitch",
        "thirty_second_pitch": "Short pitch",
    }

    with patch("app.services.ai_service._generate", return_value=VALID_ROADMAP_RESULT):
        payload = {"profile": VALID_PROFILE, "idea": VALID_IDEA, "plan": mock_plan}
        response = await client.post("/api/startups/roadmap", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "roadmap" in data
    assert len(data["roadmap"]) >= 1


@pytest.mark.asyncio
async def test_generate_roadmap_invalid_returns_422(client: AsyncClient, _mock_mongo):
    response = await client.post("/api/startups/roadmap", json={})
    assert response.status_code == 422


@ pytest.mark.asyncio
async def test_generate_readme_returns_content(client: AsyncClient, _mock_mongo):
    mock_plan = {
        "startup_name": "SkillPath AI",
        "pitch": "Pitch",
        "problem": "Problem",
        "solution": "Solution",
        "target_users": ["Users"],
        "why_now": "Now",
        "opportunity_score": 7.0,
        "competitors": [],
        "competitor_limitations": [],
        "our_advantages": [],
        "market_gaps": [],
        "mvp_features": ["Feature1"],
        "roadmap": [],
        "revenue_model": {},
        "launch_strategy": "Strategy",
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "risks": [],
        "hackathon_pitch": "Pitch",
        "thirty_second_pitch": "Short pitch",
    }

    with patch("app.services.ai_service._generate", return_value=VALID_README_RESULT):
        payload = {"profile": VALID_PROFILE, "idea": VALID_IDEA, "plan": mock_plan}
        response = await client.post("/api/startups/readme", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "SkillPath AI"
    assert "markdown" in data


@pytest.mark.asyncio
async def test_generate_readme_invalid_returns_422(client: AsyncClient, _mock_mongo):
    response = await client.post("/api/startups/readme", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 10. Idea Analyzer
# ---------------------------------------------------------------------------

VALID_IDEA_ANALYSIS_RESULT = {
    "refined_idea": "An AI platform that helps students convert skills into validated startup ideas with market analysis and 7-day MVP plans.",
    "problem_statement": "Students have technical skills but lack the business framework to turn them into viable startup concepts.",
    "target_users": ["College students", "Recent graduates", "Hackathon participants"],
    "market_demand_score": 8.5,
    "uniqueness_score": 7.0,
    "feasibility_score": 8.0,
    "revenue_potential_score": 7.5,
    "hackathon_winning_score": 9.0,
    "competitors": [
        {"name": "Y Combinator Startup School", "strengths": ["Brand", "Community"], "weaknesses": ["Generic", "Not skill-based"], "source": "ai-estimated"},
        {"name": "IdeasAI", "strengths": ["Speed"], "weaknesses": ["No market validation"], "source": "ai-estimated"},
        {"name": "GPT-5 Idea Generator", "strengths": ["Flexible"], "weaknesses": ["No structured output"], "source": "ai-estimated"},
    ],
    "differentiation_strategy": "Focus on skill-to-idea mapping with competitor validation and MVP build plans.",
    "mvp_features": ["Skill analysis", "Idea generation", "Competitor scan", "MVP builder"],
    "tech_stack_recommendation": ["Python", "FastAPI", "React", "MongoDB"],
    "monetization_model": "Freemium SaaS with free tier for students and paid pro plans for teams.",
    "risks": ["Competition from AI tools", "Student willingness to pay", "Quality consistency"],
    "improvement_suggestions": ["Add mentorship layer", "Partner with universities"],
    "seven_day_build_plan": [
        {"day": 1, "title": "Setup", "tasks": ["Init project", "Design schemas"]},
        {"day": 2, "title": "Core AI", "tasks": ["Prompt engineering", "API integration"]},
        {"day": 3, "title": "Frontend", "tasks": ["UI components", "Form flow"]},
        {"day": 4, "title": "Scoring", "tasks": ["Score logic", "Visualization"]},
        {"day": 5, "title": "Competitors", "tasks": ["Competitor module", "Diff strategy"]},
        {"day": 6, "title": "MVP Plan", "tasks": ["Day-by-day builder", "Export"]},
        {"day": 7, "title": "Polish", "tasks": ["Testing", "Deployment"]},
    ],
    "founder_readiness_check": "Strong technical fit but needs market research skills.",
    "pitch_summary": "startingUP turns your existing skills into validated startup ideas with competitor analysis and a day-by-day MVP build plan.",
}


@pytest.mark.asyncio
async def test_analyze_idea_returns_full_analysis(client: AsyncClient, _mock_mongo):
    with patch("app.services.ai_service._generate", return_value=VALID_IDEA_ANALYSIS_RESULT):
        payload = {
            "startup_idea": "An AI platform that helps students turn skills into startup ideas.",
            "target_audience": "College students",
            "industry": "EdTech",
            "skills": "Full-Stack Development, AI/ML, UI/UX Design",
            "budget_time_limit": "$100, 10 hrs/week",
        }
        response = await client.post("/api/startups/analyze-idea", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["refined_idea"]
    assert data["problem_statement"]
    assert len(data["target_users"]) >= 1
    assert 0 <= data["market_demand_score"] <= 10
    assert 0 <= data["uniqueness_score"] <= 10
    assert 0 <= data["feasibility_score"] <= 10
    assert 0 <= data["revenue_potential_score"] <= 10
    assert 0 <= data["hackathon_winning_score"] <= 10
    assert len(data["competitors"]) >= 3
    assert data["differentiation_strategy"]
    assert len(data["mvp_features"]) >= 1
    assert len(data["tech_stack_recommendation"]) >= 1
    assert data["monetization_model"]
    assert len(data["risks"]) >= 1
    assert len(data["improvement_suggestions"]) >= 1
    assert len(data["seven_day_build_plan"]) == 7
    assert data["founder_readiness_check"]
    assert data["pitch_summary"]


@pytest.mark.asyncio
async def test_analyze_idea_invalid_returns_422(client: AsyncClient, _mock_mongo):
    response = await client.post("/api/startups/analyze-idea", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 11. Idea Chat - Intent-based responses
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = {
    "refined_idea": "startingUP - turns skills into validated startup ideas",
    "target_users": ["Students", "Freelancers"],
    "market_demand_score": 8.5,
    "feasibility_score": 7.5,
    "competitors": [{"name": "IdeaGenie", "strengths": ["AI"], "weaknesses": ["No validation"]}],
    "mvp_features": ["Skill analysis", "Idea generation"],
    "risks": ["Competition"],
}


@pytest.mark.asyncio
async def test_chat_greeting_returns_greeting_no_ai_call(client: AsyncClient, _mock_mongo):
    with patch("app.services.ai_service._generate") as mock_generate:
        response = await client.post(
            "/api/startups/analyze-idea/chat",
            json={"analysis": SAMPLE_ANALYSIS, "question": "Hello"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "hello" in data["answer"].lower()
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_chat_casual_returns_casual_no_ai_call(client: AsyncClient, _mock_mongo):
    with patch("app.services.ai_service._generate") as mock_generate:
        response = await client.post(
            "/api/startups/analyze-idea/chat",
            json={"analysis": SAMPLE_ANALYSIS, "question": "How are you?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_chat_idea_question_uses_ai_and_is_concise(client: AsyncClient, _mock_mongo):
    mock_result = {"answer": "Your main competitor is IdeaGenie. They offer AI brainstorming but lack the competitor validation layer your idea provides. Focus on the validation feature to differentiate."}

    with patch("app.services.ai_service._generate", return_value=mock_result) as mock_generate:
        response = await client.post(
            "/api/startups/analyze-idea/chat",
            json={"analysis": SAMPLE_ANALYSIS, "question": "Who are my competitors?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    mock_generate.assert_called_once()
    # Verify the concise prompt was used
    prompt_used = mock_generate.call_args[0][0]
    assert "concise" in prompt_used.lower()


@pytest.mark.asyncio
async def test_chat_full_summary_uses_full_prompt(client: AsyncClient, _mock_mongo):
    mock_result = {"answer": "Here is the complete analysis overview..."}

    with patch("app.services.ai_service._generate", return_value=mock_result) as mock_generate:
        response = await client.post(
            "/api/startups/analyze-idea/chat",
            json={"analysis": SAMPLE_ANALYSIS, "question": "Give me a full summary"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    mock_generate.assert_called_once()
    prompt_used = mock_generate.call_args[0][0]
    assert "comprehensive summary" in prompt_used.lower()
