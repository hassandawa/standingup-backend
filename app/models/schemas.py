from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class AgentEvaluation(BaseModel):
    agent: str
    score: int = Field(..., ge=0, le=100)
    strengths: list[str]
    risks: list[str]
    improvements: list[str]


class FundingDecision(BaseModel):
    decision: Literal["Fund", "Revise", "Reject"]
    overall_score: int = Field(..., ge=0, le=100)
    evaluations: list[AgentEvaluation]
    summary: str


class CofounderPersona(BaseModel):
    name: str
    personality: str
    strengths: list[str]
    complement: str
    advice: list[str] = Field(..., min_length=3, max_length=3)


class RoadmapTask(BaseModel):
    phase: str
    task: str
    priority: Literal["High", "Medium", "Low"]
    estimated_time_hours: int
    tools_needed: list[str]
    status: Literal["Pending", "In Progress", "Done"] = "Pending"


class SignUpRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)


class SignInRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UserProfile(BaseModel):
    skills: list[str] = Field(..., min_length=1)
    interests: list[str] = Field(..., min_length=1)
    experience_level: str = "Intermediate"
    budget: str = "100"
    time_per_week: str = "10"
    preferred_industry: Optional[str] = ""
    goal: str = Field(..., min_length=1)


class FounderProfileResponse(BaseModel):
    founder_type: str
    strengths: list[str]
    weaknesses: list[str]
    best_startup_categories: list[str]


class StartupIdea(BaseModel):
    startup_name: str
    pitch: str
    problem: str
    solution: str
    target_users: list[str]
    why_now: str
    opportunity_score: float
    feasibility_score: float
    demand_score: float
    monetization_score: float
    competition_gap_score: float
    founder_fit_score: float


class StartupIdeasResponse(BaseModel):
    ideas: list[StartupIdea]


class CompetitorInfo(BaseModel):
    name: str
    strengths: list[str]
    weaknesses: list[str]


class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]


class RoadmapItem(BaseModel):
    week: int
    title: str
    tasks: list[str]


class StartupPlan(BaseModel):
    startup_name: str
    pitch: str
    problem: str
    solution: str
    target_users: list[str]
    why_now: str
    opportunity_score: float
    competitors: list[CompetitorInfo]
    competitor_limitations: list[str]
    our_advantages: list[str]
    market_gaps: list[str]
    mvp_features: list[str]
    mvp_v1_scope: str = ""
    mvp_v2_features: list[str] = []
    roadmap: list[RoadmapItem]
    revenue_model: dict
    launch_strategy: str
    swot: SWOTAnalysis
    risks: list[str]
    hackathon_pitch: str
    thirty_second_pitch: str


class PlanRequest(BaseModel):
    profile: UserProfile
    idea: StartupIdea


class SavePlanRequest(BaseModel):
    plan: StartupPlan
    profile: UserProfile


class EvaluationRequest(BaseModel):
    profile: UserProfile
    idea: StartupIdea


class CofounderRequest(BaseModel):
    profile: UserProfile
    idea: StartupIdea


class RoadmapRequest(BaseModel):
    profile: UserProfile
    idea: StartupIdea
    plan: StartupPlan


class ReadmeRequest(BaseModel):
    profile: UserProfile
    idea: StartupIdea
    plan: StartupPlan


class IdeaAnalysisRequest(BaseModel):
    startup_idea: str = Field(..., min_length=10, max_length=2000)
    target_audience: Optional[str] = ""
    industry: Optional[str] = ""
    skills: Optional[str] = ""
    budget_time_limit: Optional[str] = ""


class CompetitorAnalysis(BaseModel):
    name: str
    strengths: list[str]
    weaknesses: list[str]
    source: Literal["ai-estimated", "web"]


class BuildPlanDay(BaseModel):
    day: int
    title: str
    tasks: list[str]


class IdeaChatRequest(BaseModel):
    analysis: dict
    question: str = Field(..., min_length=1, max_length=1000)


