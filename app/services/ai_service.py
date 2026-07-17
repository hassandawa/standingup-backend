import asyncio
import json
import logging
import random
import secrets

logger = logging.getLogger(__name__)

from app.config import AI_PROVIDER
from app.services.ai_errors import AIServiceError, AIRateLimitError
from app.services.gemini_service import GeminiAPIError, GeminiRateLimitError, generate_with_gemini, generate_with_gemini_stream
from app.services.groq_service import generate_with_groq, generate_with_groq_stream
from app.prompts.prompts import (
    SKILL_ANALYSIS_PROMPT,
    STARTUP_GENERATION_PROMPT,
    FULL_PLAN_PROMPT,
    AGENT_EVALUATION_PROMPT,
    COFOUNDER_PROMPT,
    TASK_ROADMAP_PROMPT,
    README_GENERATOR_PROMPT,
    IDEA_ANALYSIS_PROMPT,
    IDEA_CHAT_CONCISE_PROMPT,
    IDEA_CHAT_FULL_PROMPT,
    MARKET_SIZE_PROMPT,
    DEBATE_ROOM_PROMPT,
    COMPARISON_PROMPT,
    EMAIL_REPORT_PROMPT,
    FIRST_100_CUSTOMERS_PROMPT,
    DECISION_ENGINE_PROMPT,
    BUSINESS_PLANNING_PROMPT,
    CUSTOMER_INSIGHTS_PROMPT,
    MARKET_INTELLIGENCE_PROMPT,
    AI_MENTOR_PROMPT,
    AI_PM_PROMPT,
    AI_MARKETING_PROMPT,
    AI_TECH_PROMPT,
    AI_INVESTOR_PROMPT,
    INVESTOR_TOOLS_PROMPT,
    MARKETING_HUB_PROMPT,
    DEVELOPMENT_HUB_PROMPT,
    GROWTH_HUB_PROMPT,
    FINANCIAL_PLANNING_PROMPT,
    LAUNCH_HUB_PROMPT,
)


_GREETING_WORDS = frozenset({"hi", "hello", "hey", "greetings", "howdy"})
_CASUAL_EXACT = frozenset({
    "how are you", "how's it going", "what's up", "thanks", "thank you",
    "thankyou", "thx", "ty", "i'm good", "im good", "doing well",
    "how are you doing", "how do you do",
})
_SUMMARY_MARKERS = [
    "full summary", "complete analysis", "summarize everything",
    "tell me everything", "full analysis", "whole analysis",
    "give me the full picture", "complete overview",
    "summarize the analysis", "overview of everything",
]

_GREETING_RESPONSES = {
    "mentor": "Hello! I'm your startup mentor. How can I help you move your startup forward today?",
    "product_manager": "Hey there! I'm your product advisor. What product question can I help you with?",
    "marketing": "Hi! I'm your marketing advisor. What marketing challenge can I help you tackle?",
    "technical": "Hello! I'm your technical advisor. What tech question do you have?",
    "investor": "Hi! I'm your investor advisor. What fundraising question can I help with?",
}


def _stringify_list_fields(data: dict) -> dict:
    """Convert list fields to comma-separated strings for prompts that expect strings."""
    result = dict(data)
    for key in ("target_users", "mvp_features", "competitors", "risks"):
        if isinstance(result.get(key), list):
            if key == "competitors":
                result[key] = ", ".join(
                    c.get("name", str(c)) if isinstance(c, dict) else str(c)
                    for c in result[key]
                )
            else:
                result[key] = ", ".join(str(item) for item in result[key])
    return result


def _detect_chat_intent(question: str) -> str:
    q = question.lower().strip().rstrip("?!., ")
    words = q.split()
    if not words:
        return "greeting"

    first = words[0].rstrip("?!,")

    if first in _GREETING_WORDS and len(words) <= 4:
        return "greeting"

    if q in _CASUAL_EXACT:
        return "casual"

    for marker in _SUMMARY_MARKERS:
        if marker in q:
            return "full_summary"

    return "idea_question"


async def _generate(prompt: str) -> dict:
    if AI_PROVIDER == "groq":
        return await generate_with_groq(prompt)
    try:
        return await generate_with_gemini(prompt)
    except GeminiRateLimitError as exc:
        raise AIRateLimitError(str(exc)) from exc
    except GeminiAPIError as exc:
        raise AIServiceError(str(exc)) from exc


