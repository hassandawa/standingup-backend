import json
import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from app.config import FRONTEND_URL
from app.models.schemas import (
    EvaluationRequest,
    CofounderRequest,
    RoadmapRequest,
    ReadmeRequest,
    IdeaAnalysisRequest,
    IdeaAnalysisResponse,
    IdeaChatRequest,
    IdeaChatResponse,
    ShareLinkRequest,
    ShareLinkResponse,
    FundingDecision,
    CofounderPersona,
    MarketSizeRequest,
    MarketSizeResponse,
    DebateRequest,
    DebateResponse,
    ComparisonRequest,
    ComparisonResponse,
    EmailReportRequest,
    EmailReportResponse,
    First100CustomersRequest,
    First100CustomersResponse,
    DecisionEngineRequest,
    DecisionEngineResponse,
    BusinessPlanningRequest,
    BusinessPlanningResponse,
    CustomerInsightsRequest,
    CustomerInsightsResponse,
    MarketIntelligenceRequest,
    MarketIntelligenceResponse,
    AICofounderChatRequest,
    AICofounderChatResponse,
    InvestorToolsRequest,
    InvestorToolsResponse,
    MarketingHubRequest,
    MarketingHubResponse,
    DevelopmentHubRequest,
    DevelopmentHubResponse,
    GrowthHubRequest,
    GrowthHubResponse,
    FinancialPlanRequest,
    FinancialPlanResponse,
    LaunchHubRequest,
    LaunchHubResponse,
    TeamCreateRequest,
    TeamResponse,
    TeamInviteRequest,
    TeamJoinRequest,
    TeamAddAnalysisRequest,
    CommentCreateRequest,
    CommentResponse,
    ExportRequest,
    ExportResponse,
    ProgressSaveRequest,
    AnalyticsEvent,
    AnalyticsResponse,
)
from app.services.ai_service import (
    analyze_profile,
    evaluate_startup,
    generate_cofounder,
    generate_task_roadmap,
    generate_readme,
    analyze_idea,
    analyze_idea_stream,
    chat_about_idea,
    chat_about_idea_stream,
    estimate_market_size,
    debate_idea,
    compare_ideas,
    generate_email_report,
    generate_first_100_customers,
    generate_decision_engine,
    generate_business_plan,
    generate_customer_insights,
    generate_market_intelligence,
    generate_ai_cofounder_chat,
    generate_investor_tools,
    generate_marketing_hub,
    generate_development_hub,
    generate_growth_hub,
    generate_financial_plan,
    generate_launch_hub,
)
from app.services.ai_errors import AIServiceError, AIRateLimitError
from app.services.auth_service import get_user_by_token, get_user_by_id
from app.services.database_service import save_shared_analysis, get_shared_analysis, save_build_progress, get_build_progress, track_event, get_analytics_summary, save_idea_analysis, get_saved_idea_analyses, delete_saved_idea_analysis, save_customer_strategy as db_save_customer_strategy, get_customer_strategies, delete_customer_strategy, save_decision_report as db_save_decision_report, get_decision_reports, delete_decision_report, save_business_plan, get_business_plans, delete_business_plan, save_customer_insights, get_customer_insights_list, delete_customer_insights, save_market_intelligence, get_market_intelligence_list, delete_market_intelligence, save_ai_cofounder_chat, get_ai_cofounder_chats, delete_ai_cofounder_chat, save_investor_tools, get_investor_tools_list, delete_investor_tools, save_marketing_hub, get_marketing_hub_list, delete_marketing_hub, save_development_hub, get_development_hub_list, delete_development_hub, save_growth_hub, get_growth_hub_list, delete_growth_hub, save_financial_plan, get_financial_plan_list, delete_financial_plan, save_launch_hub, get_launch_hub_list, update_launch_hub_checks, delete_launch_hub, create_team, get_user_teams, get_team_by_invite_code, join_team, add_team_analysis, get_team_analyses, create_comment, get_comments, delete_comment
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter()


def _normalize_string_list(val):
    """Ensure every element in a list is a string (coerce dicts/lists to JSON string)."""
    if not isinstance(val, list):
        return []
    return [str(item) if not isinstance(item, str) else item for item in val]


def _normalize_string(val):
    """Coerce non-string values to string."""
    return str(val) if not isinstance(val, str) else val


@router.post("/api/startups/evaluate", response_model=FundingDecision)
async def evaluate_startup_idea(request: EvaluationRequest):
    try:
        founder_analysis = await analyze_profile(request.profile.model_dump())
        result = await evaluate_startup(
            request.profile.model_dump(),
            request.idea.model_dump(),
            founder_analysis,
        )
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Evaluation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to evaluate startup. Please try again.")

    required = ("decision", "overall_score", "evaluations", "summary")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Evaluation missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete evaluation. Please try again.")

    try:
        return FundingDecision(**result)
    except Exception as e:
        logger.error("Evaluation response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/cofounder", response_model=CofounderPersona)
async def generate_cofounder_persona(request: CofounderRequest):
    try:
        founder_analysis = await analyze_profile(request.profile.model_dump())
        result = await generate_cofounder(
            request.profile.model_dump(),
            request.idea.model_dump(),
            founder_analysis,
        )
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Cofounder generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate co-founder. Please try again.")

    required = ("name", "personality", "strengths", "complement", "advice")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Cofounder missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete co-founder. Please try again.")

    try:
        return CofounderPersona(**result)
    except Exception as e:
        logger.error("Cofounder response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/roadmap")