class IdeaChatResponse(BaseModel):
    answer: str


class ShareLinkRequest(BaseModel):
    analysis: dict
    idea_form: dict = {}


class ShareLinkResponse(BaseModel):
    token: str
    url: str


class MarketSizeRequest(BaseModel):
    startup_idea: str = Field(..., min_length=10, max_length=2000)
    industry: Optional[str] = ""
    target_audience: Optional[str] = ""


class MarketSizeResponse(BaseModel):
    tam: str
    sam: str
    som: str
    growth_rate: str
    key_trends: list[str]
    revenue_projection: str
    data_confidence: Literal["high", "medium", "low"]


class DebateRequest(BaseModel):
    startup_idea: str = Field(..., min_length=10, max_length=2000)
    industry: Optional[str] = ""
    target_audience: Optional[str] = ""


class DebateAgentMessage(BaseModel):
    agent_name: str
    role: str
    argument: str
    emoji: str = ""


class DebateResponse(BaseModel):
    agents: list[DebateAgentMessage]
    consensus: str
    key_takeaways: list[str]


class ComparisonRequest(BaseModel):
    idea_a: str = Field(..., min_length=10, max_length=2000)
    idea_b: str = Field(..., min_length=10, max_length=2000)
    industry: Optional[str] = ""


class ComparisonDimension(BaseModel):
    dimension: str
    idea_a_score: int = Field(..., ge=0, le=10)
    idea_b_score: int = Field(..., ge=0, le=10)
    idea_a_notes: str
    idea_b_notes: str


class ComparisonResponse(BaseModel):
    dimensions: list[ComparisonDimension]
    overall_winner: str
    summary: str


class EmailReportRequest(BaseModel):
    analysis: dict
    recipient_email: str = Field(..., min_length=3, max_length=254)
    idea_form: dict = {}


class EmailReportResponse(BaseModel):
    sent: bool
    message: str


class ProgressSaveRequest(BaseModel):
    token: str = Field(..., min_length=1)
    day: int = Field(..., ge=1, le=7)
    completed_tasks: list[str]
    notes: str = ""


class ProgressLoadResponse(BaseModel):
    days: dict


class ColdMessageTemplate(BaseModel):
    channel: str
    subject: str
    body: str


class ActionDay(BaseModel):
    day: int
    title: str
    tasks: list[str]


class First100CustomersRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    mvp_features: list[str] = []
    competitors: list = []
    industry: str = ""


class First100CustomersResponse(BaseModel):
    ideal_early_adopters: str
    where_to_find_them: list[str]
    outreach_channels: list[str]
    cold_message_templates: list[ColdMessageTemplate]
    social_media_launch_plan: str
    referral_strategy: str
    seven_day_action_plan: list[ActionDay]
    metrics_to_track: list[str]


class RiskAnalysis(BaseModel):
    overall_risk_level: Literal["Low", "Medium", "High"]
    key_business_risks: list[str]
    technical_risks: list[str]
    market_risks: list[str]
    financial_risks: list[str]


class SuccessProbability(BaseModel):
    percentage: int = Field(..., ge=0, le=100)
    reason: str


class Recommendation(BaseModel):
    decision: Literal["Go", "Pivot", "Drop"]
    explanation: str
    action_steps: list[str]


class DecisionEngineRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    feasibility: float = 0
    revenue_potential: float = 0
    risks: list[str] = []


class DecisionEngineResponse(BaseModel):
    risk_analysis: RiskAnalysis
    success_probability: SuccessProbability
    recommendation: Recommendation


class AnalyticsEvent(BaseModel):
    event: str = Field(..., min_length=1)
    properties: dict = {}


class AnalyticsResponse(BaseModel):
    total_analyses: int
    total_shares: int
    total_chats: int
    top_industries: list[dict]
    recent_events: list[dict]

