from typing import List, Optional, Literal

from pydantic import BaseModel, Field


CatalogueFamily = Literal[
    "destination",
    "traveller",
    "timing",
    "budget",
    "intent",
    "activity",
    "transport",
    "accommodation",
    "constraints",
    "calendar",
]


class CatalogueItem(BaseModel):
    family: CatalogueFamily = Field(..., description="Logical grouping of the item")
    key: str = Field(..., description="Machine-readable identifier (snake_case)")
    display_name: str = Field(..., description="Human-readable label")
    description: str = Field(..., description="Clear meaning of the item")
    example_inputs: List[str] = Field(
        default_factory=list,
        description="Example user phrases that map to this item",
    )
    downstream_use: str = Field(
        ...,
        description="How this field is used in itinerary or calendar logic",
    )


destination_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="destination",
        key="destination_fixed",
        display_name="Fixed Destination",
        description="User specifies a clear destination",
        example_inputs=["Naivasha", "Diani", "Maasai Mara"],
        downstream_use="Locks itinerary location",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible",
        display_name="Flexible Destination",
        description="User is open to suggestions",
        example_inputs=["somewhere calm", "a quiet place", "warm place"],
        downstream_use="Triggers recommendation engine",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible_coastal",
        display_name="Flexible Coastal Destination",
        description="User wants a coastal place without naming one",
        example_inputs=["somewhere coastal", "coastal destination"],
        downstream_use="Biases recommendations toward coastal options",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible_beach",
        display_name="Flexible Beach Destination",
        description="User wants a beach place without naming one",
        example_inputs=["beach destination", "somewhere with a beach"],
        downstream_use="Biases recommendations toward beach options",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible_international",
        display_name="Flexible International Destination",
        description="User wants options outside the local country",
        example_inputs=["outside Kenya", "international trip"],
        downstream_use="Marks destination scope as international",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible_near_nairobi",
        display_name="Near Nairobi Destination",
        description="User wants a destination near Nairobi",
        example_inputs=["near Nairobi", "close to Nairobi"],
        downstream_use="Applies proximity bias around Nairobi",
    ),
    CatalogueItem(
        family="destination",
        key="destination_flexible_mountain",
        display_name="Flexible Mountain Destination",
        description="User wants a mountain setting without naming one",
        example_inputs=["mountain escape", "somewhere mountainous"],
        downstream_use="Biases recommendations toward mountain options",
    ),
    CatalogueItem(
        family="destination",
        key="multiple_destinations",
        display_name="Multiple Destinations",
        description="Trip involves more than one location",
        example_inputs=["Naivasha and Nakuru"],
        downstream_use="Split itinerary into segments",
    ),
    CatalogueItem(
        family="destination",
        key="departure_city",
        display_name="Departure City",
        description="Starting location",
        example_inputs=["from Nairobi"],
        downstream_use="Used for transport planning",
    ),
]


traveller_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="traveller",
        key="solo",
        display_name="Solo Traveller",
        description="Single traveller",
        example_inputs=["just me", "solo", "solo retreat"],
        downstream_use="Simplifies logistics",
    ),
    CatalogueItem(
        family="traveller",
        key="couple",
        display_name="Couple",
        description="Two adults travelling together",
        example_inputs=["me and my partner", "with my husband", "with my wife", "couple"],
        downstream_use="Adjust accommodation",
    ),
    CatalogueItem(
        family="traveller",
        key="family",
        display_name="Family",
        description="Adults travelling with children",
        example_inputs=["2 adults and 3 kids"],
        downstream_use="Child-safe planning",
    ),
    CatalogueItem(
        family="traveller",
        key="group",
        display_name="Group",
        description="Multiple unrelated travellers",
        example_inputs=["we are 6 people", "small group", "friends"],
        downstream_use="Group coordination logic",
    ),
    CatalogueItem(
        family="traveller",
        key="large_group",
        display_name="Large Group",
        description="Large travelling party",
        example_inputs=["large group", "big group"],
        downstream_use="Adds group capacity and coordination pressure",
    ),
    CatalogueItem(
        family="traveller",
        key="team",
        display_name="Team",
        description="Work or organized team travelling together",
        example_inputs=["team", "work team"],
        downstream_use="Applies team coordination logic",
    ),
    CatalogueItem(
        family="traveller",
        key="multi_generational_family",
        display_name="Multi-Generational Family",
        description="Family includes multiple age groups",
        example_inputs=["multi-generational", "big family"],
        downstream_use="Adds accessibility and mixed-age planning pressure",
    ),
]