async def generate_startup_roadmap(request: RoadmapRequest):
    try:
        result = await generate_task_roadmap(
            request.profile.model_dump(),
            request.idea.model_dump(),
            request.plan.model_dump(),
        )
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Roadmap generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate roadmap. Please try again.")

    if "roadmap" not in result or not isinstance(result["roadmap"], list):
        logger.error("Roadmap returned invalid structure: %s", list(result.keys()))
        raise HTTPException(status_code=502, detail="AI returned an invalid roadmap. Please try again.")

    return result


@router.post("/api/startups/analyze-idea", response_model=IdeaAnalysisResponse)
async def analyze_startup_idea(request: IdeaAnalysisRequest):
    try:
        track_event("idea_analysis", {"industry": request.industry, "idea_preview": request.startup_idea[:50]})
        result = await analyze_idea(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Idea analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze idea. Please try again.")

    required = (
        "refined_idea", "problem_statement", "target_users",
        "market_demand_score", "uniqueness_score", "feasibility_score",
        "revenue_potential_score", "hackathon_winning_score",
        "competitors", "differentiation_strategy", "mvp_features",
        "tech_stack_recommendation", "monetization_model", "risks",
        "improvement_suggestions", "seven_day_build_plan",
        "founder_readiness_check", "pitch_summary",
    )
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Idea analysis missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete analysis. Please try again.")

    result["refined_idea"] = _normalize_string(result.get("refined_idea", ""))
    result["problem_statement"] = _normalize_string(result.get("problem_statement", ""))
    result["differentiation_strategy"] = _normalize_string(result.get("differentiation_strategy", ""))
    result["monetization_model"] = _normalize_string(result.get("monetization_model", ""))
    result["founder_readiness_check"] = _normalize_string(result.get("founder_readiness_check", ""))
    result["pitch_summary"] = _normalize_string(result.get("pitch_summary", ""))
    result["target_users"] = _normalize_string_list(result.get("target_users", []))
    result["mvp_features"] = _normalize_string_list(result.get("mvp_features", []))
    result["tech_stack_recommendation"] = _normalize_string_list(result.get("tech_stack_recommendation", []))
    result["risks"] = _normalize_string_list(result.get("risks", []))
    result["improvement_suggestions"] = _normalize_string_list(result.get("improvement_suggestions", []))
    for score_key in ("market_demand_score", "uniqueness_score", "feasibility_score", "revenue_potential_score", "hackathon_winning_score"):
        try:
            result[score_key] = float(result.get(score_key, 0))
        except (ValueError, TypeError):
            result[score_key] = 0.0
    for comp in result.get("competitors", []):
        comp["name"] = _normalize_string(comp.get("name", ""))
        comp["source"] = _normalize_string(comp.get("source", "ai-estimated")).lower()
        if comp["source"] not in ("ai-estimated", "web"):
            comp["source"] = "ai-estimated"
        comp["strengths"] = _normalize_string_list(comp.get("strengths", []))
        comp["weaknesses"] = _normalize_string_list(comp.get("weaknesses", []))
    for day in result.get("seven_day_build_plan", []):
        try:
            day["day"] = int(day.get("day", 1))
        except (ValueError, TypeError):
            day["day"] = 1
        day["title"] = _normalize_string(day.get("title", ""))
        day["tasks"] = _normalize_string_list(day.get("tasks", []))
    try:
        return IdeaAnalysisResponse(**result)
    except Exception as e:
        logger.error("Idea analysis response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/analyze-idea/stream")
async def analyze_startup_idea_stream(request: IdeaAnalysisRequest):
    """SSE streaming endpoint for idea analysis. Yields tokens then final result."""
    async def event_stream():
        try:
            final_result = None
            async for item in analyze_idea_stream(request.model_dump()):
                if isinstance(item, dict):
                    final_result = item
                else:
                    yield f"data: {json.dumps({'token': item})}\n\n"
            if final_result:
                yield f"data: {json.dumps({'done': True, 'result': final_result})}\n\n"
            else:
                yield f"data: {json.dumps({'error': 'AI returned an empty response.'})}\n\n"
        except AIRateLimitError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except AIServiceError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("Streaming idea analysis failed: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'Analysis failed. Please try again.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/startups/analyze-idea/chat", response_model=IdeaChatResponse)
async def chat_about_startup_idea(request: IdeaChatRequest):
    try:
        track_event("idea_chat", {"question_preview": request.question[:50]})
        result = await chat_about_idea(request.analysis, request.question)
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Idea chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to answer question. Please try again.")

    if "answer" not in result:
        logger.error("Chat response missing answer field: %s", list(result.keys()))
        raise HTTPException(status_code=502, detail="AI returned an incomplete response.")

    return IdeaChatResponse(**result)


@router.post("/api/startups/analyze-idea/chat/stream")
async def chat_about_startup_idea_stream(request: IdeaChatRequest):
    """SSE streaming endpoint for idea chat."""
    async def event_stream():
        try:
            async for item in chat_about_idea_stream(request.analysis, request.question):
                if isinstance(item, dict):
                    answer = item.get("answer", "")
                    yield f"data: {json.dumps({'done': True, 'answer': answer})}\n\n"
                else:
                    yield f"data: {json.dumps({'token': item})}\n\n"
        except AIRateLimitError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except AIServiceError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            logger.error("Streaming chat failed: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'Chat failed. Please try again.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/startups/first-100-customers", response_model=First100CustomersResponse)
async def generate_first_100_customers_plan(request: First100CustomersRequest):
    try:
        track_event("first_100_customers", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_first_100_customers(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("First 100 customers failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate customer acquisition plan. Please try again.")

    required = ("ideal_early_adopters", "where_to_find_them", "outreach_channels", "cold_message_templates", "social_media_launch_plan", "referral_strategy", "seven_day_action_plan", "metrics_to_track")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("First 100 customers missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete plan. Please try again.")

    try:
        return First100CustomersResponse(**result)
    except Exception as e:
        logger.error("First 100 customers response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/decision-engine", response_model=DecisionEngineResponse)
async def generate_decision_engine_report(request: DecisionEngineRequest):
    try:
        track_event("decision_engine", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_decision_engine(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Decision engine failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate decision report. Please try again.")

    required = ("risk_analysis", "success_probability", "recommendation")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Decision engine missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete report. Please try again.")

    try:
        return DecisionEngineResponse(**result)
    except Exception as e:
        logger.error("Decision engine response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/business-plan", response_model=BusinessPlanningResponse)
async def generate_business_plan_report(request: BusinessPlanningRequest):
    try:
        track_event("business_plan", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_business_plan(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Business plan generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate business plan. Please try again.")

    required = ("business_model_canvas", "lean_canvas", "revenue_forecast", "pricing_strategy")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Business plan missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete business plan. Please try again.")

    try:
        return BusinessPlanningResponse(**result)
    except Exception as e:
        logger.error("Business plan response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/customer-insights", response_model=CustomerInsightsResponse)
async def generate_customer_insights_report(request: CustomerInsightsRequest):
    try:
        track_event("customer_insights", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_customer_insights(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Customer insights failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate customer insights. Please try again.")

    required = ("personas", "ideal_customer_profile", "pain_point_analysis", "customer_journey")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Customer insights missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete report. Please try again.")

    try:
        return CustomerInsightsResponse(**result)
    except Exception as e:
        logger.error("Customer insights response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/analyze-idea/share", response_model=ShareLinkResponse)
async def share_idea_analysis(request: ShareLinkRequest):
    try:
        token = save_shared_analysis(request.analysis, request.idea_form)
        share_url = f"{FRONTEND_URL.rstrip('/')}/share/{token}"
        return ShareLinkResponse(token=token, url=share_url)
    except Exception as e:
        logger.error("Share link creation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create share link.")


@router.get("/api/share/{token}")
async def get_shared_idea_analysis(token: str):
    doc = get_shared_analysis(token)
    if not doc:
        raise HTTPException(status_code=404, detail="Shared analysis not found.")
    return {
        "analysis": doc.get("analysis"),
        "idea_form": doc.get("idea_form", {}),
        "created_at": doc.get("created_at", ""),
    }


@router.post("/api/startups/readme")
async def generate_startup_readme(request: ReadmeRequest):
    try:
        result = await generate_readme(
            request.profile.model_dump(),
            request.idea.model_dump(),
            request.plan.model_dump(),
        )
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("README generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate README. Please try again.")

    required = ("project_name", "problem", "solution", "features", "tech_stack", "architecture", "setup_steps", "future_improvements", "markdown")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("README missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete README. Please try again.")

    return result


@router.post("/api/startups/market-size", response_model=MarketSizeResponse)
async def estimate_startup_market(request: MarketSizeRequest):
    try:
        track_event("market_size", {"industry": request.industry, "idea_preview": request.startup_idea[:50]})
        result = await estimate_market_size(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Market size estimation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to estimate market size.")
    required = ("tam", "sam", "som", "growth_rate", "key_trends", "revenue_projection", "data_confidence")
    missing = [f for f in required if f not in result]
    if missing:
        raise HTTPException(status_code=502, detail="AI returned incomplete market data.")
    result["tam"] = _normalize_string(result.get("tam", ""))
    result["sam"] = _normalize_string(result.get("sam", ""))
    result["som"] = _normalize_string(result.get("som", ""))
    result["growth_rate"] = _normalize_string(result.get("growth_rate", ""))
    result["revenue_projection"] = _normalize_string(result.get("revenue_projection", ""))
    result["data_confidence"] = _normalize_string(result.get("data_confidence", "medium")).lower()
    if result["data_confidence"] not in ("high", "medium", "low"):
        result["data_confidence"] = "medium"
    result["key_trends"] = _normalize_string_list(result.get("key_trends", []))
    try:
        return MarketSizeResponse(**result)
    except Exception as e:
        logger.error("Market size response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid market size format. Please try again.")


@router.post("/api/startups/debate", response_model=DebateResponse)
async def debate_startup_idea(request: DebateRequest):
    try:
        track_event("debate", {"industry": request.industry, "idea_preview": request.startup_idea[:50]})
        result = await debate_idea(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Debate failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run debate.")
    if "agents" not in result or "consensus" not in result:
        raise HTTPException(status_code=502, detail="AI returned incomplete debate.")
    result["consensus"] = _normalize_string(result.get("consensus", ""))
    result["key_takeaways"] = _normalize_string_list(result.get("key_takeaways", []))
    for agent in result.get("agents", []):
        agent["agent_name"] = _normalize_string(agent.get("agent_name", ""))
        agent["role"] = _normalize_string(agent.get("role", ""))
        agent["argument"] = _normalize_string(agent.get("argument", ""))
        agent["emoji"] = _normalize_string(agent.get("emoji", ""))
    try:
        return DebateResponse(**result)
    except Exception as e:
        logger.error("Debate response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid debate format. Please try again.")


@router.post("/api/startups/compare", response_model=ComparisonResponse)
async def compare_startup_ideas(request: ComparisonRequest):
    try:
        track_event("comparison", {"idea_a_preview": request.idea_a[:50], "idea_b_preview": request.idea_b[:50]})
        result = await compare_ideas(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Comparison failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compare ideas.")
    if "dimensions" not in result or "overall_winner" not in result:
        raise HTTPException(status_code=502, detail="AI returned incomplete comparison.")
    result["overall_winner"] = _normalize_string(result.get("overall_winner", ""))
    result["summary"] = _normalize_string(result.get("summary", ""))
    for dim in result.get("dimensions", []):
        dim["dimension"] = _normalize_string(dim.get("dimension", ""))
        dim["idea_a_notes"] = _normalize_string(dim.get("idea_a_notes", ""))
        dim["idea_b_notes"] = _normalize_string(dim.get("idea_b_notes", ""))
        try:
            dim["idea_a_score"] = int(dim.get("idea_a_score", 5))
            dim["idea_b_score"] = int(dim.get("idea_b_score", 5))
        except (ValueError, TypeError):
            dim["idea_a_score"] = 5
            dim["idea_b_score"] = 5
    try:
        return ComparisonResponse(**result)
    except Exception as e:
        logger.error("Comparison response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid comparison format. Please try again.")


@router.post("/api/startups/email-report", response_model=EmailReportResponse)
async def email_startup_report(request: EmailReportRequest):
    try:
        track_event("email_report", {"recipient": request.recipient_email[:30]})
        html_content = await generate_email_report(request.analysis)
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Email report generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate email report.")

    idea_name = request.analysis.get("refined_idea", request.idea_form.get("startup_idea", "Your Idea"))[:60]
    subject = f"Your Startup Idea Analysis - {idea_name}"
    sent, reason = await send_email(request.recipient_email, subject, html_content)
    if sent:
        return EmailReportResponse(sent=True, message=f"Report sent to {request.recipient_email}")
    return EmailReportResponse(sent=False, message=f"Email sending unavailable. {reason}")


def _optional_user_id(authorization: str = Header(default="")) -> str | None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    user = get_user_by_token(token)
    return user["id"] if user else None


def _require_user_id(authorization: str = Header(default="")) -> str:
    user_id = _optional_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user_id


@router.post("/api/startups/first-100-customers/save")
async def save_customer_strategy(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_customer_strategy", {"user_id": user_id})
        strategy = body.get("strategy", {})
        idea_context = body.get("idea_context", {})
        if not strategy:
            raise HTTPException(status_code=400, detail="Strategy data is required.")
        strategy_id = db_save_customer_strategy(strategy, idea_context, user_id=user_id)
        return {"strategy_id": strategy_id, "message": "Customer strategy saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        import os as _os
        logger.error("[pid:%s] Save customer strategy failed: %s", _os.getpid(), e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save strategy.")


@router.get("/api/startups/first-100-customers/saved")
async def list_saved_customer_strategies(user_id: str = Depends(_require_user_id)):
    try:
        strategies = get_customer_strategies(user_id=user_id)
        return {"strategies": strategies}
    except Exception as e:
        logger.error("List customer strategies failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved strategies.")


@router.delete("/api/startups/first-100-customers/{strategy_id}")
async def remove_customer_strategy(strategy_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_customer_strategy(strategy_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {"message": "Strategy deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete customer strategy failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete strategy.")


@router.post("/api/startups/decision-engine/save")
async def save_decision_report(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_decision_report", {"user_id": user_id})
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = db_save_decision_report(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Decision report saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        import os as _os
        logger.error("[pid:%s] Save decision report failed: %s", _os.getpid(), e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save report.")


@router.get("/api/startups/decision-engine/saved")
async def list_saved_decision_reports(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_decision_reports(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List decision reports failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved reports.")


@router.delete("/api/startups/decision-engine/{report_id}")
async def remove_decision_report(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_decision_report(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"message": "Report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete decision report failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete report.")


@router.post("/api/startups/business-plan/save")
async def save_business_plan_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_business_plan", {"user_id": user_id})
        plan = body.get("plan", {})
        idea_context = body.get("idea_context", {})
        if not plan:
            raise HTTPException(status_code=400, detail="Plan data is required.")
        plan_id = save_business_plan(plan, idea_context, user_id=user_id)
        return {"plan_id": plan_id, "message": "Business plan saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save business plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save business plan.")


@router.get("/api/startups/business-plan/saved")
async def list_saved_business_plans(user_id: str = Depends(_require_user_id)):
    try:
        plans = get_business_plans(user_id=user_id)
        return {"plans": plans}
    except Exception as e:
        logger.error("List business plans failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved plans.")


@router.delete("/api/startups/business-plan/{plan_id}")
async def remove_business_plan(plan_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_business_plan(plan_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete business plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete plan.")


@router.post("/api/startups/customer-insights/save")
async def save_customer_insights_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_customer_insights", {"user_id": user_id})
        insights = body.get("insights", {})
        idea_context = body.get("idea_context", {})
        if not insights:
            raise HTTPException(status_code=400, detail="Insights data is required.")
        insights_id = save_customer_insights(insights, idea_context, user_id=user_id)
        return {"insights_id": insights_id, "message": "Customer insights saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save customer insights failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save insights.")


@router.get("/api/startups/customer-insights/saved")
async def list_saved_customer_insights(user_id: str = Depends(_require_user_id)):
    try:
        insights_list = get_customer_insights_list(user_id=user_id)
        return {"insights": insights_list}
    except Exception as e:
        logger.error("List customer insights failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved insights.")


@router.delete("/api/startups/customer-insights/{insights_id}")
async def remove_customer_insights(insights_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_customer_insights(insights_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Insights not found")
        return {"message": "Insights deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete customer insights failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete insights.")


@router.post("/api/startups/market-intelligence", response_model=MarketIntelligenceResponse)
async def generate_market_intelligence_report(request: MarketIntelligenceRequest):
    try:
        track_event("market_intelligence", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_market_intelligence(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Market intelligence failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate market intelligence report. Please try again.")

    required = ("market_size", "market_trends", "industry_growth", "emerging_opportunities", "competitor_comparison")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Market intelligence missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete report. Please try again.")

    try:
        return MarketIntelligenceResponse(**result)
    except Exception as e:
        logger.error("Market intelligence response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/startups/market-intelligence/save")
async def save_market_intelligence_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_market_intelligence", {"user_id": user_id})
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_market_intelligence(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Market intelligence report saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save market intelligence failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save report.")


@router.get("/api/startups/market-intelligence/saved")
async def list_saved_market_intelligence(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_market_intelligence_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List market intelligence failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved reports.")


@router.delete("/api/startups/market-intelligence/{report_id}")
async def remove_market_intelligence(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_market_intelligence(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"message": "Report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete market intelligence failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete report.")


@router.post("/api/ai-cofounder/chat", response_model=AICofounderChatResponse)
async def ai_cofounder_chat_endpoint(request: AICofounderChatRequest):
    try:
        track_event("ai_cofounder_chat", {"advisor_type": request.advisor_type, "question_preview": request.question[:50]})
        result = await generate_ai_cofounder_chat(request.advisor_type, request.question, request.startup_context)
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("AI cofounder chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get AI advisor response. Please try again.")

    if "answer" not in result:
        logger.error("AI cofounder response missing answer field")
        raise HTTPException(status_code=502, detail="AI returned an incomplete response.")

    return AICofounderChatResponse(**result)


@router.post("/api/ai-cofounder/chat/save")
async def save_ai_cofounder_chat_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_ai_cofounder_chat", {"user_id": user_id})
        advisor_type = body.get("advisor_type", "")
        messages = body.get("messages", [])
        if not advisor_type or not messages:
            raise HTTPException(status_code=400, detail="Advisor type and messages are required.")
        chat_id = save_ai_cofounder_chat(advisor_type, messages, user_id=user_id)
        return {"chat_id": chat_id, "message": "Chat saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save AI cofounder chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save chat.")


@router.get("/api/ai-cofounder/chat/{advisor_type}")
async def get_ai_cofounder_chat_history(advisor_type: str, user_id: str = Depends(_require_user_id)):
    try:
        chats = get_ai_cofounder_chats(advisor_type, user_id=user_id)
        return {"chats": chats}
    except Exception as e:
        logger.error("Get AI cofounder chats failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch chat history.")


@router.delete("/api/ai-cofounder/chat/{chat_id}")
async def delete_ai_cofounder_chat_endpoint(chat_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_ai_cofounder_chat(chat_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete AI cofounder chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete chat.")


@router.post("/api/investor-tools/generate", response_model=InvestorToolsResponse)
async def generate_investor_tools_report(request: InvestorToolsRequest):
    try:
        track_event("investor_tools", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_investor_tools(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Investor tools generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate investor tools. Please try again.")

    required = ("pitch_deck", "elevator_pitch", "executive_summary", "readiness_score", "funding_recommendation")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Investor tools missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete report. Please try again.")

    try:
        return InvestorToolsResponse(**result)
    except Exception as e:
        logger.error("Investor tools response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/investor-tools/save")
async def save_investor_tools_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_investor_tools", {"user_id": user_id})
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_investor_tools(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Investor tools saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save investor tools failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save report.")


@router.get("/api/investor-tools/saved")
async def list_saved_investor_tools(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_investor_tools_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List investor tools failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved reports.")


@router.delete("/api/investor-tools/{report_id}")
async def remove_investor_tools(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_investor_tools(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"message": "Report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete investor tools failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete report.")


@router.post("/api/marketing-hub/generate", response_model=MarketingHubResponse)
async def generate_marketing_hub_report(request: MarketingHubRequest):
    try:
        track_event("marketing_hub", {"idea_preview": request.startup_name[:50] if request.startup_name else request.pitch[:50]})
        result = await generate_marketing_hub(request.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Marketing hub generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate marketing assets. Please try again.")

    required = ("landing_page_copy", "brand_names", "logo_ideas", "taglines", "social_media_launch", "seo_keywords")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Marketing hub missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete report. Please try again.")

    try:
        return MarketingHubResponse(**result)
    except Exception as e:
        logger.error("Marketing hub response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")


@router.post("/api/marketing-hub/save")
async def save_marketing_hub_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_marketing_hub", {"user_id": user_id})
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_marketing_hub(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Marketing assets saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save marketing hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save report.")


@router.get("/api/marketing-hub/saved")
async def list_saved_marketing_hub(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_marketing_hub_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List marketing hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved reports.")


@router.delete("/api/marketing-hub/{report_id}")
async def remove_marketing_hub(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_marketing_hub(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"message": "Report deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete marketing hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete report.")


# ─── Development Hub ──────────────────────────────────────────────────────────

@router.post("/api/development-hub/generate")
async def generate_development_hub_endpoint(
    body: DevelopmentHubRequest,
    user_id: str = Depends(_require_user_id),
):
    try:
        track_event("generate_development_hub", {"user_id": user_id})
        data = body.model_dump()
        result = await generate_development_hub(data)
        return result
    except AIRateLimitError as e:
        logger.warning("Rate limit on dev hub: %s", e)
        raise HTTPException(status_code=429, detail=str(e))
    except AIServiceError as e:
        logger.error("AI error on dev hub: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Generate dev hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate development hub.")


@router.post("/api/development-hub/save")
async def save_development_hub_endpoint(
    body: dict,
    user_id: str = Depends(_require_user_id),
):
    try:
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_development_hub(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Development hub saved to dashboard."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save dev hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save development hub.")


@router.get("/api/development-hub/saved")
async def list_development_hubs(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_development_hub_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List dev hubs failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved development hubs.")


@router.delete("/api/development-hub/{report_id}")
async def remove_development_hub(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_development_hub(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Development hub not found")
        return {"message": "Development hub deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete dev hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete development hub.")


# ─── Growth Hub ───────────────────────────────────────────────────────────────

@router.post("/api/growth-hub/generate")
async def generate_growth_hub_endpoint(
    body: GrowthHubRequest,
    user_id: str = Depends(_require_user_id),
):
    try:
        track_event("generate_growth_hub", {"user_id": user_id})
        data = body.model_dump()
        result = await generate_growth_hub(data)
        return result
    except AIRateLimitError as e:
        logger.warning("Rate limit on growth hub: %s", e)
        raise HTTPException(status_code=429, detail=str(e))
    except AIServiceError as e:
        logger.error("AI error on growth hub: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Generate growth hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate growth hub.")


@router.post("/api/growth-hub/save")
async def save_growth_hub_endpoint(
    body: dict,
    user_id: str = Depends(_require_user_id),
):
    try:
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_growth_hub(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Growth hub saved to dashboard."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save growth hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save growth hub.")


@router.get("/api/growth-hub/saved")
async def list_growth_hubs(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_growth_hub_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List growth hubs failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved growth hubs.")


@router.delete("/api/growth-hub/{report_id}")
async def remove_growth_hub(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_growth_hub(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Growth hub not found")
        return {"message": "Growth hub deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete growth hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete growth hub.")


# ─── Financial Planning Hub ───────────────────────────────────────────────────

@router.post("/api/financial-plan/generate")
async def generate_financial_plan_endpoint(
    body: FinancialPlanRequest,
    user_id: str = Depends(_require_user_id),
):
    try:
        track_event("generate_financial_plan", {"user_id": user_id})
        data = body.model_dump()
        result = await generate_financial_plan(data)
        return result
    except AIRateLimitError as e:
        logger.warning("Rate limit on financial plan: %s", e)
        raise HTTPException(status_code=429, detail=str(e))
    except AIServiceError as e:
        logger.error("AI error on financial plan: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Generate financial plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate financial plan.")


@router.post("/api/financial-plan/save")
async def save_financial_plan_endpoint(
    body: dict,
    user_id: str = Depends(_require_user_id),
):
    try:
        report = body.get("report", {})
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_financial_plan(report, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Financial plan saved to dashboard."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save financial plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save financial plan.")


@router.get("/api/financial-plan/saved")
async def list_financial_plans(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_financial_plan_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List financial plans failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved financial plans.")


@router.delete("/api/financial-plan/{report_id}")
async def remove_financial_plan(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_financial_plan(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Financial plan not found")
        return {"message": "Financial plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete financial plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete financial plan.")


@router.post("/api/startups/analyze-idea/save")
async def save_idea_analysis_progress(
    body: dict,
    user_id: str = Depends(_require_user_id),
):
    try:
        track_event("save_analysis", {"user_id": user_id})
        analysis = body.get("analysis", {})
        idea_form = body.get("idea_form", {})
        if not analysis:
            raise HTTPException(status_code=400, detail="Analysis data is required.")
        analysis_id = save_idea_analysis(analysis, idea_form, user_id=user_id)
        return {"analysis_id": analysis_id, "message": "Progress saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save idea analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save analysis.")


@router.get("/api/startups/analyze-idea/saved")
async def list_saved_idea_analyses(user_id: str = Depends(_require_user_id)):
    try:
        analyses = get_saved_idea_analyses(user_id=user_id)
        return {"analyses": analyses}
    except Exception as e:
        logger.error("List saved analyses failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved analyses.")


@router.delete("/api/startups/analyze-idea/saved/{analysis_id}")
async def remove_saved_idea_analysis(analysis_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_saved_idea_analysis(analysis_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return {"message": "Analysis deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete analysis.")


@router.post("/api/startups/progress/save")
async def save_build_progress_endpoint(request: ProgressSaveRequest):
    try:
        result = save_build_progress(request.token, request.day, request.completed_tasks, request.notes)
        return result
    except Exception as e:
        logger.error("Save progress failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save progress.")


@router.get("/api/startups/progress/{token}")
async def load_build_progress_endpoint(token: str):
    try:
        return get_build_progress(token)
    except Exception as e:
        logger.error("Load progress failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load progress.")


# ─── Launch Hub ───────────────────────────────────────────────────────────────

@router.post("/api/launch-hub/generate")
async def generate_launch_hub_endpoint(
    body: LaunchHubRequest,
    user_id: str = Depends(_require_user_id),
):
    try:
        track_event("generate_launch_hub", {"user_id": user_id})
        data = body.model_dump()
        result = await generate_launch_hub(data)
        return result
    except AIRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Generate launch hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate launch hub.")


@router.post("/api/launch-hub/save")
async def save_launch_hub_endpoint(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        report = body.get("report", {})
        checked_items = body.get("checked_items", [])
        idea_context = body.get("idea_context", {})
        if not report:
            raise HTTPException(status_code=400, detail="Report data is required.")
        report_id = save_launch_hub(report, checked_items, idea_context, user_id=user_id)
        return {"report_id": report_id, "message": "Launch hub saved to dashboard."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save launch hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save launch hub.")


@router.get("/api/launch-hub/saved")
async def list_launch_hubs(user_id: str = Depends(_require_user_id)):
    try:
        reports = get_launch_hub_list(user_id=user_id)
        return {"reports": reports}
    except Exception as e:
        logger.error("List launch hubs failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved launch hubs.")


@router.patch("/api/launch-hub/{report_id}/checks")
async def update_launch_hub_checks_endpoint(report_id: str, body: dict, user_id: str = Depends(_require_user_id)):
    try:
        checked_items = body.get("checked_items", [])
        updated = update_launch_hub_checks(report_id, checked_items, user_id=user_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Launch hub not found")
        return {"message": "Checklist updated."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update launch hub checks failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update checklist.")


@router.delete("/api/launch-hub/{report_id}")
async def remove_launch_hub(report_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_launch_hub(report_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Launch hub not found")
        return {"message": "Launch hub deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete launch hub failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete launch hub.")


# ─── Collaboration Hub: Teams ─────────────────────────────────────────────────

@router.post("/api/teams/create")
async def create_team_endpoint(body: TeamCreateRequest, user_id: str = Depends(_require_user_id)):
    try:
        user = get_user_by_id(user_id)
        email = user.get("email", "") if user else ""
        name = user.get("name", "") if user else ""
        team = create_team(body.name, body.description, user_id, email, name)
        return team
    except Exception as e:
        logger.error("Create team failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create team.")


@router.get("/api/teams/my")
async def list_user_teams(user_id: str = Depends(_require_user_id)):
    try:
        return {"teams": get_user_teams(user_id)}
    except Exception as e:
        logger.error("List teams failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch teams.")


@router.get("/api/teams/join/{invite_code}")
async def get_team_by_code(invite_code: str):
    try:
        team = get_team_by_invite_code(invite_code)
        if not team:
            raise HTTPException(status_code=404, detail="Invalid invite code.")
        return team
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get team by code failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch team.")


@router.post("/api/teams/join")
async def join_team_endpoint(body: TeamJoinRequest, user_id: str = Depends(_require_user_id)):
    try:
        user = get_user_by_id(user_id)
        email = user.get("email", "") if user else ""
        name = user.get("name", "") if user else ""
        result = join_team(body.invite_code, user_id, email, name)
        if not result:
            raise HTTPException(status_code=404, detail="Invalid invite code.")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Join team failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to join team.")


@router.post("/api/teams/analysis")
async def add_team_analysis_endpoint(body: TeamAddAnalysisRequest, user_id: str = Depends(_require_user_id)):
    try:
        analysis_id = add_team_analysis(body.team_id, body.report_type, body.report_id, body.title, user_id)
        if not analysis_id:
            raise HTTPException(status_code=400, detail="Failed to add analysis.")
        return {"analysis_id": analysis_id, "message": "Analysis added to team workspace."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Add team analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add analysis.")


@router.get("/api/teams/{team_id}/analyses")
async def list_team_analyses(team_id: str, user_id: str = Depends(_require_user_id)):
    try:
        return {"analyses": get_team_analyses(team_id)}
    except Exception as e:
        logger.error("List team analyses failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analyses.")


# ─── Collaboration Hub: Comments ──────────────────────────────────────────────

@router.post("/api/comments")
async def create_comment_endpoint(body: CommentCreateRequest, user_id: str = Depends(_require_user_id)):
    try:
        user = get_user_by_id(user_id)
        name = user.get("name", "Anonymous") if user else "Anonymous"
        comment = create_comment(body.target_type, body.target_id, body.section, body.text, user_id, name)
        return comment
    except Exception as e:
        logger.error("Create comment failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create comment.")


@router.get("/api/comments/{target_type}/{target_id}")
async def list_comments(target_type: str, target_id: str, user_id: str = Depends(_require_user_id)):
    try:
        return {"comments": get_comments(target_type, target_id)}
    except Exception as e:
        logger.error("List comments failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch comments.")


@router.delete("/api/comments/{comment_id}")
async def remove_comment(comment_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_comment(comment_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Comment not found or not yours.")
        return {"message": "Comment deleted."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete comment failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete comment.")


# ─── Collaboration Hub: Export ────────────────────────────────────────────────

@router.post("/api/export/pdf")
async def export_as_pdf(body: ExportRequest):
    try:
        data = body.report_data or {}
        report_type = body.report_type
        name = data.get("startup_name", data.get("project_name", "Startup"))
        html = _build_export_html(report_type, name, data)
        return {"content": html, "format": "html", "filename": f"{name.lower().replace(' ', '_')}_{report_type}.html"}
    except Exception as e:
        logger.error("PDF export failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate export.")


@router.post("/api/export/notion")
async def export_as_notion(body: ExportRequest):
    try:
        data = body.report_data or {}
        report_type = body.report_type
        name = data.get("startup_name", data.get("project_name", "Startup"))
        md = _build_notion_markdown(report_type, name, data)
        return {"content": md, "format": "markdown", "filename": f"{name.lower().replace(' ', '_')}_{report_type}.md"}
    except Exception as e:
        logger.error("Notion export failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate Notion export.")


def _build_export_html(report_type: str, name: str, data: dict) -> str:
    sections = ""
    for key, value in data.items():
        if isinstance(value, dict):
            inner = "".join(f"<tr><td style='padding:4px 8px;border:1px solid #000;font-size:12px;'>{k}</td><td style='padding:4px 8px;border:1px solid #000;font-size:12px;'>{_val_to_str(v)}</td></tr>" for k, v in value.items())
            sections += f"<h3 style='text-transform:uppercase;font-size:14px;margin:16px 0 8px;'>{key.replace('_', ' ').title()}</h3><table style='width:100%;border-collapse:collapse;margin-bottom:16px;'>{inner}</table>"
        elif isinstance(value, list):
            items = "".join(f"<li style='font-size:12px;margin:4px 0;'>{_val_to_str(item)}</li>" for item in value[:20])
            sections += f"<h3 style='text-transform:uppercase;font-size:14px;margin:16px 0 8px;'>{key.replace('_', ' ').title()}</h3><ul>{items}</ul>"
        else:
            sections += f"<p style='font-size:12px;margin:4px 0;'><strong>{key.replace('_', ' ').title()}:</strong> {_val_to_str(value)}</p>"
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>{name} - {report_type}</title><style>body{{font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:40px auto;padding:20px;color:#000;}}h1{{font-size:24px;text-transform:uppercase;border-bottom:2px solid #000;padding-bottom:8px;}}</style></head><body><h1>{name}</h1><p style='font-size:12px;color:#666;text-transform:uppercase;letter-spacing:1px;'>{report_type} Report</p>{sections}</body></html>"""


def _build_notion_markdown(report_type: str, name: str, data: dict) -> str:
    lines = [f"# {name}", f"*{report_type.replace('_', ' ').title()} Report*", ""]
    for key, value in data.items():
        heading = key.replace("_", " ").title()
        lines.append(f"## {heading}")
        if isinstance(value, dict):
            for k, v in value.items():
                lines.append(f"- **{k.replace('_', ' ').title()}**: {_val_to_str(v)}")
        elif isinstance(value, list):
            for item in value[:30]:
                if isinstance(item, dict):
                    inner = "; ".join(f"{ik}: {_val_to_str(iv)}" for ik, iv in list(item.items())[:5])
                    lines.append(f"- {inner}")
                else:
                    lines.append(f"- {_val_to_str(item)}")
        else:
            lines.append(f"{_val_to_str(value)}")
        lines.append("")
    return "\n".join(lines)


def _val_to_str(val) -> str:
    if isinstance(val, dict):
        return "; ".join(f"{k}: {_val_to_str(v)}" for k, v in val.items())
    if isinstance(val, list):
        return ", ".join(_val_to_str(v) for v in val[:5])
    return str(val)


@router.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics_dashboard():
    try:
        return get_analytics_summary()
    except Exception as e:
        logger.error("Analytics fetch failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics.")


@router.post("/api/analytics/track")
async def track_analytics_event(request: AnalyticsEvent):
    try:
        track_event(request.event, request.properties)
        return {"ok": True}
    except Exception as e:
        logger.error("Track event failed: %s", e, exc_info=True)
        return {"ok": False}