class IdeaAnalysisResponse(BaseModel):
    refined_idea: str
    problem_statement: str
    target_users: list[str]
    market_demand_score: float
    uniqueness_score: float
    feasibility_score: float
    revenue_potential_score: float
    hackathon_winning_score: float
    competitors: list[CompetitorAnalysis]
    differentiation_strategy: str
    mvp_features: list[str]
    tech_stack_recommendation: list[str]
    monetization_model: str
    risks: list[str]
    improvement_suggestions: list[str]
    seven_day_build_plan: list[BuildPlanDay]
    founder_readiness_check: str
    pitch_summary: str


class BusinessModelCanvas(BaseModel):
    customer_segments: list[str]
    value_proposition: str
    channels: list[str]
    customer_relationships: str
    revenue_streams: list[str]
    key_resources: list[str]
    key_activities: list[str]
    key_partners: list[str]
    cost_structure: list[str]


class LeanCanvas(BaseModel):
    problem: list[str]
    customer_segments: list[str]
    unique_value_proposition: str
    solution: list[str]
    channels: list[str]
    revenue_streams: list[str]
    cost_structure: list[str]
    key_metrics: list[str]
    unfair_advantage: str


class YearForecast(BaseModel):
    total_revenue: float = 0
    monthly_revenue: list[float] = []
    estimated_customers: int = 0
    avg_revenue_per_customer: float = 0
    growth_rate: str = ""


class ScenarioForecast(BaseModel):
    year_1_revenue: float = 0
    year_2_revenue: float = 0
    year_3_revenue: float = 0
    assumptions: str = ""


class RevenueForecast(BaseModel):
    year_1: YearForecast
    year_2: YearForecast
    year_3: YearForecast
    best_case: ScenarioForecast
    expected_case: ScenarioForecast
    worst_case: ScenarioForecast
    growth_assumptions: list[str]


class PricingTier(BaseModel):
    name: str
    price: float = 0
    features: list[str]
    target_customers: str = ""


class CompetitorPricing(BaseModel):
    competitor_name: str
    model: str
    price_range: str = ""


class PricingStrategy(BaseModel):
    recommended_model: str
    tiers: list[PricingTier]
    competitor_pricing: list[CompetitorPricing]
    justification: str
    monetization_recommendations: list[str]


class BusinessPlanningRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    feasibility: float = 0
    revenue_potential: float = 0
    risks: list[str] = []
    monetization_model: str = ""
    revenue_model_type: str = ""


class BusinessPlanningResponse(BaseModel):
    business_model_canvas: BusinessModelCanvas
    lean_canvas: LeanCanvas
    revenue_forecast: RevenueForecast
    pricing_strategy: PricingStrategy


class Persona(BaseModel):
    name: str
    age: str = ""
    occupation: str = ""
    location: str = ""
    goals: list[str] = []
    challenges: list[str] = []
    motivations: list[str] = []
    buying_behavior: str = ""
    preferred_channels: list[str] = []


class IdealCustomerProfile(BaseModel):
    target_audience: str = ""
    industry: str = ""
    company_size: str = ""
    demographics: str = ""
    interests: list[str] = []
    budget: str = ""
    buying_intent: str = ""
    decision_makers: list[str] = []
    primary_use_cases: list[str] = []


class PainPoint(BaseModel):
    pain_point: str
    existing_solutions: str = ""
    why_they_fail: str = ""
    startup_solution: str = ""
    priority: str = "Medium"


class JourneyStage(BaseModel):
    customer_goals: str = ""
    actions: list[str] = []
    pain_points: list[str] = []
    emotions: list[str] = []
    opportunities: list[str] = []


class CustomerJourney(BaseModel):
    awareness: JourneyStage
    consideration: JourneyStage
    decision: JourneyStage
    purchase: JourneyStage
    onboarding: JourneyStage
    retention: JourneyStage
    referral: JourneyStage


class CustomerInsightsRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    risks: list[str] = []
    monetization_model: str = ""


class CustomerInsightsResponse(BaseModel):
    personas: list[Persona]
    ideal_customer_profile: IdealCustomerProfile
    pain_point_analysis: list[PainPoint]
    customer_journey: CustomerJourney