async def _generate_stream(prompt: str):
    """Async generator that yields tokens then the final parsed dict."""
    if AI_PROVIDER == "groq":
        async for item in generate_with_groq_stream(prompt):
            yield item
    else:
        try:
            async for item in generate_with_gemini_stream(prompt):
                yield item
        except GeminiRateLimitError as exc:
            raise AIRateLimitError(str(exc)) from exc
        except GeminiAPIError as exc:
            raise AIServiceError(str(exc)) from exc


def _stringify_profile(profile: dict) -> dict:
    result = dict(profile)
    for key in ("skills", "interests"):
        if isinstance(result.get(key), list):
            result[key] = ", ".join(result[key])
    return result


def _with_variation(data: dict) -> dict:
    angles = [
        "underserved niche",
        "boring business automation",
        "student-friendly MVP",
        "local market wedge",
        "community-led product",
        "B2B workflow pain",
        "mobile-first habit",
        "low-budget solo founder",
        "marketplace wedge",
        "AI-assisted service",
    ]
    result = dict(data)
    result["variation_seed"] = f"{secrets.token_hex(4)}-{random.choice(angles)}"
    return result


async def analyze_profile(profile: dict) -> dict:
    data = _stringify_profile(profile)
    prompt = SKILL_ANALYSIS_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_startup_ideas(profile: dict) -> dict:
    data = _with_variation(_stringify_profile(profile))
    prompt = STARTUP_GENERATION_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_full_plan(profile: dict, idea: dict) -> dict:
    data = {**_stringify_profile(profile), **idea}
    if isinstance(data.get("target_users"), list):
        data["target_users"] = ", ".join(data["target_users"])
    prompt = FULL_PLAN_PROMPT.format(**data)
    return await _generate(prompt)


async def evaluate_startup(profile: dict, idea: dict, founder_analysis: dict) -> dict:
    data = {**_stringify_profile(profile), **idea, **founder_analysis}
    if isinstance(data.get("target_users"), list):
        data["target_users"] = ", ".join(data["target_users"])
    if isinstance(data.get("strengths"), list):
        data["strengths"] = ", ".join(data["strengths"])
    if isinstance(data.get("weaknesses"), list):
        data["weaknesses"] = ", ".join(data["weaknesses"])

    agents = [
        {
            "agent_role": "a Senior Technology Architect and Engineering Lead",
            "agent_name": "Tech Expert",
            "criteria": "- Technical feasibility & architecture soundness (30%)\n- MVP complexity and build timeline (25%)\n- Technology stack appropriateness (20%)\n- Scalability potential (15%)\n- Security & data considerations (10%)",
        },
        {
            "agent_role": "a Venture Capital Analyst and Finance Strategist",
            "agent_name": "Finance Expert",
            "criteria": "- Revenue model viability & monetization potential (30%)\n- Market size & TAM/SAM/SOM (25%)\n- Cost structure & burn rate (20%)\n- Unit economics & margin potential (15%)\n- Funding readiness & ROI timeline (10%)",
        },
        {
            "agent_role": "a Growth Marketing Director and Brand Strategist",
            "agent_name": "Marketing Expert",
            "criteria": "- Target audience clarity & fit (25%)\n- Market positioning & differentiation (25%)\n- Customer acquisition strategy (20%)\n- Growth potential & scalability of marketing (15%)\n- Brand identity & messaging strength (15%)",
        },
    ]

    async def evaluate_agent(agent_info: dict) -> dict:
        prompt = AGENT_EVALUATION_PROMPT.format(**data, **agent_info)
        return await _generate(prompt)

    results = await asyncio.gather(*[evaluate_agent(a) for a in agents])

    scores = [r.get("score", 50) for r in results]
    overall_score = round(sum(scores) / len(scores))

    strengths = []
    risks = []
    improvements = []
    for r in results:
        strengths.extend(r.get("strengths", []))
        risks.extend(r.get("risks", []))
        improvements.extend(r.get("improvements", []))

    avg_score = overall_score
    if avg_score >= 70:
        decision = "Fund"
        summary = f"This startup scores {avg_score}/100 across all expert evaluations. Strong potential for investment with recommended improvements."
    elif avg_score >= 45:
        decision = "Revise"
        summary = f"This startup scores {avg_score}/100 across all expert evaluations. Significant revisions needed before funding consideration."
    else:
        decision = "Reject"
        summary = f"This startup scores {avg_score}/100 across all expert evaluations. Major concerns across multiple dimensions. Not recommended for funding at this stage."

    return {
        "decision": decision,
        "overall_score": overall_score,
        "evaluations": results,
        "summary": summary,
    }