timing_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="timing",
        key="exact_date",
        display_name="Exact Date",
        description="Specific date provided",
        example_inputs=["April 25"],
        downstream_use="Locks schedule",
    ),
    CatalogueItem(
        family="timing",
        key="date_range",
        display_name="Date Range",
        description="Start and end dates provided",
        example_inputs=["25th to 27th"],
        downstream_use="Multi-day itinerary",
    ),
    CatalogueItem(
        family="timing",
        key="weekend_trip",
        display_name="Weekend Trip",
        description="Trip planned over a weekend",
        example_inputs=["next weekend", "this weekend", "long weekend"],
        downstream_use="Weekend optimization",
    ),
    CatalogueItem(
        family="timing",
        key="flexible_timing",
        display_name="Flexible Timing",
        description="No strict dates",
        example_inputs=["anytime next week"],
        downstream_use="Calendar optimization",
    ),
    CatalogueItem(
        family="timing",
        key="timing_relative_next_week",
        display_name="Next Week",
        description="Trip timing is next week",
        example_inputs=["upcoming week"],
        downstream_use="Marks timing as relative upcoming week",
    ),
    CatalogueItem(
        family="timing",
        key="timing_relative_next_month",
        display_name="Next Month",
        description="Trip timing is next month",
        example_inputs=["next month"],
        downstream_use="Marks timing as relative upcoming month",
    ),
    CatalogueItem(
        family="timing",
        key="timing_holiday_period",
        display_name="Holiday Period",
        description="Trip timing is tied to holidays",
        example_inputs=["holidays", "next public holiday"],
        downstream_use="Marks timing as holiday-dependent",
    ),
    CatalogueItem(
        family="timing",
        key="timing_duration_short",
        display_name="Short Duration",
        description="Short trip duration is provided",
        example_inputs=["3-day escape", "two nights"],
        downstream_use="Marks trip as short-duration planning",
    ),
    CatalogueItem(
        family="timing",
        key="timing_month_named",
        display_name="Named Month",
        description="Timing is a named month",
        example_inputs=["December"],
        downstream_use="Marks timing as month-level precision",
    ),
    CatalogueItem(
        family="timing",
        key="timing_early_month",
        display_name="Early Month",
        description="Timing is early in a named month",
        example_inputs=["early June"],
        downstream_use="Marks timing as partial month precision",
    ),
    CatalogueItem(
        family="timing",
        key="timing_first_week",
        display_name="First Week",
        description="Timing is the first week of a month",
        example_inputs=["first week of May"],
        downstream_use="Marks timing as week-level month precision",
    ),
    CatalogueItem(
        family="timing",
        key="timing_quarter_fuzzy",
        display_name="Fuzzy Quarter Timing",
        description="Timing is a fuzzy quarter or season window",
        example_inputs=["mid-year", "this quarter"],
        downstream_use="Requires timing clarification before fixed planning",
    ),
]


budget_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="budget",
        key="budget_total",
        display_name="Total Budget",
        description="Overall trip budget",
        example_inputs=["KES 50,000"],
        downstream_use="Constraint for all selections",
    ),
    CatalogueItem(
        family="budget",
        key="budget_per_person",
        display_name="Budget Per Person",
        description="Budget split per traveller",
        example_inputs=["10k per person"],
        downstream_use="Cost distribution",
    ),
    CatalogueItem(
        family="budget",
        key="budget_flexible",
        display_name="Flexible Budget",
        description="Budget not fixed",
        example_inputs=["not sure about budget", "flexible budget"],
        downstream_use="Allow optimization",
    ),
    CatalogueItem(
        family="budget",
        key="budget_low",
        display_name="Low Budget",
        description="User wants low-cost planning",
        example_inputs=["low budget", "strict budget"],
        downstream_use="Applies cost-sensitive constraints",
    ),
    CatalogueItem(
        family="budget",
        key="budget_value",
        display_name="Value Budget",
        description="User wants good value without overspending",
        example_inputs=[
            "budget-friendly",
            "affordable",
            "cost-friendly",
            "good value",
            "without overspending",
        ],
        downstream_use="Prioritizes value and cost checks",
    ),
    CatalogueItem(
        family="budget",
        key="budget_moderate",
        display_name="Moderate Budget",
        description="User wants comfortable but controlled spending",
        example_inputs=["moderate budget", "comfortable but not pricey"],
        downstream_use="Applies balanced budget constraints",
    ),
    CatalogueItem(
        family="budget",
        key="budget_premium",
        display_name="Premium Budget",
        description="User is open to premium spending",
        example_inputs=["premium", "luxury", "high-end", "elevated", "generous budget"],
        downstream_use="Allows premium allocation",
    ),
    CatalogueItem(
        family="budget",
        key="budget_premium_reasonable",
        display_name="Premium But Reasonable",
        description="User wants premium choices with cost discipline",
        example_inputs=["premium but reasonable"],
        downstream_use="Balances premium options with cost checks",
    ),
]