class MarketSizeDetail(BaseModel):
    value: str = ""
    description: str = ""
    assumptions: list[str] = []


class MarketSize(BaseModel):
    tam: MarketSizeDetail
    sam: MarketSizeDetail
    som: MarketSizeDetail
    confidence_level: str = "Medium"


class MarketTrend(BaseModel):
    trend: str
    description: str = ""
    impact_on_startup: str = ""
    priority: str = "Medium"


class IndustryGrowth(BaseModel):
    annual_growth_rate: str = ""
    growth_drivers: list[str] = []
    market_limitations: list[str] = []
    five_year_outlook: str = ""


class EmergingOpportunity(BaseModel):
    opportunity: str
    description: str = ""
    how_to_capitalize: str = ""
    impact: str = "Medium"
    feasibility: str = "Medium"


class CompetitorFeatureRow(BaseModel):
    competitor_name: str
    features: list[str] = []
    pricing_model: str = ""
    target_users: str = ""
    strengths: list[str] = []
    weaknesses: list[str] = []
    differentiation_opportunity: str = ""


class MarketIntelligenceRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    risks: list[str] = []
    monetization_model: str = ""


class MarketIntelligenceResponse(BaseModel):
    market_size: MarketSize
    market_trends: list[MarketTrend]
    industry_growth: IndustryGrowth
    emerging_opportunities: list[EmergingOpportunity]
    competitor_comparison: list[CompetitorFeatureRow]


class AICofounderChatRequest(BaseModel):
    advisor_type: Literal["mentor", "product_manager", "marketing", "technical", "investor"]
    question: str = Field(..., min_length=1, max_length=2000)
    startup_context: dict = {}


class AICofounderChatResponse(BaseModel):
    answer: str


class PitchDeckSlide(BaseModel):
    slide_number: int
    title: str
    content: str = ""
    visual_suggestion: str = ""


class PitchDeck(BaseModel):
    slides: list[PitchDeckSlide]


class ElevatorPitch(BaseModel):
    short_pitch: str = ""
    full_pitch: str = ""
    key_message: str = ""


class ExecutiveSummary(BaseModel):
    problem: str = ""
    solution: str = ""
    target_market: str = ""
    business_model: str = ""
    competitive_advantage: str = ""
    revenue_potential: str = ""
    risks: list[str] = []
    next_steps: str = ""


class ReadinessScore(BaseModel):
    overall_score: int = 0
    market_demand_score: int = 0
    uniqueness_score: int = 0
    feasibility_score: int = 0
    revenue_potential_score: int = 0
    traction_score: int = 0
    team_readiness_score: int = 0
    financial_clarity_score: int = 0
    risk_management_score: int = 0
    strengths: list[str] = []
    weaknesses: list[str] = []
    improvement_suggestions: list[str] = []


class FundingRecommendation(BaseModel):
    recommended_type: str = ""
    explanation: str = ""
    amount_range: str = ""
    equity_to_offer: str = ""
    preparation_steps: list[str] = []
    ideal_investor_types: list[str] = []
    milestones_to_reach_before_fundraising: list[str] = []


class InvestorToolsRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    feasibility: float = 0
    revenue_potential: float = 0
    risks: list[str] = []
    monetization_model: str = ""


class InvestorToolsResponse(BaseModel):
    pitch_deck: PitchDeck
    elevator_pitch: ElevatorPitch
    executive_summary: ExecutiveSummary
    readiness_score: ReadinessScore
    funding_recommendation: FundingRecommendation


class LandingPageFeature(BaseModel):
    feature: str = ""
    description: str = ""


class SocialProof(BaseModel):
    testimonial_placeholder: str = ""
    stat_placeholder: str = ""
    trust_badges: list[str] = []


class FAQ(BaseModel):
    question: str = ""
    answer: str = ""


class CTA(BaseModel):
    primary_cta: str = ""
    secondary_cta: str = ""
    cta_description: str = ""