async def generate_cofounder(profile: dict, idea: dict, founder_analysis: dict) -> dict:
    data = {**_stringify_profile(profile), **idea, **founder_analysis}
    if isinstance(data.get("target_users"), list):
        data["target_users"] = ", ".join(data["target_users"])
    if isinstance(data.get("strengths"), list):
        data["strengths"] = ", ".join(data["strengths"])
    if isinstance(data.get("weaknesses"), list):
        data["weaknesses"] = ", ".join(data["weaknesses"])

    prompt = COFOUNDER_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_task_roadmap(profile: dict, idea: dict, plan: dict) -> dict:
    data = {**_stringify_profile(profile), **idea, **plan}
    if isinstance(data.get("target_users"), list):
        data["target_users"] = ", ".join(data["target_users"])
    if isinstance(data.get("mvp_features"), list):
        data["mvp_features"] = ", ".join(data["mvp_features"])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("revenue_model"), dict):
        data["revenue_model"] = data["revenue_model"].get("pricing_model", str(data["revenue_model"]))

    prompt = TASK_ROADMAP_PROMPT.format(**data)
    result = await _generate(prompt)
    return result


async def analyze_idea(data: dict) -> dict:
    prompt = IDEA_ANALYSIS_PROMPT.format(**data)
    return await _generate(prompt)


async def chat_about_idea(analysis: dict, question: str) -> dict:
    intent = _detect_chat_intent(question)

    if intent == "greeting":
        return {"answer": "Hello! How can I help you with your startup idea?"}
    if intent == "casual":
        return {"answer": "I'm great, thanks! Ready to dive into your startup idea whenever you are."}

    data = {"analysis": json.dumps(analysis, indent=2), "question": question}
    if intent == "full_summary":
        prompt = IDEA_CHAT_FULL_PROMPT.format(**data)
    else:
        prompt = IDEA_CHAT_CONCISE_PROMPT.format(**data)
    return await _generate(prompt)


async def _yield_hardcoded_stream(answer: str):
    words = answer.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
    yield {"answer": answer}


async def chat_about_idea_stream(analysis: dict, question: str):
    intent = _detect_chat_intent(question)

    if intent == "greeting":
        async for item in _yield_hardcoded_stream("Hello! How can I help you with your startup idea?"):
            yield item
        return

    if intent == "casual":
        async for item in _yield_hardcoded_stream("I'm great, thanks! Ready to dive into your startup idea whenever you are."):
            yield item
        return

    data = {"analysis": json.dumps(analysis, indent=2), "question": question}
    if intent == "full_summary":
        prompt = IDEA_CHAT_FULL_PROMPT.format(**data)
    else:
        prompt = IDEA_CHAT_CONCISE_PROMPT.format(**data)
    async for item in _generate_stream(prompt):
        yield item


async def analyze_idea_stream(data: dict):
    """Stream tokens then yield final parsed result for idea analysis."""
    prompt = IDEA_ANALYSIS_PROMPT.format(**data)
    async for item in _generate_stream(prompt):
        yield item


async def estimate_market_size(data: dict) -> dict:
    prompt = MARKET_SIZE_PROMPT.format(**data)
    return await _generate(prompt)


async def debate_idea(data: dict) -> dict:
    prompt = DEBATE_ROOM_PROMPT.format(**data)
    return await _generate(prompt)


async def compare_ideas(data: dict) -> dict:
    prompt = COMPARISON_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_email_report(analysis: dict) -> str:
    data = {"analysis": json.dumps(analysis, indent=2)}
    prompt = EMAIL_REPORT_PROMPT.format(**data)
    result = await _generate(prompt)
    html = result.get("html", "")
    if not html:
        html = result.get("answer", "")
    if not html:
        html = json.dumps(result)
    return html


