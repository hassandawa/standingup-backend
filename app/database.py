import logging
import certifi
from pymongo import MongoClient, ASCENDING, DESCENDING
from app.config import MONGODB_URL, DATABASE_NAME

logger = logging.getLogger(__name__)

# tlsCAFile=certifi.where() fixes TLS handshake failures
# (e.g. "TLSV1_ALERT_INTERNAL_ERROR") seen on some serverless Linux
# runtimes where the system CA bundle doesn't fully validate Atlas's
# certificate chain. Safe to keep on any platform.
client = MongoClient(
    MONGODB_URL,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    tls=True,
    tlsCAFile=certifi.where(),
)
db = client[DATABASE_NAME]

founder_profiles = db["founder_profiles"]
startup_plans = db["startup_plans"]
shared_analyses = db["shared_analyses"]
saved_analyses = db["saved_analyses"]
build_progress = db["build_progress"]
analytics_events = db["analytics_events"]
customer_strategies = db["customer_strategies"]
decision_reports = db["decision_reports"]
business_plans = db["business_plans"]
customer_insights = db["customer_insights"]
market_intelligence = db["market_intelligence"]
ai_cofounder_chats = db["ai_cofounder_chats"]
investor_tools = db["investor_tools"]
marketing_hub = db["marketing_hub"]
development_hubs = db["development_hubs"]
growth_hubs = db["growth_hubs"]
financial_plans = db["financial_plans"]
launch_hubs = db["launch_hubs"]
teams = db["teams"]
team_invites = db["team_invites"]
team_analyses = db["team_analyses"]
comments = db["comments"]
users = db["users"]
saved_ideas = db["saved_ideas"]
password_resets = db["password_resets"]


def ensure_indexes():
    """Create indexes for performance. Safe to call multiple times."""
    try:
        startup_plans.create_index([("created_at", DESCENDING)])
        startup_plans.create_index([("plan.startup_name", ASCENDING)])
        startup_plans.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        saved_analyses.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        customer_strategies.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        decision_reports.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        business_plans.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        customer_insights.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        market_intelligence.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        ai_cofounder_chats.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        ai_cofounder_chats.create_index([("advisor_type", ASCENDING), ("user_id", ASCENDING)])
        investor_tools.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        marketing_hub.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        development_hubs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        growth_hubs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        financial_plans.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        launch_hubs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        teams.create_index([("owner_id", ASCENDING)])
        teams.create_index([("invite_code", ASCENDING)], unique=True)
        team_invites.create_index([("team_id", ASCENDING), ("email", ASCENDING)])
        team_analyses.create_index([("team_id", ASCENDING)])
        comments.create_index([("target_type", ASCENDING), ("target_id", ASCENDING)])
        comments.create_index([("user_id", ASCENDING)])
        founder_profiles.create_index([("created_at", DESCENDING)])
        users.create_index([("email", ASCENDING)], unique=True)
        users.create_index([("created_at", DESCENDING)])
        saved_ideas.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        password_resets.create_index([("token", ASCENDING)], unique=True)
        password_resets.create_index([("email", ASCENDING)])
        password_resets.create_index([("created_at", ASCENDING)], expireAfterSeconds=900)
        logger.info("MongoDB indexes ensured.")
    except Exception as e:
        logger.warning("Failed to create MongoDB indexes: %s", e)