class Footer(BaseModel):
    tagline: str = ""
    links: list[str] = []
    copyright: str = ""


class LandingPageCopy(BaseModel):
    hero_headline: str = ""
    subheadline: str = ""
    value_proposition: str = ""
    key_features: list[LandingPageFeature] = []
    benefits: list[str] = []
    social_proof: SocialProof
    faqs: list[FAQ] = []
    cta: CTA
    footer: Footer


class BrandName(BaseModel):
    name: str
    explanation: str = ""
    style: str = ""
    is_memorable: bool = True
    is_scalable: bool = True


class LogoIdea(BaseModel):
    style: str = ""
    colors: list[str] = []
    typography: str = ""
    icon_suggestion: str = ""
    brand_personality: str = ""
    ai_image_prompt: str = ""


class TaglineCategory(BaseModel):
    professional: list[str] = []
    modern: list[str] = []
    premium: list[str] = []
    creative: list[str] = []
    minimal: list[str] = []
    startup_focused: list[str] = []


class SocialPost(BaseModel):
    day: int = 0
    post_type: str = ""
    content: str = ""
    hashtags: list[str] = []


class PlatformStrategy(BaseModel):
    platform: str = ""
    content_ideas: list[SocialPost] = []
    posting_frequency: str = ""
    engagement_strategy: str = ""


class SocialMediaLaunch(BaseModel):
    strategy_overview: str = ""
    platforms: list[PlatformStrategy] = []
    launch_day_checklist: list[str] = []


class SEOKeyword(BaseModel):
    keyword: str = ""
    search_intent: str = ""
    difficulty: str = ""
    content_idea: str = ""


class SEOKeywordSecondary(BaseModel):
    keyword: str = ""
    search_intent: str = ""
    content_idea: str = ""


class BlogTopic(BaseModel):
    title: str = ""
    target_keyword: str = ""
    description: str = ""


class SEOKeywords(BaseModel):
    primary_keywords: list[SEOKeyword] = []
    secondary_keywords: list[SEOKeywordSecondary] = []
    long_tail_keywords: list[SEOKeywordSecondary] = []
    blog_topics: list[BlogTopic] = []
    seo_tips: list[str] = []


class MarketingHubRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: list[str] = []
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: list[str] = []
    competitors: list = []
    market_demand: float = 0
    uniqueness: float = 0
    feasibility: float = 0
    risks: list[str] = []
    monetization_model: str = ""


class MarketingHubResponse(BaseModel):
    landing_page_copy: LandingPageCopy
    brand_names: list[BrandName]
    logo_ideas: list[LogoIdea]
    taglines: TaglineCategory
    social_media_launch: SocialMediaLaunch
    seo_keywords: SEOKeywords


# ─── Development Hub ──────────────────────────────────────────────────────────

class DevelopmentHubRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: str = ""
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: str = ""
    competitors: str = ""
    tech_stack: str = ""
    monetization_model: str = ""


class DBAttribute(BaseModel):
    name: str
    type: str
    constraints: str
    description: str

class DBEntity(BaseModel):
    name: str
    description: str
    attributes: list[DBAttribute]
    relationships: list[str]

class DBIndex(BaseModel):
    name: str
    fields: list[str]
    type: str
    purpose: str

class DatabaseSchema(BaseModel):
    entities: list[DBEntity]
    indexes: list[DBIndex]
    er_diagram_summary: str
    design_notes: list[str]

class APIEndpoint(BaseModel):
    method: str
    path: str
    auth_required: bool
    description: str
    request_body: str
    response: str
    status_codes: list[str]

class APIEndpoints(BaseModel):
    endpoints: list[APIEndpoint]
    api_design_notes: list[str]

class ProjectFolder(BaseModel):
    path: str
    purpose: str
    children: list["ProjectFolder"] | None = None

class KeyFile(BaseModel):
    path: str
    purpose: str

class ProjectStructure(BaseModel):
    root_folder: str
    folders: list[ProjectFolder]
    key_files: list[KeyFile]
    architectural_notes: list[str]

