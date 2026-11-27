"""Compare one expected BSC contract call with one saved wallet observation."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_REPORT_BYTES = 16_384
MAX_TIMESTAMP = 253_402_300_799

Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
Calldata = Annotated[str, Field(pattern=r"^0x(?:[0-9a-fA-F]{2}){4,2048}$")]
Wei = Annotated[int, Field(ge=0, le=2**256 - 1)]
Timestamp = Annotated[int, Field(ge=0, le=MAX_TIMESTAMP)]
WalletSurface = Literal["binance_dapp_browser", "binance_ai_pro", "binance_agentic_cli"]


class ExpectedCall(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    chain_id: Annotated[int, Field(ge=56, le=56)]
    surface: WalletSurface
    sender: Address
    target: Address
    calldata: Calldata
    native_value_wei: Annotated[int, Field(ge=0, le=0)]
    requires_wallet_fee: bool
    requires_app_confirmation: bool
    max_observation_age_seconds: Annotated[int, Field(gt=0)]


class WalletObservation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    evidence: Literal["FIXTURE", "USER_REPORTED"]
    surface: WalletSurface | Literal["unknown"]
    stage: Literal["wallet_selected", "preview_passed", "preview_blocked", "unknown"]
    observed_at: Timestamp | None = None
    preview_expires_at: Timestamp | None = None
    chain_id: Annotated[int, Field(gt=0)] | None = None
    sender: Address | None = None
    target: Address | None = None
    calldata: Calldata | None = None
    native_value_wei: Wei | None = None
    wallet_fee_wei: Wei | None = None
    app_confirmation_required: bool | None = None
    risk_findings: Literal["clear", "warning"] | None = None


class CompatibilityCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(ge=1, le=1)]
    expected: ExpectedCall
    observation: WalletObservation


def _compare(expected, observed):
    if observed is None:
        return "UNKNOWN"
    if isinstance(expected, str):
        expected, observed = expected.lower(), observed.lower()
    return "MATCH" if expected == observed else "MISMATCH"


def check_compatibility(case: CompatibilityCase, now: int) -> dict:
    """Report only evidence scoped to this action, without granting permission."""
    if type(now) is not int or not 0 <= now <= MAX_TIMESTAMP:
        raise ValueError("Invalid evaluation time")
    expected, observation = case.expected, case.observation
    checks = {
        name: _compare(getattr(expected, name), getattr(observation, name))
        for name in ("chain_id", "sender")
    }
    preview_observed = observation.stage in ("preview_passed", "preview_blocked")
    checks.update({
        name: _compare(getattr(expected, name), getattr(observation, name)) if preview_observed else "UNKNOWN"
        for name in ("target", "calldata", "native_value_wei")
    })
    reported_surface = None if observation.surface == "unknown" else observation.surface
    checks["wallet_surface"] = _compare(expected.surface, reported_surface)
    checks["simulation"] = "PASSED" if observation.stage == "preview_passed" else "UNKNOWN"
    if observation.observed_at is None:
        checks["observation_age"] = "UNKNOWN"
    else:
        age = now - observation.observed_at
        if age < 0:
            checks["observation_age"] = "FUTURE"
        elif age > expected.max_observation_age_seconds:
            checks["observation_age"] = "STALE"
        else:
            checks["observation_age"] = "FRESH"

    checks["preview_expiry"] = "UNKNOWN"
    if observation.preview_expires_at is not None:
        checks["preview_expiry"] = "EXPIRED" if now >= observation.preview_expires_at else "FRESH"
    checks["wallet_fee"] = "UNKNOWN" if expected.requires_wallet_fee else "NOT_REQUIRED"
    checks["app_confirmation"] = "UNKNOWN" if expected.requires_app_confirmation else "NOT_REQUIRED"
    checks["risk_review"] = "UNKNOWN"
    if observation.stage == "preview_passed":
        if expected.requires_wallet_fee and observation.wallet_fee_wei is not None:
            checks["wallet_fee"] = "MATCH"
        if expected.requires_app_confirmation:
            checks["app_confirmation"] = _compare(True, observation.app_confirmation_required)
        if observation.risk_findings is not None:
            checks["risk_review"] = observation.risk_findings.upper()

    # Wallet selection alone can establish a mismatch. Preview-only fields
    # from a separate or unsupported stage cannot establish compatibility.
    if observation.stage == "preview_blocked":
        result = "BLOCKED_BY_WALLET"
    elif checks["observation_age"] != "FRESH" or (
        observation.stage == "preview_passed" and checks["preview_expiry"] != "FRESH"
    ):
        result = "INCONCLUSIVE"
    elif observation.stage not in ("wallet_selected", "preview_passed"):
        result = "INCONCLUSIVE"
    elif checks["risk_review"] == "WARNING":
        result = "INCONCLUSIVE"
    elif "MISMATCH" in checks.values():
        result = "INCOMPATIBLE"
    elif observation.stage == "preview_passed" and "UNKNOWN" not in checks.values():
        result = "PREVIEW_MATCHED"
    else:
        result = "INCONCLUSIVE"

    return {
        "schema_version": 1,
        "status": result,
        "evidence": observation.evidence,
        "expected_wallet_surface": expected.surface,
        "wallet_surface": observation.surface,
        "reported_stage": observation.stage,
        "observed_at": observation.observed_at,
        "evaluated_at": now,
        "checks": checks,
        "execution_authorized": False,
        "submission_verified": False,
    }