async def generate_readme(profile: dict, idea: dict, plan: dict) -> dict:
    data = {**_stringify_profile(profile), **idea, **plan}
    if isinstance(data.get("target_users"), list):
        data["target_users"] = ", ".join(data["target_users"])
    if isinstance(data.get("mvp_features"), list):
        data["mvp_features"] = ", ".join(data["mvp_features"])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("revenue_model"), dict):
        data["revenue_model"] = data["revenue_model"].get("pricing_model", str(data["revenue_model"]))

    prompt = README_GENERATOR_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_first_100_customers(data: dict) -> dict:
    for key in ("target_users", "mvp_features"):
        if isinstance(data.get(key), list):
            data[key] = ", ".join(data[key])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    prompt = FIRST_100_CUSTOMERS_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_decision_engine(data: dict) -> dict:
    for key in ("target_users", "mvp_features"):
        if isinstance(data.get(key), list):
            data[key] = ", ".join(data[key])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("risks"), list):
        data["risks"] = ", ".join(data["risks"])
    prompt = DECISION_ENGINE_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_business_plan(data: dict) -> dict:
    for key in ("target_users", "mvp_features"):
        if isinstance(data.get(key), list):
            data[key] = ", ".join(data[key])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("risks"), list):
        data["risks"] = ", ".join(data["risks"])
    prompt = BUSINESS_PLANNING_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_customer_insights(data: dict) -> dict:
    for key in ("target_users", "mvp_features"):
        if isinstance(data.get(key), list):
            data[key] = ", ".join(data[key])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("risks"), list):
        data["risks"] = ", ".join(data["risks"])
    prompt = CUSTOMER_INSIGHTS_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_market_intelligence(data: dict) -> dict:
    for key in ("target_users", "mvp_features"):
        if isinstance(data.get(key), list):
            data[key] = ", ".join(data[key])
    if isinstance(data.get("competitors"), list):
        data["competitors"] = ", ".join(
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in data["competitors"]
        )
    if isinstance(data.get("risks"), list):
        data["risks"] = ", ".join(data["risks"])
    prompt = MARKET_INTELLIGENCE_PROMPT.format(**data)
    return await _generate(prompt)


_ADVISOR_PROMPTS = {
    "mentor": AI_MENTOR_PROMPT,
    "product_manager": AI_PM_PROMPT,
    "marketing": AI_MARKETING_PROMPT,
    "technical": AI_TECH_PROMPT,
    "investor": AI_INVESTOR_PROMPT,
}


async def generate_ai_cofounder_chat(advisor_type: str, question: str, startup_context: dict) -> dict:
    intent = _detect_chat_intent(question)

    if intent == "greeting":
        greeting = _GREETING_RESPONSES.get(advisor_type, "Hello! How can I help you with your startup?")
        return {"answer": greeting}
    if intent == "casual":
        return {"answer": "I'm here to help! Feel free to ask me anything about your startup."}

    prompt_template = _ADVISOR_PROMPTS.get(advisor_type)
    if not prompt_template:
        raise AIServiceError(f"Unknown advisor type: {advisor_type}")

    context = _stringify_list_fields(startup_context)
    context["question"] = question

    try:
        prompt = prompt_template.format(**context)
        return await _generate(prompt)
    except KeyError as e:
        logger.error("Missing field in advisor context: %s", e)
        return {"answer": f"I need more context to answer that. Could you provide more details about your startup?"}
    except Exception as e:
        logger.error("Advisor chat failed: %s", e)
        return {"answer": "I encountered an error processing your question. Please try again."}


async def generate_investor_tools(data: dict) -> dict:
    data = _stringify_list_fields(data)
    data.setdefault("revenue_potential", "0")
    prompt = INVESTOR_TOOLS_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_marketing_hub(data: dict) -> dict:
    data = _stringify_list_fields(data)
    data.setdefault("revenue_potential", "0")
    prompt = MARKETING_HUB_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_development_hub(data: dict) -> dict:
    data = _stringify_list_fields(data)
    data.setdefault("tech_stack", "")
    prompt = DEVELOPMENT_HUB_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_growth_hub(data: dict) -> dict:
    data = _stringify_list_fields(data)
    data.setdefault("revenue_potential", "0")
    prompt = GROWTH_HUB_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_financial_plan(data: dict) -> dict:
    data = _stringify_list_fields(data)
    prompt = FINANCIAL_PLANNING_PROMPT.format(**data)
    return await _generate(prompt)


async def generate_launch_hub(data: dict) -> dict:
    data = _stringify_list_fields(data)
    prompt = LAUNCH_HUB_PROMPT.format(**data)
    return await _generate(prompt)