class GettingStarted(BaseModel):
    prerequisites: list[str]
    installation: list[str]
    development: list[str]

class ReadmeContent(BaseModel):
    project_name: str
    description: str
    features: list[str]
    tech_stack: list[str]
    getting_started: GettingStarted
    api_documentation: str
    contributing: list[str]
    license: str
    readme_notes: list[str]

class DeploymentEnvironment(BaseModel):
    name: str
    purpose: str
    hosting: str
    url: str

class DockerInfo(BaseModel):
    dockerfile: str
    docker_compose: str

class CICD(BaseModel):
    provider: str
    pipeline_steps: list[str]

class HostingOption(BaseModel):
    platform: str
    frontend: bool
    backend: bool
    estimated_cost: str
    notes: str

class EnvVariable(BaseModel):
    key: str
    description: str
    required: bool

class DeploymentGuide(BaseModel):
    environments: list[DeploymentEnvironment]
    docker: DockerInfo
    ci_cd: CICD
    hosting_options: list[HostingOption]
    environment_variables: list[EnvVariable]
    deployment_steps: list[str]
    post_deployment: list[str]
    deployment_notes: list[str]

class DevelopmentHubResponse(BaseModel):
    database_schema: DatabaseSchema
    api_endpoints: APIEndpoints
    project_structure: ProjectStructure
    readme: ReadmeContent
    deployment_guide: DeploymentGuide


# ─── Growth Hub ───────────────────────────────────────────────────────────────

class GrowthHubRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: str = ""
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: str = ""
    competitors: str = ""
    market_demand: float = 0
    uniqueness: float = 0
    feasibility: float = 0
    risks: str = ""
    monetization_model: str = ""


class GrowthAction(BaseModel):
    day: int
    action: str
    owner: str
    metrics: str
    priority: str

class GrowthPhase(BaseModel):
    title: str
    focus: str
    goals: list[str]
    actions: list[GrowthAction]
    success_criteria: list[str]

class GrowthMilestone(BaseModel):
    title: str
    deadline: str
    description: str
    verification: str

class GrowthPlan(BaseModel):
    overview: str
    phase_1_30_days: GrowthPhase
    phase_2_60_days: GrowthPhase
    phase_3_90_days: GrowthPhase
    key_milestones: list[GrowthMilestone]

class KPI(BaseModel):
    name: str
    category: str
    current_estimate: str
    day_30_target: str = Field("", alias="30_day_target")
    day_60_target: str = Field("", alias="60_day_target")
    day_90_target: str = Field("", alias="90_day_target")
    measurement_frequency: str = ""
    formula: str = ""
    why_it_matters: str = ""

class KPIDashboard(BaseModel):
    overview: str
    kpis: list[KPI]
    leading_indicators: list[str]
    lagging_indicators: list[str]
    review_cadence: str

class InputMetric(BaseModel):
    name: str
    lever: str
    current_estimate: str

class NorthStarMetric(BaseModel):
    metric_name: str
    definition: str
    formula: str
    why_this_metric: str
    input_metrics: list[InputMetric]
    target: str
    alignment_questions: list[str]

class AcquisitionChannel(BaseModel):
    name: str
    strategy: str
    estimated_cac: str
    estimated_ltv: str
    timeline_to_roi: str
    effort: str
    impact: str
    tactics: list[str]

class BudgetSplit(BaseModel):
    channel: str
    percentage: int
    rationale: str

class UserAcquisition(BaseModel):
    overview: str
    channels: list[AcquisitionChannel]
    recommended_budget_split: list[BudgetSplit]
    viral_loop: str

class GrowthHack(BaseModel):
    title: str
    description: str
    implementation: str
    expected_impact: str
    time_to_implement: str
    resources_needed: list[str]
    success_metric: str

