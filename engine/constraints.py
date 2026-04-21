from pydantic import BaseModel, ConfigDict


class ConstraintPolicy(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    family_safe: bool = False
    low_risk: bool = False
    avoid_premium: bool = False
    value_focused: bool = False
    group_coordination: bool = False
    kids_present: bool = False
    low_mobility: bool = False
    quiet_preferred: bool = False
    slow_pace: bool = False
    high_activity: bool = False