intent_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="intent",
        key="relaxation",
        display_name="Relaxation",
        description="Calm and restful trip",
        example_inputs=["just chill", "relax", "relaxing", "slow, restful"],
        downstream_use="Low activity planning",
    ),
    CatalogueItem(
        family="intent",
        key="adventure",
        display_name="Adventure",
        description="Active and thrilling trip",
        example_inputs=["hiking", "quad biking", "adventurous", "thrilling"],
        downstream_use="High activity planning",
    ),
    CatalogueItem(
        family="intent",
        key="family_outing",
        display_name="Family Outing",
        description="Family-focused experience",
        example_inputs=["kids trip"],
        downstream_use="Child-friendly filtering",
    ),
    CatalogueItem(
        family="intent",
        key="romantic",
        display_name="Romantic",
        description="Romantic or intimate trip",
        example_inputs=["romantic", "cozy, intimate"],
        downstream_use="Biases plan toward intimate pacing",
    ),
    CatalogueItem(
        family="intent",
        key="celebration",
        display_name="Celebration",
        description="Trip marks a celebration",
        example_inputs=["celebratory", "mood-lifting"],
        downstream_use="Adds celebration-oriented experience bias",
    ),
    CatalogueItem(
        family="intent",
        key="peaceful",
        display_name="Peaceful",
        description="Quiet and peaceful trip",
        example_inputs=["peaceful", "calm, quiet"],
        downstream_use="Biases plan toward quiet low-friction options",
    ),
    CatalogueItem(
        family="intent",
        key="exploratory",
        display_name="Exploratory",
        description="Trip is for exploration",
        example_inputs=["exploratory", "exciting"],
        downstream_use="Biases plan toward discovery and variety",
    ),
    CatalogueItem(
        family="intent",
        key="wellness",
        display_name="Wellness",
        description="Trip focuses on wellness",
        example_inputs=["wellness-focused", "reflective solo retreat"],
        downstream_use="Biases plan toward restorative choices",
    ),
    CatalogueItem(
        family="intent",
        key="social",
        display_name="Social",
        description="Trip should be lively and social",
        example_inputs=["lively and social", "fun and active"],
        downstream_use="Biases plan toward group-friendly activities",
    ),
]


activity_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="activity",
        key="wildlife",
        display_name="Wildlife",
        description="Game drives and safaris",
        example_inputs=["see animals"],
        downstream_use="Park selection",
    ),
    CatalogueItem(
        family="activity",
        key="water",
        display_name="Water Activities",
        description="Lake or ocean activities",
        example_inputs=["boat ride"],
        downstream_use="Water-based filtering",
    ),
    CatalogueItem(
        family="activity",
        key="scenic",
        display_name="Scenic Relaxation",
        description="Views and calm settings",
        example_inputs=["nice views", "nature-focused"],
        downstream_use="Location scoring",
    ),
]


transport_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="transport",
        key="self_drive",
        display_name="Self Drive",
        description="User drives themselves",
        example_inputs=["I’ll drive"],
        downstream_use="Route planning",
    ),
    CatalogueItem(
        family="transport",
        key="private_transfer",
        display_name="Private Transfer",
        description="Driver provided",
        example_inputs=["need a driver"],
        downstream_use="Vehicle booking",
    ),
]


accommodation_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="accommodation",
        key="day_trip",
        display_name="Day Trip",
        description="No overnight stay",
        example_inputs=["just one day"],
        downstream_use="Skip accommodation",
    ),
    CatalogueItem(
        family="accommodation",
        key="hotel",
        display_name="Hotel Stay",
        description="Standard hotel",
        example_inputs=["book hotel"],
        downstream_use="Hotel selection",
    ),
    CatalogueItem(
        family="accommodation",
        key="villa",
        display_name="Villa Stay",
        description="Private villa",
        example_inputs=["private place"],
        downstream_use="Premium allocation",
    ),
]


constraints_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="constraints",
        key="with_kids",
        display_name="Travelling with Kids",
        description="Children included",
        example_inputs=["with kids"],
        downstream_use="Safety filters",
    ),
    CatalogueItem(
        family="constraints",
        key="avoid_long_drives",
        display_name="Avoid Long Drives",
        description="Limit travel distance",
        example_inputs=["not too far"],
        downstream_use="Distance constraint",
    ),
]


calendar_catalogue: List[CatalogueItem] = [
    CatalogueItem(
        family="calendar",
        key="calendar_check_required",
        display_name="Calendar Check Required",
        description="Check availability before planning",
        example_inputs=["check my schedule"],
        downstream_use="Calendar validation step",
    ),
    CatalogueItem(
        family="calendar",
        key="schedule_conflict_check",
        display_name="Conflict Check",
        description="Ensure no overlap",
        example_inputs=["make sure I'm free"],
        downstream_use="Conflict detection",
    ),
    CatalogueItem(
        family="calendar",
        key="best_time_suggestion",
        display_name="Best Time Suggestion",
        description="Suggest optimal timing",
        example_inputs=["when is best"],
        downstream_use="Optimization engine",
    ),
]


FULL_CATALOGUE = (
    destination_catalogue
    + traveller_catalogue
    + timing_catalogue
    + budget_catalogue
    + intent_catalogue
    + activity_catalogue
    + transport_catalogue
    + accommodation_catalogue
    + constraints_catalogue
    + calendar_catalogue
)