class GrowthHubResponse(BaseModel):
    growth_plan: GrowthPlan
    kpi_dashboard: KPIDashboard
    north_star_metric: NorthStarMetric
    user_acquisition: UserAcquisition
    growth_hacks: list[GrowthHack]


# ─── Financial Planning Hub ───────────────────────────────────────────────────

class FinancialPlanRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: str = ""
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: str = ""
    competitors: str = ""
    monetization_model: str = ""


class BudgetCategory(BaseModel):
    name: str
    amount: float
    percentage: float
    notes: str

class MonthlyBudget(BaseModel):
    total: float
    categories: list[BudgetCategory]

class BudgetPlanner(BaseModel):
    overview: str
    currency: str
    monthly_budget: MonthlyBudget
    annual_budget_total: float
    budget_assumptions: list[str]
    cost_optimization_tips: list[str]

class BurnRateCategory(BaseModel):
    category: str
    monthly: float
    annual: float
    percentage: float

class RunwayScenario(BaseModel):
    scenario: str
    runway_months: int
    description: str

class BurnRate(BaseModel):
    monthly_burn_rate: float
    annual_burn_rate: float
    current_runway_months: int
    total_funding_raised: float
    burn_rate_by_category: list[BurnRateCategory]
    runway_scenarios: list[RunwayScenario]
    burn_rate_assumptions: list[str]
    reduction_strategies: list[str]

class BreakEvenPoint(BaseModel):
    month: int
    revenue: float
    costs: float
    cumulative_profit: float

class SensitivityAnalysis(BaseModel):
    variable: str
    impact: str
    recommendation: str

class BreakEven(BaseModel):
    fixed_costs_monthly: float
    variable_costs_per_unit: float
    average_revenue_per_unit: float
    contribution_margin: float
    break_even_units_monthly: float
    break_even_revenue_monthly: float
    break_even_months: int
    months_to_break_even: int
    break_even_chart: list[BreakEvenPoint]
    assumptions: list[str]
    sensitivity_analysis: list[SensitivityAnalysis]

class MonthlyProjection(BaseModel):
    month: int
    users: int
    revenue: float
    growth_rate: str
    notes: str

class YearlySummary(BaseModel):
    year: int
    total_revenue: float
    total_costs: float
    net_profit: float
    total_users: int

class RevenueStream(BaseModel):
    name: str
    percentage: float
    monthly_projection_year_1: float
    monthly_projection_year_2: float

class RiskMitigation(BaseModel):
    risk: str
    impact: str
    mitigation: str

class RevenueProjection(BaseModel):
    overview: str
    projection_type: str
    currency: str
    monthly_projections: list[MonthlyProjection]
    yearly_summary: list[YearlySummary]
    revenue_streams: list[RevenueStream]
    assumptions: list[str]
    risks_and_mitigations: list[RiskMitigation]

class MonthlyProfit(BaseModel):
    month: int
    revenue: float
    cogs: float
    gross_profit: float
    operating_expenses: float
    net_profit: float
    margin: str

class KeyRatio(BaseModel):
    name: str
    value: str
    industry_benchmark: str
    status: str

class ProfitEstimator(BaseModel):
    overview: str
    currency: str
    monthly_estimates: list[MonthlyProfit]
    key_ratios: list[KeyRatio]
    profitability_timeline: str
    optimization_levers: list[str]
    assumptions: list[str]

class FinancialPlanResponse(BaseModel):
    budget_planner: BudgetPlanner
    burn_rate: BurnRate
    break_even: BreakEven
    revenue_projection: RevenueProjection
    profit_estimator: ProfitEstimator


# ─── Launch Hub ───────────────────────────────────────────────────────────────

class LaunchHubRequest(BaseModel):
    startup_name: str = ""
    pitch: str = ""
    problem: str = ""
    solution: str = ""
    target_users: str = ""
    industry: str = ""
    location: str = ""
    business_model: str = ""
    mvp_features: str = ""
    competitors: str = ""
    monetization_model: str = ""
    risks: str = ""


class ChecklistItem(BaseModel):
    id: str
    text: str
    category: str
    priority: str
    estimated_time: str
    details: str


class ProductHuntChecklist(BaseModel):
    overview: str
    items: list[ChecklistItem]
    total_items: int
    launch_day_timeline: dict
    tips: list[str]


class AppStoreChecklist(BaseModel):
    overview: str
    platform: str
    items: list[ChecklistItem]
    total_items: int
    review_time_estimate: str
    aso_tips: list[str]
    tips: list[str]


class BetaAction(BaseModel):
    day: int
    action: str
    owner: str
    details: str


class BetaPhase(BaseModel):
    phase: str
    duration: str
    goals: list[str]
    actions: list[BetaAction]


class BetaLaunchPlan(BaseModel):
    overview: str
    phases: list[BetaPhase]
    beta_tester_criteria: list[str]
    feedback_collection: str
    success_metrics: list[str]
    tips: list[str]


class CustomerChannel(BaseModel):
    name: str
    tactic: str
    estimated_reach: str
    estimated_conversions: str
    cost: str
    timeline: str


class WeeklyTarget(BaseModel):
    week: int
    target: int
    actions: list[str]
    expected_source: str


class CustomerMilestone(BaseModel):
    customers: int
    celebration: str
    signal: str


class First100Customers(BaseModel):
    overview: str
    target_segment: str
    channels: list[CustomerChannel]
    incentive_strategy: str
    referral_program: str
    weekly_targets: list[WeeklyTarget]
    milestones: list[CustomerMilestone]
    risks: list[str]
    tips: list[str]


class LaunchHubResponse(BaseModel):
    product_hunt_checklist: ProductHuntChecklist
    app_store_checklist: AppStoreChecklist
    beta_launch_plan: BetaLaunchPlan
    first_100_customers: First100Customers


# ─── Collaboration Hub ────────────────────────────────────────────────────────

class TeamCreateRequest(BaseModel):
    name: str = ""
    description: str = ""


class TeamMember(BaseModel):
    user_id: str = ""
    email: str = ""
    name: str = ""
    role: str = "viewer"
    joined_at: str = ""


class TeamResponse(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    owner_id: str = ""
    invite_code: str = ""
    members: list[TeamMember] = []
    created_at: str = ""


class TeamInviteRequest(BaseModel):
    team_id: str = ""
    email: str = ""


class TeamJoinRequest(BaseModel):
    invite_code: str = ""


class TeamAddAnalysisRequest(BaseModel):
    team_id: str = ""
    report_type: str = ""
    report_id: str = ""
    title: str = ""


class CommentCreateRequest(BaseModel):
    target_type: str = ""
    target_id: str = ""
    section: str = ""
    text: str = ""


class CommentResponse(BaseModel):
    id: str = ""
    target_type: str = ""
    target_id: str = ""
    section: str = ""
    text: str = ""
    user_id: str = ""
    user_name: str = ""
    created_at: str = ""
    updated_at: str = ""


class ExportRequest(BaseModel):
    report_type: str = ""
    report_data: dict = {}


class ExportResponse(BaseModel):
    content: str = ""
    format: str = ""
    filename: str = ""


# ─── Saved Ideas (Centralized Idea Registry) ──────────────────────────────────

class SavedIdeaCreate(BaseModel):
    title: str = ""
    description: str = ""
    idea_data: dict = {}
    analysis: dict = {}
    plan: dict = {}
    profile: dict = {}


class SavedIdeaResponse(BaseModel):
    id: str = ""
    user_id: str = ""
    title: str = ""
    description: str = ""
    idea_data: dict = {}
    analysis: dict = {}
    plan: dict = {}
    profile: dict = {}
    hub_reports: dict = {}
    created_at: str = ""
    updated_at: str = ""


class SavedIdeasListResponse(BaseModel):
    ideas: list = []


class SavedIdeaUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    idea_data: dict | None = None
    analysis: dict | None = None
    plan: dict | None = None
    profile: dict | None = None
    hub_reports: dict | None = None
